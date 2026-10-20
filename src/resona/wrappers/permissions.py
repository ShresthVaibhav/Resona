"""Permission checks shared by every handler.

Handlers must not implement their own authorization; the wrapper layer calls
:func:`check_permission` before dispatch. Checks fail closed.
"""

from __future__ import annotations

from telegram import Chat, Update
from telegram.ext import ContextTypes

from resona.config.settings import Settings, get_settings


def _resolve_settings(context: ContextTypes.DEFAULT_TYPE) -> Settings:
    settings = context.application.bot_data.get("settings")
    if isinstance(settings, Settings):
        return settings
    return get_settings()


def _bot_admin_ids(context: ContextTypes.DEFAULT_TYPE, settings: Settings) -> set[int]:
    from_data = context.application.bot_data.get("BOT_ADMIN_IDS")
    if from_data is not None:
        return set(from_data)
    return set(settings.admin_ids)


async def check_permission(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    permission: str,
) -> bool:
    """Return whether the update's author satisfies ``permission``."""
    if permission == "everyone":
        return True

    user = update.effective_user
    chat = update.effective_chat

    if user is None:
        return False

    settings = _resolve_settings(context)

    if permission == "owner":
        return user.id == settings.BOT_OWNER_ID

    if permission == "bot_admin":
        # The owner always has bot-admin privileges.
        if user.id == settings.BOT_OWNER_ID:
            return True
        return user.id in _bot_admin_ids(context, settings)

    if permission == "group_admin":
        if chat is None or chat.type == Chat.PRIVATE:
            return False

        if user.id == settings.BOT_OWNER_ID:
            return True

        try:
            member = await context.bot.get_chat_member(
                chat_id=chat.id,
                user_id=user.id,
            )
        except Exception:
            # Fail closed: if Telegram cannot verify the role, deny.
            return False

        return member.status in ("administrator", "creator")

    return False
