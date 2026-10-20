"""Gacha history collection and rendering."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import genshin
import pytest

from resona.core.errors import CredentialsMissingError, UserError
from resona.games.genshin.service import GenshinService
from resona.games.hsr.service import StarRailService
from resona.games.zzz.service import ZZZService
from resona.handlers.gacha import _parse_history_args


class FakeAccounts:
    def __init__(self, account: SimpleNamespace | None, client: FakeClient) -> None:
        self.account = account
        self.client = client
        self.build_calls: list[tuple[int, str, str | None]] = []

    async def primary_account(
        self, telegram_id: int, game: str
    ) -> SimpleNamespace | None:
        return self.account

    async def build_client(
        self, telegram_id: int, game: str, uid: str | None = None
    ) -> FakeClient:
        self.build_calls.append((telegram_id, game, uid))
        return self.client


class FakeClient:
    def __init__(
        self,
        entries: dict[str, list[SimpleNamespace]] | None = None,
        *,
        fetch_error: Exception | None = None,
        page_error: Exception | None = None,
        pity_error: Exception | None = None,
    ) -> None:
        self.entries = entries or {}
        self.page_error = page_error
        self.pity_error = pity_error
        self.fetch_authkey = AsyncMock(side_effect=fetch_error)
        self.set_authkey = Mock()
        self.wish_history = Mock(side_effect=self._history)
        self.warp_history = Mock(side_effect=self._history)
        self.signal_history = Mock(side_effect=self._history)
        self.mw_wish_history = Mock(side_effect=self._history)

    def _history(self, *, banner_type: object, limit: int) -> object:
        if self.page_error is not None:
            return _failing(self.page_error)
        if self.pity_error is not None and limit > 11:
            return _failing(self.pity_error)

        name = getattr(banner_type, "name", "")
        return _paginator(self.entries.get(name, [])[:limit])


def _paginator(items: list[SimpleNamespace]) -> object:
    async def generate():
        for item in items:
            yield item

    return generate()


def _failing(error: Exception) -> object:
    async def generate():
        raise error
        yield  # pragma: no cover - makes this an async generator

    return generate()


def _account() -> SimpleNamespace:
    return SimpleNamespace(nickname="Traveler", uid="800000001")


def _entry(
    name: str,
    *,
    rarity: int = 5,
    banner: str = "CHARACTER",
    when: datetime | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        name=name,
        rarity=rarity,
        type="Character",
        banner_type=SimpleNamespace(name=banner),
        time=when or datetime(2026, 10, 20, 12, 0, tzinfo=UTC),
    )


def _service(
    client: FakeClient,
    account: SimpleNamespace | None = None,
) -> GenshinService:
    return GenshinService(FakeAccounts(account or _account(), client))


async def test_wishes_fetches_an_authkey_and_sorts_newest_first() -> None:
    client = FakeClient(
        {
            "CHARACTER": [
                _entry("Furina", when=datetime(2026, 10, 20, 12, 0, tzinfo=UTC))
            ],
            "STANDARD": [
                _entry("Diluc", when=datetime(2026, 10, 19, 12, 0, tzinfo=UTC))
            ],
        }
    )

    rendered = await _service(client).wishes(1)

    client.fetch_authkey.assert_awaited_once_with(800000001, game=genshin.Game.GENSHIN)
    client.set_authkey.assert_not_called()
    assert "Genshin Impact wish history" in rendered
    assert "Last 2 pulls" in rendered
    assert rendered.index("Furina") < rendered.index("Diluc")
    assert "Character - 2026-10-20 12:00" in rendered


async def test_wishes_uses_a_supplied_authkey_without_fetching() -> None:
    client = FakeClient()
    url = "https://example.test/history?authkey=abc"

    await _service(client).wishes(1, authkey=url)

    client.set_authkey.assert_called_once_with(url, game=genshin.Game.GENSHIN)
    client.fetch_authkey.assert_not_called()


async def test_wishes_reports_a_missing_account() -> None:
    service = GenshinService(FakeAccounts(None, FakeClient()))

    with pytest.raises(CredentialsMissingError):
        await service.wishes(1)


async def test_wishes_explains_that_a_manual_authkey_is_needed() -> None:
    client = FakeClient(fetch_error=RuntimeError("overseas only"))

    with pytest.raises(UserError, match="manual authkey"):
        await _service(client).wishes(1)


async def test_wishes_reports_an_expired_authkey() -> None:
    client = FakeClient(page_error=genshin.AuthkeyTimeout())

    with pytest.raises(UserError, match="expired"):
        await _service(client).wishes(1)


async def test_wishes_shows_estimated_pity_for_the_latest_banner() -> None:
    client = FakeClient(
        {
            "CHARACTER": [
                _entry(
                    "Recent 4-star",
                    rarity=4,
                    when=datetime(2026, 10, 20, 12, 0, tzinfo=UTC),
                ),
                _entry(
                    "Older 4-star",
                    rarity=4,
                    when=datetime(2026, 10, 19, 12, 0, tzinfo=UTC),
                ),
                _entry(
                    "Five-star",
                    rarity=5,
                    when=datetime(2026, 10, 18, 12, 0, tzinfo=UTC),
                ),
            ]
        }
    )

    rendered = await _service(client).wishes(1)

    assert "Pity (estimated, latest banner: Character)" in rendered
    assert "5-star: 2 pulls since last (hard pity 90)" in rendered
    assert "4-star: 0 pulls since last (hard pity 10)" in rendered


async def test_wishes_keeps_history_when_pity_lookup_fails() -> None:
    client = FakeClient(
        {
            "CHARACTER": [
                _entry(
                    "Furina",
                    rarity=5,
                    when=datetime(2026, 10, 20, 12, 0, tzinfo=UTC),
                )
            ]
        },
        pity_error=genshin.TooManyRequests(),
    )

    rendered = await _service(client).wishes(1)

    assert "Furina" in rendered
    assert "Pity" not in rendered


async def test_wishes_paginates_without_fetching_pity_on_later_pages() -> None:
    client = FakeClient(
        {
            "CHARACTER": [
                _entry(
                    f"Pull {index}",
                    rarity=4,
                    when=datetime(2026, 10, 20, 12, index, tzinfo=UTC),
                )
                for index in range(12)
            ]
        }
    )

    rendered = await _service(client).wishes(1, page=2)

    assert "Pulls 11-12" in rendered
    assert "Pity" not in rendered
    assert client.wish_history.call_args.kwargs["limit"] == 21


async def test_wishes_rejects_an_out_of_range_page() -> None:
    with pytest.raises(UserError, match="Page must be between"):
        await _service(FakeClient()).wishes(1, page=99)


async def test_miliastra_uses_the_wonderland_history_endpoint() -> None:
    client = FakeClient(
        {
            "EVENT": [
                _entry(
                    "Festival outfit",
                    rarity=4,
                    banner="EVENT",
                    when=datetime(2026, 10, 20, 12, 0, tzinfo=UTC),
                )
            ]
        }
    )

    rendered = await _service(client).miliastra(1)

    client.mw_wish_history.assert_called()
    assert "Miliastra Wonderland history" in rendered
    assert "Festival outfit" in rendered


def test_history_arguments_accept_a_page_and_url_in_either_order() -> None:
    url = "https://example.test/history?authkey=abc"

    assert _parse_history_args([url]) == (url, 1)
    assert _parse_history_args(["2", url]) == (url, 2)
    assert _parse_history_args([url, "2"]) == (url, 2)
    assert _parse_history_args(["2"]) == (None, 2)


def test_history_arguments_reject_duplicates_and_invalid_pages() -> None:
    with pytest.raises(UserError, match="one page number"):
        _parse_history_args(["1", "2"])

    with pytest.raises(UserError, match="one history URL"):
        _parse_history_args(["one", "two"])

    with pytest.raises(UserError, match="Page must be at least 1"):
        _parse_history_args(["0"])


@pytest.mark.parametrize(
    ("service_type", "method", "title"),
    [
        (StarRailService, "warp_history", "warp history"),
        (ZZZService, "signal_history", "signal history"),
    ],
)
async def test_each_game_uses_its_own_history_endpoint(
    service_type: type,
    method: str,
    title: str,
) -> None:
    client = FakeClient()
    service = service_type(FakeAccounts(_account(), client))

    rendered = await service.wishes(1)

    getattr(client, method).assert_called()
    assert title in rendered
