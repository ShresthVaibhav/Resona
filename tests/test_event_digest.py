"""Opt-in event digest job."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

from telegram.error import Forbidden

from resona.core.errors import UserError
from resona.games.common import EventSummary, GameEventDigest
from resona.jobs.event_digest import (
    DigestSection,
    render_digest,
    run_daily_event_digest,
    run_event_digest,
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


def _preferences(
    *, notifications: bool = True, event_digest: bool = True
) -> SimpleNamespace:
    return SimpleNamespace(
        notifications_enabled=notifications,
        event_digest_enabled=event_digest,
    )


def _service(
    *,
    events: tuple[EventSummary, ...] = (),
    error: Exception | None = None,
) -> SimpleNamespace:
    digest = GameEventDigest(nickname="Traveler", uid="800000001", events=events)
    return SimpleNamespace(
        events_ending=AsyncMock(return_value=digest, side_effect=error)
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


async def test_run_event_digest_sends_only_to_opted_in_users() -> None:
    credentials = [
        _credential(1, "genshin", "800000001"),
        _credential(1, "hsr", "800000002"),
        _credential(2, "genshin", "800000003"),
        _credential(3, "genshin", "800000004"),
    ]
    games = {
        "genshin": _service(events=(EventSummary("Windblume", 3600),)),
        "hsr": _service(events=(EventSummary("Cosmodyssey", 7200),)),
    }
    services = _services(
        credentials,
        {
            1: _preferences(),
            2: _preferences(event_digest=False),
            3: _preferences(notifications=False),
        },
        games,
    )
    bot = SimpleNamespace(send_message=AsyncMock())

    await run_event_digest(services, bot, days=3)

    bot.send_message.assert_awaited_once()
    call = bot.send_message.await_args.kwargs
    assert call["chat_id"] == 1
    assert "Events ending in the next 3 days" in call["text"]
    assert "Genshin Impact - Traveler" in call["text"]
    assert "Windblume: ends in 1h" in call["text"]
    assert "Honkai: Star Rail - Traveler" in call["text"]
    assert "Cosmodyssey: ends in 2h" in call["text"]


async def test_run_event_digest_deduplicates_games_per_user() -> None:
    services = _services(
        [
            _credential(1, "genshin", "800000001"),
            _credential(1, "genshin", "800000002"),
        ],
        {1: _preferences()},
        {"genshin": _service(events=(EventSummary("Windblume", 3600),))},
    )
    bot = SimpleNamespace(send_message=AsyncMock())

    await run_event_digest(services, bot)

    services.games.get("genshin").events_ending.assert_awaited_once()
    bot.send_message.assert_awaited_once()


async def test_run_event_digest_skips_users_without_upcoming_events() -> None:
    services = _services(
        [_credential(1, "genshin", "800000001")],
        {1: _preferences()},
        {"genshin": _service()},
    )
    bot = SimpleNamespace(send_message=AsyncMock())

    await run_event_digest(services, bot)

    bot.send_message.assert_not_awaited()


async def test_run_event_digest_reports_errors_beside_other_games() -> None:
    services = _services(
        [
            _credential(1, "genshin", "800000001"),
            _credential(1, "hsr", "800000002"),
        ],
        {1: _preferences()},
        {
            "genshin": _service(error=UserError("credentials expired")),
            "hsr": _service(events=(EventSummary("Cosmodyssey", 7200),)),
        },
    )
    bot = SimpleNamespace(send_message=AsyncMock())

    await run_event_digest(services, bot)

    text = bot.send_message.await_args.kwargs["text"]
    assert "Cosmodyssey: ends in 2h" in text
    assert "Could not refresh: Genshin Impact: credentials expired" in text
    assert "800000001" not in text


async def test_run_event_digest_hides_unexpected_failures() -> None:
    services = _services(
        [
            _credential(1, "genshin", "800000001"),
            _credential(1, "hsr", "800000002"),
        ],
        {1: _preferences()},
        {
            "genshin": _service(error=RuntimeError("secret upstream payload")),
            "hsr": _service(events=(EventSummary("Cosmodyssey", 7200),)),
        },
    )
    bot = SimpleNamespace(send_message=AsyncMock())

    await run_event_digest(services, bot)

    text = bot.send_message.await_args.kwargs["text"]
    assert "Genshin Impact: temporarily unavailable" in text
    assert "secret upstream payload" not in text


async def test_run_event_digest_uses_a_rich_card_when_available() -> None:
    services = _services(
        [_credential(1, "genshin", "800000001")],
        {1: _preferences()},
        {"genshin": _service(events=(EventSummary("Windblume", 3600),))},
    )
    bot = SimpleNamespace(send_message=AsyncMock(), _post=AsyncMock())

    await run_event_digest(services, bot)

    bot._post.assert_awaited_once()
    endpoint, payload = bot._post.await_args.args
    assert endpoint == "sendRichMessage"
    assert payload["chat_id"] == 1
    assert "rich_message" in payload
    bot.send_message.assert_not_awaited()


async def test_run_event_digest_falls_back_when_rich_fails() -> None:
    services = _services(
        [_credential(1, "genshin", "800000001")],
        {1: _preferences()},
        {"genshin": _service(events=(EventSummary("Windblume", 3600),))},
    )
    bot = SimpleNamespace(
        send_message=AsyncMock(),
        _post=AsyncMock(side_effect=RuntimeError("unsupported")),
    )

    await run_event_digest(services, bot)

    bot.send_message.assert_awaited_once()
    assert "Windblume" in bot.send_message.await_args.kwargs["text"]


async def test_run_event_digest_survives_a_blocked_user() -> None:
    services = _services(
        [_credential(1, "genshin", "800000001")],
        {1: _preferences()},
        {"genshin": _service(events=(EventSummary("Windblume", 3600),))},
    )
    bot = SimpleNamespace(send_message=AsyncMock(side_effect=Forbidden("blocked")))

    await run_event_digest(services, bot)


async def test_run_event_digest_does_nothing_without_credentials() -> None:
    bot = SimpleNamespace(send_message=AsyncMock())
    services = _services([], {}, {})

    await run_event_digest(services, bot)

    bot.send_message.assert_not_awaited()


async def test_run_daily_event_digest_requires_services() -> None:
    context = SimpleNamespace(
        application=SimpleNamespace(bot_data={}, bot=SimpleNamespace())
    )

    await run_daily_event_digest(context)


async def test_run_daily_event_digest_uses_configured_days() -> None:
    service = _service(events=(EventSummary("Windblume", 3600),))
    services = _services(
        [_credential(1, "genshin", "800000001")],
        {1: _preferences()},
        {"genshin": service},
    )
    bot = SimpleNamespace(send_message=AsyncMock())
    context = SimpleNamespace(
        application=SimpleNamespace(
            bot_data={
                "services": services,
                "settings": SimpleNamespace(EVENT_DIGEST_DAYS=5),
            },
            bot=bot,
        )
    )

    await run_daily_event_digest(context)

    service.events_ending.assert_awaited_once_with(1, within_days=5)
    assert "next 5 days" in bot.send_message.await_args.kwargs["text"]


def test_render_digest_returns_none_without_events() -> None:
    assert render_digest([]) is None
    assert render_digest([DigestSection("Genshin Impact", "Traveler", ())]) is None


def test_render_digest_limits_events_per_game() -> None:
    events = tuple(EventSummary(f"Event {index}", 3600) for index in range(12))
    text = render_digest([DigestSection("Genshin Impact", "Traveler", events)])

    assert text is not None
    assert "Event 9" in text
    assert "Event 10" not in text
    assert "Turn this off with /settings event_digest off." in text
