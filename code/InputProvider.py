from abc import ABC, abstractmethod

from pygame.event import Event

from Board import Board
from Coordinate import Coordinate
from Settings import c, u


class InputProvider(ABC):
    """Base class for providing inputs to the game."""

    @abstractmethod
    def getClickedCoordinate(self, event: Event, board: Board) -> Coordinate | None: ...


class MouseInputProvider(InputProvider):
    """Converts real mouse clicks (in pixels) into board Coordinates."""

    def getClickedCoordinate(self, event: Event, board: Board) -> Coordinate | None:
        """Gets the board coordinate of a click based on a pygame event click.

        Args:
            event (Event): The click event.
            board (Board): The board.

        Returns:
            Coordinate | None: The board Coordinate. None if the Coordinate is not valid.
        """
        return self.pixelToCoordinate(event.pos, board)

    @staticmethod
    def pixelToCoordinate(pixelPos: tuple[int, int], board: Board) -> Coordinate | None:
        """Converts a pixel position on screen to the nearest board Coordinate.

        Args:
            pixelPos (tuple[int, int]): The (x, y) pixel position.
            board (Board): The board, used to validate the coordinate exists.

        Returns:
            Coordinate | None: The coordinate, or None if it's not a valid spot on
                the board.
        """
        mouseX, mouseY = pixelPos

        xCoord: int = round((mouseX - c) / u)
        yCoord: int = round((c - mouseY) / u)

        try:
            candidate: Coordinate = Coordinate(xCoord, yCoord)
        except ValueError:
            return None

        if candidate in board.coordinates:
            return candidate
        return None
