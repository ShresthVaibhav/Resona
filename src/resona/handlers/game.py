"""Game-agnostic commands, dispatched to the selected game service."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from resona.config.constants import (
    CATEGORY_GAMES,
    GAME_LABELS,
    IMPLEMENTED_GAMES,
    PLANNED_GAMES,
)
from resona.core.context import ResonaContext
from resona.core.errors import CredentialsMissingError, UserError
from resona.wrappers import command

_GAME_CHOICES = ", ".join(IMPLEMENTED_GAMES)


async def _resolve_game(ctx: ResonaContext, args: list[str]) -> str:
    """Pick the game from the first argument, the default, or the only link."""
    if ctx.user_id is None:
        raise CredentialsMissingError()

    if args:
        candidate = args[0].lower()
        if candidate in IMPLEMENTED_GAMES:
            args.pop(0)
            return candidate
        if candidate in PLANNED_GAMES:
            raise UserError(
                f"{GAME_LABELS[candidate]} is planned but not supported yet."
            )

    settings = await ctx.services.users.get_settings(ctx.user_id)
    if settings.default_game in IMPLEMENTED_GAMES:
        return settings.default_game

    accounts = await ctx.services.accounts.list_accounts(ctx.user_id)
    games = {account.game for account in accounts if account.game in IMPLEMENTED_GAMES}

    if len(games) == 1:
        return next(iter(games))
    if not games:
        raise CredentialsMissingError()

    raise UserError(
        "You have several games linked. Name one, for example "
        "/notes genshin, or set a default with /settings game <game>.\n"
        f"Games: {_GAME_CHOICES}"
    )


async def _run(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str) -> None:
    ctx = ResonaContext.from_update(update, context)
    if ctx.user_id is None:
        return

    try:
        game = await _resolve_game(ctx, ctx.args)
        service = ctx.services.games.get(game)
        text = await getattr(service, action)(ctx.user_id)
    except UserError as exc:
        await ctx.reply(str(exc))
        return

    await ctx.reply(text)


@command(
    "notes",
    aliases=("stamina",),
    description="Show stamina and daily notes",
    category=CATEGORY_GAMES,
    private=True,
    groups=True,
    usage="/notes [game]",
    rate_limit=10,
)
async def notes_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show real-time notes for the selected game."""
    await _run(update, context, "notes")


@command(
    "characters",
    description="List your characters or agents",
    category=CATEGORY_GAMES,
    private=True,
    groups=True,
    usage="/characters [game]",
    rate_limit=5,
)
async def characters_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """List owned characters or agents for the selected game."""
    await _run(update, context, "characters")


@command(
    "checkin",
    description="Claim the daily HoYoLAB reward",
    category=CATEGORY_GAMES,
    private=True,
    usage="/checkin [game]",
    rate_limit=3,
)
async def checkin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Claim the daily reward for the selected game."""
    await _run(update, context, "checkin")


@command(
    "diary",
    description="Show this month's income",
    category=CATEGORY_GAMES,
    private=True,
    usage="/diary [game]",
    rate_limit=5,
)
async def diary_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the monthly income breakdown for the selected game."""
    await _run(update, context, "diary")


@command(
    "endgame",
    description="Show endgame progress",
    category=CATEGORY_GAMES,
    private=True,
    usage="/endgame [game]",
    rate_limit=5,
)
async def endgame_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show endgame progress for the selected game."""
    await _run(update, context, "endgame")


@command(
    "events",
    description="Show active events",
    category=CATEGORY_GAMES,
    private=True,
    groups=True,
    usage="/events [game]",
    rate_limit=5,
)
async def events_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show active events for the selected game."""
    await _run(update, context, "events")
