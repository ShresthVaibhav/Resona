"""Database client and lifecycle.

The client is created eagerly (PyMongo connects lazily) so repositories are
available immediately, while :meth:`Database.connect` performs the actual
connection check and index creation during application startup.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from pymongo import AsyncMongoClient

from resona.database.collections import (
    COLLECTION_CREDENTIALS,
    COLLECTION_GAME_ACCOUNTS,
    COLLECTION_USER_SETTINGS,
    COLLECTION_USERS,
)
from resona.database.indexes import ensure_indexes
from resona.database.repositories import (
    CredentialsRepository,
    GameAccountRepository,
    SettingsRepository,
    UserRepository,
)

logger = logging.getLogger("resona.database")

DEFAULT_TIMEOUT_MS = 5000


class Database:
    """Owns the Mongo client and exposes typed repositories."""

    def __init__(
        self,
        uri: str,
        database_name: str = "resona",
        *,
        client_factory: Callable[..., Any] | None = None,
        timeout_ms: int = DEFAULT_TIMEOUT_MS,
    ) -> None:
        factory = client_factory or AsyncMongoClient
        self._client = factory(uri, tz_aware=True, serverSelectionTimeoutMS=timeout_ms)
        self._database = self._client[database_name]
        self._connected = False

        self.users = UserRepository(self._database[COLLECTION_USERS])
        self.settings = SettingsRepository(self._database[COLLECTION_USER_SETTINGS])
        self.credentials = CredentialsRepository(self._database[COLLECTION_CREDENTIALS])
        self.game_accounts = GameAccountRepository(
            self._database[COLLECTION_GAME_ACCOUNTS]
        )

    @property
    def client(self) -> Any:
        return self._client

    @property
    def database(self) -> Any:
        return self._database

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self) -> None:
        """Verify connectivity and ensure indexes. Safe to call twice."""
        if self._connected:
            return

        await self._client.admin.command("ping")
        await ensure_indexes(self._database)

        self._connected = True
        logger.info("Connected to the %r database.", self._database.name)

    async def close(self) -> None:
        """Release the client. Safe to call when not connected."""
        try:
            await self._client.close()
        finally:
            self._connected = False
        logger.info("Database connection closed.")

    async def __aenter__(self) -> Database:
        await self.connect()
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.close()
