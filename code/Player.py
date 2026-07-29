from abc import ABC, abstractmethod

from dataclasses import dataclass

from typing import Literal

from Coordinate import Coordinate
from BasicTile import BasicTile
from Board import Board


@dataclass
class MoveDecision:
    fromCoord: Coordinate
    toCoord: Coordinate


@dataclass
class TradeDecision:
    templeCoord: Coordinate
    tile: BasicTile


TurnDecision = MoveDecision | TradeDecision


class BotPlayer(ABC):
    """The abstract class for creating your own bots. It is recommended to also have a
    `_chooseTradeTarget()` that can then be plugged into `decideTurn()` if there is an
    eligible trade.
    """

    def __init__(self, color: Literal["white", "black"]) -> None:
        self.color: Literal["white", "black"] = color

    @abstractmethod
    def decideTurn(self, board: Board) -> TurnDecision: ...

    @abstractmethod
    def chooseAbilityTarget(
        self, abilityTile: BasicTile, targets: list[BasicTile]
    ) -> BasicTile | None: ...

    def getMyActiveTiles(self, board: Board) -> list[BasicTile]:
        """Gets all of this players active tiles (tiles that aren't captured).

        Args:
            board (Board): The board.

        Returns:
            list[BasicTile]: The on-board tiles for this player.
        """
        return [
            tile
            for tile in board.tiles
            if tile.color == self.color
            and tile not in board.whiteCapturedTiles
            and tile not in board.blackCapturedTiles
        ]


if __name__ == "__main__":
    print(
        "You are running Player.py directly. This file is meant to be"
        " imported as a module, so there is no code to run here."
    )
