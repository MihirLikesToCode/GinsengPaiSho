import random
from Board import Board
from BasicTile import BasicTile
from Coordinate import Coordinate
from Player import BotPlayer, MoveDecision, TradeDecision, TurnDecision


class TestBot(BotPlayer):
    """A test bot used to test bot movement, abilities, and trading."""

    def decideTurn(self, board: Board) -> TurnDecision | None:
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

    def _chooseMove(self, board: Board) -> MoveDecision | None:
        """Chooses a random move. Returns None if this color has no legal move
        at all (e.g. every tile is trapped/boxed in) - previously this looped
        forever re-picking an empty-moves tile, since it assumed some tile
        always had a move available."""
        allMoves: dict[BasicTile, list[Coordinate]] = board._getAllMovesForAColor(
            self.color
        )
        movableTiles = [tile for tile, moves in allMoves.items() if moves]
        if not movableTiles:
            return None

        randKey: BasicTile = random.choice(movableTiles)
        randMove: Coordinate = random.choice(allMoves[randKey])

        return MoveDecision(randKey.pos, randMove)

    def chooseAbilityTarget(
        self, abilityTile: BasicTile, targets: list[BasicTile]
    ) -> BasicTile | None:
        """50% chance of activating the ability"""
        if not targets:
            return None
        return targets[0] if random.random() < 0.5 else None
