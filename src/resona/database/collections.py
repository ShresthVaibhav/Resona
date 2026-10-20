"""Collection names and typed document models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

COLLECTION_USERS = "users"
COLLECTION_USER_SETTINGS = "user_settings"
COLLECTION_CREDENTIALS = "user_credentials"
COLLECTION_GAME_ACCOUNTS = "game_accounts"

# Collections that participate in index creation at startup.
INDEXED_COLLECTIONS = (
    COLLECTION_USERS,
    COLLECTION_USER_SETTINGS,
    COLLECTION_CREDENTIALS,
    COLLECTION_GAME_ACCOUNTS,
)


class Document(BaseModel):
    """Base for persisted documents.

    Unknown fields (such as Mongo's ``_id``) are ignored so documents can be
    validated directly from driver results.
    """

    model_config = ConfigDict(extra="ignore")

    def to_record(self) -> dict[str, Any]:
        """Serialise the document for storage."""
        return self.model_dump()


class UserDocument(Document):
    telegram_id: int
    username: str | None = None
    first_name: str | None = None
    language_code: str | None = None
    is_blocked: bool = False
    created_at: datetime
    updated_at: datetime
    last_seen_at: datetime


class UserSettingsDocument(Document):
    telegram_id: int
    locale: str = "en"
    timezone: str = "UTC"
    default_game: str | None = None
    notifications_enabled: bool = True
    event_digest_enabled: bool = False
    created_at: datetime
    updated_at: datetime


class CredentialsDocument(Document):
    """Encrypted HoYoLAB credentials for one game account."""

    telegram_id: int
    game: str
    uid: str
    encrypted_cookies: str
    region: str | None = None
    hoyolab_id: int | None = None
    created_at: datetime
    updated_at: datetime


class GameAccountDocument(Document):
    telegram_id: int
    game: str
    uid: str
    nickname: str | None = None
    server: str | None = None
    level: int | None = None
    is_primary: bool = False
    last_synced_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
