"""``/help`` command reference generated from the registry."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from resona.config.constants import CATEGORY_HELP, PROJECT_NAME
from resona.core.context import ResonaContext
from resona.core.rich import CommandEntry, help_page
from resona.core.utils import escape_markdown
from resona.wrappers import command
from resona.wrappers.registry import commands_by_category, get_categories


def render_help() -> str:
    """Build the help text from currently registered commands."""
    grouped = commands_by_category()

    lines = [f"*{escape_markdown(PROJECT_NAME)} commands*", ""]
    for category in get_categories():
        lines.append(f"*{escape_markdown(category)}*")
        for spec in sorted(grouped[category], key=lambda item: item.canonical):
            aliases = ""
            if spec.aliases:
                rendered = ", ".join(f"/{alias}" for alias in spec.aliases)
                aliases = f" \\(also {escape_markdown(rendered)}\\)"
            description = escape_markdown(spec.description)
            lines.append(f"/{spec.canonical}{aliases} - {description}")
        lines.append("")

    return "\n".join(lines).strip()


@command(
    "help",
    aliases=("commands",),
    description="List every available command",
    category=CATEGORY_HELP,
    private=True,
    groups=True,
)
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send the generated command reference."""
    ctx = ResonaContext.from_update(update, context)
    if ctx.message is None:
        return

    grouped = commands_by_category()
    sections = [
        (
            category,
            [
                CommandEntry(
                    name=spec.canonical,
                    description=spec.description,
                    aliases=tuple(spec.aliases),
                )
                for spec in sorted(grouped[category], key=lambda item: item.canonical)
            ],
        )
        for category in get_categories()
    ]
    await ctx.reply_rich(help_page(sections))
