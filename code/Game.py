from Board import Board
from Settings import SCREEN_SIZE, c, u
from Coordinate import Coordinate
from BasicTile import BasicTile
from AbilityPopUpGui import AbilityPopUpGui
from GameOverPopUpGui import GameOverPopUpGui

import pygame as pg
from pygame.surface import Surface
from pygame.time import Clock

from pygame_gui.ui_manager import UIManager

from typing import Literal


class Game:
    def __init__(self) -> None:
        """Initializes the game."""
        self.board: Board = Board()
        self.initScreen()
        self.turn: Literal["White", "Black"] = "White"
        self.pendingAbilityTile: BasicTile | None = None
        self.uiManager: UIManager = UIManager((SCREEN_SIZE, SCREEN_SIZE))
        self.abilityPopUp: AbilityPopUpGui | None = None
        self.gameOverPopUp: GameOverPopUpGui | None = None

    def initScreen(self) -> None:
        """Initializes the screen."""
        self.screen: Surface = pg.display.set_mode((SCREEN_SIZE, SCREEN_SIZE))
        pg.display.set_caption("Ginseng Pai Sho")

    def drawScreen(self, coordsToHighlight: list[Coordinate]) -> None:
        """Draws the entirety of the screen."""
        self.screen.fill((255, 255, 255))
        self.board.drawBoard(self.screen, coordsToHighlight, self.turn)
        self.uiManager.draw_ui(self.screen)

        pg.display.flip()

    def switchTurn(self) -> None:
        if self.turn == "White":
            self.turn = "Black"
        else:
            self.turn = "White"


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

                if self.selectedTile.pieceType == "Orchid":
                    g.board.removeTile(self.selectedTile)
                    self.selectedTile = None
                    self.validMoves = []
                    g.switchTurn()

                    return []

            # move AFTER you remove the captured tile
            self.selectedTile.moveTo(clickedCoords)
            g.switchTurn()

            # the tile which has an ability pending (the Badgermole or Dragon)
            g.pendingAbilityTile = self.selectedTile

            self.selectedTile = None
            self.validMoves = []
            return []

        # Case 2: Clicked on a tile
        tileAtCoord: BasicTile | None = g.board.getTileAtCoord(clickedCoords)

        if tileAtCoord is not None:
            self.selectedTile = tileAtCoord
            if tileAtCoord.color == g.turn.lower():
                self.validMoves = g.board.getValidMovesForTile(tileAtCoord)
            else:
                self.validMoves = []

            return self.validMoves

        # Case 3: Clicked on an empty space
        self.selectedTile = None
        self.validMoves = []
        return []


if __name__ == "__main__":
    MEH: MouseEventHandler = MouseEventHandler()
    g: Game = Game()
    clock: Clock = Clock()

    coordsToHighlight: list[Coordinate] = []
    running: bool = True

    while running:
        timeDelta: float = clock.tick(60) / 1000
        g.uiManager.update(timeDelta)

        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False
                pg.quit()

            g.uiManager.process_events(event)

            # check if there is an active popup
            if g.abilityPopUp is not None and g.abilityPopUp.isActive == True:
                g.abilityPopUp.processEvent(event)

            elif g.gameOverPopUp is not None and g.gameOverPopUp.isActive == True:
                g.gameOverPopUp.processEvent(event)

            elif event.type == pg.MOUSEBUTTONDOWN:
                if event.button == 1:
                    coordsToHighlight = MEH.handleLeftClick()

        # check for a pop up result
        if g.abilityPopUp is not None and g.abilityPopUp.resultBool is not None:

            if (
                g.abilityPopUp.resultTile is not None
                and g.pendingAbilityTile is not None
            ):
                abilityTile = g.pendingAbilityTile
                targetTile = g.abilityPopUp.resultTile

                if abilityTile.pieceType == "Dragon":
                    abilityTile.applyDragonPush(
                        targetTile, g.board.tiles, g.board.coordinates
                    )
                elif abilityTile.pieceType == "Badgermole":
                    abilityTile.applyBadgermoleFlip(
                        targetTile, g.board.tiles, g.board.coordinates
                    )

            g.abilityPopUp.kill()
            g.abilityPopUp = None
            g.pendingAbilityTile = None

        # check for a new game request
        if g.gameOverPopUp is not None and g.gameOverPopUp.newGameRequested == True:
            g.gameOverPopUp.kill()
            g.gameOverPopUp = None
            g.board = Board()
            g.turn = "White"
            g.pendingAbilityTile = None
            g.abilityPopUp = None
            coordsToHighlight = []

        # check for a game end (win/loss/draw)
        if g.gameOverPopUp is None and g.abilityPopUp is None:
            winner: Literal["white", "black"] | None = g.board.checkIfAColorHasWon()
            isDraw: bool = g.board.checkForDraw()

            if winner is not None:
                g.gameOverPopUp = GameOverPopUpGui(g.uiManager, winner)
            elif isDraw:
                g.gameOverPopUp = GameOverPopUpGui(g.uiManager, "draw")

        # spawn a pop up if a pending ability tile was just set
        if g.pendingAbilityTile is not None and g.abilityPopUp is None:
            tile = g.pendingAbilityTile
            targets: list[BasicTile] = []
            title: str = ""

            if tile.pieceType == "Dragon":
                targets: list[BasicTile] = tile.getDragonPushTargets(
                    g.board.tiles, g.board.coordinates
                )
                title: str = "Dragon Push Ability"
            elif tile.pieceType == "Badgermole":
                targets: list[BasicTile] = tile.getBadgermoleTargets(
                    g.board.tiles, g.board.coordinates
                )
                title: str = "Badgermole Flip Ability"

            if len(targets) > 0:
                g.abilityPopUp = AbilityPopUpGui(g.uiManager, targets, title)
            else:
                g.pendingAbilityTile = None

        g.drawScreen(coordsToHighlight)
