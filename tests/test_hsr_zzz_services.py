"""HSR and ZZZ service orchestration with fake clients."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import genshin
import pytest

from resona.core.errors import CredentialsMissingError
from resona.games.hsr import views as hsr_views
from resona.games.hsr.service import StarRailService
from resona.games.zzz import views as zzz_views
from resona.games.zzz.service import ZZZService


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


def _account(uid: str = "800000002") -> SimpleNamespace:
    return SimpleNamespace(nickname="Traveler", uid=uid)


@pytest.fixture(autouse=True)
def _stub_views(monkeypatch: pytest.MonkeyPatch) -> None:
    for module in (hsr_views, zzz_views):
        for name in (
            "render_notes",
            "render_characters",
            "render_diary",
            "render_endgame",
            "render_events",
            "render_checkin",
        ):
            monkeypatch.setattr(module, name, lambda *args, _name=name: _name)


# -- Honkai: Star Rail -------------------------------------------------------
class FakeHSRClient:
    def __init__(self) -> None:
        self.get_starrail_notes = AsyncMock(return_value=SimpleNamespace())
        self.get_starrail_characters = AsyncMock(return_value=SimpleNamespace())
        self.get_starrail_diary = AsyncMock(return_value=SimpleNamespace())
        self.get_starrail_challenge = AsyncMock(return_value=SimpleNamespace())
        self.get_starrail_rogue = AsyncMock(return_value=SimpleNamespace())
        self.get_starrail_pure_fiction = AsyncMock(return_value=SimpleNamespace())
        self.get_apocalyptic_shadow = AsyncMock(return_value=SimpleNamespace())
        self.get_anomaly_arbitration = AsyncMock(return_value=SimpleNamespace())
        self.get_starrail_event_calendar = AsyncMock(return_value=SimpleNamespace())
        self.claim_daily_reward = AsyncMock(return_value=SimpleNamespace())
        self.get_reward_info = AsyncMock(return_value=SimpleNamespace())


def _hsr() -> tuple[StarRailService, FakeHSRClient]:
    client = FakeHSRClient()
    return StarRailService(FakeAccounts(_account(), client)), client


async def test_hsr_reads_use_the_stored_uid() -> None:
    service, client = _hsr()

    assert await service.notes(1) == "render_notes"
    assert await service.diary(1) == "render_diary"
    assert await service.endgame(1) == "render_endgame"
    assert await service.events(1) == "render_events"

    client.get_starrail_notes.assert_awaited_once_with(800000002)
    client.get_starrail_diary.assert_awaited_once_with(800000002)
    client.get_starrail_challenge.assert_awaited_once_with(800000002)
    client.get_starrail_rogue.assert_awaited_once_with(800000002)
    client.get_starrail_pure_fiction.assert_awaited_once_with(800000002)
    client.get_apocalyptic_shadow.assert_awaited_once_with(800000002)
    client.get_anomaly_arbitration.assert_awaited_once_with(800000002)
    client.get_starrail_event_calendar.assert_awaited_once_with(800000002)


async def test_hsr_characters_request_simple_payload() -> None:
    service, client = _hsr()

    assert await service.characters(1) == "render_characters"
    client.get_starrail_characters.assert_awaited_once_with(800000002, simple=True)


async def test_hsr_checkin_uses_the_starrail_game() -> None:
    service, client = _hsr()

    assert await service.checkin(1) == "render_checkin"
    client.claim_daily_reward.assert_awaited_once_with(game=genshin.Game.STARRAIL)
    client.get_reward_info.assert_awaited_once_with(game=genshin.Game.STARRAIL)


async def test_hsr_checkin_handles_already_claimed() -> None:
    service, client = _hsr()
    client.claim_daily_reward = AsyncMock(side_effect=genshin.AlreadyClaimed())

    assert await service.checkin(1) == "render_checkin"


# -- Zenless Zone Zero -------------------------------------------------------
class FakeZZZClient:
    def __init__(self) -> None:
        self.get_zzz_notes = AsyncMock(return_value=SimpleNamespace())
        self.get_zzz_agents = AsyncMock(return_value=[])
        self.get_zzz_diary = AsyncMock(return_value=SimpleNamespace())
        self.get_deadly_assault = AsyncMock(return_value=SimpleNamespace())
        self.get_shiyu_defense = AsyncMock(return_value=SimpleNamespace())
        self.get_annihilation_simulacrum = AsyncMock(return_value=SimpleNamespace())
        self.get_lost_void_summary = AsyncMock(return_value=SimpleNamespace())
        self.get_zzz_event_calendar = AsyncMock(return_value=[])
        self.claim_daily_reward = AsyncMock(return_value=SimpleNamespace())
        self.get_reward_info = AsyncMock(return_value=SimpleNamespace())


def _zzz() -> tuple[ZZZService, FakeZZZClient]:
    client = FakeZZZClient()
    return ZZZService(FakeAccounts(_account("1300000001"), client)), client


async def test_zzz_reads_use_the_stored_uid() -> None:
    service, client = _zzz()

    assert await service.notes(1) == "render_notes"
    assert await service.characters(1) == "render_characters"
    assert await service.diary(1) == "render_diary"
    assert await service.endgame(1) == "render_endgame"
    assert await service.events(1) == "render_events"

    client.get_zzz_notes.assert_awaited_once_with(1300000001)
    client.get_zzz_agents.assert_awaited_once_with(1300000001)
    client.get_zzz_diary.assert_awaited_once_with(1300000001)
    client.get_deadly_assault.assert_awaited_once_with(1300000001)
    client.get_shiyu_defense.assert_awaited_once_with(1300000001)
    client.get_annihilation_simulacrum.assert_awaited_once_with(1300000001)
    client.get_lost_void_summary.assert_awaited_once_with(1300000001)
    client.get_zzz_event_calendar.assert_awaited_once_with(1300000001)


async def test_zzz_checkin_uses_the_zzz_game() -> None:
    service, client = _zzz()

    assert await service.checkin(1) == "render_checkin"
    client.claim_daily_reward.assert_awaited_once_with(game=genshin.Game.ZZZ)
    client.get_reward_info.assert_awaited_once_with(game=genshin.Game.ZZZ)


async def test_missing_account_is_reported_for_both_games() -> None:
    hsr = StarRailService(FakeAccounts(None, FakeHSRClient()))
    zzz = ZZZService(FakeAccounts(None, FakeZZZClient()))

    with pytest.raises(CredentialsMissingError):
        await hsr.notes(1)
    with pytest.raises(CredentialsMissingError):
        await zzz.notes(1)
