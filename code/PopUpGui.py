from abc import abstractmethod

from pygame_gui.ui_manager import UIManager
from pygame_gui.elements import UIWindow

from pygame.rect import Rect
from pygame.event import Event


class NonClosableUIWindow(UIWindow):
    def on_close_window_button_pressed(self) -> None:
        return


class PopUpGui:
    """Shared behavior for the game's modal popups."""

    def __init__(self, manager: UIManager, window: NonClosableUIWindow) -> None:
        """Creates a pop up.

        Args:
            manager (UIManager): The UIManager
            window (UIWindow): The UIWindow
        """
        self.manager = manager
        self.window = window
        self.isActive: bool = True

    def clampToScreen(self, screenSize: int) -> None:
        """Keeps the window fully within the screen bounds, snapping it back in if
        it's been dragged (partially or fully) outside of them.

        Args:
            screenSize (int): The width/height of the (square) screen, in pixels.
        """
        rect = self.window._rect
        assert type(rect) == Rect

        clampedX: int = min(max(rect.x, 0), screenSize - rect.width)
        clampedY: int = min(max(rect.y, 0), screenSize - rect.height)

        if (clampedX, clampedY) != (rect.x, rect.y):
            self.window.set_position((clampedX, clampedY))

    def kill(self) -> None:
        """Closes the popup."""
        self.isActive = False
        self.window.kill()

    @abstractmethod
    def processEvent(self, event: Event) -> None:
        """Processes a pygame.event.Event.

        Args:
            event (Event): The event.
        """


if __name__ == "__main__":
    print(
        "You are running PopUpGui.py directly. This file is meant to be"
        " imported as a module, so there is no code to run here."
    )
