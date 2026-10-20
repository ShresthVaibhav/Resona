"""Connect validated registry specs to the Telegram application."""

from __future__ import annotations

import logging
from functools import wraps
from typing import Any

from telegram import (
    BotCommand,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
    BotCommandScopeChatAdministrators,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
)

from resona.core.availability import AvailabilityController
from resona.core.ratelimit import RateLimiter
from resona.core.utils import format_duration
from resona.wrappers.permissions import check_permission
from resona.wrappers.registry import (
    HandlerSpec,
    get_command_id,
    get_commands,
    get_handler_specs,
    validate_registry,
)

logger = logging.getLogger("resona.wrappers")

UNAVAILABLE_MESSAGE = "This feature is temporarily unavailable."
NOT_ALLOWED_MESSAGE = "You are not allowed to use this feature."


def resolve_command_id(spec: HandlerSpec) -> str:
    """Stable command ID for a command spec."""
    if spec.command_id:
        return spec.command_id
    if spec.names:
        resolved = get_command_id(spec.names[0])
        if resolved:
            return resolved
        canonical = spec.names[0]
        return f"{spec.game}_{canonical}" if spec.game else f"core_{canonical}"
    return "<unknown>"


async def _respond(update: Any, text: str) -> None:
    """Reply to the originating message or callback query."""
    if update.callback_query is not None:
        await update.callback_query.answer(text, show_alert=True)
    elif update.effective_message is not None:
        await update.effective_message.reply_text(text)


async def _is_enabled(
    availability: AvailabilityController,
    spec: HandlerSpec,
    update: Any,
) -> bool:
    chat = update.effective_chat
    chat_id = chat.id if chat else None

    if spec.kind == "command":
        return await availability.is_command_enabled(
            command_id=resolve_command_id(spec),
            game=spec.game,
            chat_id=chat_id,
        )

    if spec.game:
        return await availability.is_game_enabled(game=spec.game, chat_id=chat_id)

    return True


def _validate_arguments(spec: HandlerSpec, context: Any) -> str | None:
    """Return a usage error message when argument counts are wrong."""
    args = list(getattr(context, "args", []) or [])
    count = len(args)

    too_few = count < spec.min_args
    too_many = spec.max_args is not None and count > spec.max_args

    if not too_few and not too_many:
        return None

    if spec.usage:
        detail = f"Usage: {spec.usage}"
    elif spec.names:
        detail = f"Usage: /{spec.names[0]}"
    else:
        detail = "Invalid usage."

    return f"Invalid arguments.\n{detail}"


def _rate_limit_key(spec: HandlerSpec, update: Any) -> tuple[str, int] | None:
    identifier = update.effective_user.id if update.effective_user else None
    if identifier is None and update.effective_chat is not None:
        identifier = update.effective_chat.id
    if identifier is None:
        return None
    return resolve_command_id(spec), identifier


def _guarded_callback(spec: HandlerSpec):
    """Wrap a handler with availability, permission, argument and rate checks."""

    @wraps(spec.callback)
    async def guarded(update: Any, context: Any) -> Any:
        application = context.application

        if not spec.enabled:
            await _respond(update, UNAVAILABLE_MESSAGE)
            return None

        availability = application.bot_data.get("resona_availability")
        if isinstance(availability, AvailabilityController):
            if not await _is_enabled(availability, spec, update):
                await _respond(update, availability.unavailable_message(game=spec.game))
                return None

        if not await check_permission(update, context, spec.permission):
            await _respond(update, NOT_ALLOWED_MESSAGE)
            return None

        if spec.kind == "command":
            usage_error = _validate_arguments(spec, context)
            if usage_error is not None:
                await _respond(update, usage_error)
                return None

            if spec.rate_limit:
                limiter = application.bot_data.get("resona_ratelimiter")
                key = _rate_limit_key(spec, update)
                if isinstance(limiter, RateLimiter) and key is not None:
                    if not limiter.allow(key):
                        retry_after = limiter.retry_after(key)
                        await _respond(
                            update,
                            "You are sending commands too quickly. "
                            f"Try again in {format_duration(retry_after)}.",
                        )
                        return None

        return await spec.callback(update, context)

    return guarded


def register_handlers(application: Application) -> None:
    """Validate the registry and register every handler.

    Nothing is added to the application unless validation succeeds, so a broken
    declaration cannot leave the bot partially configured.
    """
    validate_registry()

    prepared: list[tuple[Any, int]] = []

    for spec in get_handler_specs():
        callback = _guarded_callback(spec)

        if spec.kind == "command":
            prepared.append(
                (
                    CommandHandler(
                        command=list(spec.names + spec.aliases),
                        callback=callback,
                    ),
                    spec.group,
                )
            )
        elif spec.kind == "callback":
            prepared.append(
                (
                    CallbackQueryHandler(callback=callback, pattern=spec.pattern),
                    spec.group,
                )
            )
        elif spec.kind == "message":
            prepared.append(
                (
                    MessageHandler(filters=spec.message_filters, callback=callback),
                    spec.group,
                )
            )

    for handler, group in prepared:
        application.add_handler(handler, group=group)

    logger.info(
        "Registered %d handlers and %d commands.",
        len(prepared),
        len(get_commands()),
    )


async def register_bot_commands(
    application: Application,
    group_chat_ids: tuple[int, ...] = (),
) -> None:
    """Publish canonical command names in Telegram menus.

    Aliases remain usable but are not duplicated in menus. Call from PTB's
    ``post_init`` hook.
    """
    validate_registry()
    commands = get_commands()

    def menu_commands(scope_name: str) -> list[BotCommand]:
        return [
            BotCommand(command=spec.canonical, description=spec.description)
            for spec in commands.values()
            if scope_name in spec.scopes
        ]

    scopes = (
        (BotCommandScopeAllPrivateChats(), menu_commands("private")),
        (BotCommandScopeAllGroupChats(), menu_commands("groups")),
    )

    for scope, items in scopes:
        if items:
            await _safe_set_commands(application, items, scope)

    admin_commands = menu_commands("group_admins")
    for chat_id in group_chat_ids:
        if admin_commands:
            await _safe_set_commands(
                application,
                admin_commands,
                BotCommandScopeChatAdministrators(chat_id=chat_id),
            )


async def _safe_set_commands(
    application: Application, items: list[BotCommand], scope: Any
) -> None:
    try:
        await application.bot.set_my_commands(items, scope=scope)
    except Exception:
        logger.warning(
            "Failed to publish command menu for scope %r.", scope, exc_info=True
        )
