"""Shared game helpers."""

from __future__ import annotations

import genshin
import pytest

from resona.core.errors import UserError
from resona.games.common import optional_api


async def _raise(error: Exception) -> object:
    raise error


async def test_optional_api_skips_private_sections() -> None:
    assert await optional_api(_raise(genshin.DataNotPublic()), action="Theater") is None


async def test_optional_api_keeps_rate_limits_visible() -> None:
    with pytest.raises(UserError, match="rate limiting"):
        await optional_api(_raise(genshin.TooManyRequests()), action="Theater")
