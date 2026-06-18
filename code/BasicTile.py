from Coordinate import Coordinate
from Settings import center, neg, pos, u

from collections import deque

from pygame.surface import Surface
from pygame.rect import Rect
from pygame.image import load
from pygame.transform import smoothscale


class BasicTile:
    """Represents a basic tile in Ginseng Pai Sho"""

    def __init__(self, pos: Coordinate, owner: str, spritePath: str) -> None:
        self.maxMovement: int = 5
        self.pos: Coordinate = pos
        self.spritePath: str = spritePath
        self.owner: str = owner

    def drawTile(self, screen: Surface) -> None:
        c: int = center  # shorthand

        imgSurface: Surface = load(self.spritePath)
        imgSurface: Surface = smoothscale(imgSurface, (40, 40))

        imgRect: Rect = imgSurface.get_rect()
        imgRect.center = (c + self.pos.x * u, c - self.pos.y * u)

        screen.blit(imgSurface, imgRect)
