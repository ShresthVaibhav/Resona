"""``/start`` onboarding."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from resona.config.constants import CATEGORY_GENERAL, PROJECT_NAME
from resona.core.context import ResonaContext
from resona.wrappers import command


@command(
    "start",
    description=f"Get started with {PROJECT_NAME}",
    category=CATEGORY_GENERAL,
    private=True,
    groups=True,
)
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Greet the user and point them at help."""
    ctx = ResonaContext.from_update(update, context)
    name = ctx.user.first_name if ctx.user and ctx.user.first_name else "there"

    await ctx.reply(
        f"Hi {name}! I'm {PROJECT_NAME}.\n\nUse /help to see everything I can do."
    )
