from pygame.rect import Rect
from pygame.event import Event

import pygame_gui as pgg
from pygame_gui.ui_manager import UIManager
from pygame_gui.elements import UIWindow, UILabel, UIButton

from typing import Literal


class GameOverPopUpGui:
    def __init__(
        self, uiManager: UIManager, result: Literal["white", "black", "draw"]
    ) -> None:
        self.manager = uiManager

        if result == "draw":
            title: str = "Draw!"
            message: str = "A player can't make any moves. Draw!"
        else:
            title: str = f"{result.capitalize()} wins!"
            message: str = f"{result.capitalize()}'s Lotus Flower has crossed!"

        self.window = UIWindow(
            Rect((250, 175), (320, 180)),
            self.manager,
            title,
            object_id="#game_over_popup",
        )

        UILabel(
            Rect((10, 10), (280, 50)),
            message,
            self.manager,
            self.window,
        )

        self.btnNewGame = UIButton(
            Rect((85, 80), (130, 40)), "New Game", self.manager, self.window
        )

        self.isActive: bool = True
        self.newGameRequested: bool = False

    def processEvent(self, event: Event) -> None:
        if not self.isActive:
            return

        if event.type == pgg.UI_BUTTON_PRESSED:
            if event.ui_element == self.btnNewGame:
                self.newGameRequested = True

    def kill(self) -> None:
        self.isActive = False
        self.window.kill()
