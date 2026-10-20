"""Daily check-in job and its scheduler wiring."""

from __future__ import annotations

from datetime import UTC, time
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram.error import Forbidden

from resona.core.errors import UserError
from resona.jobs.cache import run_cache_maintenance
from resona.jobs.checkin import (
    AccountReport,
    render_summary,
    run_checkin,
    run_daily_checkin,
)
from resona.jobs.scheduler import (
    CACHE_PURGE_INTERVAL,
    CACHE_PURGE_JOB,
    DAILY_CHECKIN_JOB,
    DAILY_EVENT_DIGEST_JOB,
    register_jobs,
)


class FakeAccounts:
    def __init__(self, credentials: list[SimpleNamespace]) -> None:
        self.credentials = credentials

    async def list_credentials(self, game: str | None = None) -> list[SimpleNamespace]:
        return self.credentials


class FakeUsers:
    def __init__(self, preferences: dict[int, SimpleNamespace]) -> None:
        self.preferences = preferences

    async def get_settings(self, telegram_id: int) -> SimpleNamespace:
        return self.preferences[telegram_id]


class FakeGames:
    def __init__(self, services: dict[str, SimpleNamespace]) -> None:
        self.services = services

    def get(self, game: str) -> SimpleNamespace:
        return self.services[game]


def _credential(telegram_id: int, game: str, uid: str) -> SimpleNamespace:
    return SimpleNamespace(telegram_id=telegram_id, game=game, uid=uid)


def _service(
    *, claimed: bool = True, error: Exception | None = None
) -> SimpleNamespace:
    return SimpleNamespace(
        checkin_account=AsyncMock(
            return_value=SimpleNamespace(nickname="Traveler", claimed=claimed),
            side_effect=error,
        )
    )


def _services(
    credentials: list[SimpleNamespace],
    preferences: dict[int, SimpleNamespace],
    games: dict[str, SimpleNamespace],
) -> SimpleNamespace:
    return SimpleNamespace(
        accounts=FakeAccounts(credentials),
        users=FakeUsers(preferences),
        games=FakeGames(games),
    )


def _preferences(enabled: bool = True) -> SimpleNamespace:
    return SimpleNamespace(notifications_enabled=enabled)


async def test_run_checkin_groups_accounts_and_skips_disabled_users() -> None:
    credentials = [
        _credential(1, "genshin", "800000001"),
        _credential(1, "hsr", "800000002"),
        _credential(2, "genshin", "800000003"),
    ]
    games = {
        "genshin": _service(claimed=True),
        "hsr": _service(claimed=False),
    }
    services = _services(
        credentials, {1: _preferences(), 2: _preferences(False)}, games
    )
    bot = SimpleNamespace(send_message=AsyncMock())

    await run_checkin(services, bot)

    bot.send_message.assert_awaited_once()
    chat_id = bot.send_message.await_args.kwargs["chat_id"]
    text = bot.send_message.await_args.kwargs["text"]
    assert chat_id == 1
    assert "Genshin Impact — Traveler: claimed" in text
    assert "Honkai: Star Rail — Traveler: already claimed" in text
    assert "800000003" not in text


async def test_run_checkin_reports_failures_without_stopping() -> None:
    credentials = [
        _credential(1, "genshin", "800000001"),
        _credential(1, "hsr", "800000002"),
    ]
    games = {
        "genshin": _service(error=UserError("credentials expired")),
        "hsr": _service(claimed=True),
    }
    services = _services(credentials, {1: _preferences()}, games)
    bot = SimpleNamespace(send_message=AsyncMock())

    await run_checkin(services, bot)

    text = bot.send_message.await_args.kwargs["text"]
    assert "Genshin Impact — 800000001: failed: credentials expired" in text
    assert "Honkai: Star Rail — Traveler: claimed" in text


async def test_run_checkin_reports_unexpected_failures_safely() -> None:
    services = _services(
        [_credential(1, "genshin", "800000001")],
        {1: _preferences()},
        {"genshin": _service(error=RuntimeError("secret upstream payload"))},
    )
    bot = SimpleNamespace(send_message=AsyncMock())

    await run_checkin(services, bot)

    text = bot.send_message.await_args.kwargs["text"]
    assert "temporarily unavailable" in text
    assert "secret upstream payload" not in text


async def test_run_checkin_survives_a_blocked_user() -> None:
    services = _services(
        [_credential(1, "genshin", "800000001")],
        {1: _preferences()},
        {"genshin": _service()},
    )
    bot = SimpleNamespace(send_message=AsyncMock(side_effect=Forbidden("blocked")))

    await run_checkin(services, bot)


async def test_run_checkin_does_nothing_without_credentials() -> None:
    bot = SimpleNamespace(send_message=AsyncMock())
    services = _services([], {}, {})

    await run_checkin(services, bot)

    bot.send_message.assert_not_awaited()


async def test_run_daily_checkin_requires_services() -> None:
    context = SimpleNamespace(
        application=SimpleNamespace(bot_data={}, bot=SimpleNamespace())
    )

    await run_daily_checkin(context)


async def test_run_daily_checkin_uses_application_services() -> None:
    services = _services(
        [_credential(1, "genshin", "800000001")],
        {1: _preferences()},
        {"genshin": _service()},
    )
    bot = SimpleNamespace(send_message=AsyncMock())
    context = SimpleNamespace(
        application=SimpleNamespace(bot_data={"services": services}, bot=bot)
    )

    await run_daily_checkin(context)

    bot.send_message.assert_awaited_once()
    assert (
        "Genshin Impact — Traveler: claimed"
        in (bot.send_message.await_args.kwargs["text"])
    )


