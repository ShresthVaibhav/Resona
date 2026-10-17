from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Telegram
    BOT_TOKEN: str = Field(min_length=1)
    BOT_OWNER_ID: int
    BOT_USERNAME: str = ""

    # MongoDB
    MONGO_URI: str = Field(min_length=1)
    MONGO_DATABASE: str = "resona"

    # Application
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    TIMEZONE: str = "Asia/Kolkata"

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


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
