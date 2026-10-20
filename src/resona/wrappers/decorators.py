"""Decorators that declare handlers.

Decorators only record metadata in the registry; they never touch Telegram.
:func:`resona.wrappers.registration.register_handlers` performs the actual
registration once the registry has been validated.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from telegram.ext import filters

from resona.config.constants import CATEGORY_GENERAL
from resona.wrappers.registry import (
    VALID_PERMISSIONS,
    VALID_SCOPES,
    HandlerSpec,
    add_handler_spec,
)


def command(
    name: str,
    *,
    aliases: Sequence[str] = (),
    game: str | None = None,
    command_id: str | None = None,
    description: str | None = None,
    category: str = CATEGORY_GENERAL,
    usage: str | None = None,
    min_args: int = 0,
    max_args: int | None = None,
    private: bool = False,
    groups: bool = False,
    group_admins: bool = False,
    bot_admins: bool = False,
    owner: bool = False,
    permission: str = "everyone",
    group: int = 0,
    rate_limit: int | None = None,
    enabled: bool = True,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Declare a text command.

    Args:
        name: Canonical Telegram command name (without ``/``).
        aliases: Alternate names. Must be globally unique.
        game: Game identifier for game-specific commands.
        command_id: Override the generated stable ID (rarely needed).
        description: Menu/help description.
        category: Help category.
        usage: Usage hint shown on invalid arguments.
        min_args: Minimum positional arguments.
        max_args: Maximum positional arguments; ``None`` means unlimited.
        private/groups/group_admins/bot_admins/owner: Telegram menu scopes.
        permission: Required permission level.
        group: PTB handler group.
        rate_limit: Optional per-user limit in commands per minute.
        enabled: When ``False`` the command is registered but marked unavailable.
    """
    if not name:
        raise ValueError("@command requires a canonical command name.")

    scopes = tuple(
        scope
        for scope, is_enabled in (
            ("private", private),
            ("groups", groups),
            ("group_admins", group_admins),
            ("bot_admins", bot_admins),
            ("owner", owner),
        )
        if is_enabled
    )

    if set(scopes) - VALID_SCOPES:
        raise ValueError(f"Invalid command scopes: {scopes!r}")

    if permission not in VALID_PERMISSIONS:
        raise ValueError(f"Invalid permission: {permission!r}")

    if scopes and not (description and description.strip()):
        raise ValueError(
            "A non-empty description is required when a command "
            "is exposed in any Telegram menu scope."
        )

    if min_args < 0:
        raise ValueError("min_args must not be negative.")

    if max_args is not None and max_args < min_args:
        raise ValueError("max_args must be greater than or equal to min_args.")

    if rate_limit is not None and rate_limit <= 0:
        raise ValueError("rate_limit must be positive when set.")

    normalized_aliases = tuple(aliases)
    if name in normalized_aliases:
        raise ValueError("The canonical name must not be repeated in aliases.")

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        add_handler_spec(
            HandlerSpec(
                kind="command",
                callback=func,
                names=(name,),
                aliases=normalized_aliases,
                game=game,
                command_id=command_id,
                description=description,
                category=category,
                usage=usage,
                min_args=min_args,
                max_args=max_args,
                scopes=scopes,
                permission=permission,
                group=group,
                rate_limit=rate_limit,
                enabled=enabled,
            )
        )
        return func

    return decorator


def callback_query(
    pattern: str,
    *,
    game: str | None = None,
    permission: str = "everyone",
    group: int = 0,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Declare an inline-keyboard callback handler."""
    if not pattern:
        raise ValueError("@callback_query requires a pattern.")
    if permission not in VALID_PERMISSIONS:
        raise ValueError(f"Invalid permission: {permission!r}")

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        add_handler_spec(
            HandlerSpec(
                kind="callback",
                callback=func,
                pattern=pattern,
                game=game,
                permission=permission,
                group=group,
            )
        )
        return func

    return decorator


def message(
    message_filters: filters.BaseFilter,
    *,
    game: str | None = None,
    permission: str = "everyone",
    group: int = 0,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Declare a generic message handler."""
    if permission not in VALID_PERMISSIONS:
        raise ValueError(f"Invalid permission: {permission!r}")

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        add_handler_spec(
            HandlerSpec(
                kind="message",
                callback=func,
                message_filters=message_filters,
                game=game,
                permission=permission,
                group=group,
            )
        )
        return func

    return decorator
