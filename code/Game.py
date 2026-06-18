from Board import Board
from Settings import SCREEN_SIZE, c, u
from Coordinate import Coordinate

import pygame as pg
from pygame.surface import Surface
from pygame.event import Event


class Game:
    def __init__(self) -> None:
        """Initializes the game."""
        self.board: Board = Board()
        self.initScreen()

    def initScreen(self) -> None:
        """Initializes the screen."""
        self.screen: Surface = pg.display.set_mode((SCREEN_SIZE, SCREEN_SIZE))
        pg.display.set_caption("Ginseng Pai Sho")

    def drawScreen(self) -> None:
        """Draws the entirety of the screen."""
        self.screen.fill((255, 255, 255))
        self.board.drawBoard(self.screen)

        pg.display.flip()


class MouseEventHandler:
    def __init__(self) -> None:
        return None

    def getMousePos(self) -> tuple[int, int]:
        return pg.mouse.get_pos()

    def getMouseCoords(self) -> Coordinate | None:
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


if __name__ == "__main__":
    MEH: MouseEventHandler = MouseEventHandler()

    g: Game = Game()
    g.drawScreen()

    running: bool = True
    while running:
        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False
                pg.quit()
            elif event.type == pg.MOUSEBUTTONDOWN:
                print(MEH.getMouseCoords())
