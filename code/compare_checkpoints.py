"""One-off diagnostic: run a larger, lower-noise evaluation (vs. the 15-game
rolling eval used during training) across several checkpoints_v3 milestones,
to tell whether the late-run win-rate dip (episodes ~12500-13200) is real
regression or eval noise. Not part of the regular training pipeline."""

import sys

import torch

from PolicyValueNetwork import PolicyValueNetwork
from train_rl import evaluate

CHECKPOINTS = [
    "../checkpoints_v3/episode_10000.pt",
    "../checkpoints_v3/episode_11000.pt",
    "../checkpoints_v3/episode_12000.pt",
    "../checkpoints_v3/episode_13000.pt",
]

N_GAMES = 100

for path in CHECKPOINTS:
    network = PolicyValueNetwork()
    checkpoint = torch.load(path, map_location="cpu")
    network.load_state_dict(checkpoint["networkState"])
    network.eval()
    winRate = evaluate(network, nGames=N_GAMES)
    print(f"{path} (episode {checkpoint['episode']}): win-rate = {winRate:.3f} over {N_GAMES} games", flush=True)
    sys.stdout.flush()
