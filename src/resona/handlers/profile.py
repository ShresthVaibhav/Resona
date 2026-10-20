"""User-facing profile and preference commands."""

from __future__ import annotations

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from telegram import Update
from telegram.ext import ContextTypes

from resona.config.constants import (
    CATEGORY_PROFILE,
    GAME_LABELS,
    IMPLEMENTED_GAMES,
)
from resona.core.context import ResonaContext
from resona.core.rich import profile_summary
from resona.database.collections import UserSettingsDocument
from resona.wrappers import command

_SETTINGS_USAGE = (
    "Change a setting with:\n"
    "/settings language <code>\n"
    "/settings timezone <area/city>\n"
    "/settings game <game|none>\n"
    "/settings notifications <on|off>\n"
    "/settings event_digest <on|off>"
)


def _yes_no(value: bool) -> str:
    return "on" if value else "off"


def _render_settings(settings: UserSettingsDocument) -> str:
    game = settings.default_game
    lines = [
        "Settings",
        "",
        f"Language: {settings.locale}",
        f"Timezone: {settings.timezone}",
        f"Default game: {GAME_LABELS[game] if game else 'none'}",
        f"Notifications: {_yes_no(settings.notifications_enabled)}",
        f"Event digest: {_yes_no(settings.event_digest_enabled)}",
        "",
        _SETTINGS_USAGE,
    ]
    return "\n".join(lines)


def _parse_toggle(value: str) -> bool | None:
    normalized = value.strip().lower()
    if normalized in {"on", "true", "yes", "enable", "enabled", "1"}:
        return True
    if normalized in {"off", "false", "no", "disable", "disabled", "0"}:
        return False
    return None


@command(
    "profile",
    description="Show your Resona profile",
    category=CATEGORY_PROFILE,
    private=True,
    groups=True,
)
async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the Telegram identity, linked accounts and preferences."""
    ctx = ResonaContext.from_update(update, context)
    if ctx.user is None:
        return

    document = await ctx.services.users.ensure_user(ctx.user)
    settings = await ctx.services.users.get_settings(document.telegram_id)
    accounts = await ctx.services.accounts.list_accounts(document.telegram_id)

    content = profile_summary(
        name=document.first_name or "Unknown",
        username=document.username,
        telegram_id=document.telegram_id,
        member_since=f"{document.created_at:%Y-%m-%d}",
        linked_accounts=len(accounts),
        locale=settings.locale,
        timezone=settings.timezone,
        default_game=(
            GAME_LABELS[settings.default_game] if settings.default_game else "none"
        ),
        notifications=settings.notifications_enabled,
        event_digest=settings.event_digest_enabled,
    )
    await ctx.reply_rich(content)


@command(
    "settings",
    description="View or change your preferences",
    category=CATEGORY_PROFILE,
    private=True,
    usage="/settings [key] [value]",
    max_args=2,
)
async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display preferences, or update one when arguments are given."""
    ctx = ResonaContext.from_update(update, context)
    if ctx.user_id is None:
        return

    args = ctx.args
    if not args:
        settings = await ctx.services.users.get_settings(ctx.user_id)
        await ctx.reply(_render_settings(settings))
        return

    key = args[0].lower()
    if len(args) < 2:
        await ctx.reply(f"Missing value for {key}.\n\n{_SETTINGS_USAGE}")
        return

    value = args[1]
    fields: dict[str, object] = {}

    if key in {"notifications", "notify"}:
        enabled = _parse_toggle(value)
        if enabled is None:
            await ctx.reply("Notifications must be 'on' or 'off'.")
            return
        fields["notifications_enabled"] = enabled

    elif key in {"event_digest", "digest"}:
        enabled = _parse_toggle(value)
        if enabled is None:
            await ctx.reply("Event digest must be 'on' or 'off'.")
            return
        fields["event_digest_enabled"] = enabled

    elif key == "timezone":
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            await ctx.reply(
                "Unknown timezone. Use an IANA name such as Asia/Kolkata or UTC."
            )
            return
        fields["timezone"] = value

    elif key == "game":
        normalized = value.lower()
        if normalized == "none":
            fields["default_game"] = None
        elif normalized in IMPLEMENTED_GAMES:
            fields["default_game"] = normalized
        else:
            await ctx.reply(
                "Unknown game. Choose one of: "
                + ", ".join(IMPLEMENTED_GAMES)
                + ", none."
            )
            return

    elif key in {"language", "locale"}:
        normalized = value.lower()
        if not normalized.isalpha() or not 2 <= len(normalized) <= 5:
            await ctx.reply("Use a short language code such as en, de or ja.")
            return
        fields["locale"] = normalized

    else:
        await ctx.reply(f"Unknown setting: {key}\n\n{_SETTINGS_USAGE}")
        return

    settings = await ctx.services.users.update_settings(ctx.user_id, **fields)
    await ctx.reply("Updated.\n\n" + _render_settings(settings))
