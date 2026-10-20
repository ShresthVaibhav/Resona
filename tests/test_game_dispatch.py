"""Game selection and service lookup."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from resona.core.errors import CredentialsMissingError, UserError
from resona.handlers.game import _resolve_game
from resona.services.games import GameServices


def _ctx(
    *,
    default_game: str | None = None,
    accounts: tuple[SimpleNamespace, ...] = (),
    user_id: int | None = 1,
) -> SimpleNamespace:
    settings = SimpleNamespace(default_game=default_game)
    users = SimpleNamespace(get_settings=AsyncMock(return_value=settings))
    accounts_service = SimpleNamespace(
        list_accounts=AsyncMock(return_value=list(accounts))
    )
    return SimpleNamespace(
        user_id=user_id,
        services=SimpleNamespace(users=users, accounts=accounts_service),
    )


def _account(game: str) -> SimpleNamespace:
    return SimpleNamespace(game=game)


async def test_explicit_game_wins_and_is_consumed() -> None:
    args = ["hsr", "extra"]

    assert await _resolve_game(_ctx(), args) == "hsr"
    assert args == ["extra"]


async def test_planned_game_is_rejected() -> None:
    with pytest.raises(UserError, match="planned"):
        await _resolve_game(_ctx(), ["wuthering_waves"])


async def test_default_game_is_used() -> None:
    assert await _resolve_game(_ctx(default_game="zzz"), []) == "zzz"


async def test_sole_linked_game_is_inferred() -> None:
    ctx = _ctx(accounts=(_account("genshin"),))

    assert await _resolve_game(ctx, []) == "genshin"


async def test_multiple_games_require_a_choice() -> None:
    ctx = _ctx(accounts=(_account("genshin"), _account("hsr")))

    with pytest.raises(UserError, match="several games"):
        await _resolve_game(ctx, [])


async def test_missing_links_are_reported() -> None:
    with pytest.raises(CredentialsMissingError):
        await _resolve_game(_ctx(), [])


async def test_missing_user_is_reported() -> None:
    with pytest.raises(CredentialsMissingError):
        await _resolve_game(_ctx(user_id=None), [])


def test_game_services_resolves_every_implemented_game() -> None:
    services = GameServices(accounts=None)  # type: ignore[arg-type]

    assert services.games == ("genshin", "hsr", "zzz")
    for game in services.games:
        assert services.get(game).game == game


def test_game_services_rejects_unimplemented_games() -> None:
    services = GameServices(accounts=None)  # type: ignore[arg-type]

    with pytest.raises(UserError, match="not supported yet"):
        services.get("wuthering_waves")
