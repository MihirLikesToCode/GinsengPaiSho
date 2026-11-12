"""Self-play training loop for RLBot - v1 of the reinforcement learning agent.
See RL_GAME_PLAN.md for the full design and reasoning. This implements steps 3
and 4 of the "Rollout order": a working self-play loop with REINFORCE + a value
baseline, and an evaluation harness against TestBot's random play.

v1 milestone: win-rate vs. TestBot climbing above 50%. That's the bar to clear
before scaling up (step 5) or upgrading the algorithm (step 6) - see the plan.

Most training episodes are pure self-play (RLBot vs. RLBot, both sharing the
one network being trained), but a fraction mix in TestBot as one side instead -
see TESTBOT_MIX_PROB and RL_GAME_PLAN.md's "Lessons learned". Pure self-play
alone was found to let the policy specialize at beating an evolving version of
itself without that generalizing to beating a genuinely different opponent.

A further fraction mix in a *frozen past checkpoint* of the network itself
instead (PAST_CHECKPOINT_MIX_PROB) - a fixed-difficulty opponent that's
neither a moving target (live self-play) nor capped at "beats random play"
(TestBot). See RL_GAME_PLAN.md's "past-checkpoint opponent pool" section.

evaluateAgainstLadder() is a separate, much-less-frequent evaluation against
a handful of *fixed* past checkpoints (LADDER_EPISODES) - unlike evaluate()
(vs. TestBot), this doesn't saturate once the policy clearly surpasses a weak
opponent, since the ladder opponents are genuinely-capable past selves. See
RL_GAME_PLAN.md's "oscillation" investigation for why evaluate() alone
stopped being a trustworthy progress signal.
"""

import argparse
import os
import random
from typing import Literal, TypeGuard

import torch
import torch.nn.functional as F
import torch.optim as optim

from BoardEncoding import lotusProgressPotential
from BotTest import TestBot
from HeadlessGame import HeadlessGame
from Player import BotPlayer
from PolicyValueNetwork import PolicyValueNetwork
from RLBot import RLBot, Transition

# Recalibrated from a real measurement (see RL_GAME_PLAN.md's "Lessons learned"):
# 15 games of random TestBot-vs-TestBot play had a median length of 1137 turns
# and a 93rd-percentile of ~2071 (one outlier at 4433) - nothing like the old
# MAX_TURNS=300, which every single one of those games would have blown through
# unresolved. GAMMA also had to move with it: with episodes this long, the old
# 0.99 decays by gamma**distance-from-the-end, so by ~1000 steps back it's
# ~0.00004 - the terminal reward would be mathematically invisible to anything
# but the last ~100-200 moves. 0.999 keeps >10% credit out to ~2300 steps,
# matching the horizon we actually measured.
GAMMA = 0.999
SHAPING_COEFF = 0.05
# Bumped further after the Temple-exclusivity bug fix: a 10-game regression
# batch surfaced a couple of legitimate games resolving at ~3300-3500 turns,
# meaning a meaningful fraction were still getting cut off at 3000. 0.999**4000
# ~= 0.018, still enough residual credit to be useful at this horizon.
MAX_TURNS = 4000
LEARNING_RATE = 1e-3
VALUE_LOSS_COEFF = 0.5
ENTROPY_COEFF = 0.01

# Fraction of training episodes that pit the RLBot against TestBot (random
# play) instead of against another copy of itself. A starting value, not a
# carefully-tuned one - high enough to give a real, direct incentive to
# generalize beyond beating its own reflection, while staying a minority so
# self-play's main benefit (an opponent that gets more sophisticated over
# time, which TestBot never does) isn't thrown away.
TESTBOT_MIX_PROB = 0.3

