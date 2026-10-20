"""Account linking commands: ``/link``, ``/unlink`` and ``/accounts``."""

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from resona.config.constants import (
    CATEGORY_ACCOUNT,
    GAME_LABELS,
    IMPLEMENTED_GAMES,
)
from resona.core.context import ResonaContext
from resona.core.errors import ConfigurationError, UserError
from resona.core.rich import AccountEntry, account_overview
from resona.wrappers import command

logger = logging.getLogger("resona.handlers.account")

_GAME_CHOICES = ", ".join(IMPLEMENTED_GAMES)

_LINK_HELP = (
    "Link a HoYoLAB account\n\n"
    "1. Open hoyolab.com in a browser and sign in.\n"
    "2. Open developer tools, find any request to hoyolab.com and copy its "
    "Cookie request header.\n"
    "3. Send it here:\n\n"
    "/link <game> <cookies>\n"
    "/link <game> <uid> <cookies>\n\n"
    f"Games: {_GAME_CHOICES}\n\n"
    "Example:\n"
    "/link genshin ltuid_v2=...; ltoken_v2=...; ltmid_v2=...\n\n"
    "Cookies are encrypted before they are stored. The message containing them "
    "is deleted when Telegram allows it."
)


async def _delete_source_message(ctx: ResonaContext) -> None:
    """Best-effort removal of the message that carried the cookies."""
    message = ctx.message
    if message is None:
        return
    try:
        await message.delete()
    except Exception:  # Telegram forbids deleting user messages in some chats.
        logger.debug("Could not delete the linking message.", exc_info=True)


def _split_link_arguments(args: list[str]) -> tuple[str, str | None, str] | None:
    """Parse ``<game> [uid] <cookies>`` from PTB's whitespace-split args.

    Cookie headers contain spaces, so everything after the game (and optional
    numeric UID) is rejoined.
    """
    if not args:
        return None

    game = args[0].lower()
    rest = list(args[1:])
    uid: str | None = None

    if rest and rest[0].isdigit():
        uid = rest.pop(0)

    cookies = " ".join(rest).strip()
    return game, uid, cookies


@command(
    "link",
    description="Link a HoYoLAB account",
    category=CATEGORY_ACCOUNT,
    private=True,
    usage="/link <game> <cookies> [uid]",
    rate_limit=3,
)
async def link_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Validate and store HoYoLAB cookies for one game account."""
    ctx = ResonaContext.from_update(update, context)
    if ctx.user_id is None:
        return

    parsed = _split_link_arguments(ctx.args)
    if parsed is None or not parsed[2]:
        await ctx.reply(_LINK_HELP)
        return

    game, uid, cookies = parsed
    if game not in IMPLEMENTED_GAMES:
        await ctx.reply(f"Unknown game. Choose one of: {_GAME_CHOICES}.")
        return

    # Remove the secret from the chat as early as possible.
    await _delete_source_message(ctx)

    try:
        account = await ctx.services.accounts.link(ctx.user_id, game, cookies, uid=uid)
    except ConfigurationError:
        logger.warning("Account linking requested without a valid encryption key.")
        await ctx.reply(
            "Account linking is not configured on this bot yet. "
            "Please contact the bot owner."
        )
        return
    except UserError as exc:
        await ctx.reply(str(exc))
        return

    name = account.nickname or "Unknown"
    await ctx.reply(
        f"Linked {GAME_LABELS[game]} account {name} (UID {account.uid}).\n"
        "Cookies are stored encrypted. Use /unlink to remove them."
    )


@command(
    "unlink",
    description="Remove a linked account",
    category=CATEGORY_ACCOUNT,
    private=True,
    usage="/unlink [game]",
    max_args=1,
)
async def unlink_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Delete stored credentials for one game, or for every game."""
    ctx = ResonaContext.from_update(update, context)
    if ctx.user_id is None:
        return

    game = ctx.args[0].lower() if ctx.args else None
    if game is not None and game not in IMPLEMENTED_GAMES:
        await ctx.reply(f"Unknown game. Choose one of: {_GAME_CHOICES}.")
        return

    try:
        removed = await ctx.services.accounts.unlink(ctx.user_id, game)
    except UserError as exc:
        await ctx.reply(str(exc))
        return

    if removed == 0:
        scope = GAME_LABELS[game] if game else "any game"
        await ctx.reply(f"No linked accounts found for {scope}.")
        return

    if game:
        await ctx.reply(
            f"Unlinked {removed} {GAME_LABELS[game]} account"
            f"{'' if removed == 1 else 's'}."
        )
    else:
        await ctx.reply(f"Unlinked {removed} account{'' if removed == 1 else 's'}.")


@command(
    "accounts",
    description="List your linked accounts",
    category=CATEGORY_ACCOUNT,
    private=True,
)
async def accounts_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show every linked account grouped by game."""
    ctx = ResonaContext.from_update(update, context)
    if ctx.user_id is None:
        return

    accounts = await ctx.services.accounts.list_accounts(ctx.user_id)
    if not accounts:
        await ctx.reply(
            "No accounts linked yet. Use /link to connect a HoYoLAB account."
        )
        return

    sections = []
    for game in IMPLEMENTED_GAMES:
        game_accounts = [item for item in accounts if item.game == game]
        if not game_accounts:
            continue

        sections.append(
            (
                GAME_LABELS[game],
                [
                    AccountEntry(
                        name=account.nickname or "Unknown",
                        uid=account.uid,
                        server=account.server,
                        is_primary=account.is_primary,
                    )
                    for account in game_accounts
                ],
            )
        )

    await ctx.reply_rich(account_overview(sections))
