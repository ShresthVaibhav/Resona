"""Runtime availability of games, commands and features.

The controller is stored on ``application.bot_data["resona_availability"]`` and
consulted by the wrapper layer before every handler runs. It supports global
maintenance mode, per-game and per-command switch-off, per-chat overrides and
named feature flags. All checks are async so a database-backed implementation
can be dropped in later without changing call sites.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AvailabilityController:
    """Decides whether a game, command or feature is currently available."""

    maintenance: bool = False
    maintenance_message: str = "Resona is under maintenance. Please try again later."
    disabled_games: set[str] = field(default_factory=set)
    disabled_commands: set[str] = field(default_factory=set)
    feature_flags: dict[str, bool] = field(default_factory=dict)
    # chat_id -> disabled command IDs
    chat_command_overrides: dict[int, set[str]] = field(default_factory=dict)

    # -- games ---------------------------------------------------------------
    async def is_game_enabled(
        self, *, game: str | None, chat_id: int | None = None
    ) -> bool:
        if self.maintenance:
            return False
        if game is None:
            return True
        return game not in self.disabled_games

    # -- commands ------------------------------------------------------------
    async def is_command_enabled(
        self,
        *,
        command_id: str,
        game: str | None = None,
        chat_id: int | None = None,
    ) -> bool:
        if self.maintenance:
            return False
        if command_id in self.disabled_commands:
            return False
        if game is not None and game in self.disabled_games:
            return False
        if chat_id is not None:
            overrides = self.chat_command_overrides.get(chat_id)
            if overrides and command_id in overrides:
                return False
        return True

    # -- feature flags -------------------------------------------------------
    def is_feature_enabled(self, name: str, *, default: bool = False) -> bool:
        return self.feature_flags.get(name, default)

    def set_feature_flag(self, name: str, enabled: bool) -> None:
        self.feature_flags[name] = enabled

    # -- administratively modifying state ------------------------------------
    def set_maintenance(self, enabled: bool, *, message: str | None = None) -> None:
        self.maintenance = enabled
        if message is not None:
            self.maintenance_message = message

    def disable_game(self, game: str) -> None:
        self.disabled_games.add(game)

    def enable_game(self, game: str) -> None:
        self.disabled_games.discard(game)

    def disable_command(self, command_id: str) -> None:
        self.disabled_commands.add(command_id)

    def enable_command(self, command_id: str) -> None:
        self.disabled_commands.discard(command_id)

    def set_chat_command_disabled(
        self, chat_id: int, command_id: str, *, disabled: bool
    ) -> None:
        overrides = self.chat_command_overrides.setdefault(chat_id, set())
        if disabled:
            overrides.add(command_id)
        else:
            overrides.discard(command_id)

    def unavailable_message(self, *, game: str | None = None) -> str:
        if self.maintenance:
            return self.maintenance_message
        return "This feature is temporarily unavailable."

    def snapshot(self) -> dict[str, object]:
        """A JSON-friendly view of current state, for diagnostics."""
        return {
            "maintenance": self.maintenance,
            "disabled_games": sorted(self.disabled_games),
            "disabled_commands": sorted(self.disabled_commands),
            "feature_flags": dict(self.feature_flags),
        }
