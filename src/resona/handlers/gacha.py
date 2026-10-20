"""Gacha history commands for each implemented game."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from resona.config.constants import CATEGORY_GAMES
from resona.core.context import ResonaContext
from resona.core.errors import UserError
from resona.games.genshin.service import GenshinService
from resona.wrappers import command


def _parse_history_args(args: list[str]) -> tuple[str | None, int]:
    """Read an optional page number and optional history URL in any order."""
    authkey: str | None = None
    page = 1
    page_seen = False

    for arg in args:
        if arg.isdigit():
            if page_seen:
                raise UserError("Send at most one page number.")
            page = int(arg)
            page_seen = True
        else:
            if authkey is not None:
                raise UserError("Send at most one history URL.")
            authkey = arg

    if page < 1:
        raise UserError("Page must be at least 1.")

    return authkey, page


async def _run_history(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    game: str,
) -> None:
    ctx = ResonaContext.from_update(update, context)
    if ctx.user_id is None:
        return

    try:
        authkey, page = _parse_history_args(ctx.args)
        service = ctx.services.games.get(game)
        text = await service.wishes(
            ctx.user_id,
            authkey=authkey,
            page=page,
        )
    except UserError as exc:
        await ctx.reply(str(exc))
        return

    await ctx.reply(text)


@command(
    "wishes",
    description="Show recent Genshin wishes",
    category=CATEGORY_GAMES,
    private=True,
    usage="/wishes [page] [history URL]",
    max_args=2,
    rate_limit=3,
)
async def wishes_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show recent Genshin Impact wishes."""
    await _run_history(update, context, "genshin")


@command(
    "warp",
    description="Show recent Star Rail warps",
    category=CATEGORY_GAMES,
    private=True,
    usage="/warp [page] [history URL]",
    max_args=2,
    rate_limit=3,
)
async def warp_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show recent Honkai: Star Rail warps."""
    await _run_history(update, context, "hsr")


@command(
    "signals",
    description="Show recent ZZZ signal searches",
    category=CATEGORY_GAMES,
    private=True,
    usage="/signals [page] [history URL]",
    max_args=2,
    rate_limit=3,
)
async def signals_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show recent Zenless Zone Zero signal searches."""
    await _run_history(update, context, "zzz")


@command(
    "miliastra",
    description="Show recent Miliastra Wonderland pulls",
    category=CATEGORY_GAMES,
    private=True,
    usage="/miliastra [page] [history URL]",
    max_args=2,
    rate_limit=3,
)
async def miliastra_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show recent Genshin Impact Miliastra Wonderland pulls."""
    ctx = ResonaContext.from_update(update, context)
    if ctx.user_id is None:
        return

    try:
        authkey, page = _parse_history_args(ctx.args)
        service = ctx.services.games.get("genshin")
        if not isinstance(service, GenshinService):
            raise UserError("Genshin Impact is not available.")
        text = await service.miliastra(
            ctx.user_id,
            authkey=authkey,
            page=page,
        )
    except UserError as exc:
        await ctx.reply(str(exc))
        return

    await ctx.reply(text)