# Fraction of training episodes that pit the RLBot against a frozen past
# checkpoint of itself (see _availablePastCheckpoints/_loadFrozenNetwork)
# instead of the live network or TestBot. Also a starting guess. Carved out of
# the self-play fraction (not TESTBOT_MIX_PROB, which is already validated) -
# self-play drops from 0.7 to 0.4 of episodes. Motivation: a ~13,000-episode
# checkpoints_v3 run oscillated around the same win-rate for ~10,000 episodes
# after an early plateau, with no capability regression (confirmed via direct
# head-to-head between the best- and worst-scoring checkpoints: a dead-even
# 50/50). Pure self-play (even with TestBot mixed in) still spends most of
# training chasing a live, ever-changing mirror of itself - the same dynamic
# that caused the checkpoints_v2 collapse, just not severely enough to show up
# as a clean decline this time. A frozen past self is a fixed-difficulty
# opponent: harder than TestBot, but not a moving target. See
# RL_GAME_PLAN.md's "past-checkpoint opponent pool" section.
PAST_CHECKPOINT_MIX_PROB = 0.3

# Checkpoints and the learning-curve log live outside code/ so they don't get
# mixed in with source files - see .gitignore (they're binary/generated, not
# something to commit).
CHECKPOINT_DIR = os.path.join(os.path.dirname(__file__), "..", "checkpoints")
CHECKPOINT_PATH = os.path.join(CHECKPOINT_DIR, "latest.pt")
LOG_PATH = os.path.join(CHECKPOINT_DIR, "training_log.csv")
LADDER_LOG_PATH = os.path.join(CHECKPOINT_DIR, "ladder_log.csv")

# latest.pt is overwritten every eval, so a long run can't roll back to an
# earlier point or compare checkpoints side-by-side once it's moved on. Every
# MILESTONE_EVERY episodes, also keep a numbered snapshot that's never
# overwritten. These also double as both the past-checkpoint opponent pool
# (any of them can be sampled as a training opponent) and the pool
# LADDER_EPISODES is drawn from.
MILESTONE_EVERY = 1000

# Fixed reference opponents for evaluateAgainstLadder() - deliberately never
# changed once chosen, so they stay a stable ruler. Spread across the
# checkpoints_v3 lineage (early/mid/late) rather than clustered. A checkpoint
# from a run too short to have reached one of these yet just skips it (see
# evaluateAgainstLadder) - the list doesn't need to shrink for early runs.
#
# Deliberately NOT relative to CHECKPOINT_DIR: these are frozen reference
# points from the checkpoints_v3 lineage specifically, independent of
# wherever the live run (any lineage after v3) is saving its own milestones.
# A bug caught in checkpoints_v4's first run: this used to be built from
# CHECKPOINT_DIR, so every run's ladder eval silently checked for its own
# nonexistent episode_3000/6000/9000/12000.pt instead of these, and found
# nothing every time - see RL_GAME_PLAN.md's "evaluation ladder" section.
LADDER_CHECKPOINT_DIR = os.path.join(os.path.dirname(__file__), "..", "checkpoints_v3")
LADDER_EPISODES = [3000, 6000, 9000, 12000]

Color = Literal["white", "black"]
Result = Literal["white", "black", "draw", "turn_limit"]

# See "Reward design" in RL_GAME_PLAN.md: sparse terminal reward, turn_limit
# treated exactly like a draw (not partial credit for whoever's closer).
TERMINAL_REWARD: dict[Result, dict[Color, float]] = {
    "white": {"white": 1.0, "black": -1.0},
    "black": {"white": -1.0, "black": 1.0},
    "draw": {"white": 0.0, "black": 0.0},
    "turn_limit": {"white": 0.0, "black": 0.0},
}


# Frozen past-checkpoint networks, loaded once and reused - reloading from
# disk every episode they're sampled would be wasteful, and nothing about a
# frozen checkpoint's weights ever changes mid-run.
_frozenNetworkCache: dict[str, PolicyValueNetwork] = {}


def _loadFrozenNetwork(path: str) -> PolicyValueNetwork:
    if path not in _frozenNetworkCache:
        network = PolicyValueNetwork()
        checkpoint = torch.load(path, map_location="cpu")
        network.load_state_dict(checkpoint["networkState"])
        network.eval()
        _frozenNetworkCache[path] = network
    return _frozenNetworkCache[path]


