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

from resona.wrappers.permissions import check_permission
from resona.wrappers.registry import (
    CommandSpec,
    HandlerSpec,
    get_commands,
    get_handler_specs,
    validate_registry,
)

logger = logging.getLogger("resona.wrappers")


async def _is_enabled(
    application: Application,
    spec: HandlerSpec,
    update: Any,
) -> tuple[bool, str | None]:
    """
    Optional controller interface:

    await controller.is_command_enabled(command_id, game, chat_id)

    Return True when enabled, or False when blocked.
    """
    controller = application.bot_data.get("resona_availability")

    if controller is None:
        return True, None

    chat = update.effective_chat
    chat_id = chat.id if chat else None

    if spec.kind == "command":
        canonical = spec.names[0]
        command_id = spec.command_id or (
            f"{spec.game}_{canonical}" if spec.game else f"core_{canonical}"
        )

        enabled = await controller.is_command_enabled(
            command_id=command_id,
            game=spec.game,
            chat_id=chat_id,
        )
    else:
        enabled = await controller.is_game_enabled(
            game=spec.game,
            chat_id=chat_id,
        ) if spec.game else True

    if enabled:
        return True, None

    return False, (
        "This feature is temporarily unavailable."
    )


def _guarded_callback(spec: HandlerSpec):
    @wraps(spec.callback)
    async def guarded(update, context):
        allowed, message = await _is_enabled(
            context.application,
            spec,
            update,
        )

        if not allowed:
            # Do not expose internal maintenance reasons to users.
            if update.callback_query:
                await update.callback_query.answer(
                    message or "This feature is unavailable.",
                    show_alert=True,
                )
            elif update.effective_message:
                await update.effective_message.reply_text(
                    message or "This feature is unavailable."
                )
            return None

        if not await check_permission(update, context, spec.permission):
            if update.callback_query:
                await update.callback_query.answer(
                    "You are not allowed to use this feature.",
                    show_alert=True,
                )
            elif update.effective_message:
                await update.effective_message.reply_text(
                    "You are not allowed to use this feature."
                )
            return None

        return await spec.callback(update, context)

    return guarded


def register_handlers(application: Application) -> None:
    """
    Validate everything first. No handlers are registered if validation
    fails, preventing partially registered command configurations.
    """
    validate_registry()

    specs = get_handler_specs()

    # Build all PTB handlers before mutating the application.
    prepared = []

    for spec in specs:
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
                    CallbackQueryHandler(
                        callback=callback,
                        pattern=spec.pattern,
                    ),
                    spec.group,
                )
            )

        elif spec.kind == "message":
            prepared.append(
                (
                    MessageHandler(
                        filters=spec.message_filters,
                        callback=callback,
                    ),
                    spec.group,
                )
            )

    # Only add handlers once the entire registry is valid and constructed.
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
    """
    Publish only canonical names in Telegram menus.
    Aliases remain usable but aren't duplicated in menus.

    Call from PTB's post_init hook.
    """
    validate_registry()
    commands = get_commands()

    def menu_commands(scope_name: str) -> list[BotCommand]:
        return [
            BotCommand(command=spec.canonical, description=spec.description)
            for spec in commands.values()
            if scope_name in spec.scopes
        ]

    private_commands = menu_commands("private")
    group_commands = menu_commands("groups")
    admin_commands = menu_commands("group_admins")

    if private_commands:
        await application.bot.set_my_commands(
            private_commands,
            scope=BotCommandScopeAllPrivateChats(),
        )

    if group_commands:
        await application.bot.set_my_commands(
            group_commands,
            scope=BotCommandScopeAllGroupChats(),
        )

    # Telegram's admin command scope requires a specific chat.
    for chat_id in group_chat_ids:
        if admin_commands:
            await application.bot.set_my_commands(
                admin_commands,
                scope=BotCommandScopeChatAdministrators(chat_id=chat_id),
            )