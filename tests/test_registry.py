"""Registry metadata and command ID behaviour."""

from __future__ import annotations

import pytest

from resona.wrappers import command
from resona.wrappers.registry import (
    commands_by_category,
    get_categories,
    get_command_id,
    get_commands,
    validate_registry,
)


def test_core_command_is_registered_with_stable_id() -> None:
    @command(
        "profile",
        aliases=("me",),
        description="View your profile",
        category="Profile",
        private=True,
    )
    async def profile(update, context):  # pragma: no cover - declaration only
        ...

    validate_registry()
    commands = get_commands()

    assert "core_profile" in commands
    spec = commands["core_profile"]
    assert spec.canonical == "profile"
    assert spec.aliases == ("me",)
    assert spec.category == "Profile"
    assert spec.description == "View your profile"


def test_alias_and_name_lookup_resolve_to_same_command() -> None:
    @command("notes", aliases=("stamina",), description="Show notes", private=True)
    async def notes(update, context):  # pragma: no cover
        ...

    validate_registry()

    assert get_command_id("notes") == "core_notes"
    assert get_command_id("/notes") == "core_notes"
    assert get_command_id("stamina") == "core_notes"


def test_game_command_uses_game_prefix() -> None:
    @command(
        "characters",
        description="List characters",
        category="Genshin",
        game="genshin",
    )
    async def characters(update, context):  # pragma: no cover
        ...

    validate_registry()

    assert "genshin_characters" in get_commands()


def test_categories_preserve_registration_order() -> None:
    @command("a", description="A", category="General")
    async def a(update, context):  # pragma: no cover
        ...

    @command("b", description="B", category="Genshin", game="genshin")
    async def b(update, context):  # pragma: no cover
        ...

    validate_registry()

    assert get_categories() == ["General", "Genshin"]
    grouped = commands_by_category()
    assert [spec.canonical for spec in grouped["General"]] == ["a"]


def test_adding_a_command_after_validation_is_rejected() -> None:
    validate_registry()

    with pytest.raises(RuntimeError, match="already finalized"):

        @command("late", description="Too late")
        async def late(update, context):  # pragma: no cover
            ...
