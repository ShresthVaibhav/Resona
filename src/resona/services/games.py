"""Registry of implemented game services."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from resona.config.constants import (
    GAME_GENSHIN,
    GAME_HSR,
    GAME_LABELS,
    GAME_ZZZ,
)
from resona.core.errors import UserError
from resona.games.base import GameService
from resona.games.genshin import GenshinService
from resona.games.hsr import StarRailService
from resona.games.zzz import ZZZService

if TYPE_CHECKING:
    from resona.core.cache import TTLCache
    from resona.services.accounts import AccountService


class GameServices:
    """Resolves a game identifier to its service."""

    def __init__(
        self,
        accounts: AccountService,
        cache: TTLCache[Any, Any] | None = None,
    ) -> None:
        self._services: dict[str, GameService] = {
            GAME_GENSHIN: GenshinService(accounts, cache),
            GAME_HSR: StarRailService(accounts, cache),
            GAME_ZZZ: ZZZService(accounts, cache),
        }

    def get(self, game: str) -> GameService:
        try:
            return self._services[game]
        except KeyError as exc:
            label = GAME_LABELS.get(game, game)
            raise UserError(f"{label} is not supported yet.") from exc

    @property
    def games(self) -> tuple[str, ...]:
        return tuple(self._services)


__all__ = ["GameServices"]
