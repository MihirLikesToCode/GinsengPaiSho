class Coordinate:
    """Class representing a coordinate on the board."""

    def __init__(self, x: int, y: int) -> None:
        """Initializes a coordinate with x and y values.

        Args:
            x (int): An integer representing the x-coordinate (horizontal).
            y (int): An integer representing the y-coordinate (vertical).

        Raises:
            ValueError: If either coordinate is outside the valid range of -8
            to 8 inclusive.
        """
        if not (Coordinate._checkBounds(x) and Coordinate._checkBounds(y)):
            raise ValueError("Coordinates must be between -8 and 8 inclusive.")
        self.x = x
        self.y = y

    def __str__(self) -> str:
        return f"({self.x}, {self.y})"

    def __repr__(self) -> str:
        return self.__str__()

    @staticmethod
    def _checkBounds(n: int) -> bool:
        """Checks if a number is between -8 and 8 inclusive.

        Args:
            n (int): Any number.

        Returns:
            bool: True if within bounds, False otherwise.
        """
        return -8 <= n <= 8

    def __eq__(self, other) -> bool:
        """Checks if two Coordinate objects are equal based on their x and y
        values.

        Args:
            other (Coordinate): Another Coordinate object to compare against.

        Returns:
            bool: True if the coordinates are equal, False otherwise.
        """
        if not isinstance(other, Coordinate):
            return False
        return self.x == other.x and self.y == other.y

    def __lt__(self, other) -> bool:
        """Defines a less-than comparison for Coordinate objects based on their
        x and y values. Note that this is for sorting purposes and does not
        have a mathematical meaning in terms of distance or direction.

        Args:
            other (Coordinate): Another Coordinate object to compare against.

        Returns:
            bool: True if this coordinate is less than the other, False
            otherwise.
        """
        if not isinstance(other, Coordinate):
            return NotImplemented
        if self.x < other.x:
            return True
        elif self.x == other.x:
            return self.y < other.y
        else:
            return False


if __name__ == "__main__":
    print(
        "You are running Coordinate.py directly. This file is meant to be"
        " imported as a module, so there is no code to run here."
    )
