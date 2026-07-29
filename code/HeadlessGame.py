from typing import Literal

from MatchEngine import MatchEngine
from Player import BotPlayer


class HeadlessGame(MatchEngine):
    """For fast bot versus bot play."""

    def __init__(self, whitePlayer: BotPlayer, blackPlayer: BotPlayer) -> None:
        if whitePlayer is None or blackPlayer is None:
            raise ValueError(
                "HeadlessGame requires both whitePlayer and blackPlayer to be"
                " BotPlayers."
            )
        super().__init__(whitePlayer, blackPlayer)

    def playEpisode(self) -> Literal["white", "black", "draw"]:
        """Resets the board and plays one full game to completion.

        Returns:
            Literal["white", "black", "draw"]: The outcome of the game.
        """
        self._resetGameState()
        return self.runHeadless()

    def runHeadless(self) -> Literal["white", "black", "draw"]:
        """Plays a headless game.

        Returns:
            Literal["white", "black", "draw"]: The outcome of the game.
        """
        while True:
            player = self.getPlayerForColor(self.turn)
            assert player is not None

            decision = player.decideTurn(self.board)
            if decision is None:
                return "draw"

            self._applyBotDecision(decision)
            self._resolveHeadlessAbility()

            result = self._getGameResult()
            if result is not None:
                return result

    def _resolveHeadlessAbility(self) -> None:
        """Resolves the Dragon/Badgermole ability without a pop up."""
        if self.pendingAbilityTile is None:
            return

        tile = self.pendingAbilityTile
        targets, _ = self._getAbilityTargetsAndTitle(tile)

        if targets:
            player = self.getPlayerForColor(tile.color)
            assert player is not None

            chosenTarget = player.chooseAbilityTarget(tile, targets)
            self._applyAbility(tile, chosenTarget)

        self.pendingAbilityTile = None

    def playEpisodeCapped(self, maxTurns=300):
        self._resetGameState()
        for _ in range(maxTurns):
            player = self.getPlayerForColor(self.turn)
            assert player is not None

            decision = player.decideTurn(self.board)
            if decision is None:
                return "draw"
            self._applyBotDecision(decision)
            self._resolveHeadlessAbility()
            result = self._getGameResult()
            if result is not None:
                return result
        return "turn_limit"
