import pygame as pg
import pygame_gui as pgg

from BasicTile import BasicTile

from pygame import Rect
from pygame.event import Event

from pygame_gui.ui_manager import UIManager
from pygame_gui.elements import UIWindow, UILabel, UIDropDownMenu, UIButton


class AbilityPopUpGui:
    def __init__(
        self, uiManager: UIManager, targetTiles: list[BasicTile], titleCard: str
    ) -> None:
        self.manager = uiManager
        self.targetTiles = targetTiles
        self.tileStrMap: dict[str, BasicTile] = {
            tile.__str__(): tile for tile in self.targetTiles
        }

        self.window = UIWindow(
            Rect((250, 175), (320, 220)),
            self.manager,
            titleCard,
            object_id="#ability_popup",
        )

        UILabel(
            Rect((10, 10), (280, 30)), "Choose a game piece", self.manager, self.window
        )

        self.dropdown = UIDropDownMenu(
            [tile.__str__() for tile in self.targetTiles],
            self.targetTiles[0].__str__() if self.targetTiles else "",
            Rect((40, 50), (210, 30)),
            self.manager,
            self.window,
        )

        self.btnYes = UIButton(
            Rect((30, 110), (100, 40)), "Use Ability", self.manager, self.window
        )

        self.btnNo = UIButton(
            Rect((160, 110), (100, 40)), "Skip Ability", self.manager, self.window
        )

        self.isActive: bool = True
        self.resultBool: bool | None = None
        self.resultTile: BasicTile | None = None

    def processEvent(self, event: Event) -> None:
        """Processes a clicking event on the popup/

        Args:
            event (Event): Pygame Event
        """
        if not self.isActive:
            return

        if event.type == pgg.UI_BUTTON_PRESSED:

            if event.ui_element == self.btnYes:
                selected: str = self.dropdown.selected_option[0]
                self.resultTile = self.tileStrMap[selected]
                self.resultBool = True

            elif event.ui_element == self.btnNo:
                self.resultBool = False
                self.resultTile = None

    def kill(self) -> None:
        self.isActive = False
        self.window.kill()
