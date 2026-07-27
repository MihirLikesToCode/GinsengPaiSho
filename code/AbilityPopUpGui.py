import pygame_gui as pgg

from BasicTile import BasicTile
from PopUpGui import PopUpGui, NonClosableUIWindow

from pygame import Rect
from pygame.event import Event

from pygame_gui.ui_manager import UIManager
from pygame_gui.elements import UILabel, UIDropDownMenu, UIButton


class AbilityPopUpGui(PopUpGui):
    def __init__(
        self,
        uiManager: UIManager,
        targetTiles: list[BasicTile],
        titleCard: str,
        promptText: str = "Choose a game piece",
        yesLabel: str = "Use Ability",
        noLabel: str = "Skip Ability",
    ) -> None:
        """Creates an Ability Pop up

        Args:
            uiManager (UIManager): The UIManager
            targetTiles (list[BasicTile]): The target tiles to apply the ability to.
            titleCard (str): The title of the pop up.
            promptText (str, optional): Prompt text. Defaults to "Choose a game piece".
            yesLabel (str, optional): Text on the `yes` button. Defaults to "Use Ability".
            noLabel (str, optional): Text on the `no` button. Defaults to "Skip Ability".
        """
        self.targetTiles = targetTiles
        self.tileStrMap: dict[str, BasicTile] = {
            tile.__str__(): tile for tile in self.targetTiles
        }

        window: NonClosableUIWindow = NonClosableUIWindow(
            Rect((250, 175), (320, 220)),
            uiManager,
            titleCard,
            object_id="#ability_popup",
            draggable=True,
        )
        super().__init__(uiManager, window)

        UILabel(Rect((10, 10), (280, 30)), promptText, self.manager, self.window)

        self.dropdown: UIDropDownMenu = UIDropDownMenu(
            [tile.__str__() for tile in self.targetTiles],
            self.targetTiles[0].__str__() if self.targetTiles else "",
            Rect((40, 50), (210, 30)),
            self.manager,
            self.window,
        )

        self.btnYes: UIButton = UIButton(
            Rect((30, 110), (100, 40)), yesLabel, self.manager, self.window
        )

        self.btnNo: UIButton = UIButton(
            Rect((160, 110), (100, 40)), noLabel, self.manager, self.window
        )

        self.resultBool: bool | None = None
        self.resultTile: BasicTile | None = None

    def processEvent(self, event: Event) -> None:
        """Processes a clicking event on the popup.

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