def _availablePastCheckpoints() -> list[str]:
    """Milestone checkpoints already on disk for this run's CHECKPOINT_DIR -
    the pool of frozen past-self training opponents. Grows for free as
    MILESTONE_EVERY saves new ones; no separate bookkeeping needed."""
    if not os.path.isdir(CHECKPOINT_DIR):
        return []
    return [
        os.path.join(CHECKPOINT_DIR, name)
        for name in os.listdir(CHECKPOINT_DIR)
        if name.startswith("episode_") and name.endswith(".pt")
    ]


def makeTrainingMatchup(network: PolicyValueNetwork) -> tuple[BotPlayer, BotPlayer]:
    """Decides one training episode's matchup: pure self-play most of the
    time, or the live RLBot against TestBot (TESTBOT_MIX_PROB) or against a
    frozen past checkpoint of itself (PAST_CHECKPOINT_MIX_PROB) otherwise -
    see the module docstring for why.

    Returns:
        tuple[BotPlayer, BotPlayer]: (whitePlayer, blackPlayer). Exactly one
          side is always an RLBot sharing `network`'s live weights (the thing
          actually being trained); the other is either a second live RLBot
          (self-play), a TestBot, or an RLBot wrapping a frozen past
          checkpoint's network - see playSelfPlayEpisode's trajectory-recording
          guard, which only trains on whichever side is `network` itself.
    """
    roll = random.random()

    if roll < TESTBOT_MIX_PROB:
        rlColor: Color = random.choice(["white", "black"])
        rlBot = RLBot(rlColor, network)
        testBot = TestBot("black" if rlColor == "white" else "white")
        return (rlBot, testBot) if rlColor == "white" else (testBot, rlBot)

    if roll < TESTBOT_MIX_PROB + PAST_CHECKPOINT_MIX_PROB:
        pastCheckpoints = _availablePastCheckpoints()
        if pastCheckpoints:
            pastNetwork = _loadFrozenNetwork(random.choice(pastCheckpoints))
            rlColor: Color = random.choice(["white", "black"])
            liveBot = RLBot(rlColor, network)
            # Sampling (not greedy), like a live self-play opponent - a
            # frozen-but-deterministic opponent would only ever play one line.
            pastBot = RLBot("black" if rlColor == "white" else "white", pastNetwork)
            return (liveBot, pastBot) if rlColor == "white" else (pastBot, liveBot)
        # No milestones saved yet (e.g. early in a fresh run) - fall through
        # to self-play for this episode instead.

    return RLBot("white", network), RLBot("black", network)


def _isLiveRLBot(bot: BotPlayer, network: PolicyValueNetwork) -> TypeGuard[RLBot]:
    """True if `bot` is an RLBot wired to the actual network being trained -
    as opposed to TestBot (not network-driven at all) or an RLBot wrapping a
    frozen past checkpoint's network (see PAST_CHECKPOINT_MIX_PROB) - either
    of which has nothing to train on, since only `network`'s weights are
    registered with the optimizer."""
    return isinstance(bot, RLBot) and bot.network is network


