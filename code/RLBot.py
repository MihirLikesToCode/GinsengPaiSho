"""An RL-driven BotPlayer: uses a shared PolicyValueNetwork to score every legal
candidate action (moves, temple trades, ability targets) and samples from them.

It records its own trajectory (state, action, log-probability, value estimate)
as it plays, since HeadlessGame calls decideTurn()/chooseAbilityTarget() directly
and doesn't hand back trajectory data itself - see RL_GAME_PLAN.md's "Self-play
loop" section. train_rl.py is what turns that trajectory into a reward-labeled
one and runs the learning update.

decideTurn() samples hierarchically - which tile to act with first, then what to
do with it - rather than flattening every (tile, destination) pair into one
list. See RL_GAME_PLAN.md's "Lessons learned": a flattened list gives a tile
with many destinations (e.g. Ginseng/Orchid, standard BFS movement) far more
representation than a tile with few (e.g. the Lotus Flower, whose diagonal-jump
movement is much more constrained, and has exactly 0 candidates at the start of
the game). A roughly-uniform policy over a flattened list is then structurally
biased away from ever picking the one piece that actually matters for winning -
`TestBot` doesn't have this problem since it already picks a tile uniformly
first, then a destination for that tile.
"""

import contextlib
from dataclasses import dataclass
from typing import Literal

import torch
import torch.nn.functional as F

from Board import Board
from BasicTile import BasicTile
from Coordinate import Coordinate
from Player import BotPlayer, MoveDecision, TradeDecision, TurnDecision
from BoardEncoding import PIECE_TYPE_INDEX, PIECE_TYPES, encodeBoard
from PolicyValueNetwork import PolicyValueNetwork

N_PIECE_TYPES = len(PIECE_TYPES)


@dataclass
class Transition:
    """One recorded decision: enough to compute a policy-gradient loss once the
    episode's outcome (and any shaping reward) is known. `reward` starts at 0 and
    is filled in later by train_rl.py via RLBot.recordPendingReward()."""

    logProb: torch.Tensor
    value: torch.Tensor
    entropy: torch.Tensor
    reward: float = 0.0


def _normalizedCoord(
    coord: Coordinate, perspective: Literal["white", "black"]
) -> tuple[float, float]:
    """Normalizes a coordinate to roughly [-1, 1], rotated 180 degrees for black
    to match the board-encoding perspective in BoardEncoding.py."""
    x, y = coord.x, coord.y
    if perspective == "black":
        x, y = -x, -y
    return x / 8.0, y / 8.0


