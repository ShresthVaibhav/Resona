"""Shared per-account check-in used by the jobs."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import genshin
import pytest

from resona.core.errors import CredentialsMissingError
from resona.games.checkin import AccountCheckinMixin


class FakeAccounts:
    def __init__(self, account: Any, client: Any) -> None:
        self.account = account
        self.client = client

    async def get_account(self, telegram_id: int, game: str, uid: str) -> Any:
        return self.account

    async def build_client(
        self, telegram_id: int, game: str, uid: str | None = None
    ) -> Any:
        return self.client


class FakeService(AccountCheckinMixin):
    game = "hsr"

    def __init__(self, accounts: FakeAccounts) -> None:
        self._accounts = accounts


def _account() -> SimpleNamespace:
    return SimpleNamespace(nickname="Trailblazer", uid="800000002")


def _client(*, side_effect: Exception | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        claim_daily_reward=AsyncMock(return_value=None, side_effect=side_effect)
    )


async def test_checkin_account_claims_once_and_returns_an_outcome() -> None:
    client = _client()
    service = FakeService(FakeAccounts(_account(), client))

    outcome = await service.checkin_account(1, "800000002")

    assert outcome.game == "hsr"
    assert outcome.uid == "800000002"
    assert outcome.nickname == "Trailblazer"
    assert outcome.claimed is True
    client.claim_daily_reward.assert_awaited_once_with(
        game=genshin.Game.STARRAIL, reward=False
    )


async def test_checkin_account_reports_an_already_claimed_reward() -> None:
    client = _client(side_effect=genshin.AlreadyClaimed())
    service = FakeService(FakeAccounts(_account(), client))

    outcome = await service.checkin_account(1, "800000002")

    assert outcome.claimed is False


@pytest.mark.parametrize(
    ("game", "library"),
    [
        ("genshin", genshin.Game.GENSHIN),
        ("hsr", genshin.Game.STARRAIL),
        ("zzz", genshin.Game.ZZZ),
    ],
)
async def test_checkin_account_maps_each_game(game: str, library: genshin.Game) -> None:
    client = _client()
    service = FakeService(FakeAccounts(_account(), client))
    service.game = game

    outcome = await service.checkin_account(1, "800000002")

    assert outcome.game == game
    client.claim_daily_reward.assert_awaited_once_with(game=library, reward=False)


async def test_checkin_account_requires_a_linked_account() -> None:
    service = FakeService(FakeAccounts(None, _client()))

    with pytest.raises(CredentialsMissingError):
        await service.checkin_account(1, "800000002")
