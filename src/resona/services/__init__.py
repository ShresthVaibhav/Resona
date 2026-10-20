"""Shared services used by handlers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from resona.config.settings import Settings
    from resona.core.cache import TTLCache
    from resona.database import Database
    from resona.services.accounts import AccountService
    from resona.services.games import GameServices
    from resona.services.users import UserService


@dataclass(frozen=True, slots=True)
class Services:
    """Bundle of stateless services, built once at startup."""

    users: UserService
    accounts: AccountService
    games: GameServices
    cache: TTLCache[Any, Any] | None = None

    @classmethod
    def from_database(cls, database: Database, settings: Settings) -> Services:
        # Imported here so game modules can import ``services.api`` without
        # triggering a package-level circular import.
        from resona.core.cache import TTLCache
        from resona.services.accounts import AccountService
        from resona.services.games import GameServices
        from resona.services.users import UserService

        accounts = AccountService(
            settings,
            database.credentials,
            database.game_accounts,
        )
        cache = TTLCache(ttl=settings.CACHE_TTL, enabled=settings.CACHE_ENABLED)
        return cls(
            users=UserService(database.users, database.settings),
            accounts=accounts,
            games=GameServices(accounts, cache),
            cache=cache,
        )


__all__ = ["Services"]
