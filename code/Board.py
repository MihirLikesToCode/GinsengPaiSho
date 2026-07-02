from Coordinate import Coordinate
from Settings import neg, pos, u, c
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

    def drawBoard(self, screen: Surface, coordsToHighlight: list[Coordinate]) -> None:
        self._drawBoardBackground(screen)
        self._drawTiles(screen)
        self._highlightCoords(screen, coordsToHighlight)
        # self._drawText(screen)

    def _drawBoardBackground(self, screen: Surface) -> None:
        """Draws the background of the game board. That is, draws the circle, colored
        regions, and lines."""
        RED: tuple[int, int, int] = (160, 44, 44)
        TAN: tuple[int, int, int] = (161, 147, 138)
        BLACK: tuple[int, int, int] = (0, 0, 0)
        WHITE: tuple[int, int, int] = (218, 210, 210)

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
            pg.draw.line(grid_surface, BLACK, (c + i * u, neg), (c + i * u, pos), 2)
            pg.draw.line(grid_surface, BLACK, (neg, c + i * u), (pos, c + i * u), 2)

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
        pg.draw.circle(mask_surface, (255, 255, 255, 255), (c, c), 9.2 * u)

        grid_surface.set_colorkey(None)
        final_surface = pg.Surface(screen.get_size(), pg.SRCALPHA)
        final_surface.blit(grid_surface, (0, 0))
        final_surface.blit(mask_surface, (0, 0), special_flags=pg.BLEND_RGBA_MIN)

        # dark grey background outside circle
        screen.fill((100, 100, 100))
        screen.blit(final_surface, (0, 0))

        # thick dark border
        pg.draw.circle(screen, (60, 40, 40), (c, c), 9.2 * u, 8)

    def _initTiles(self) -> list[BasicTile]:
        blackBadgermole: BasicTile = BasicTile(Coordinate(1, 7), "Badgermole", "black")
        blackDragon: BasicTile = BasicTile(Coordinate(-1, 7), "Dragon", "black")
        blackFlyingBison: BasicTile = BasicTile(
            Coordinate(-2, 6), "FlyingBison", "black"
        )
        blackGinseng1: BasicTile = BasicTile(Coordinate(-4, 4), "Ginseng", "black")
        blackGinseng2: BasicTile = BasicTile(Coordinate(4, 4), "Ginseng", "black")
        blackKoi: BasicTile = BasicTile(Coordinate(2, 6), "Koi", "black")
        blackLionTurtle: BasicTile = BasicTile(Coordinate(0, 4), "LionTurtle", "black")
        blackLotusFlower: BasicTile = BasicTile(
            Coordinate(0, 8), "LotusFlower", "black"
        )
        blackOrchid1: BasicTile = BasicTile(Coordinate(-5, 4), "Orchid", "black")
        blackOrchid2: BasicTile = BasicTile(Coordinate(5, 4), "Orchid", "black")
        blackWheel1: BasicTile = BasicTile(Coordinate(-3, 5), "Wheel", "black")
        blackWheel2: BasicTile = BasicTile(Coordinate(3, 5), "Wheel", "black")

        whiteBadgermole: BasicTile = BasicTile(
            Coordinate(-1, -7), "Badgermole", "white"
        )
        whiteDragon: BasicTile = BasicTile(Coordinate(1, -7), "Dragon", "white")
        whiteFlyingBison: BasicTile = BasicTile(
            Coordinate(2, -6), "FlyingBison", "white"
        )
        whiteGinseng1: BasicTile = BasicTile(Coordinate(4, -4), "Ginseng", "white")
        whiteGinseng2: BasicTile = BasicTile(Coordinate(-4, -4), "Ginseng", "white")
        whiteKoi: BasicTile = BasicTile(Coordinate(-2, -6), "Koi", "white")
        whiteLionTurtle: BasicTile = BasicTile(Coordinate(0, -4), "LionTurtle", "white")
        whiteLotusFlower: BasicTile = BasicTile(
            Coordinate(0, -8), "LotusFlower", "white"
        )
        whiteOrchid1: BasicTile = BasicTile(Coordinate(5, -4), "Orchid", "white")
        whiteOrchid2: BasicTile = BasicTile(Coordinate(-5, -4), "Orchid", "white")
        whiteWheel1: BasicTile = BasicTile(Coordinate(3, -5), "Wheel", "white")
        whiteWheel2: BasicTile = BasicTile(Coordinate(-3, -5), "Wheel", "white")

        ret: list[BasicTile] = [
            blackBadgermole,
            blackDragon,
            blackFlyingBison,
            blackGinseng1,
            blackGinseng2,
            blackKoi,
            blackLionTurtle,
            blackLotusFlower,
            blackOrchid1,
            blackOrchid2,
            blackWheel1,
            blackWheel2,
            whiteBadgermole,
            whiteDragon,
            whiteFlyingBison,
            whiteGinseng1,
            whiteGinseng2,
            whiteKoi,
            whiteLionTurtle,
            whiteLotusFlower,
            whiteOrchid1,
            whiteOrchid2,
            whiteWheel1,
            whiteWheel2,
        ]

        return ret

    def _drawTiles(self, screen: Surface) -> None:
        for tile in self.tiles:
            tile.drawTile(screen)

    def getTileAtCoord(self, pos: Coordinate) -> BasicTile | None:
        """Gets the tile at a specific coordinate.

        Args:
            pos (Coordinate): The coordinate to check.

        Returns:
            BasicTile | None: The tile if there is one. None otherwise.
        """
        for tile in self.tiles:
            if tile.pos == pos:
                return tile
        return None

    def _highlightCoords(
        self, screen: Surface, coordsToHighlight: list[Coordinate]
    ) -> None:
        for coord in coordsToHighlight:
            pg.draw.circle(
                screen,
                (20, 200, 200),
                (c + coord.x * u, c - coord.y * u),
                5,
                3,
            )

    def getValidMovesForTile(self, tile: BasicTile) -> list[Coordinate]:
        """Gets all the valid moves for this tile.

        Args:
            tile (BasicTile): The tile you want to check.

        Returns:
            list[Coordinate]: All the possible moves for this tile.
        """
        return tile.getValidMoves(self.tiles, self.coordinates)

    def getSurroundingTilesForTile(self, tile: BasicTile) -> list[BasicTile]:
        """Gets the surrounding tiles for this tile.

        Args:
            tile (BasicTile): The tile you want to check.

        Returns:
            list[BasicTile]: All surrounding tiles in the 8 spots closest to it.
        """
        return tile.getSurroundingTiles(self.tiles, self.coordinates)

    def removeTile(self, tile: BasicTile) -> None:
        """Removes a tile from the board.

        Args:
            tile (BasicTile): The tile to remove.
        """
        if tile in self.tiles:
            self.tiles.remove(tile)


if __name__ == "__main__":
    print(
        "You are running Board.py directly. This file is meant to be"
        " imported as a module, so there is no code to run here."
    )

    print()
