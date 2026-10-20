"""Application construction and shared-state wiring."""

from __future__ import annotations

from telegram.ext import Application

from resona.application import _post_init, _post_shutdown, build_application
from resona.config.settings import Settings
from resona.core.availability import AvailabilityController
from resona.core.ratelimit import RateLimiter
from resona.database.repositories import (
    CredentialsRepository,
    GameAccountRepository,
    SettingsRepository,
    UserRepository,
)
from resona.services import Services
from resona.wrappers import command
from resona.wrappers.registry import get_commands
from tests.fakes import FakeCollection


class StubDatabase:
    """Records lifecycle calls without touching MongoDB."""

    def __init__(self) -> None:
        self.connected = False
        self.closed = False

        self.users = UserRepository(FakeCollection(unique_keys=[("telegram_id",)]))
        self.settings = SettingsRepository(
            FakeCollection(unique_keys=[("telegram_id",)])
        )
        self.credentials = CredentialsRepository(
            FakeCollection(unique_keys=[("telegram_id", "game", "uid")])
        )
        self.game_accounts = GameAccountRepository(
            FakeCollection(unique_keys=[("telegram_id", "game", "uid")])
        )

    async def connect(self) -> None:
        self.connected = True

    async def close(self) -> None:
        self.closed = True


def _settings(**overrides) -> Settings:
    values = {
        "BOT_TOKEN": "123456:TEST-TOKEN",
        "BOT_OWNER_ID": 1,
        "MONGO_URI": "mongodb://localhost:27017",
    }
    values.update(overrides)
    return Settings(**values)


def _build(**overrides):
    database = StubDatabase()
    application = build_application(_settings(**overrides), database=database)
    return application, database


def test_build_application_wires_shared_state() -> None:
    @command("selftest", description="Wiring check", private=True)
    async def selftest(update, context):  # pragma: no cover - not invoked
        ...

    application, database = _build()

    assert isinstance(application, Application)
    assert application.bot_data["db"] is database
    assert isinstance(application.bot_data["settings"], Settings)
    assert isinstance(application.bot_data["services"], Services)
    assert isinstance(
        application.bot_data["resona_availability"], AvailabilityController
    )
    assert isinstance(application.bot_data["resona_ratelimiter"], RateLimiter)
    assert application.bot_data["BOT_ADMIN_IDS"] == set()


def test_build_application_registers_declared_command() -> None:
    @command("notes", description="Show notes", game="genshin", category="Genshin")
    async def notes(update, context):  # pragma: no cover
        ...

    _build()

    assert "genshin_notes" in get_commands()


def test_maintenance_mode_is_reflected_in_availability() -> None:
    @command("healthcheck", description="Liveness check", private=True)
    async def healthcheck(update, context):  # pragma: no cover
        ...

    application, _ = _build(MAINTENANCE_MODE=True)

    availability = application.bot_data["resona_availability"]
    assert availability.maintenance is True


async def test_post_init_connects_the_database(monkeypatch) -> None:
    application, database = _build()

    async def _noop(_application) -> None:
        return None

    monkeypatch.setattr("resona.application.register_bot_commands", _noop)

    await _post_init(application)

    assert database.connected is True


async def test_post_shutdown_closes_the_database() -> None:
    application, database = _build()

    await _post_shutdown(application)

    assert database.closed is True
