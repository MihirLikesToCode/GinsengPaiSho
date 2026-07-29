from pygame.rect import Rect
from pygame.event import Event

import pygame_gui as pgg
from pygame_gui.ui_manager import UIManager
from pygame_gui.elements import UILabel, UIButton

from PopUpGui import PopUpGui, NonClosableUIWindow

from typing import Literal


class GameOverPopUpGui(PopUpGui):
    def __init__(
        self, uiManager: UIManager, result: Literal["white", "black", "draw"]
    ) -> None:
        """Creates a Game Over PopUp

        Args:
            uiManager (UIManager): The UIManager
            result (Literal["white", "black", "draw"]): The result of the game.
        """
        if result == "draw":
            title: str = "Draw!"
            message: str = "A player can't make any moves. Draw!"
        else:
            title: str = f"{result.capitalize()} wins!"
            message: str = f"{result.capitalize()}'s Lotus Flower has crossed!"

        window: NonClosableUIWindow = NonClosableUIWindow(
            Rect((250, 175), (320, 180)),
            uiManager,
            title,
            object_id="#game_over_popup",
            draggable=True,
        )

        super().__init__(uiManager, window)

        UILabel(
            Rect((10, 10), (280, 50)),
            message,
            self.manager,
            self.window,
        )

        self.btnNewGame: UIButton = UIButton(
            Rect((85, 80), (130, 40)), "New Game", self.manager, self.window
        )

        self.newGameRequested: bool = False

    def processEvent(self, event: Event) -> None:
        if not self.isActive:
            return

        if event.type == pgg.UI_BUTTON_PRESSED:
            if event.ui_element == self.btnNewGame:
                self.newGameRequested = True

    def answer(self, requestNewGame: bool = True) -> None:
        """Answers this pop up automatically without processing an event.

        Args:
            requestNewGame (bool, optional): Whether to request a new game or not.
            Defaults to True.
        """
        self.newGameRequested = requestNewGame


if __name__ == "__main__":
    print(
        "You are running GameOverPopUpGui.py directly. This file is meant to be"
        " imported as a module, so there is no code to run here."
    )
