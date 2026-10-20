"""Decorator, registry and registration API."""

from __future__ import annotations

from resona.wrappers.decorators import callback_query, command, message
from resona.wrappers.error_handler import handle_error, register_error_handler
from resona.wrappers.permissions import check_permission
from resona.wrappers.registration import (
    register_bot_commands,
    register_handlers,
)
from resona.wrappers.registry import (
    CommandSpec,
    HandlerSpec,
    commands_by_category,
    get_categories,
    get_command_by_id,
    get_command_id,
    get_commands,
    get_commands_for_game,
    iter_commands,
    validate_registry,
)

__all__ = [
    "CommandSpec",
    "HandlerSpec",
    "callback_query",
    "check_permission",
    "command",
    "commands_by_category",
    "get_categories",
    "get_command_by_id",
    "get_command_id",
    "get_commands",
    "get_commands_for_game",
    "handle_error",
    "iter_commands",
    "message",
    "register_bot_commands",
    "register_error_handler",
    "register_handlers",
    "validate_registry",
]