def test_render_summary_covers_every_state() -> None:
    text = render_summary(
        [
            AccountReport(label="Genshin Impact", name="A", claimed=True),
            AccountReport(label="Honkai: Star Rail", name="B", claimed=False),
            AccountReport(label="Zenless Zone Zero", name="C", error="nope"),
        ]
    )

    assert "Genshin Impact — A: claimed" in text
    assert "Honkai: Star Rail — B: already claimed" in text
    assert "Zenless Zone Zero — C: failed: nope" in text


def test_register_jobs_schedules_the_daily_checkin() -> None:
    settings = SimpleNamespace(
        CHECKIN_ENABLED=True,
        CHECKIN_HOUR_UTC=16,
        CHECKIN_MINUTE_UTC=5,
        EVENT_DIGEST_ENABLED=False,
    )
    queue = SimpleNamespace(run_daily=MagicMock())
    application = SimpleNamespace(bot_data={"settings": settings}, job_queue=queue)

    register_jobs(application)

    queue.run_daily.assert_called_once()
    call = queue.run_daily.call_args
    assert call.kwargs["name"] == DAILY_CHECKIN_JOB
    assert call.kwargs["time"] == time(16, 5, tzinfo=UTC)


def test_register_jobs_schedules_the_event_digest() -> None:
    settings = SimpleNamespace(
        CHECKIN_ENABLED=False,
        EVENT_DIGEST_ENABLED=True,
        EVENT_DIGEST_HOUR_UTC=9,
        EVENT_DIGEST_MINUTE_UTC=30,
    )
    queue = SimpleNamespace(run_daily=MagicMock())
    application = SimpleNamespace(bot_data={"settings": settings}, job_queue=queue)

    register_jobs(application)

    queue.run_daily.assert_called_once()
    call = queue.run_daily.call_args
    assert call.kwargs["name"] == DAILY_EVENT_DIGEST_JOB
    assert call.kwargs["time"] == time(9, 30, tzinfo=UTC)


def test_register_jobs_respects_the_feature_flags() -> None:
    settings = SimpleNamespace(
        CHECKIN_ENABLED=False,
        EVENT_DIGEST_ENABLED=False,
    )
    queue = SimpleNamespace(run_daily=MagicMock())
    application = SimpleNamespace(bot_data={"settings": settings}, job_queue=queue)

    register_jobs(application)

    queue.run_daily.assert_not_called()


def test_register_jobs_schedules_cache_maintenance() -> None:
    settings = SimpleNamespace(
        CHECKIN_ENABLED=False,
        EVENT_DIGEST_ENABLED=False,
        CACHE_ENABLED=True,
    )
    queue = SimpleNamespace(run_daily=MagicMock(), run_repeating=MagicMock())
    application = SimpleNamespace(bot_data={"settings": settings}, job_queue=queue)

    register_jobs(application)

    queue.run_daily.assert_not_called()
    queue.run_repeating.assert_called_once()
    call = queue.run_repeating.call_args
    assert call.kwargs["name"] == CACHE_PURGE_JOB
    assert call.kwargs["interval"] == CACHE_PURGE_INTERVAL


async def test_run_cache_maintenance_purges_expired_entries() -> None:
    cache = MagicMock()
    cache.purge_expired.return_value = 2
    services = SimpleNamespace(cache=cache)
    context = SimpleNamespace(
        application=SimpleNamespace(bot_data={"services": services})
    )

    await run_cache_maintenance(context)

    cache.purge_expired.assert_called_once()


async def test_run_cache_maintenance_without_services_does_not_raise() -> None:
    context = SimpleNamespace(application=SimpleNamespace(bot_data={}))

    await run_cache_maintenance(context)


def test_register_jobs_without_a_job_queue_does_not_raise() -> None:
    settings = SimpleNamespace(
        CHECKIN_ENABLED=True,
        CHECKIN_HOUR_UTC=16,
        CHECKIN_MINUTE_UTC=5,
        EVENT_DIGEST_ENABLED=True,
        EVENT_DIGEST_HOUR_UTC=9,
        EVENT_DIGEST_MINUTE_UTC=0,
    )
    application = SimpleNamespace(bot_data={"settings": settings}, job_queue=None)

    register_jobs(application)


def test_register_jobs_without_settings_does_not_raise() -> None:
    application = SimpleNamespace(bot_data={}, job_queue=SimpleNamespace())

    register_jobs(application)


@pytest.mark.parametrize("enabled", [True, False])
def test_checkin_settings_are_valid(enabled: bool) -> None:
    from resona.config.settings import Settings

    settings = Settings(
        BOT_TOKEN="123456:TEST-TOKEN",
        BOT_OWNER_ID=1,
        MONGO_URI="mongodb://localhost:27017",
        CHECKIN_ENABLED=enabled,
    )

    assert settings.CHECKIN_ENABLED is enabled
    assert settings.CHECKIN_HOUR_UTC == 16
    assert settings.CHECKIN_MINUTE_UTC == 5
    assert settings.EVENT_DIGEST_ENABLED is True
    assert settings.EVENT_DIGEST_HOUR_UTC == 9
    assert settings.EVENT_DIGEST_MINUTE_UTC == 0
    assert settings.EVENT_DIGEST_DAYS == 3