def playSelfPlayEpisode(
    whiteBot: BotPlayer,
    blackBot: BotPlayer,
    network: PolicyValueNetwork,
    maxTurns: int = MAX_TURNS,
) -> tuple[list[Transition], list[Transition], Result]:
    """Plays one self-play game, applying reward shaping and the terminal reward
    to each bot's trajectory along the way. Mirrors HeadlessGame.playEpisodeCapped,
    but with reward bookkeeping woven in around each step (HeadlessGame itself
    is left untouched - see RL_GAME_PLAN.md's "Self-play loop").

    `network` is the live network actually being trained this run - needed to
    tell it apart from a frozen past-checkpoint opponent (see
    PAST_CHECKPOINT_MIX_PROB), which is also an RLBot but shouldn't be trained
    on.

    Returns:
        tuple[list[Transition], list[Transition], Result]: (whiteTrajectory,
          blackTrajectory, result). Either list is empty if that seat wasn't
          played by the live network this episode (see makeTrainingMatchup) -
          there's nothing to train on for a side that never used it.
    """
    hGame = HeadlessGame(whiteBot, blackBot)
    hGame._resetGameState()

    result: Result = "turn_limit"
    for _ in range(maxTurns):
        actingColor: Color = hGame.turn
        actingBot = whiteBot if actingColor == "white" else blackBot

        potentialBefore = lotusProgressPotential(hGame.board, actingColor)

        decision = actingBot.decideTurn(hGame.board)
        if decision is None:
            result = "draw"
            break

        hGame._applyBotDecision(decision)
        hGame._resolveHeadlessAbility()

        # TestBot and a frozen past-checkpoint opponent (see
        # makeTrainingMatchup) aren't driven by the live network, so they have
        # no trajectory to attach a shaping reward to.
        if _isLiveRLBot(actingBot, network):
            potentialAfter = lotusProgressPotential(hGame.board, actingColor)
            shapingReward = SHAPING_COEFF * (GAMMA * potentialAfter - potentialBefore)
            actingBot.recordPendingReward(shapingReward)

        outcome = hGame._getGameResult()
        if outcome is not None:
            result = outcome
            break

    whiteTrajectory = whiteBot.popTrajectory() if _isLiveRLBot(whiteBot, network) else []
    blackTrajectory = blackBot.popTrajectory() if _isLiveRLBot(blackBot, network) else []

    if whiteTrajectory:
        whiteTrajectory[-1].reward += TERMINAL_REWARD[result]["white"]
    if blackTrajectory:
        blackTrajectory[-1].reward += TERMINAL_REWARD[result]["black"]

    return whiteTrajectory, blackTrajectory, result


def _computeReturns(trajectory: list[Transition], gamma: float) -> list[float]:
    """Backward discounted-return pass: G_t = r_t + gamma * G_{t+1}."""
    returns: list[float] = []
    discountedReturn = 0.0
    for transition in reversed(trajectory):
        discountedReturn = transition.reward + gamma * discountedReturn
        returns.insert(0, discountedReturn)
    return returns


def _trajectoryLoss(trajectory: list[Transition]) -> torch.Tensor | None:
    """Computes the REINFORCE-with-baseline loss for a single player's
    trajectory from one episode. Returns None if the trajectory was empty.
    """
    if not trajectory:
        return None

    returns = torch.tensor(_computeReturns(trajectory, GAMMA), dtype=torch.float32)
    logProbs = torch.stack([t.logProb for t in trajectory])
    values = torch.stack([t.value for t in trajectory])
    entropies = torch.stack([t.entropy for t in trajectory])

    # The value head is the baseline: it reduces how noisy the policy gradient
    # is by only reinforcing actions that did better than expected, rather than
    # every action in a won game and none in a lost one.
    advantages = returns - values.detach()

    # Tried switching this to .sum() (textbook policy-gradient is a sum over the
    # trajectory) on the theory that .mean() was diluting the gradient on these
    # long (1000-4000 step) episodes. Verified empirically against a 20-episode
    # test and it made no measurable difference - entropy barely moved either
    # way (see RL_GAME_PLAN.md's "Lessons learned"). Root cause: Adam normalizes
    # each update by a running estimate of that gradient's own magnitude, so
    # it's close to invariant to a constant rescaling of the loss like this.
    # Left as .mean() (the tested, stable config) - the actual lever that
    # matters is just running far more episodes/updates.
    policyLoss = -(logProbs * advantages).mean()
    valueLoss = F.mse_loss(values, returns)
    entropyBonus = entropies.mean()  # encourages continued exploration

    return policyLoss + VALUE_LOSS_COEFF * valueLoss - ENTROPY_COEFF * entropyBonus


def trainOnEpisode(
    network: PolicyValueNetwork,
    optimizer: optim.Optimizer,
    whiteTrajectory: list[Transition],
    blackTrajectory: list[Transition],
) -> float:
    """Runs one REINFORCE-with-baseline update using both players' trajectories
    from a single episode. Both bots share the same network weights, so their
    losses must be combined into a single backward()/step() call - doing two
    separate ones would have the first step() mutate weights that the second
    trajectory's stored computation graph still refers to (an in-place-modified-
    variable autograd error). Returns the combined loss value (0.0 if both
    trajectories were empty).
    """
    losses = [
        loss
        for loss in (_trajectoryLoss(whiteTrajectory), _trajectoryLoss(blackTrajectory))
        if loss is not None
    ]
    if not losses:
        return 0.0

    totalLoss = torch.stack(losses).sum()

    optimizer.zero_grad()
    totalLoss.backward()
    optimizer.step()

    return float(totalLoss.item())


