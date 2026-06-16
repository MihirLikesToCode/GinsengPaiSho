from Coordinate import Coordinate


class Board:
    """Class representing the game board."""

    def __init__(self) -> None:
        """Initializes the board."""
        self.coordinates = Board._getAllPossibleCoordinates()

    @staticmethod
    def _getAllPossibleCoordinates() -> list[Coordinate]:
        """Generates a list of all possible coordinates on the board, and also
            sets the instance variable self.coordinates to this list.

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
        # print(quarterCoords)

        return [Coordinate(x, y) for x, y in quarterCoords[::-1]]


if __name__ == "__main__":
    print(
        "You are running Board.py directly. This file is meant to be"
        " imported as a module, so there is no code to run here."
    )
