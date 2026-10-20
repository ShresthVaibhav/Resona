"""Mapping of upstream API failures to safe, user-facing errors."""

from __future__ import annotations

import logging
from collections.abc import Awaitable
from typing import TypeVar

from resona.core.errors import (
    AccountNotFoundError,
    CredentialsExpiredError,
    DataNotPublicError,
    ExternalAPIError,
    UserError,
)

T = TypeVar("T")

logger = logging.getLogger("resona.services.api")


async def run_api(operation: Awaitable[T], *, action: str) -> T:
    """Await an upstream call, translating known failures.

    Unknown failures become :class:`ExternalAPIError` so the global handler can
    log them without leaking upstream payloads to the user.
    """
    import genshin

    try:
        return await operation
    except genshin.InvalidCookies as exc:
        raise CredentialsExpiredError() from exc
    except genshin.TooManyRequests as exc:
        raise UserError(
            "HoYoLAB is rate limiting requests. Please wait a few minutes."
        ) from exc
    except genshin.DataNotPublic as exc:
        raise DataNotPublicError(
            f"{action} is not public. Enable it in the game settings and try again."
        ) from exc
    except genshin.AccountNotFound as exc:
        raise AccountNotFoundError() from exc
    except genshin.GenshinException as exc:
        logger.warning("%s failed: %s", action, exc)
        raise ExternalAPIError(f"{action} failed.") from exc
