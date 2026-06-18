from Coordinate import Coordinate
from Settings import center, neg, pos, u
from BasicTile import BasicTile

import pygame as pg
from pygame.surface import Surface


class Board:
    """Class representing the game board."""

    def __init__(self) -> None:
        """Initializes the board."""
        self.coordinates = Board._getAllPossibleCoordinates()
        self.tiles: list[BasicTile] = self._initTiles()

    @staticmethod
    def _getAllPossibleCoordinates() -> list[Coordinate]:
        """Generates a list of all possible coordinates on the board.

        Returns:
            list[Coordinate]: A list of Coordinate objects representing all
            valid positions on the board.
        """

        # gets all coordinates in the top right quadrant
        quarterCoords: list[tuple[int, int]] = []
        for x in range(0, 9):
            for y in range(0, 9):
                if (x**2 + y**2) <= 80:  # ensures it is the proper circle
                    quarterCoords.append((x, y))

        length: int = len(quarterCoords)

        # gets all the coordinates from the other quadrants
        for i in range(length):
            coord: tuple[int, int] = quarterCoords[i]

            quarterCoords.append((-coord[0], coord[1]))
            quarterCoords.append((coord[0], -coord[1]))
            quarterCoords.append((-coord[0], -coord[1]))

        # removes duplicates, and converts the tuples into Coordinate objetcs
        quarterCoords = sorted(list(set(quarterCoords)))

        return [Coordinate(x, y) for x, y in quarterCoords[::-1]]

    def drawBoard(self, screen: Surface) -> None:
        self._drawBoardBackground(screen)
        self._drawTiles(screen)

    def _drawBoardBackground(self, screen: Surface) -> None:
        """Draws the background of the game board. That is, draws the circle, colored
        regions, and lines."""

        c: int = center  # shorthand

        RED: tuple[int, int, int] = (180, 30, 30)
        TAN: tuple[int, int, int] = (210, 200, 185)
        BLACK: tuple[int, int, int] = (0, 0, 0)
        WHITE: tuple[int, int, int] = (240, 240, 240)

        grid_surface = pg.Surface(screen.get_size())
        grid_surface.fill(TAN)  # base board color

        # The 4 small red triangles
        # Top
        pg.draw.polygon(
            grid_surface,
            RED,
            [(c, c - 7 * u), (c + 2 * u, c - 9 * u), (c - 2 * u, c - 9 * u)],
        )
        # Bottom
        pg.draw.polygon(
            grid_surface,
            RED,
            [(c, c + 7 * u), (c + 2 * u, c + 9 * u), (c - 2 * u, c + 9 * u)],
        )
        # Left
        pg.draw.polygon(
            grid_surface,
            RED,
            [(c - 7 * u, c), (c - 9 * u, c - 2 * u), (c - 9 * u, c + 2 * u)],
        )
        # Right
        pg.draw.polygon(
            grid_surface,
            RED,
            [(c + 7 * u, c), (c + 9 * u, c - 2 * u), (c + 9 * u, c + 2 * u)],
        )

        # Draw center regions
        pg.draw.polygon(grid_surface, WHITE, [(c, c - 7 * u), (c + 7 * u, c), (c, c)])
        pg.draw.polygon(grid_surface, WHITE, [(c, c + 7 * u), (c - 7 * u, c), (c, c)])
        pg.draw.polygon(grid_surface, RED, [(c, c + 7 * u), (c + 7 * u, c), (c, c)])
        pg.draw.polygon(grid_surface, RED, [(c, c - 7 * u), (c - 7 * u, c), (c, c)])

        # Draw grid lines
        for i in range(-9, 10):
            pg.draw.line(
                grid_surface, BLACK, (center + i * u, neg), (center + i * u, pos), 2
            )
            pg.draw.line(
                grid_surface, BLACK, (neg, center + i * u), (pos, center + i * u), 2
            )

        # Draw diagonal lines
        pg.draw.line(
            grid_surface, BLACK, (c + 9 * u, c - 2 * u), (c - 2 * u, c + 9 * u), 2
        )

        pg.draw.line(
            grid_surface, BLACK, (c + 2 * u, c + 9 * u), (c - 9 * u, c - 2 * u), 2
        )

        pg.draw.line(
            grid_surface, BLACK, (c - 9 * u, c + 2 * u), (c + 2 * u, c - 9 * u), 2
        )

        pg.draw.line(
            grid_surface, BLACK, (c - 2 * u, c - 9 * u), (c + 9 * u, c + 2 * u), 2
        )

        # Circular mask
        mask_surface = pg.Surface(screen.get_size(), pg.SRCALPHA)
        mask_surface.fill((0, 0, 0, 0))
        pg.draw.circle(mask_surface, (255, 255, 255, 255), (center, center), 8.9 * u)

        grid_surface.set_colorkey(None)
        final_surface = pg.Surface(screen.get_size(), pg.SRCALPHA)
        final_surface.blit(grid_surface, (0, 0))
        final_surface.blit(mask_surface, (0, 0), special_flags=pg.BLEND_RGBA_MIN)

        # dark grey background outside circle
        screen.fill((100, 100, 100))
        screen.blit(final_surface, (0, 0))

        # thick dark border
        pg.draw.circle(screen, (60, 40, 40), (center, center), 8.9 * u, 8)

    def _initTiles(self) -> list[BasicTile]:
        tile1: BasicTile = BasicTile(
            Coordinate(0, 0), "tempOwner", "assets/BlackBadgermole.png"
        )
        return [tile1]

    def _drawTiles(self, screen: Surface) -> None:
        for tile in self.tiles:
            tile.drawTile(screen)


if __name__ == "__main__":
    print(
        "You are running Board.py directly. This file is meant to be"
        " imported as a module, so there is no code to run here."
    )
