"""MongoDB persistence layer."""

from __future__ import annotations

from resona.database.client import Database
from resona.database.collections import (
    COLLECTION_CREDENTIALS,
    COLLECTION_GAME_ACCOUNTS,
    COLLECTION_USER_SETTINGS,
    COLLECTION_USERS,
    CredentialsDocument,
    GameAccountDocument,
    UserDocument,
    UserSettingsDocument,
)
from resona.database.indexes import ensure_indexes
from resona.database.repositories import (
    CredentialsRepository,
    GameAccountRepository,
    SettingsRepository,
    UserRepository,
)

__all__ = [
    "COLLECTION_CREDENTIALS",
    "COLLECTION_GAME_ACCOUNTS",
    "COLLECTION_USERS",
    "COLLECTION_USER_SETTINGS",
    "CredentialsDocument",
    "CredentialsRepository",
    "Database",
    "GameAccountDocument",
    "GameAccountRepository",
    "SettingsRepository",
    "UserDocument",
    "UserRepository",
    "UserSettingsDocument",
    "ensure_indexes",
]
