"""Application settings.

Settings are loaded lazily so that importing any module never requires a fully
configured environment. Startup validates them once and fails with a single,
readable error (see :func:`validate_settings`).
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from the environment and ``.env``."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Telegram
    BOT_TOKEN: str = Field(min_length=1)
    BOT_OWNER_ID: int = Field(gt=0)
    BOT_USERNAME: str = ""
    BOT_ADMIN_IDS: str = ""

    # MongoDB
    MONGO_URI: str = Field(min_length=1)
    MONGO_DATABASE: str = "resona"

    # Credential encryption (required for account linking)
    COOKIE_ENCRYPTION_KEY: str = ""

    # Application
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    TIMEZONE: str = "Asia/Kolkata"
    DEFAULT_LOCALE: str = "en"

    # Telegram Bot API server (optional)
    LOCAL_BOT_API: bool = False
    BOT_API_BASE_URL: str = "http://127.0.0.1:8081/bot"
    BOT_API_FILE_URL: str = "http://127.0.0.1:8081/file/bot"

    # Performance
    CONCURRENT_UPDATES: int = Field(default=32, ge=1)
    DROP_PENDING_UPDATES: bool = False

    # Caching
    CACHE_ENABLED: bool = True
    CACHE_TTL: int = Field(default=300, ge=0)

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = Field(default=20, ge=0)

    # Rich messages (Bot API 10.1+)
    RICH_MESSAGES_ENABLED: bool = True

    # Background jobs
    CHECKIN_ENABLED: bool = True
    CHECKIN_HOUR_UTC: int = Field(default=16, ge=0, le=23)
    CHECKIN_MINUTE_UTC: int = Field(default=5, ge=0, le=59)

    # Users opt in with ``/settings event_digest on``.
    EVENT_DIGEST_ENABLED: bool = True
    EVENT_DIGEST_HOUR_UTC: int = Field(default=9, ge=0, le=23)
    EVENT_DIGEST_MINUTE_UTC: int = Field(default=0, ge=0, le=59)
    EVENT_DIGEST_DAYS: int = Field(default=3, ge=1, le=14)

    # Availability
    MAINTENANCE_MODE: bool = False
    MAINTENANCE_MESSAGE: str = "Resona is under maintenance. Please try again later."

    @field_validator("LOG_LEVEL")
    @classmethod
    def _upper_log_level(cls, value: str) -> str:
        return value.upper()

    @property
    def admin_ids(self) -> frozenset[int]:
        """Bot administrator Telegram IDs parsed from a comma-separated value."""
        ids: set[int] = set()
        for chunk in self.BOT_ADMIN_IDS.replace(";", ",").split(","):
            chunk = chunk.strip()
            if chunk:
                ids.add(int(chunk))
        return frozenset(ids)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings, loading them on first use."""
    return Settings()


def validate_settings() -> Settings:
    """Load and return settings, raising a clear error when misconfigured.

    Raises:
        ConfigurationError: when required values are missing or invalid.
    """
    from resona.core.errors import ConfigurationError

    try:
        return get_settings()
    except Exception as exc:  # pydantic ValidationError
        raise ConfigurationError(
            "Invalid or missing configuration. Copy .env.example to .env and "
            f"set the required values.\n\n{exc}"
        ) from exc


def reset_settings_cache() -> None:
    """Clear the cached settings. Intended for tests."""
    get_settings.cache_clear()
