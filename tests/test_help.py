"""Help text generated from the registry."""

from __future__ import annotations

from resona.handlers.help import render_help
from resona.wrappers import command
from resona.wrappers.registry import validate_registry


def test_help_lists_registered_commands_by_category() -> None:
    @command("alpha", description="First command", category="General", private=True)
    async def alpha(update, context):  # pragma: no cover
        ...

    @command(
        "beta",
        aliases=("b",),
        description="Second command",
        category="Genshin",
        game="genshin",
    )
    async def beta(update, context):  # pragma: no cover
        ...

    validate_registry()
    text = render_help()

    assert "/alpha" in text
    assert "/beta" in text
    assert "General" in text
    assert "Genshin" in text
    assert "First command" in text


def test_help_renders_aliases() -> None:
    @command("notes", aliases=("stamina",), description="Notes", private=True)
    async def notes(update, context):  # pragma: no cover
        ...

    validate_registry()
    text = render_help()

    assert "stamina" in text


def test_help_with_no_commands_still_renders_a_header() -> None:
    validate_registry()
    assert "commands" in render_help()
