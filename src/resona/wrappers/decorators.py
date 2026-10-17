from collections.abc import Callable
from typing import Any

from telegram.ext import filters

from resona.wrappers.registry import (
    VALID_PERMISSIONS,
    VALID_SCOPES,
    HandlerSpec,
    add_handler_spec,
)


def command(
    *names: str,
    aliases: tuple[str, ...] = (),
    game: str | None = None,
    command_id: str | None = None,
    description: str | None = None,
    private: bool = False,
    groups: bool = False,
    group_admins: bool = False,
    bot_admins: bool = False,
    owner: bool = False,
    permission: str = "everyone",
    group: int = 0,
) -> Callable:
    if not names:
        raise ValueError("@command requires a canonical command name.")

    scopes = tuple(
        name
        for name, enabled in (
            ("private", private),
            ("groups", groups),
            ("group_admins", group_admins),
            ("bot_admins", bot_admins),
            ("owner", owner),
        )
        if enabled
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

    if len(names) != 1:
        raise ValueError(
            "Pass exactly one canonical name to @command; "
            "use aliases= for alternate names."
        )

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        add_handler_spec(
            HandlerSpec(
                kind="command",
                callback=func,
                names=names,
                aliases=tuple(aliases),
                game=game,
                command_id=command_id,
                description=description,
                scopes=scopes,
                permission=permission,
                group=group,
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
) -> Callable:
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
) -> Callable:
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