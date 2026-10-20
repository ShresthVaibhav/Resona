"""Handler registration against a real python-telegram-bot application."""

from __future__ import annotations

import pytest
from telegram.ext import Application

from resona.wrappers import command, register_handlers


def _application() -> Application:
    return Application.builder().token("123456:TEST-TOKEN").build()


def test_register_handlers_adds_command_handler() -> None:
    @command("ping", description="Liveness check", private=True)
    async def ping(update, context):  # pragma: no cover - not invoked
        ...

    application = _application()
    register_handlers(application)

    assert len(application.handlers[0]) == 1


def test_aliases_are_registered_on_the_same_handler() -> None:
    @command("notes", aliases=("stamina", "resin"), description="Notes", private=True)
    async def notes(update, context):  # pragma: no cover
        ...

    application = _application()
    register_handlers(application)

    handler = next(iter(application.handlers[0]))
    assert set(handler.commands) == {"notes", "stamina", "resin"}


def test_registration_is_blocked_by_a_collision() -> None:
    @command("dup", description="One")
    async def one(update, context):  # pragma: no cover
        ...

    @command("dup", description="Two")
    async def two(update, context):  # pragma: no cover
        ...

    application = _application()

    with pytest.raises(RuntimeError, match="collision"):
        register_handlers(application)
