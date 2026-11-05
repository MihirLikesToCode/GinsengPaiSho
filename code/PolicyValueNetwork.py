"""The shared policy+value network. See RL_GAME_PLAN.md for the overall design:
a small CNN trunk over the board produces a state embedding, which feeds both a
value head and a candidate-scoring policy head. The policy head is deliberately
generic - it scores one candidate action at a time from a fixed-size feature
vector, which is what lets the same head handle moves, ability-target choices,
and temple trades uniformly (see RLBot.py for how each is encoded).
"""

import torch
import torch.nn as nn
import torch.nn.functional as F

from torch.nn import Module, Conv2d, Linear, Sequential, ReLU
from torch import Tensor

from BoardEncoding import N_PLANES, GRID_SIZE, PIECE_TYPES

N_PIECE_TYPES = len(PIECE_TYPES)

# Candidate feature layout (built in RLBot.py):
#   [0:9]   piece type one-hot - the tile being moved, or the target/captured tile
#   [9:13]  kind one-hot: move, ability_target, trade, decline
#   [13:15] from-coordinate (x, y), normalized to roughly [-1, 1]; zero if unused
#   [15:17] to-coordinate (x, y), normalized to roughly [-1, 1]; zero if unused
#   [17]    isMine flag (1.0 if the candidate tile belongs to the acting player)
#   [18]    isCaptured flag (1.0 if the candidate tile is currently off the board)
CANDIDATE_FEATURE_SIZE = N_PIECE_TYPES + 4 + 2 + 2 + 1 + 1


class PolicyValueNetwork(Module):
    """Shared trunk + value head + candidate-scoring policy head."""

    def __init__(self, embedDim: int = 128, candidateEmbedDim: int = 32) -> None:
        super().__init__()

        self.conv1: Conv2d = Conv2d(N_PLANES, 32, kernel_size=3, padding=1)
        self.conv2: Conv2d = Conv2d(32, 32, kernel_size=3, padding=1)

        flattenedSize: int = 32 * GRID_SIZE * GRID_SIZE
        self.trunkFc: Linear = Linear(flattenedSize + 2, embedDim)

        self.valueHead: Sequential = Sequential(
            Linear(embedDim, 64),
            ReLU(),
            Linear(64, 1),
        )

        self.candidateEncoder: Sequential = Sequential(
            Linear(CANDIDATE_FEATURE_SIZE, candidateEmbedDim),
            ReLU(),
        )
        self.scorer: Sequential = Sequential(
            Linear(embedDim + candidateEmbedDim, 64),
            ReLU(),
            Linear(64, 1),
        )

    def encodeState(self, planes: Tensor, scalarFeatures: Tensor) -> Tensor:
        """Encodes a single board into an embedding vector.

        Args:
            planes (torch.Tensor): shape (N_PLANES, GRID_SIZE, GRID_SIZE).
            scalarFeatures (torch.Tensor): shape (2,).

        Returns:
            torch.Tensor: shape (embedDim,).
        """
        x: Tensor = planes.unsqueeze(0)  # add a batch dimension of 1
        x = F.relu(self.conv1(x))
        x = F.relu(self.conv2(x))
        x = x.flatten(start_dim=1)
        x = torch.cat([x, scalarFeatures.unsqueeze(0)], dim=1)
        embedding: Tensor = F.relu(self.trunkFc(x))
        return embedding.squeeze(0)

    def valueOf(self, stateEmbedding: Tensor) -> Tensor:
        """Estimates V(s), squashed to roughly [-1, 1] to match the reward scale.

        Args:
            stateEmbedding (torch.Tensor): shape (embedDim,), from encodeState.

        Returns:
            torch.Tensor: a 0-dim scalar tensor.
        """
        return torch.tanh(self.valueHead(stateEmbedding.unsqueeze(0))).squeeze()

    def scoreCandidates(
        self, stateEmbedding: Tensor, candidateFeatures: Tensor
    ) -> Tensor:
        """Scores every legal candidate action for this state.

        Args:
            stateEmbedding (torch.Tensor): shape (embedDim,), from encodeState.
            candidateFeatures (torch.Tensor): shape
              (numCandidates, CANDIDATE_FEATURE_SIZE).

        Returns:
            torch.Tensor: shape (numCandidates,), one logit per candidate.
        """
        numCandidates = candidateFeatures.shape[0]
        candidateEmbeddings = self.candidateEncoder(candidateFeatures)
        broadcastState = stateEmbedding.unsqueeze(0).expand(numCandidates, -1)
        combined = torch.cat([broadcastState, candidateEmbeddings], dim=1)
        return self.scorer(combined).squeeze(-1)


if __name__ == "__main__":
    print(
        "You are running PolicyValueNetwork.py directly. This file is meant to"
        " be imported as a module, so there is no code to run here."
    )
