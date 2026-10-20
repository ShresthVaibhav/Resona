"""Handlers that are shared across the bot.

``load_handlers`` imports each handler module so its decorators run and
populate the registry. It is idempotent.
"""

from __future__ import annotations

import importlib

_HANDLER_MODULES = (
    "resona.handlers.start",
    "resona.handlers.help",
    "resona.handlers.misc",
    "resona.handlers.account",
    "resona.handlers.profile",
    "resona.handlers.game",
    "resona.handlers.gacha",
)


def load_handlers() -> None:
    """Import every handler module, registering its commands."""
    for module in _HANDLER_MODULES:
        importlib.import_module(module)


__all__ = ["load_handlers"]
