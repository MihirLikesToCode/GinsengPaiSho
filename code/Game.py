from typing import Literal

import pygame as pg
from pygame.event import Event
from pygame.surface import Surface
from pygame.time import Clock

from pygame_gui.ui_manager import UIManager

from AbilityPopUpGui import AbilityPopUpGui
from BasicTile import BasicTile
from GameOverPopUpGui import GameOverPopUpGui
from InputProvider import InputProvider, MouseInputProvider
from MatchEngine import MatchEngine
from Player import BotPlayer
from PopUpGui import PopUpGui
from Settings import SCREEN_SIZE
from BotTest import TestBot


class Game(MatchEngine):
    """Creates a game with a window."""

    def __init__(
        self,
        whitePlayer: BotPlayer | None = None,
        blackPlayer: BotPlayer | None = None,
        inputProvider: InputProvider | None = None,
    ) -> None:
        super().__init__(whitePlayer, blackPlayer)

        self.screen: Surface = self._initScreen()
        self.uiManager: UIManager = UIManager((SCREEN_SIZE, SCREEN_SIZE))
        self.inputProvider: InputProvider = inputProvider or MouseInputProvider()

        self.abilityPopUp: AbilityPopUpGui | None = None
        self.tradePopUp: AbilityPopUpGui | None = None
        self.gameOverPopUp: GameOverPopUpGui | None = None

        self.running: bool = True

    @staticmethod
    def _initScreen() -> Surface:
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
            self._takeBotTurnIfNeeded()

            self.drawScreen()

        pg.quit()

    def _activePopUp(self) -> PopUpGui | None:
        """Gets the active pop up.

        Returns:
            PopUpGui | None: The active pop up, or None if there isn't a pop up.
        """
        for popUp in (self.abilityPopUp, self.tradePopUp, self.gameOverPopUp):
            if popUp is not None and popUp.isActive:
                return popUp
        return None

    def _clampActivePopUp(self) -> None:
        """Clamps the active pop up to the confines of the screen."""
        activePopUp: PopUpGui | None = self._activePopUp()
        if activePopUp is not None:
            activePopUp.clampToScreen(SCREEN_SIZE)

    def _processEvents(self) -> None:
        """Processes pygame.event.Event() events."""
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.running = False
                return

            self.uiManager.process_events(event)

            activePopUp: PopUpGui | None = self._activePopUp()
            if activePopUp is not None:
                activePopUp.processEvent(event)
            elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                self._handleMouseClick(event)

    def _handleMouseClick(self, event: Event) -> None:
        """Handles a mouse click in the form of a pygame.event.Event() event.

        Args:
            event (Event): The mouse click.
        """
        if self.getPlayerForColor(self.turn) is not None:
            return  # a bot controls this turn - ignore stray mouse input
        clickedCoord = self.inputProvider.getClickedCoordinate(event, self.board)
        self.applyClick(clickedCoord)

    def _onTradeEligible(self, tile: BasicTile) -> None:
        """Spawns the trade pop up.

        Args:
            tile (BasicTile): The tile on the trade temple.
        """
        self._spawnTradePopUp(tile)

    # ------------------------------------------------------------------ #
    # Popups
    # ------------------------------------------------------------------ #

    def _resolveAbilityPopUp(self) -> None:
        """Applies the result of the ability pop up."""
        if self.abilityPopUp is None or self.abilityPopUp.resultBool is None:
            return

        self._applyAbility(self.pendingAbilityTile, self.abilityPopUp.resultTile)

        self.abilityPopUp.kill()
        self.abilityPopUp = None
        self.pendingAbilityTile = None

    def _spawnAbilityPopUpIfNeeded(self) -> None:
        """Spawns the ability pop up when the conditions of an ability are met."""
        if self.pendingAbilityTile is None or self._activePopUp() is not None:
            return

        tile: BasicTile = self.pendingAbilityTile
        targets, title = self._getAbilityTargetsAndTitle(tile)

        if not targets:
            self.pendingAbilityTile = None
            return

        self.abilityPopUp = AbilityPopUpGui(self.uiManager, targets, title)

        botPlayer: BotPlayer | None = self.getPlayerForColor(tile.color)
        if botPlayer is not None:
            chosenTarget: BasicTile | None = botPlayer.chooseAbilityTarget(
                tile, targets
            )
            self.abilityPopUp.answer(chosenTarget is not None, chosenTarget)

    def _spawnTradePopUp(self, tile: BasicTile) -> None:
        """Spawns the trade pop up when the conditions for initiating a trade are met.

        Args:
            tile (BasicTile): The tile on the trade temple.
        """
        if self._activePopUp() is not None:
            return
        if self.getPlayerForColor(tile.color) is not None:
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
        """Applies the result of the trade pop up."""
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
        """Starts a new game if the player has requested one."""
        if self.gameOverPopUp is not None and self.gameOverPopUp.newGameRequested:
            self._resetGame()

    def _resetGame(self) -> None:
        """Resets the game."""
        if self.gameOverPopUp is not None:
            self.gameOverPopUp.kill()
            self.gameOverPopUp = None
        self.abilityPopUp = None
        self.tradePopUp = None
        self._resetGameState()

    def _checkForGameEnd(self) -> None:
        """Spawns the game-over popup on a win or a draw. Skipped while any
        popup is already open."""
        if self._activePopUp() is not None:
            return

        result: Literal["white", "black", "draw"] | None = self._getGameResult()
        if result is not None:
            self.gameOverPopUp = GameOverPopUpGui(self.uiManager, result)

    # ------------------------------------------------------------------ #
    # Bot turns
    # ------------------------------------------------------------------ #

    def _takeBotTurnIfNeeded(self) -> None:
        """Asks a bot to decide a turn, then plays it. Nothing happens on a humans turn,
        an active pop up, an ability, or a trade.
        """
        if self._activePopUp() is not None:
            return
        if self.pendingAbilityTile is not None or self.pendingTradeTile is not None:
            return

        player: BotPlayer | None = self.getPlayerForColor(self.turn)
        if player is None:
            return

        decision = player.decideTurn(self.board)
        if decision is not None:
            self._applyBotDecision(decision)

    # ------------------------------------------------------------------ #
    # Drawing
    # ------------------------------------------------------------------ #

    def drawScreen(self) -> None:
        """Draws the entirety of the screen."""
        self.screen.fill((255, 255, 255))
        self.board.drawBoard(self.screen, self.highlightedCoords, self.turn)
        self.uiManager.draw_ui(self.screen)

        pg.display.flip()


if __name__ == "__main__":
    # Mode 1: mouse vs mouse (hotseat).
    # Game().run()

    # Mode 2: mouse (white) vs a bot (black).
    Game(blackPlayer=TestBot("black")).run()

    # Mode 3: bot vs bot, shown in a window (e.g. to watch them play).
    # Game(whitePlayer=TestBot("white"), blackPlayer=TestBot("black")).run()
