"""Persistence repositories."""

from __future__ import annotations

from resona.database.repositories.base import BaseRepository
from resona.database.repositories.credentials import CredentialsRepository
from resona.database.repositories.game_data import GameAccountRepository
from resona.database.repositories.settings import SettingsRepository
from resona.database.repositories.users import UserRepository

__all__ = [
    "BaseRepository",
    "CredentialsRepository",
    "GameAccountRepository",
    "SettingsRepository",
    "UserRepository",
]
