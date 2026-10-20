"""Upstream error translation."""

from __future__ import annotations

from typing import TypeVar

import genshin
import pytest

from resona.core.errors import (
    AccountNotFoundError,
    CredentialsExpiredError,
    DataNotPublicError,
    ExternalAPIError,
    UserError,
)
from resona.services.api import run_api

T = TypeVar("T")


async def _raise(error: Exception) -> T:
    raise error


async def test_passes_through_results() -> None:
    async def _value() -> int:
        return 7

    assert await run_api(_value(), action="Test") == 7


async def test_invalid_cookies_become_expired_credentials() -> None:
    with pytest.raises(CredentialsExpiredError):
        await run_api(_raise(genshin.InvalidCookies()), action="Notes")


async def test_rate_limits_are_explained() -> None:
    with pytest.raises(UserError, match="rate limiting"):
        await run_api(_raise(genshin.TooManyRequests()), action="Notes")


async def test_private_data_is_explained() -> None:
    with pytest.raises(DataNotPublicError, match="not public"):
        await run_api(_raise(genshin.DataNotPublic()), action="Diary")


async def test_missing_account_is_explained() -> None:
    with pytest.raises(AccountNotFoundError, match="could not be found"):
        await run_api(_raise(genshin.AccountNotFound()), action="Notes")


async def test_unknown_api_errors_are_hidden() -> None:
    with pytest.raises(ExternalAPIError):
        await run_api(_raise(genshin.GenshinException()), action="Notes")
