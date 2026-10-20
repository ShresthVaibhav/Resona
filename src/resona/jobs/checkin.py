"""Daily HoYoLAB check-in for every linked account."""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from telegram.error import Forbidden
from telegram.ext import ContextTypes

from resona.config.constants import GAME_LABELS
from resona.core.errors import UserError

if TYPE_CHECKING:
    from resona.database.collections import CredentialsDocument
    from resona.services import Services

logger = logging.getLogger("resona.jobs.checkin")


@dataclass(frozen=True, slots=True)
class AccountReport:
    """One account's line in the daily summary."""

    label: str
    name: str
    claimed: bool | None = None
    error: str | None = None


async def run_daily_checkin(context: ContextTypes.DEFAULT_TYPE) -> None:
    """JobQueue entry point."""
    application = context.application
    services: Services | None = application.bot_data.get("services")
    if services is None:
        logger.warning("Daily check-in skipped: services are not configured.")
        return

    await run_checkin(services, application.bot)


async def run_checkin(services: Services, bot: Any) -> None:
    """Check in every linked account whose owner has notifications enabled."""
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

        reports = [
            await _check_one(services, telegram_id, credential) for credential in items
        ]
        await _deliver(bot, telegram_id, render_summary(reports))


async def _check_one(
    services: Services,
    telegram_id: int,
    credential: CredentialsDocument,
) -> AccountReport:
    label = GAME_LABELS.get(credential.game, credential.game)

    try:
        service = services.games.get(credential.game)
        outcome = await service.checkin_account(telegram_id, credential.uid)
    except UserError as exc:
        return AccountReport(label=label, name=credential.uid, error=str(exc))
    except Exception:
        logger.exception(
            "Check-in failed for user %s (%s).", telegram_id, credential.game
        )
        return AccountReport(
            label=label,
            name=credential.uid,
            error="temporarily unavailable",
        )

    return AccountReport(
        label=label,
        name=outcome.nickname or outcome.uid,
        claimed=outcome.claimed,
    )


def render_summary(reports: list[AccountReport]) -> str:
    """Build the plain-text notification body."""
    lines = ["Daily check-in", ""]
    for report in reports:
        if report.error:
            status = f"failed: {report.error}"
        else:
            status = "claimed" if report.claimed else "already claimed"
        lines.append(f"{report.label} — {report.name}: {status}")
    return "\n".join(lines)


async def _deliver(bot: Any, telegram_id: int, text: str) -> None:
    try:
        await bot.send_message(chat_id=telegram_id, text=text)
    except Forbidden:
        logger.info(
            "User %s has blocked the bot; skipping check-in summary.", telegram_id
        )
    except Exception:
        logger.exception(
            "Could not deliver the check-in summary to user %s.", telegram_id
        )
