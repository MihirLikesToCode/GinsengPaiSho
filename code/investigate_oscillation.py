"""One-off diagnostic, not part of the regular training pipeline.

Investigates the late-checkpoints_v3 oscillation (good/bad/good/bad across
episode_10000/11000/12000/13000) found by compare_checkpoints.py. Three parts:

1. Fill in the full milestone curve (episode_3000..9000) at 100 games each,
   matching the resolution already gathered for 10000-13000, so we can see
   the oscillation's full shape instead of just its last quarter.
2. Head-to-head: the best checkpoint found so far (episode_10000) played
   directly against the final one (episode_13000), greedy vs greedy,
   alternating colors - tests whether episode_13000 is genuinely weaker, or
   just happens to score worse specifically against TestBot.
3. A simple loop/repetition check: for episode_10000 and episode_13000 (greedy)
   vs TestBot, track how many of each game's board states were already seen
   earlier in that same game. A low unique-state ratio means the bot is
   stuck cycling rather than making progress - the automated version of the
   "watch it play and see a Wheel-oscillation loop" check used earlier in
   this project.
"""

import sys

import torch

from Board import Board
from BasicTile import BasicTile
from BotTest import TestBot
from HeadlessGame import HeadlessGame
from PolicyValueNetwork import PolicyValueNetwork
from RLBot import RLBot
from train_rl import MAX_TURNS, evaluate

CHECKPOINT_DIR = "../checkpoints_v3"


def loadNetwork(episode: int) -> PolicyValueNetwork:
    network = PolicyValueNetwork()
    checkpoint = torch.load(
        f"{CHECKPOINT_DIR}/episode_{episode}.pt", map_location="cpu"
    )
    network.load_state_dict(checkpoint["networkState"])
    network.eval()
    return network


def boardFingerprint(board: Board) -> tuple:
    tileState = tuple(
        sorted(
            (t.color, t.pieceType, t.pos.x, t.pos.y, getattr(t, "captured", False))
            for t in board.tiles
        )
    )
    whiteCaptured = len(board.getCapturedTiles("white"))
    blackCaptured = len(board.getCapturedTiles("black"))
    return (tileState, whiteCaptured, blackCaptured)


def playWithFingerprints(whitePlayer, blackPlayer, maxTurns=MAX_TURNS):
    """Like HeadlessGame.playEpisodeCapped, but also returns (turnsPlayed,
    uniqueStateRatio)."""
    game = HeadlessGame(whitePlayer, blackPlayer)
    game._resetGameState()
    seen = set()
    turns = 0
    for _ in range(maxTurns):
        fingerprint = boardFingerprint(game.board)
        seen.add(fingerprint)
        turns += 1

        player = game.getPlayerForColor(game.turn)
        decision = player.decideTurn(game.board)
        if decision is None:
            return "draw", turns, len(seen) / turns
        game._applyBotDecision(decision)
        game._resolveHeadlessAbility()
        result = game._getGameResult()
        if result is not None:
            return result, turns, len(seen) / turns
    return "turn_limit", turns, len(seen) / turns


def headToHead(networkA, networkB, nGames: int) -> float:
    """Returns A's win rate (draws count 0.5) over nGames, alternating colors."""
    wins = 0.0
    for i in range(nGames):
        aColor = "white" if i % 2 == 0 else "black"
        bColor = "black" if aColor == "white" else "white"
        botA = RLBot(aColor, networkA, greedy=True)
        botB = RLBot(bColor, networkB, greedy=True)
        whitePlayer = botA if aColor == "white" else botB
        blackPlayer = botB if aColor == "white" else botA
        try:
            result = HeadlessGame(whitePlayer, blackPlayer).playEpisodeCapped(
                maxTurns=MAX_TURNS
            )
        except Exception as exc:
            print(f"    game crashed ({type(exc).__name__}: {exc}) - skipping")
            continue
        if result == aColor:
            wins += 1.0
        elif result in ("draw", "turn_limit"):
            wins += 0.5
    return wins / nGames


def main():
    print("=== Part 1: full milestone curve, episodes 3000-9000 (100 games each) ===", flush=True)
    for episode in [3000, 4000, 5000, 6000, 7000, 8000, 9000]:
        network = loadNetwork(episode)
        winRate = evaluate(network, nGames=100)
        print(f"episode_{episode}.pt: win-rate = {winRate:.3f} over 100 games", flush=True)

    print("\n=== Part 2: head-to-head, episode_10000 (best) vs episode_13000 (final) ===", flush=True)
    net10000 = loadNetwork(10000)
    net13000 = loadNetwork(13000)
    winRate = headToHead(net10000, net13000, nGames=40)
    print(f"episode_10000 win-rate vs episode_13000, direct play: {winRate:.3f} over 40 games", flush=True)

    print("\n=== Part 3: loop/repetition check vs TestBot, 20 games each ===", flush=True)
    for episode, network in [(10000, net10000), (13000, net13000)]:
        results = []
        ratios = []
        for i in range(20):
            color = "white" if i % 2 == 0 else "black"
            otherColor = "black" if color == "white" else "white"
            rlBot = RLBot(color, network, greedy=True)
            testBot = TestBot(otherColor)
            whitePlayer = rlBot if color == "white" else testBot
            blackPlayer = testBot if color == "white" else rlBot
            try:
                result, turns, ratio = playWithFingerprints(whitePlayer, blackPlayer)
            except Exception as exc:
                print(f"    game crashed ({type(exc).__name__}: {exc}) - skipping")
                continue
            results.append(result)
            ratios.append(ratio)
        avgRatio = sum(ratios) / len(ratios) if ratios else float("nan")
        turnLimitCount = sum(1 for r in results if r == "turn_limit")
        print(
            f"episode_{episode}.pt: avg unique-state ratio = {avgRatio:.3f} "
            f"(lower = more repetition/looping), turn_limit hit {turnLimitCount}/{len(results)} games",
            flush=True,
        )

    print("\nDone.", flush=True)


if __name__ == "__main__":
    main()
