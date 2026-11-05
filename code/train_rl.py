"""Self-play training loop for RLBot - v1 of the reinforcement learning agent.
See RL_GAME_PLAN.md for the full design and reasoning. This implements steps 3
and 4 of the "Rollout order": a working self-play loop with REINFORCE + a value
baseline, and an evaluation harness against TestBot's random play.

v1 milestone: win-rate vs. TestBot climbing above 50%. That's the bar to clear
before scaling up (step 5) or upgrading the algorithm (step 6) - see the plan.
"""

import argparse
import os
from typing import Literal

import torch
import torch.nn.functional as F
import torch.optim as optim

from BoardEncoding import lotusProgressPotential
from BotTest import TestBot
from HeadlessGame import HeadlessGame
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

# Checkpoints and the learning-curve log live outside code/ so they don't get
# mixed in with source files - see .gitignore (they're binary/generated, not
# something to commit).
CHECKPOINT_DIR = os.path.join(os.path.dirname(__file__), "..", "checkpoints")
CHECKPOINT_PATH = os.path.join(CHECKPOINT_DIR, "latest.pt")
LOG_PATH = os.path.join(CHECKPOINT_DIR, "training_log.csv")

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


def playSelfPlayEpisode(
    whiteBot: RLBot, blackBot: RLBot, maxTurns: int = MAX_TURNS
) -> tuple[list[Transition], list[Transition], Result]:
    """Plays one self-play game, applying reward shaping and the terminal reward
    to each bot's trajectory along the way. Mirrors HeadlessGame.playEpisodeCapped,
    but with reward bookkeeping woven in around each step (HeadlessGame itself
    is left untouched - see RL_GAME_PLAN.md's "Self-play loop").

    Returns:
        tuple[list[Transition], list[Transition], Result]: (whiteTrajectory,
          blackTrajectory, result).
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

        potentialAfter = lotusProgressPotential(hGame.board, actingColor)
        shapingReward = SHAPING_COEFF * (GAMMA * potentialAfter - potentialBefore)
        actingBot.recordPendingReward(shapingReward)

        outcome = hGame._getGameResult()
        if outcome is not None:
            result = outcome
            break

    whiteTrajectory = whiteBot.popTrajectory()
    blackTrajectory = blackBot.popTrajectory()

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
    network: PolicyValueNetwork, optimizer: optim.Optimizer, episode: int
) -> str:
    """Saves the network + optimizer state to CHECKPOINT_PATH, overwriting
    whatever was there before. `optimizer.state_dict()` is saved too (not just
    the network's weights) so a resumed run picks up Adam's per-weight step-size
    history instead of restarting it from scratch.

    Returns:
        str: the path saved to.
    """
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    torch.save(
        {
            "episode": episode,
            "networkState": network.state_dict(),
            "optimizerState": optimizer.state_dict(),
        },
        CHECKPOINT_PATH,
    )
    return CHECKPOINT_PATH


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


def main(
    nEpisodes: int = 2000,
    evalEvery: int = 100,
    evalGames: int = 20,
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
        whiteBot = RLBot("white", network)
        blackBot = RLBot("black", network)

        try:
            whiteTrajectory, blackTrajectory, result = playSelfPlayEpisode(
                whiteBot, blackBot
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

    main(
        nEpisodes=args.episodes,
        evalEvery=args.eval_every,
        evalGames=args.eval_games,
        resume=args.resume,
    )
