from typing import Literal

import pygame as pg
from pygame.event import Event
from pygame.surface import Surface
from pygame.time import Clock

from pygame_gui.ui_manager import UIManager

from AbilityPopUpGui import AbilityPopUpGui
from BasicTile import BasicTile
from Board import Board
from Coordinate import Coordinate
from GameOverPopUpGui import GameOverPopUpGui
from InputProvider import InputProvider, MouseInputProvider
from MoveController import ClickResult, MoveController
from PopUpGui import PopUpGui
from Settings import SCREEN_SIZE


class Game:
    """Owns all game state and orchestrates a single frame's worth of work."""

    def __init__(self, inputProvider: InputProvider | None = None) -> None:
        """Initializes a game with an inputProvider

        Args:
            inputProvider (InputProvider | None, optional): Defaults to None.
        """
        self.board: Board = Board()
        self.turn: Literal["White", "Black"] = "White"
        self.screen: Surface = self._initScreen()
        self.uiManager: UIManager = UIManager((SCREEN_SIZE, SCREEN_SIZE))

        self.inputProvider: InputProvider = inputProvider or MouseInputProvider()
        self.moveController: MoveController = MoveController()

        self.abilityPopUp: AbilityPopUpGui | None = None
        self.tradePopUp: AbilityPopUpGui | None = None
        self.gameOverPopUp: GameOverPopUpGui | None = None
        self.pendingAbilityTile: BasicTile | None = None
        self.pendingTradeTile: BasicTile | None = None
        self.highlightedCoords: list[Coordinate] = []

        self.running: bool = True

    @staticmethod
    def _initScreen() -> Surface:
        """Initializes the screen.

        Returns:
            Surface: The screen, in the form of a pygame.surface.Surface
        """
        screen: Surface = pg.display.set_mode((SCREEN_SIZE, SCREEN_SIZE))
        pg.display.set_caption("Ginseng Pai Sho")
        return screen

    # ------------------------------------------------------------------ #
    # Main loop
    # ------------------------------------------------------------------ #

    def run(self) -> None:
        """Runs the game until the window is closed."""
        clock: Clock = Clock()

        while self.running:
            timeDelta: float = clock.tick(60) / 1000
            self.uiManager.update(timeDelta)

            self._processEvents()
            self._clampActivePopUp()
            self._resolveAbilityPopUp()
            self._resolveTradePopUp()
            self._resolveGameOverPopUp()
            self._checkForGameEnd()
            self._spawnAbilityPopUpIfNeeded()

            self.drawScreen()

        pg.quit()

    def _getActivePopUp(self) -> PopUpGui | None:
        """Returns the active pop up (There can only ever be one active pop up).

        Returns:
            PopUpGui | None: The active pop up.
        """
        for popUp in (self.abilityPopUp, self.tradePopUp, self.gameOverPopUp):
            if popUp is not None and popUp.isActive:
                return popUp
        return None

    def _clampActivePopUp(self) -> None:
        """Keeps the active pop up on screen (clamps it to the screen)."""
        activePopUp: PopUpGui | None = self._getActivePopUp()
        if activePopUp is not None:
            activePopUp.clampToScreen(SCREEN_SIZE)

    def _processEvents(self) -> None:
        """Processes events in the pygame.event.get() stream."""
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.running = False
                return

            self.uiManager.process_events(event)

            activePopUp: PopUpGui | None = self._getActivePopUp()
            if activePopUp is not None:
                activePopUp.processEvent(event)
            elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                self._handleMouseClick(event)

    def _handleMouseClick(self, event: Event) -> None:
        """Handles a mouse click.

        Args:
            event (Event): A pygame.event.Event mouse click.
        """
        clickedCoord: Coordinate | None = self.inputProvider.getClickedCoordinate(
            event, self.board
        )
        self.applyClick(clickedCoord)

    def applyClick(self, clickedCoord: Coordinate | None) -> None:
        """Applies a click to the game state.

        Args:
            clickedCoord (Coordinate | None): The clicked coordinate.
        """

        result: ClickResult = self.moveController.handleClick(
            clickedCoord, self.board, self.turn
        )
        self.highlightedCoords = result.highlightCoords

        if result.tradeEligibleTile is not None:
            self._spawnTradePopUp(result.tradeEligibleTile)

        if result.turnEnded:
            self.switchTurn()
            self.pendingAbilityTile = result.pendingAbilityTile

    # ------------------------------------------------------------------ #
    # Popups
    # ------------------------------------------------------------------ #

    def _resolveAbilityPopUp(self) -> None:
        """Handles the ability pop up."""
        if self.abilityPopUp is None or self.abilityPopUp.resultBool is None:
            return

        abilityTile: BasicTile | None = self.pendingAbilityTile
        targetTile: BasicTile | None = self.abilityPopUp.resultTile

        if abilityTile is not None and targetTile is not None:
            if abilityTile.pieceType == "Dragon":
                abilityTile.applyDragonPush(
                    targetTile, self.board.tiles, self.board.coordinates
                )
            elif abilityTile.pieceType == "Badgermole":
                abilityTile.applyBadgermoleFlip(
                    targetTile, self.board.tiles, self.board.coordinates
                )

        self.abilityPopUp.kill()
        self.abilityPopUp = None
        self.pendingAbilityTile = None

    def _spawnAbilityPopUpIfNeeded(self) -> None:
        """Creates the ability pop up if it is needed and is not currently active."""
        if self.pendingAbilityTile is None or self._getActivePopUp() is not None:
            return

        tile: BasicTile = self.pendingAbilityTile
        targets, title = self._getAbilityTargetsAndTitle(tile)

        if targets:
            self.abilityPopUp = AbilityPopUpGui(self.uiManager, targets, title)
        else:
            self.pendingAbilityTile = None

    def _getAbilityTargetsAndTitle(
        self, tile: BasicTile
    ) -> tuple[list[BasicTile], str]:
        """Gets the targets and title of a specific ability for a given tile.

        Args:
            tile (BasicTile): The tile.

        Returns:
            tuple[list[BasicTile], str]: The list of targets, and the string of the title.
        """
        if tile.pieceType == "Dragon":
            targets = tile.getDragonPushTargets(
                self.board.tiles, self.board.coordinates
            )
            return targets, "Dragon Push Ability"

        if tile.pieceType == "Badgermole":
            targets = tile.getBadgermoleTargets(
                self.board.tiles, self.board.coordinates
            )
            return targets, "Badgermole Flip Ability"

        return [], ""

    def _spawnTradePopUp(self, tile: BasicTile) -> None:
        """Creates the trade pop up tile if it is needed and is not currently active.

        Args:
            tile (BasicTile): The tile on the trade temple.
        """
        if self._getActivePopUp() is not None:
            return

        self.pendingTradeTile = tile
        capturedOptions: list[BasicTile] = self.board.getCapturedTiles(tile.color)

        self.tradePopUp = AbilityPopUpGui(
            self.uiManager,
            capturedOptions,
            "Temple Trade",
            promptText="Trade for a captured tile?",
            yesLabel="Trade",
            noLabel="Skip Trade",
        )

    def _resolveTradePopUp(self) -> None:
        """Handles the trade pop up."""
        if self.tradePopUp is None or self.tradePopUp.resultBool is None:
            return

        tileOnBoard: BasicTile | None = self.pendingTradeTile
        chosenCapturedTile: BasicTile | None = self.tradePopUp.resultTile

        if (
            self.tradePopUp.resultBool
            and tileOnBoard is not None
            and chosenCapturedTile is not None
        ):
            traded: bool = self.board.exchangeAtSideTemple(
                tileOnBoard, chosenCapturedTile
            )
            if traded:
                self.moveController.selectedTile = None
                self.moveController.validMoves = []
                self.highlightedCoords = []
                self.switchTurn()

        self.tradePopUp.kill()
        self.tradePopUp = None
        self.pendingTradeTile = None

    def _resolveGameOverPopUp(self) -> None:
        """Handles the game over pop up."""
        if self.gameOverPopUp is not None and self.gameOverPopUp.newGameRequested:
            self._resetGame()

    def _resetGame(self) -> None:
        """Resets the game."""
        assert self.gameOverPopUp is not None
        self.gameOverPopUp.kill()
        self.gameOverPopUp = None

        self.board = Board()
        self.turn = "White"
        self.moveController = MoveController()
        self.pendingAbilityTile = None
        self.pendingTradeTile = None
        self.abilityPopUp = None
        self.tradePopUp = None
        self.highlightedCoords = []

    def _checkForGameEnd(self) -> None:
        """Checks if the game is over, and initializes the corresponding pop up if so."""
        if self._getActivePopUp() is not None:
            return

        winner: Literal["white", "black"] | None = self.board.checkIfAColorHasWon()

        if winner is not None:
            self.gameOverPopUp = GameOverPopUpGui(self.uiManager, winner)
        elif self.board.checkForDraw():
            self.gameOverPopUp = GameOverPopUpGui(self.uiManager, "draw")

    # ------------------------------------------------------------------ #
    # Misc
    # ------------------------------------------------------------------ #

    def switchTurn(self) -> None:
        """Switches the turn."""
        self.turn = "Black" if self.turn == "White" else "White"

    def drawScreen(self) -> None:
        """Draws the entirety of the screen."""
        self.screen.fill((255, 255, 255))
        self.board.drawBoard(self.screen, self.highlightedCoords, self.turn)
        self.uiManager.draw_ui(self.screen)

        pg.display.flip()


if __name__ == "__main__":
    Game().run()
