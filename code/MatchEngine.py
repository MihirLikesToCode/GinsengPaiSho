from typing import Literal

from BasicTile import BasicTile
from Board import Board
from Coordinate import Coordinate
from MoveController import ClickResult, MoveController
from Player import BotPlayer, MoveDecision, TradeDecision, TurnDecision


class MatchEngine:
    """Holds the rules-level state of a match and the logic to advance it: the
    Board, whose turn it is, tile selection, and applying either a human's click
    or a bot's decision.
    """

    def __init__(
        self,
        whitePlayer: BotPlayer | None = None,
        blackPlayer: BotPlayer | None = None,
    ) -> None:
        """Creates a MatchEngine with two players. None for a human player.

        Args:
            whitePlayer (BotPlayer | None, optional): The white player. Defaults to None.
            blackPlayer (BotPlayer | None, optional): The black player. Defaults to None.
        """
        if whitePlayer is not None and whitePlayer.color != "white":
            raise ValueError("whitePlayer must be an BotPlayer with color='white'")
        if blackPlayer is not None and blackPlayer.color != "black":
            raise ValueError("blackPlayer must be an BotPlayer with color='black'")

        self.whitePlayer: BotPlayer | None = whitePlayer
        self.blackPlayer: BotPlayer | None = blackPlayer

        self.board: Board = Board()
        self.turn: Literal["white", "black"] = "white"
        self.moveController: MoveController = MoveController()

        self.pendingAbilityTile: BasicTile | None = None
        self.pendingTradeTile: BasicTile | None = None
        self.highlightedCoords: list[Coordinate] = []

    # ------------------------------------------------------------------ #
    # Turn state
    # ------------------------------------------------------------------ #

    def switchTurn(self) -> None:
        """Switches the turn from white to black, or vice versa."""
        self.turn = "black" if self.turn == "white" else "white"

    def getPlayerForColor(self, color: Literal["white", "black"]) -> BotPlayer | None:
        """Gets the player for a specific color.

        Args:
            color (Literal"white", "black"]): The target color.

        Returns:
            BotPlayer | None: The player. None if the color is controlled by a human.
        """
        return self.whitePlayer if color == "white" else self.blackPlayer

    def _resetGameState(self) -> None:
        """Resets the game."""
        self.board = Board()
        self.turn = "white"
        self.moveController = MoveController()
        self.pendingAbilityTile = None
        self.pendingTradeTile = None
        self.highlightedCoords = []

    def _getGameResult(self) -> Literal["white", "black", "draw"] | None:
        """Gets the game result. None if the game is unfinished/on-going.

        Returns:
            Literal["white", "black", "draw"] | None: The team that won, draw,
              or the game isn't over.
        """
        winner = self.board.checkIfAColorHasWon()
        if winner is not None:
            return winner
        if self.board.checkForDraw():
            return "draw"
        return None

    # ------------------------------------------------------------------ #
    # Applying a click
    # ------------------------------------------------------------------ #

    def applyClick(self, clickedCoord: Coordinate | None) -> None:
        """Applies a click to the board. Either from a mouse or from a bot.

        Args:
            clickedCoord (Coordinate | None): The target coordinate.
        """
        result: ClickResult = self.moveController.handleClick(
            clickedCoord, self.board, self.turn
        )
        self.highlightedCoords = result.highlightCoords

        if result.tradeEligibleTile is not None:
            self._onTradeEligible(result.tradeEligibleTile)

        if result.turnEnded:
            self.switchTurn()
            self.pendingAbilityTile = result.pendingAbilityTile

    def _onTradeEligible(self, tile: BasicTile) -> None:
        """Hook for trading via mouse input only. Useless, runs no code."""
        pass

    def _getAbilityTargetsAndTitle(
        self, tile: BasicTile
    ) -> tuple[list[BasicTile], str]:
        """Gets the targets of the ability and the name of the pop-up title for a given tile

        Args:
            tile (BasicTile): The tile. (Must be a Dragon or a Badgermole).

        Returns:
            tuple[list[BasicTile], str]: The list of targets, the title text for the
            pop-up window. `([], "")` if `tile` is not a valid tile.
        """
        if tile.pieceType == "Dragon":
            targets = tile.getDragonPushTargets(
                self.board.tiles, self.board.coordinates
            )
            return targets, "Dragon Push Ability"

        if tile.pieceType == "Badgermole":
            targets = tile.getBadgermoleTargets(
                self.board.tiles, self.board.coordinates
            )
            return targets, "Badgermole Flip Ability"

        return [], ""

    def _applyAbility(
        self, abilityTile: BasicTile | None, targetTile: BasicTile | None
    ) -> None:
        """Appies an ability. Does nothing if either parameter is None.

        Args:
            abilityTile (BasicTile | None): The tile that is using its ability.
            targetTile (BasicTile | None): The tile that the ability is being applied onto.
        """
        if abilityTile is None or targetTile is None:
            return

        if abilityTile.pieceType == "Dragon":
            abilityTile.applyDragonPush(
                targetTile, self.board.tiles, self.board.coordinates
            )
        elif abilityTile.pieceType == "Badgermole":
            abilityTile.applyBadgermoleFlip(
                targetTile, self.board.tiles, self.board.coordinates
            )

    # ------------------------------------------------------------------ #
    # Applying a bot's decision
    # ------------------------------------------------------------------ #

    def _applyBotDecision(self, decision: TurnDecision) -> None:
        """Applies a bot decision, based on if it's a MoveDecision or a TradeDecision

        Args:
            decision (TurnDecision): The decision for a turn.
        """
        if isinstance(decision, MoveDecision):
            self._applyBotMove(decision)
        elif isinstance(decision, TradeDecision):
            self._applyBotTrade(decision)
        else:
            raise TypeError("This shouldn't be possible")

    def _applyBotMove(self, decision: MoveDecision) -> None:
        """Applies a bot's MoveDecision to the board.

        Args:
            decision (MoveDecision): The MoveDecision.
        """
        bot: BotPlayer | None = self.getPlayerForColor(self.turn)
        assert bot is not None

        self.applyClick(decision.fromCoord)

        selected: BasicTile | None = self.moveController.selectedTile
        if selected is None or selected.color != self.turn:
            raise ValueError(
                f"Bot proposed an illegal move: no controllable tile at"
                f" {decision.fromCoord}"
            )
        if decision.toCoord not in self.moveController.validMoves:
            raise ValueError(
                f"Bot proposed an illegal move: {decision.toCoord} is not a"
                f" valid destination for {decision.fromCoord}"
            )

        self.applyClick(decision.toCoord)

    def _applyBotTrade(self, decision: TradeDecision) -> None:
        """Applies a bot's TradeDecision to the board.

        Args:
            decision (TradeDecision): The TradeDecision.
        """
        templeTile: BasicTile | None = self.board.getTileAtCoord(decision.templeCoord)
        if templeTile is None:
            raise ValueError(
                f"Bot proposed a trade at an empty coordinate: {decision.templeCoord}"
            )

        traded: bool = self.board.exchangeAtSideTemple(templeTile, decision.tile)
        if not traded:
            raise ValueError("Bot proposed an illegal temple trade")

        self.moveController.selectedTile = None
        self.moveController.validMoves = []
        self.highlightedCoords = []
        self.switchTurn()
