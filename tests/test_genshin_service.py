"""Genshin service orchestration with a fake client."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import genshin
import pytest

from resona.core.cache import TTLCache
from resona.core.errors import CredentialsMissingError
from resona.games.genshin import views
from resona.games.genshin.service import GenshinService


class FakeClient:
    def __init__(self) -> None:
        self.get_genshin_notes = AsyncMock(return_value=SimpleNamespace())
        self.get_genshin_characters = AsyncMock(return_value=[])
        self.get_genshin_diary = AsyncMock(return_value=SimpleNamespace())
        self.get_spiral_abyss = AsyncMock(return_value=SimpleNamespace())
        self.get_imaginarium_theater = AsyncMock(return_value=SimpleNamespace())
        self.get_stygian_onslaught = AsyncMock(return_value=[])
        self.get_genshin_event_calendar = AsyncMock(return_value=SimpleNamespace())
        self.claim_daily_reward = AsyncMock(return_value=SimpleNamespace())
        self.get_reward_info = AsyncMock(return_value=SimpleNamespace())


class FakeAccounts:
    def __init__(self, account: Any, client: Any) -> None:
        self.account = account
        self.client = client
        self.build_calls: list[tuple[int, str, str | None]] = []

    async def primary_account(self, telegram_id: int, game: str) -> Any:
        return self.account

    async def build_client(
        self, telegram_id: int, game: str, uid: str | None = None
    ) -> Any:
        self.build_calls.append((telegram_id, game, uid))
        return self.client


def _account() -> SimpleNamespace:
    return SimpleNamespace(nickname="Traveler", uid="800000001")


@pytest.fixture(autouse=True)
def _stub_views(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "render_notes",
        "render_characters",
        "render_diary",
        "render_endgame",
        "render_events",
        "render_checkin",
    ):
        monkeypatch.setattr(views, name, lambda *args, _name=name: _name)


def _service() -> tuple[GenshinService, FakeAccounts, FakeClient]:
    client = FakeClient()
    accounts = FakeAccounts(_account(), client)
    return GenshinService(accounts), accounts, client


async def test_notes_uses_the_stored_uid() -> None:
    service, accounts, client = _service()

    result = await service.notes(1)

    assert result == "render_notes"
    assert accounts.build_calls == [(1, "genshin", "800000001")]
    client.get_genshin_notes.assert_awaited_once_with(800000001)


async def test_characters_and_diary() -> None:
    service, _, client = _service()

    assert await service.characters(1) == "render_characters"
    assert await service.diary(1) == "render_diary"
    client.get_genshin_characters.assert_awaited_once_with(800000001)
    client.get_genshin_diary.assert_awaited_once_with(800000001)


async def test_endgame_and_events() -> None:
    service, _, client = _service()

    assert await service.endgame(1) == "render_endgame"
    assert await service.events(1) == "render_events"
    client.get_spiral_abyss.assert_awaited_once_with(800000001)
    client.get_imaginarium_theater.assert_awaited_once_with(800000001)
    client.get_stygian_onslaught.assert_awaited_once_with(800000001)
    client.get_genshin_event_calendar.assert_awaited_once_with(800000001)


async def test_events_use_the_optional_cache() -> None:
    client = FakeClient()
    service = GenshinService(
        FakeAccounts(_account(), client),
        TTLCache(ttl=60),
    )

    assert await service.events(1) == "render_events"
    assert await service.events(1) == "render_events"

    client.get_genshin_event_calendar.assert_awaited_once_with(800000001)


async def test_checkin_claims_and_reads_status() -> None:
    service, _, client = _service()

    result = await service.checkin(1)

    assert result == "render_checkin"
    client.claim_daily_reward.assert_awaited_once_with(game=genshin.Game.GENSHIN)
    client.get_reward_info.assert_awaited_once_with(game=genshin.Game.GENSHIN)


async def test_checkin_handles_already_claimed() -> None:
    service, _, client = _service()
    client.claim_daily_reward = AsyncMock(side_effect=genshin.AlreadyClaimed())

    result = await service.checkin(1)

    assert result == "render_checkin"
    client.get_reward_info.assert_awaited_once_with(game=genshin.Game.GENSHIN)


async def test_missing_account_is_reported() -> None:
    accounts = FakeAccounts(None, FakeClient())
    service = GenshinService(accounts)

    with pytest.raises(CredentialsMissingError):
        await service.notes(1)
