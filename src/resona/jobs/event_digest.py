"""Opt-in digest of events that are about to end."""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from telegram.error import Forbidden
from telegram.ext import ContextTypes

from resona.config.constants import GAME_LABELS, IMPLEMENTED_GAMES
from resona.core.errors import UserError
from resona.core.rich import (
    EventDigestSection,
    RichContent,
    event_digest_summary,
    send_rich_message,
    supports_rich_messages,
)
from resona.core.utils import format_duration, truncate
from resona.games.common import EventSummary

if TYPE_CHECKING:
    from resona.database.collections import CredentialsDocument
    from resona.services import Services

logger = logging.getLogger("resona.jobs.event_digest")

_MAX_EVENTS_PER_GAME = 10


@dataclass(frozen=True, slots=True)
class DigestSection:
    """One game's events in a user's digest."""

    label: str
    name: str
    events: tuple[EventSummary, ...]


async def run_daily_event_digest(context: ContextTypes.DEFAULT_TYPE) -> None:
    """JobQueue entry point."""
    application = context.application
    services: Services | None = application.bot_data.get("services")
    if services is None:
        logger.warning("Event digest skipped: services are not configured.")
        return

    settings = application.bot_data.get("settings")
    days = settings.EVENT_DIGEST_DAYS if settings is not None else 3
    rich_enabled = (
        getattr(settings, "RICH_MESSAGES_ENABLED", True)
        if settings is not None
        else True
    )
    await run_event_digest(
        services,
        application.bot,
        days=days,
        rich_enabled=rich_enabled,
    )


async def run_event_digest(
    services: Services,
    bot: Any,
    *,
    days: int = 3,
    rich_enabled: bool = True,
) -> None:
    """Send a digest to every user who explicitly opted in."""
    credentials = await services.accounts.list_credentials()
    if not credentials:
        return

    grouped: dict[int, list[CredentialsDocument]] = defaultdict(list)
    for credential in credentials:
        grouped[credential.telegram_id].append(credential)

    for telegram_id, items in grouped.items():
        preferences = await services.users.get_settings(telegram_id)
        if not preferences.notifications_enabled:
            continue
        if not preferences.event_digest_enabled:
            continue

        sections: list[DigestSection] = []
        errors: list[str] = []
        games = dict.fromkeys(item.game for item in items)
        for game in sorted(games, key=_game_order):
            section, error = await _digest_game(services, telegram_id, game, days=days)
            if section is not None:
                sections.append(section)
            if error is not None:
                errors.append(error)

        text = render_digest(sections, days=days, errors=errors)
        if text is not None:
            rich_sections = [
                EventDigestSection(
                    label=section.label,
                    name=section.name,
                    events=tuple(
                        (
                            event.name,
                            format_duration(event.seconds_remaining),
                        )
                        for event in section.events[:_MAX_EVENTS_PER_GAME]
                    ),
                )
                for section in sections
                if section.events
            ]
            rich = event_digest_summary(
                rich_sections,
                days=days,
                errors=errors,
                fallback_text=text,
            )
            await _deliver(
                bot,
                telegram_id,
                text,
                rich=rich,
                rich_enabled=rich_enabled,
            )


def _game_order(game: str) -> int:
    try:
        return IMPLEMENTED_GAMES.index(game)
    except ValueError:
        return len(IMPLEMENTED_GAMES)


async def _digest_game(
    services: Services,
    telegram_id: int,
    game: str,
    *,
    days: int,
) -> tuple[DigestSection | None, str | None]:
    label = GAME_LABELS.get(game, game)

    try:
        service = services.games.get(game)
        digest = await service.events_ending(telegram_id, within_days=days)
    except UserError as exc:
        return None, f"{label}: {exc}"
    except Exception:
        logger.exception("Event digest failed for user %s (%s).", telegram_id, game)
        return None, f"{label}: temporarily unavailable"

    if not digest.events:
        return None, None

    return (
        DigestSection(
            label=label,
            name=digest.nickname or digest.uid,
            events=digest.events,
        ),
        None,
    )


def render_digest(
    sections: Sequence[DigestSection],
    *,
    days: int = 3,
    errors: Sequence[str] = (),
) -> str | None:
    """Build the plain-text digest, or ``None`` when there is nothing to send."""
    active = [section for section in sections if section.events]
    if not active:
        return None

    unit = "day" if days == 1 else "days"
    lines = [f"Events ending in the next {days} {unit}", ""]

    for section in active:
        lines.append(f"{section.label} - {section.name}")
        for event in section.events[:_MAX_EVENTS_PER_GAME]:
            remaining = format_duration(event.seconds_remaining)
            lines.append(f"  {event.name}: ends in {remaining}")
        lines.append("")

    if errors:
        lines.append("Could not refresh: " + "; ".join(errors))
        lines.append("")

    lines.append("Turn this off with /settings event_digest off.")
    return truncate("\n".join(lines).strip(), 3900)


async def _deliver(
    bot: Any,
    telegram_id: int,
    text: str,
    *,
    rich: RichContent | None = None,
    rich_enabled: bool = True,
) -> None:
    if rich is not None and rich_enabled and supports_rich_messages(bot):
        try:
            await send_rich_message(bot, telegram_id, rich.payload)
            return
        except Exception:
            logger.warning(
                "Rich event digest failed for user %s; falling back to text.",
                telegram_id,
                exc_info=True,
            )

    try:
        await bot.send_message(chat_id=telegram_id, text=text)
    except Forbidden:
        logger.info("User %s has blocked the bot; skipping event digest.", telegram_id)
    except Exception:
        logger.exception("Could not deliver the event digest to user %s.", telegram_id)
