from telegram import Update
from telegram.ext import ContextTypes

from resona.config.settings import settings


async def check_permission(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    permission: str,
) -> bool:
    if permission == "everyone":
        return True

    user = update.effective_user
    chat = update.effective_chat

    if user is None:
        return False

    if permission == "owner":
        return user.id == settings.BOT_OWNER_ID

    if permission == "bot_admin":
        # Owner automatically has bot-admin privileges.
        if user.id == settings.BOT_OWNER_ID:
            return True

        # Bot-admin IDs can be configured in application.bot_data.
        bot_admin_ids = context.application.bot_data.get(
            "BOT_ADMIN_IDS", set()
        )
        return user.id in bot_admin_ids

    if permission == "group_admin":
        if chat is None or chat.type == "private":
            return False

        if user.id == settings.BOT_OWNER_ID:
            return True

        try:
            member = await context.bot.get_chat_member(
                chat_id=chat.id,
                user_id=user.id,
            )
        except Exception:
            # Fail closed: if Telegram cannot verify the role,
            # do not allow the restricted action.
            return False

        return member.status in ("administrator", "creator")

    return False