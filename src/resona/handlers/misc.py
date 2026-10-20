"""Small general-purpose commands."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from resona.config.constants import (
    CATEGORY_GENERAL,
    PROJECT_NAME,
    PROJECT_VERSION,
)
from resona.core.context import ResonaContext
from resona.wrappers import command


@command(
    "ping",
    description="Check that the bot is responding",
    category=CATEGORY_GENERAL,
    private=True,
    groups=True,
    rate_limit=30,
)
async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reply with a short liveness confirmation."""
    ctx = ResonaContext.from_update(update, context)
    await ctx.reply("Pong!")


@command(
    "about",
    description=f"About {PROJECT_NAME}",
    category=CATEGORY_GENERAL,
    private=True,
    groups=True,
)
async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show version and scope information."""
    ctx = ResonaContext.from_update(update, context)
    await ctx.reply(
        f"{PROJECT_NAME} v{PROJECT_VERSION}\n\n"
        "A modular Telegram bot for HoYoLAB-based game utilities.\n"
        "Supported games: Genshin Impact, Honkai: Star Rail, "
        "and Zenless Zone Zero."
    )
