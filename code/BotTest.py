import random
from Board import Board
from BasicTile import BasicTile
from Coordinate import Coordinate
from Player import BotPlayer, MoveDecision, TradeDecision, TurnDecision


class TestBot(BotPlayer):
    """A test bot used to test bot movement, abilities, and trading."""

    def decideTurn(self, board: Board) -> TurnDecision:
        tradeDecision = self._maybeTrade(board)
        if tradeDecision is not None:
            return tradeDecision
        return self._chooseMove(board)

    def _maybeTrade(self, board: Board) -> TradeDecision | None:
        """50% chance of trading"""
        eligibleTiles = [
            tile
            for tile in board.tiles
            if tile.color == self.color and board.isEligibleForTempleTrade(tile)
        ]
        for tile in eligibleTiles:
            if random.random() < 0.5:
                capturedTile = board.getCapturedTiles(self.color)[0]
                return TradeDecision(tile.pos, capturedTile)
        return None

    def _chooseMove(self, board: Board) -> MoveDecision:
        """Chooses a random move."""
        allMoves: dict[BasicTile, list[Coordinate]] = board._getAllMovesForAColor(
            self.color
        )
        randKey: BasicTile = random.choice(list(allMoves.keys()))

        while len(allMoves[randKey]) == 0:
            randKey = random.choice(list(allMoves.keys()))

        randMove: Coordinate = random.choice(allMoves[randKey])

        return MoveDecision(randKey.pos, randMove)

    def chooseAbilityTarget(
        self, abilityTile: BasicTile, targets: list[BasicTile]
    ) -> BasicTile | None:
        """50% chance of activating the ability"""
        if not targets:
            return None
        return targets[0] if random.random() < 0.5 else None