def saveCheckpoint(
    network: PolicyValueNetwork,
    optimizer: optim.Optimizer,
    episode: int,
    path: str | None = None,
) -> str:
    """Saves the network + optimizer state to `path` (CHECKPOINT_PATH by
    default), overwriting whatever was there before. `optimizer.state_dict()`
    is saved too (not just the network's weights) so a resumed run picks up
    Adam's per-weight step-size history instead of restarting it from scratch.

    Returns:
        str: the path saved to.
    """
    path = path or CHECKPOINT_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    torch.save(
        {
            "episode": episode,
            "networkState": network.state_dict(),
            "optimizerState": optimizer.state_dict(),
        },
        path,
    )
    return path


def loadCheckpoint(
    network: PolicyValueNetwork, optimizer: optim.Optimizer, path: str
) -> int:
    """Loads a checkpoint in place into `network`/`optimizer`.

    Returns:
        int: the episode number it was saved at, so a resumed run can continue
          numbering from there instead of restarting at 1.
    """
    checkpoint = torch.load(path, map_location="cpu")
    network.load_state_dict(checkpoint["networkState"])
    optimizer.load_state_dict(checkpoint["optimizerState"])
    return checkpoint["episode"]


def _logEvaluation(episode: int, result: Result, winRate: float) -> None:
    """Appends one row to the learning-curve CSV, creating it (with a header)
    on the first call. Kept dead simple on purpose - it's a small CSV you can
    load with pandas/plot directly, no dependency on anything beyond the
    standard library.
    """
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    isNewFile = not os.path.exists(LOG_PATH)
    with open(LOG_PATH, "a") as logFile:
        if isNewFile:
            logFile.write("episode,last_result,win_rate\n")
        logFile.write(f"{episode},{result},{winRate:.4f}\n")


def evaluate(network: PolicyValueNetwork, nGames: int = 20) -> float:
    """Plays nGames of a greedy RLBot vs. a random TestBot, alternating colors.

    Returns:
        float: the RLBot's win rate (a draw/turn_limit counts as half a win).
          Games that hit the rare engine crash (see RL_GAME_PLAN.md's "Lessons
          learned") are excluded from both the numerator and denominator rather
          than counted as a loss/draw, so they don't bias the measurement.
    """
    wins = 0.0
    completedGames = 0
    for i in range(nGames):
        rlColor: Color = "white" if i % 2 == 0 else "black"
        otherColor: Color = "black" if rlColor == "white" else "white"

        rlBot = RLBot(rlColor, network, greedy=True)
        randomBot = TestBot(otherColor)
        whitePlayer = rlBot if rlColor == "white" else randomBot
        blackPlayer = rlBot if rlColor == "black" else randomBot

        try:
            result = HeadlessGame(whitePlayer, blackPlayer).playEpisodeCapped(
                maxTurns=MAX_TURNS
            )
        except Exception as exc:
            print(f"  eval game crashed ({type(exc).__name__}: {exc}) - skipping")
            continue

        completedGames += 1
        if result == rlColor:
            wins += 1.0
        elif result in ("draw", "turn_limit"):
            wins += 0.5

    return wins / completedGames if completedGames else 0.0


