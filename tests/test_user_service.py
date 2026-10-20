"""User record and preference service."""

from __future__ import annotations

from types import SimpleNamespace

from resona.database.repositories import SettingsRepository, UserRepository
from resona.services.users import UserService
from tests.fakes import FakeCollection


def _service() -> UserService:
    return UserService(
        UserRepository(FakeCollection(unique_keys=[("telegram_id",)])),
        SettingsRepository(FakeCollection(unique_keys=[("telegram_id",)])),
    )


def _telegram_user(**overrides) -> SimpleNamespace:
    values = {
        "id": 1,
        "username": "nitin",
        "first_name": "Nitin",
        "language_code": "en",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


async def test_ensure_user_creates_record_and_defaults() -> None:
    service = _service()

    document = await service.ensure_user(_telegram_user())

    assert document.telegram_id == 1
    assert document.username == "nitin"
    assert document.first_name == "Nitin"

    settings = await service.get_settings(1)
    assert settings.locale == "en"
    assert settings.timezone == "UTC"
    assert settings.notifications_enabled is True
    assert settings.event_digest_enabled is False


async def test_ensure_user_refreshes_profile_fields() -> None:
    service = _service()
    await service.ensure_user(_telegram_user())

    updated = await service.ensure_user(_telegram_user(username="renamed"))

    assert updated.username == "renamed"


async def test_update_settings_validates_fields() -> None:
    service = _service()
    await service.ensure_user(_telegram_user())

    settings = await service.update_settings(
        1,
        timezone="Asia/Kolkata",
        notifications_enabled=False,
        event_digest_enabled=True,
    )

    assert settings.timezone == "Asia/Kolkata"
    assert settings.notifications_enabled is False
    assert settings.event_digest_enabled is True
