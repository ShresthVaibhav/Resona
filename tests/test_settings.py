"""Settings loading and validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from resona.config.settings import Settings, reset_settings_cache, validate_settings
from resona.core.errors import ConfigurationError


def test_admin_ids_accept_commas_and_semicolons() -> None:
    settings = Settings(
        BOT_TOKEN="test",
        BOT_OWNER_ID=1,
        MONGO_URI="mongodb://localhost:27017",
        BOT_ADMIN_IDS="2, 3;4",
    )
    assert settings.admin_ids == frozenset({2, 3, 4})


def test_admin_ids_default_to_empty() -> None:
    settings = Settings(
        BOT_TOKEN="test",
        BOT_OWNER_ID=1,
        MONGO_URI="mongodb://localhost:27017",
    )
    assert settings.admin_ids == frozenset()


def test_log_level_is_normalised() -> None:
    settings = Settings(
        BOT_TOKEN="test",
        BOT_OWNER_ID=1,
        MONGO_URI="mongodb://localhost:27017",
        LOG_LEVEL="debug",
    )
    assert settings.LOG_LEVEL == "DEBUG"


def test_missing_required_value_raises_configuration_error(monkeypatch) -> None:
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    reset_settings_cache()

    with pytest.raises(ConfigurationError, match="Invalid or missing configuration"):
        validate_settings()


def test_owner_id_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        Settings(
            BOT_TOKEN="test",
            BOT_OWNER_ID=0,
            MONGO_URI="mongodb://localhost:27017",
        )
