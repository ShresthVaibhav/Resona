"""Collision and invalid-declaration detection."""

from __future__ import annotations

import pytest

from resona.wrappers import command
from resona.wrappers.registry import validate_registry


def test_duplicate_command_name_is_rejected() -> None:
    @command("ping", description="First")
    async def first(update, context):  # pragma: no cover
        ...

    @command("ping", description="Second")
    async def second(update, context):  # pragma: no cover
        ...

    with pytest.raises(RuntimeError, match="collision"):
        validate_registry()


def test_alias_collision_between_commands_is_rejected() -> None:
    @command("alpha", aliases=("shared",), description="A")
    async def alpha(update, context):  # pragma: no cover
        ...

    @command("beta", aliases=("shared",), description="B")
    async def beta(update, context):  # pragma: no cover
        ...

    with pytest.raises(RuntimeError, match="collision"):
        validate_registry()


def test_canonical_name_repeated_in_aliases_is_rejected_at_declaration() -> None:
    with pytest.raises(ValueError, match="canonical name"):

        @command("loop", aliases=("loop",), description="Broken")
        async def loop(update, context):  # pragma: no cover
            ...


def test_invalid_command_name_is_rejected() -> None:
    @command("Bad-Name", description="Invalid characters")
    async def handler(update, context):  # pragma: no cover
        ...

    with pytest.raises(RuntimeError, match="invalid Telegram command name"):
        validate_registry()


def test_duplicate_aliases_within_a_command_are_rejected() -> None:
    @command("x", aliases=("y", "y"), description="Duplicate aliases")
    async def handler(update, context):  # pragma: no cover
        ...

    with pytest.raises(RuntimeError, match="duplicate aliases"):
        validate_registry()


def test_missing_description_is_rejected() -> None:
    @command("nodesc")
    async def handler(update, context):  # pragma: no cover
        ...

    with pytest.raises(RuntimeError, match="needs a non-empty description"):
        validate_registry()


def test_invalid_argument_bounds_are_rejected_at_declaration() -> None:
    with pytest.raises(ValueError, match="max_args"):

        @command("x", description="Bad bounds", min_args=2, max_args=1)
        async def handler(update, context):  # pragma: no cover
            ...


def test_non_positive_rate_limit_is_rejected_at_declaration() -> None:
    with pytest.raises(ValueError, match="rate_limit"):

        @command("x", description="Bad rate", rate_limit=0)
        async def handler(update, context):  # pragma: no cover
            ...


def test_description_required_when_exposed_in_a_menu_scope() -> None:
    with pytest.raises(ValueError, match="description is required"):

        @command("x", private=True)
        async def handler(update, context):  # pragma: no cover
            ...
