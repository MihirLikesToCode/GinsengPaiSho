from Board import Board
from Settings import SCREEN_SIZE, c, u
from Coordinate import Coordinate
from BasicTile import BasicTile

import pygame as pg
from pygame.surface import Surface


class Game:
    def __init__(self) -> None:
        """Initializes the game."""
        self.board: Board = Board()
        self.initScreen()

    def initScreen(self) -> None:
        """Initializes the screen."""
        self.screen: Surface = pg.display.set_mode((SCREEN_SIZE, SCREEN_SIZE))
        pg.display.set_caption("Ginseng Pai Sho")

    def drawScreen(self, coordsToHighlight: list[Coordinate]) -> None:
        """Draws the entirety of the screen."""
        self.screen.fill((255, 255, 255))
        self.board.drawBoard(self.screen, coordsToHighlight)

        pg.display.flip()


class MouseEventHandler:
    def __init__(self) -> None:
        self.selectedTile: BasicTile | None = None
        self.validMoves: list[Coordinate] = []

    def getMousePos(self) -> tuple[int, int]:
        """Gets the mouse position in terms of pixels.

        Returns:
            tuple[int, int]: The mouse pos.
        """
        return pg.mouse.get_pos()

    def getMouseCoords(self) -> Coordinate | None:
        """Gets the mouse positions in terms of board coordinates.

        Returns:
            Coordinate | None: The board coordinate the mouse is closest to. None if it is
              not near a valid coordinate.
        """
        mousePos: tuple[int, int] = self.getMousePos()
        mouseX, mouseY = mousePos

        xCoord: int = round((mouseX - c) / u)
        yCoord: int = round((c - mouseY) / u)

        try:
            possibleCoord: Coordinate = Coordinate(xCoord, yCoord)

            if possibleCoord in Board._getAllPossibleCoordinates():
                return possibleCoord
            else:
                return None
        except ValueError:
            return None

    def handleLeftClick(self) -> list[Coordinate]:
        """Handles the left click for the game loop

        Returns:
            list[Coordinate]: The list of coordinates to highlight.
        """

        clickedCoords: Coordinate | None = self.getMouseCoords()

        if clickedCoords == None:
            self.selectedTile = None
            self.validMoves = []
            return []

        # Case 1: A tile is alr selected, and we have clicked a valid move.
        if (self.selectedTile is not None) and (clickedCoords in self.validMoves):

            # If we have captured a tile, remove it.
            capturedTile: BasicTile | None = g.board.getTileAtCoord(clickedCoords)
            if (
                (capturedTile is not None)
                and (capturedTile is not self.selectedTile)
                and (capturedTile.color != self.selectedTile.color)
            ):
                g.board.removeTile(capturedTile)

            # move AFTER you remove the captured tile
            self.selectedTile.moveTo(clickedCoords)

            self.selectedTile = None
            self.validMoves = []
            return []

        # Case 2: Clicked on a tile
        tileAtCoord: BasicTile | None = g.board.getTileAtCoord(clickedCoords)

        if tileAtCoord is not None:
            self.selectedTile = tileAtCoord
            self.validMoves = g.board.getValidMovesForTile(tileAtCoord)
            return self.validMoves

        # Case 3: Clicked on an empty space
        self.selectedTile = None
        self.validMoves = []
        return []


if __name__ == "__main__":
    MEH: MouseEventHandler = MouseEventHandler()
    g: Game = Game()

    coordsToHighlight: list[Coordinate] = []
    running: bool = True
    while running:

        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False
                pg.quit()
            elif event.type == pg.MOUSEBUTTONDOWN:
                if event.button == 1:
                    coordsToHighlight = MEH.handleLeftClick()

        g.drawScreen(coordsToHighlight)