def headToHead(
    networkA: PolicyValueNetwork, networkB: PolicyValueNetwork, nGames: int = 20
) -> float:
    """Plays nGames of sampled RLBot(networkA) vs. sampled RLBot(networkB),
    alternating colors - the same shape as evaluate(), just with a second
    network instead of TestBot as the opponent.

    Deliberately *not* greedy on both sides: two fully deterministic policies
    play the exact same game every time a given color assignment repeats, so
    with only 2 distinct color assignments, nGames can't average out
    anything - and if that one deterministic game happens to loop forever
    (confirmed happening for a real checkpoints_v4-vs-checkpoints_v3 pair:
    every single greedy-vs-greedy game hit the turn limit, while sampled play
    between the same two networks resolved decisively 7/8 times), the result
    is a meaningless, structurally-forced ~0.5 regardless of actual skill
    gap. Sampling reintroduces per-game variation so nGames games are
    actually nGames distinct trials. See RL_GAME_PLAN.md's "evaluation
    ladder" section.

    Returns:
        float: networkA's win rate (a draw/turn_limit counts as half a win).
    """
    wins = 0.0
    completedGames = 0
    for i in range(nGames):
        aColor: Color = "white" if i % 2 == 0 else "black"
        bColor: Color = "black" if aColor == "white" else "white"

        botA = RLBot(aColor, networkA, greedy=False)
        botB = RLBot(bColor, networkB, greedy=False)
        whitePlayer = botA if aColor == "white" else botB
        blackPlayer = botB if aColor == "white" else botA

        try:
            result = HeadlessGame(whitePlayer, blackPlayer).playEpisodeCapped(
                maxTurns=MAX_TURNS
            )
        except Exception as exc:
            print(f"  ladder game crashed ({type(exc).__name__}: {exc}) - skipping")
            continue

        completedGames += 1
        if result == aColor:
            wins += 1.0
        elif result in ("draw", "turn_limit"):
            wins += 0.5

    return wins / completedGames if completedGames else 0.0


def evaluateAgainstLadder(
    network: PolicyValueNetwork, nGames: int = 20
) -> dict[int, float]:
    """Plays `network` head-to-head against each fixed ladder checkpoint in
    LADDER_EPISODES that exists yet in LADDER_CHECKPOINT_DIR (skipping any
    that don't). Unlike evaluate() (vs. TestBot), this
    doesn't saturate once the policy clearly surpasses a weak opponent - the
    ladder opponents are genuinely-capable past selves, so it keeps
    distinguishing real strength. See RL_GAME_PLAN.md's "oscillation"
    investigation for why evaluate() alone stopped being trustworthy on its
    own this deep into a run.

    Returns:
        dict[int, float]: {ladder episode: network's win rate against it}.
    """
    results: dict[int, float] = {}
    for episode in LADDER_EPISODES:
        path = os.path.join(LADDER_CHECKPOINT_DIR, f"episode_{episode}.pt")
        if not os.path.exists(path):
            continue
        opponent = _loadFrozenNetwork(path)
        results[episode] = headToHead(network, opponent, nGames=nGames)
    return results


def _logLadderEvaluation(episode: int, ladderResults: dict[int, float]) -> None:
    """Appends one row to the ladder-eval CSV, creating it (with a header, one
    column per LADDER_EPISODES entry) on the first call. A missing result
    (ladder checkpoint didn't exist yet) is logged as an empty cell."""
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    isNewFile = not os.path.exists(LADDER_LOG_PATH)
    with open(LADDER_LOG_PATH, "a") as logFile:
        if isNewFile:
            header = "episode," + ",".join(
                f"vs_episode_{e}" for e in LADDER_EPISODES
            )
            logFile.write(header + "\n")
        row = [str(episode)] + [
            f"{ladderResults[e]:.4f}" if e in ladderResults else ""
            for e in LADDER_EPISODES
        ]
        logFile.write(",".join(row) + "\n")


