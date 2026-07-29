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
    def __init__(self, color: Literal["white", "black"]) -> None:
        self.color = color

    @abstractmethod
    def decideTurn(self, board: Board) -> TurnDecision: ...

    @abstractmethod
    def chooseAbilityTarget(
        self, abilityTile: BasicTile, targets: list[BasicTile]
    ) -> BasicTile | None: ...


if __name__ == "__main__":
    print(
        "You are running Player.py directly. This file is meant to be"
        " imported as a module, so there is no code to run here."
    )
