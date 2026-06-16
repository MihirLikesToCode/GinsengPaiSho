from Board import Board
from Settings import PIXELS_PER_UNIT, SCREEN_SIZE

import pygame as pg
from pygame.surface import Surface


class Game:
    def __init__(self) -> None:
        self.board: Board = Board()
        self.initScreen()

        self.centerCoord: int = SCREEN_SIZE // 2
        self.negCoord: int = self.centerCoord - 9 * PIXELS_PER_UNIT
        self.posCoord: int = self.centerCoord + 9 * PIXELS_PER_UNIT

    def initScreen(self) -> None:
        self.screen: Surface = pg.display.set_mode((SCREEN_SIZE, SCREEN_SIZE))
        pg.display.set_caption("Ginseng Pai Sho")

    def drawScreen(self) -> None:
        self.screen.fill((255, 255, 255))
        self.board.drawBoard(self.screen)

        pg.display.flip()


if __name__ == "__main__":
    g: Game = Game()
    g.drawScreen()

    running: bool = True
    while running:
        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False
                pg.quit()