def main(
    nEpisodes: int = 2000,
    evalEvery: int = 100,
    evalGames: int = 20,
    ladderEvalEvery: int = MILESTONE_EVERY,
    ladderGames: int = 20,
    resume: bool = False,
) -> None:
    network = PolicyValueNetwork()
    optimizer = optim.Adam(network.parameters(), lr=LEARNING_RATE)

    startEpisode = 1
    if resume and os.path.exists(CHECKPOINT_PATH):
        lastEpisode = loadCheckpoint(network, optimizer, CHECKPOINT_PATH)
        startEpisode = lastEpisode + 1
        print(f"Resumed from {CHECKPOINT_PATH} (was at episode {lastEpisode})")

    endEpisode = startEpisode + nEpisodes - 1
    crashCount = 0
    for episode in range(startEpisode, endEpisode + 1):
        whiteBot, blackBot = makeTrainingMatchup(network)

        try:
            whiteTrajectory, blackTrajectory, result = playSelfPlayEpisode(
                whiteBot, blackBot, network
            )
            trainOnEpisode(network, optimizer, whiteTrajectory, blackTrajectory)
        except Exception as exc:
            # A rare, pre-existing engine bug can occasionally corrupt a game
            # mid-play (see RL_GAME_PLAN.md's "Lessons learned" - still being
            # root-caused). Don't let one bad game take down a multi-hour run;
            # log it and move on. Keep an eye on crashCount in the final
            # summary - if this climbs into the dozens+, that's a sign the bug
            # is more frequent than thought and needs a real fix, not a skip.
            crashCount += 1
            print(
                f"Episode {episode:5d} | CRASHED ({type(exc).__name__}: {exc})"
                " - skipping",
                flush=True,
            )
            continue

        if episode % evalEvery == 0:
            winRate = evaluate(network, nGames=evalGames)
            print(
                f"Episode {episode:5d} | last game result: {result:10s} | "
                f"win-rate vs TestBot: {winRate:.2f}",
                flush=True,
            )
            _logEvaluation(episode, result, winRate)
            savedPath = saveCheckpoint(network, optimizer, episode)
            print(f"  saved checkpoint -> {savedPath}", flush=True)

            if episode % MILESTONE_EVERY == 0:
                milestonePath = os.path.join(
                    CHECKPOINT_DIR, f"episode_{episode}.pt"
                )
                saveCheckpoint(network, optimizer, episode, path=milestonePath)
                print(f"  saved milestone -> {milestonePath}", flush=True)

        if episode % ladderEvalEvery == 0:
            ladderResults = evaluateAgainstLadder(network, nGames=ladderGames)
            if ladderResults:
                summary = ", ".join(
                    f"vs{e}={wr:.2f}" for e, wr in sorted(ladderResults.items())
                )
                print(f"  ladder eval @ episode {episode:5d} | {summary}", flush=True)
                _logLadderEvaluation(episode, ladderResults)

    saveCheckpoint(network, optimizer, endEpisode)
    print(
        f"Done. Final checkpoint saved at episode {endEpisode}."
        f" ({crashCount} episode(s) hit the rare engine crash and were skipped.)",
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train the Ginseng Pai Sho RLBot.")
    parser.add_argument("--episodes", type=int, default=2000)
    parser.add_argument("--eval-every", type=int, default=100)
    parser.add_argument("--eval-games", type=int, default=20)
    parser.add_argument(
        "--ladder-eval-every",
        type=int,
        default=MILESTONE_EVERY,
        help=(
            "How often (in episodes) to run evaluateAgainstLadder(), the"
            " fixed-past-checkpoint evaluation that doesn't saturate the way"
            " evaluate() (vs. TestBot) does. Defaults to MILESTONE_EVERY since"
            " that's also when new ladder-eligible checkpoints appear."
        ),
    )
    parser.add_argument("--ladder-games", type=int, default=20)
    parser.add_argument(
        "--resume",
        action="store_true",
        help=f"continue from {CHECKPOINT_PATH} if it exists, instead of starting fresh",
    )
    parser.add_argument(
        "--checkpoint-dir",
        type=str,
        default=None,
        help=(
            "Use a different folder for checkpoints/logs than the default"
            " checkpoints/ - e.g. to keep a run under a new action/network"
            " scheme cleanly separate from an older one's history."
        ),
    )
    args = parser.parse_args()

    if args.checkpoint_dir is not None:
        CHECKPOINT_DIR = args.checkpoint_dir
        CHECKPOINT_PATH = os.path.join(CHECKPOINT_DIR, "latest.pt")
        LOG_PATH = os.path.join(CHECKPOINT_DIR, "training_log.csv")
        LADDER_LOG_PATH = os.path.join(CHECKPOINT_DIR, "ladder_log.csv")

    main(
        nEpisodes=args.episodes,
        evalEvery=args.eval_every,
        evalGames=args.eval_games,
        ladderEvalEvery=args.ladder_eval_every,
        ladderGames=args.ladder_games,
        resume=args.resume,
    )
