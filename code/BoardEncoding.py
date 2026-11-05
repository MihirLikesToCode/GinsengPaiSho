"""Encodes a Board into tensors for the RL network, and defines the potential
function used for reward shaping.
"""

from typing import Literal

import torch
from torch import Tensor

from Board import Board
from Coordinate import Coordinate

PIECE_TYPES: list[str] = [
    "Badgermole",
    "Dragon",
    "FlyingBison",
    "Ginseng",
    "Koi",
    "LionTurtle",
    "LotusFlower",
    "Orchid",
    "Wheel",
]
PIECE_TYPE_INDEX: dict[str, int] = {name: i for i, name in enumerate(PIECE_TYPES)}

GRID_SIZE: int = 17
N_PLANES: int = len(PIECE_TYPES) * 2  # "mine" planes + "theirs" planes

Color = Literal["white", "black"]


def _opponent(color: Color) -> Color:
    return "black" if color == "white" else "white"


def _canonicalGridIndex(coord: Coordinate, perspective: Color) -> tuple[int, int]:
    """Rotates a coordinate 180 degrees when viewing from black's perspective, so
    the network always sees the board as if it were the mover's own side, then
    shifts it into a [0, GRID_SIZE - 1] grid index.

    Args:
        coord (Coordinate): The board coordinate.
        perspective (Color): Whose point of view to encode from.

    Returns:
        tuple[int, int]: (gridX, gridY), each in [0, GRID_SIZE - 1].
    """
    x, y = coord.x, coord.y
    if perspective == "black":
        x, y = -x, -y
    return x + 8, y + 8


def encodeBoard(board: Board, perspective: Color) -> tuple[Tensor, Tensor]:
    """Encodes a board from a given player's perspective.

    Args:
        board (Board): The board to encode.
        perspective (Color): Whose point of view to encode the board from. This
          player's tiles always land in the "mine" planes, and the whole board is
          rotated 180 degrees for black so one network only ever has to learn one
          point of view.

    Returns:
        tuple[torch.Tensor, torch.Tensor]: (planes, scalarFeatures).
          planes has shape (N_PLANES, GRID_SIZE, GRID_SIZE): a one-hot occupancy
          grid, "mine" planes first, then "theirs".
          scalarFeatures has shape (2,): [myCapturedCount, opponentCapturedCount],
          each normalized by the 12 tiles each side starts with.
    """
    planes: Tensor = torch.zeros(N_PLANES, GRID_SIZE, GRID_SIZE)

    for tile in board.tiles:

        gridX, gridY = _canonicalGridIndex(
            tile.pos, perspective
        )  # get location on board
        pieceIndex: int = PIECE_TYPE_INDEX[tile.pieceType]
        isMine: bool = tile.color == perspective

        planeIndex: int = (
            pieceIndex if isMine else pieceIndex + len(PIECE_TYPES)
        )  # what plane to put the piece onto

        planes[planeIndex, gridY, gridX] = 1.0

    """
    planes is an encoding of the board.
    planes is a 18 x 17 x 17 vector tensor. It is mostly filled with zeros.
    Plane 0 has zeros everywhere, except for where my Badgermole is.
    Plane 1 has zeros everywhere, except for where my Dragon is.
    Plane 17 has zeros everywhere, except for where the enemy Wheel is.
    """

    myCaptured: int = len(board.getCapturedTiles(perspective))
    oppCaptured: int = len(board.getCapturedTiles(_opponent(perspective)))

    scalarFeatures: Tensor = torch.tensor(
        [myCaptured / 12.0, oppCaptured / 12.0], dtype=torch.float32
    )

    """
    scalarFeatures is just how many of my pieces versus opponents pieces
    have been captured.
    """

    return planes, scalarFeatures


def lotusProgressPotential(board: Board, color: Color) -> float:
    """The potential function used for reward shaping: how far this color's Lotus
    Flower has progressed toward crossing the border into enemy territory. Higher
    is better. Normalized to roughly [-1, 1] (16 is the board's full length along
    the y-axis).

    Args:
        board (Board): The board.
        color (Color): The color whose Lotus Flower to check.

    Returns:
        float: The potential value. 0.0 in the (should-never-happen) case that
          this color's Lotus Flower can't be found.
    """
    for tile in board.tiles:
        if tile.pieceType == "LotusFlower" and tile.color == color:
            return (tile.pos.y / 16.0) if color == "white" else (-tile.pos.y / 16.0)
    return 0.0


if __name__ == "__main__":
    print(
        "You are running BoardEncoding.py directly. This file is meant to be"
        " imported as a module, so there is no code to run here."
    )