class RLBot(BotPlayer):
    """A BotPlayer driven by a shared PolicyValueNetwork.

    Set `greedy=True` for evaluation (always picks the highest-scoring candidate,
    and skips building an autograd graph); leave it False during self-play
    training (samples from the policy, so the agent explores).
    """

    def __init__(
        self,
        color: Literal["white", "black"],
        network: PolicyValueNetwork,
        greedy: bool = False,
    ) -> None:
        super().__init__(color)
        self.network = network
        self.greedy = greedy
        self.trajectory: list[Transition] = []
        # chooseAbilityTarget() isn't handed the board, but it's always called
        # for a move this same bot just made - the Board object is mutated in
        # place, so this cached reference is always current. Set in decideTurn().
        self._lastBoard: Board | None = None

    # ------------------------------------------------------------------ #
    # Candidate feature vectors - see CANDIDATE_FEATURE_SIZE in
    # PolicyValueNetwork.py for the layout these all build.
    # ------------------------------------------------------------------ #

    def _moveGroupFeature(self, tile: BasicTile) -> list[float]:
        """Stage-1 feature: 'this tile has at least one legal move' - used to
        pick which tile to act with, before picking its specific destination.
        Same layout as _moveCandidateFeature, just with the (not-yet-chosen)
        destination zeroed out."""
        pieceOneHot = [0.0] * N_PIECE_TYPES
        pieceOneHot[PIECE_TYPE_INDEX[tile.pieceType]] = 1.0
        kindOneHot = [1.0, 0.0, 0.0, 0.0]
        fromX, fromY = _normalizedCoord(tile.pos, self.color)
        return pieceOneHot + kindOneHot + [fromX, fromY, 0.0, 0.0, 1.0, 0.0]

    def _tradeGroupFeature(self, tile: BasicTile) -> list[float]:
        """Stage-1 feature: 'this on-board tile is eligible to trade' - mirrors
        _moveGroupFeature, just tagged with the trade kind instead of move."""
        pieceOneHot = [0.0] * N_PIECE_TYPES
        pieceOneHot[PIECE_TYPE_INDEX[tile.pieceType]] = 1.0
        kindOneHot = [0.0, 0.0, 1.0, 0.0]
        fromX, fromY = _normalizedCoord(tile.pos, self.color)
        return pieceOneHot + kindOneHot + [fromX, fromY, 0.0, 0.0, 1.0, 0.0]

    def _moveCandidateFeature(self, tile: BasicTile, dest: Coordinate) -> list[float]:
        pieceOneHot = [0.0] * N_PIECE_TYPES
        pieceOneHot[PIECE_TYPE_INDEX[tile.pieceType]] = 1.0
        kindOneHot = [1.0, 0.0, 0.0, 0.0]
        fromX, fromY = _normalizedCoord(tile.pos, self.color)
        toX, toY = _normalizedCoord(dest, self.color)
        return pieceOneHot + kindOneHot + [fromX, fromY, toX, toY, 1.0, 0.0]

    def _abilityCandidateFeature(self, target: BasicTile) -> list[float]:
        pieceOneHot = [0.0] * N_PIECE_TYPES
        pieceOneHot[PIECE_TYPE_INDEX[target.pieceType]] = 1.0
        kindOneHot = [0.0, 1.0, 0.0, 0.0]
        toX, toY = _normalizedCoord(target.pos, self.color)
        isMine = 1.0 if target.color == self.color else 0.0
        return pieceOneHot + kindOneHot + [0.0, 0.0, toX, toY, isMine, 0.0]

    def _tradeCandidateFeature(self, capturedTile: BasicTile) -> list[float]:
        pieceOneHot = [0.0] * N_PIECE_TYPES
        pieceOneHot[PIECE_TYPE_INDEX[capturedTile.pieceType]] = 1.0
        kindOneHot = [0.0, 0.0, 1.0, 0.0]
        return pieceOneHot + kindOneHot + [0.0, 0.0, 0.0, 0.0, 1.0, 1.0]

    def _declineCandidateFeature(self) -> list[float]:
        pieceOneHot = [0.0] * N_PIECE_TYPES
        kindOneHot = [0.0, 0.0, 0.0, 1.0]
        return pieceOneHot + kindOneHot + [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

    # ------------------------------------------------------------------ #
    # Shared sampling logic
    # ------------------------------------------------------------------ #

    def _sample(self, board: Board, candidateFeatures: list[list[float]]) -> int:
        """Scores every candidate, samples (or greedily picks) one, and records a
        Transition. Returns the chosen candidate's index.
        """
        noGrad = torch.no_grad() if self.greedy else contextlib.nullcontext()
        with noGrad:
            planes, scalarFeatures = encodeBoard(board, self.color)
            stateEmbedding = self.network.encodeState(planes, scalarFeatures)
            value = self.network.valueOf(stateEmbedding)

            featureTensor = torch.tensor(candidateFeatures, dtype=torch.float32)
            logits = self.network.scoreCandidates(stateEmbedding, featureTensor)
            probs = F.softmax(logits, dim=0)
            distribution = torch.distributions.Categorical(probs=probs)

            if self.greedy:
                chosenIndex = int(torch.argmax(probs).item())
            else:
                chosenIndex = int(distribution.sample().item())

            self.trajectory.append(
                Transition(
                    logProb=distribution.log_prob(torch.tensor(chosenIndex)),
                    value=value,
                    entropy=distribution.entropy(),
                )
            )

        return chosenIndex

    # ------------------------------------------------------------------ #
    # BotPlayer interface
    # ------------------------------------------------------------------ #

    def decideTurn(self, board: Board) -> TurnDecision | None:
        self._lastBoard = board

        allMoves = board._getAllMovesForAColor(self.color)
        moveTiles: list[BasicTile] = [tile for tile, dests in allMoves.items() if dests]

        myCapturedTiles = board.getCapturedTiles(self.color)
        tradeTiles: list[BasicTile] = (
            [
                tile
                for tile in board.tiles
                if tile.color == self.color and board.isEligibleForTempleTrade(tile)
            ]
            if myCapturedTiles
            else []
        )

        if not moveTiles and not tradeTiles:
            return None  # no legal action at all - HeadlessGame treats this as a draw

        # Stage 1: which tile to act with (uniform-ish over tiles, not over
        # individual destinations - see the module docstring for why).
        groupFeatures = [self._moveGroupFeature(t) for t in moveTiles] + [
            self._tradeGroupFeature(t) for t in tradeTiles
        ]
        groupIndex = self._sample(board, groupFeatures)

        # Stage 2: given that tile, which specific destination (or, for a
        # trade, which captured tile to bring back in).
        if groupIndex < len(moveTiles):
            tile = moveTiles[groupIndex]
            destinations = allMoves[tile]
            destFeatures = [self._moveCandidateFeature(tile, d) for d in destinations]
            destIndex = self._sample(board, destFeatures)
            return MoveDecision(tile.pos, destinations[destIndex])

        tile = tradeTiles[groupIndex - len(moveTiles)]
        tradeFeatures = [self._tradeCandidateFeature(c) for c in myCapturedTiles]
        tradeIndex = self._sample(board, tradeFeatures)
        return TradeDecision(tile.pos, myCapturedTiles[tradeIndex])

    def chooseAbilityTarget(
        self, abilityTile: BasicTile, targets: list[BasicTile]
    ) -> BasicTile | None:
        if not targets:
            return None
        assert self._lastBoard is not None  # decideTurn always runs first

        features = [self._abilityCandidateFeature(t) for t in targets] + [
            self._declineCandidateFeature()
        ]

        chosenIndex = self._sample(self._lastBoard, features)

        return targets[chosenIndex] if chosenIndex < len(targets) else None

    # ------------------------------------------------------------------ #
    # Trajectory bookkeeping, used by train_rl.py
    # ------------------------------------------------------------------ #

    def recordPendingReward(self, reward: float) -> None:
        """Adds an immediate reward (e.g. shaping, or the terminal reward) to the
        most recently recorded transition. No-op if nothing's been recorded yet.
        """
        if self.trajectory:
            self.trajectory[-1].reward += reward

    def popTrajectory(self) -> list[Transition]:
        """Returns and clears this bot's recorded trajectory for the episode."""
        trajectory = self.trajectory
        self.trajectory = []
        self._lastBoard = None
        return trajectory


if __name__ == "__main__":
    print(
        "You are running RLBot.py directly. This file is meant to be imported"
        " as a module, so there is no code to run here."
    )
