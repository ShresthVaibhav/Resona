"""Rendering helpers shared by every game module."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from resona.core.errors import (
    AccountNotFoundError,
    CredentialsExpiredError,
    CredentialsMissingError,
    DataNotPublicError,
    RateLimitedError,
)
from resona.core.utils import truncate
from resona.services.api import run_api

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Hashable, Sequence

    from resona.core.cache import TTLCache
    from resona.database.collections import GameAccountDocument

logger = logging.getLogger("resona.games.common")


@dataclass(frozen=True, slots=True)
class EventSummary:
    """One active event, with the time left before it ends."""

    name: str
    seconds_remaining: float


@dataclass(frozen=True, slots=True)
class GameEventDigest:
    """The events ending soon for one linked game account."""

    nickname: str | None
    uid: str
    events: tuple[EventSummary, ...]


@dataclass(frozen=True, slots=True)
class GachaPity:
    """Estimated pity counters for the latest banner."""

    banner: str
    five_star: int
    four_star: int
    five_star_cap: int
    four_star_cap: int = 10
    five_star_at_least: bool = False
    four_star_at_least: bool = False


def account_header(account: GameAccountDocument, title: str) -> str:
    """``Title - Nickname (UID ...)`` used at the top of every response."""
    return f"{title} - {account.nickname or 'Unknown'} (UID {account.uid})"


def render_checkin(
    account: GameAccountDocument,
    title: str,
    reward: Any,
    info: Any,
) -> str:
    """Render a daily check-in result for any game."""
    lines = [account_header(account, f"{title} check-in"), ""]

    if reward is not None:
        lines.append(f"Claimed: {reward.name} x{reward.amount}.")
    else:
        lines.append("Today's reward was already claimed.")

    if info is not None:
        lines.append(f"Claimed this month: {info.claimed_rewards}")

    return "\n".join(lines)


_GACHA_TITLES = {
    "genshin": "Genshin Impact wish history",
    "hsr": "Honkai: Star Rail warp history",
    "zzz": "Zenless Zone Zero signal history",
    "genshin_mw": "Genshin Impact Miliastra Wonderland history",
}

_GACHA_COMMANDS = {
    "genshin": "wishes",
    "hsr": "warp",
    "zzz": "signals",
    "genshin_mw": "miliastra",
}


def render_gacha(
    account: GameAccountDocument,
    game: str,
    entries: Sequence[Any],
    *,
    page: int = 1,
    page_size: int = 10,
    has_more: bool = False,
    pity: GachaPity | None = None,
) -> str:
    """Render recent pulls for any game."""
    lines = [account_header(account, _GACHA_TITLES[game]), ""]

    if not entries:
        if page > 1:
            lines.append("No pulls on this page.")
        else:
            lines.append("No recent pulls were returned.")
        return "\n".join(lines)

    if page == 1:
        lines.append(f"Last {len(entries)} pulls")
    else:
        first = (page - 1) * page_size + 1
        last = first + len(entries) - 1
        lines.append(f"Pulls {first}-{last}")
    lines.append("")

    if pity is not None:
        five = f"{pity.five_star}{'+' if pity.five_star_at_least else ''}"
        four = f"{pity.four_star}{'+' if pity.four_star_at_least else ''}"
        lines.append(f"Pity (estimated, latest banner: {pity.banner})")
        lines.append(
            f"  5-star: {five} pulls since last (hard pity {pity.five_star_cap})"
        )
        lines.append(
            f"  4-star: {four} pulls since last (hard pity {pity.four_star_cap})"
        )
        lines.append("")

    for entry in entries:
        when = entry.time.strftime("%Y-%m-%d %H:%M") if entry.time else "unknown"
        lines.append(f"{entry.rarity}-star {entry.name} ({entry.type})")
        lines.append(f"  {_enum_label(entry.banner_type)} - {when}")

    if has_more:
        command = _GACHA_COMMANDS[game]
        lines.append("")
        lines.append(f"Use /{command} {page + 1} for older pulls.")

    return truncate("\n".join(lines), 3900)


async def cached_api(
    cache: TTLCache[Any, Any] | None,
    key: Hashable,
    operation: Callable[[], Awaitable[Any]],
    *,
    action: str,
) -> Any:
    """Run an API call through an optional TTL cache."""
    if cache is not None:
        cached = cache.get(key)
        if cached is not None:
            return cached

    result = await run_api(operation(), action=action)
    if cache is not None:
        cache.set(key, result)
    return result


async def optional_api(operation: Awaitable[Any], *, action: str) -> Any | None:
    """Run a section API call, returning ``None`` when it is not public.

    Credential and rate-limit failures affect every section, so they are
    re-raised instead of silently hiding the whole response.
    """
    try:
        return await run_api(operation, action=action)
    except (
        CredentialsExpiredError,
        CredentialsMissingError,
        RateLimitedError,
    ):
        raise
    except (DataNotPublicError, AccountNotFoundError) as exc:
        logger.info("%s is unavailable: %s", action, exc)
        return None


def _enum_label(value: Any) -> str:
    name = getattr(value, "name", None)
    return name.replace("_", " ").title() if name else str(value)
