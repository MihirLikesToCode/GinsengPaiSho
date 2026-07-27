from dataclasses import dataclass, field
from typing import Literal

from Board import Board
from BasicTile import BasicTile
from Coordinate import Coordinate


@dataclass
class ClickResult:
    """The outcome of feeding one board coordinate into the MoveController."""

    highlightCoords: list[Coordinate] = field(default_factory=list)
    turnEnded: bool = False
    pendingAbilityTile: BasicTile | None = None
    tradeEligibleTile: BasicTile | None = None


class MoveController:
    """Owns the tile-selection state machine for a turn: which tile (if any) is
    currently selected, and which coordinates are legal moves for it.
    """

    def __init__(self) -> None:
        """Creates a move controller."""
        self.selectedTile: BasicTile | None = None
        self.validMoves: list[Coordinate] = []

    def handleClick(
        self,
        clickedCoord: Coordinate | None,
        board: Board,
        turn: Literal["White", "Black"],
    ) -> ClickResult:
        """Feeds a single 'click' (from any source) into the selection state machine.

        Args:
            clickedCoord (Coordinate | None): The board coordinate that was clicked,
              or None if the click didn't land on a valid board coordinate.
            board (Board): The current board.
            turn (Literal["White", "Black"]): Whose turn it currently is.

        Returns:
            ClickResult: What happened as a result of this click.
        """
        # case 1: we havent clicked a valid option
        if clickedCoord is None:
            return self._deselect()

        # case 2: a tile has already been selected and we click
        if self.selectedTile is not None and clickedCoord in self.validMoves:
            return self._makeMove(clickedCoord, board)

        # case 3: we select a tile
        return self._selectTile(clickedCoord, board, turn)

    def _deselect(self) -> ClickResult:
        """Deselects the current selected tile, if there is one.

        Returns:
            ClickResult: ClickResult
        """
        self.selectedTile = None
        self.validMoves = []
        return ClickResult()

    def _makeMove(self, destination: Coordinate, board: Board) -> ClickResult:
        """Makes a move on the board.

        Args:
            destination (Coordinate): The destination coordinate.
            board (Board): The board.

        Returns:
            ClickResult: ClickResult
        """
        movingTile = self.selectedTile
        assert movingTile is not None  # guaranteed by handleClick's guard

        capturedTile: BasicTile | None = board.getTileAtCoord(destination)
        isEnemyCapture: bool = (
            capturedTile is not None  # the enemy tile exists
            and capturedTile is not movingTile  # its not our own tile
            and capturedTile.color != movingTile.color  # its on the opposite team
        )

        if isEnemyCapture:
            assert capturedTile is not None
            board.removeTile(capturedTile)

            # Orchids are removed once they capture something
            if movingTile.pieceType == "Orchid":
                board.removeTile(movingTile)
                self._deselect()
                return ClickResult(turnEnded=True)

        movingTile.moveTo(destination)
        self._deselect()
        return ClickResult(turnEnded=True, pendingAbilityTile=movingTile)

    def _selectTile(
        self, coord: Coordinate, board: Board, turn: Literal["White", "Black"]
    ) -> ClickResult:
        """Selects a tile, getting its possible moves and eligibility for trading/

        Args:
            coord (Coordinate): The coordinate that was clicked.
            board (Board): The board.
            turn (Literal["White", "Black"]): _description_

        Returns:
            ClickResult: _description_
        """
        tileAtCoord: BasicTile | None = board.getTileAtCoord(coord)

        if tileAtCoord is None:
            return self._deselect()

        self.selectedTile = tileAtCoord
        isOwnTile: bool = tileAtCoord.color == turn.lower()
        self.validMoves = board.getValidMovesForTile(tileAtCoord) if isOwnTile else []

        tradeEligibleTile: BasicTile | None = None
        if isOwnTile and board.isEligibleForTempleTrade(tileAtCoord):
            tradeEligibleTile = tileAtCoord

        return ClickResult(
            highlightCoords=self.validMoves, tradeEligibleTile=tradeEligibleTile
        )
