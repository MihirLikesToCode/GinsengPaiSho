from Coordinate import Coordinate
from Settings import u, c

from collections import deque
from typing import Literal

from pygame.surface import Surface
from pygame.rect import Rect
from pygame.image import load
from pygame.transform import smoothscale


class BasicTile:
    """Represents a basic tile in Ginseng Pai Sho"""

    def __init__(
        self,
        pos: Coordinate,
        pieceType: Literal[
            "Badgermole",
            "Dragon",
            "FlyingBison",
            "Ginseng",
            "Koi",
            "LionTurtle",
            "LotusFlower",
            "Orchid",
            "Wheel",
        ],
        color: Literal["white", "black"],
    ) -> None:
        """Creates a tile.

        Args:
            pos (Coordinate): The coordinate to spawn the tile in at.
            pieceType (str): The piece type.
            color (Literal[&quot;white&quot;, &quot;black&quot;]): The color/team of the
              tile.
        """
        self.maxMovement: int = 5
        self.pos: Coordinate = pos
        self.pieceType = pieceType
        self.color: Literal["white", "black"] = color

    def _getSpritePath(self) -> str:
        """Gets the path of the sprite for this tile."""
        return f"assets/{self.color.capitalize()}{self.pieceType}.png"

    def drawTile(self, screen: Surface) -> None:
        """Draws the tile to the screen, at its current position, given its sprite.

        Args:
            screen (Surface): The screen to draw the tile to.
        """
        imgSurface: Surface = load(self._getSpritePath())
        imgSurface: Surface = smoothscale(imgSurface, (40, 40))

        imgRect: Rect = imgSurface.get_rect()
        imgRect.center = (c + self.pos.x * u, c - self.pos.y * u)

        screen.blit(imgSurface, imgRect)

    def __str__(self) -> str:
        return f"{self.color.capitalize()} {self.pieceType} at {self.pos}"

    def __repr__(self) -> str:
        return self.__str__()


if __name__ == "__main__":
    print(
        "You are running BasicTile.py directly. This file is meant to be"
        " imported as a module, so there is no code to run here."
    )
