"""A convenience wrapper around ``(update, context)``.

Handlers keep the standard python-telegram-bot ``(update, context)`` signature.
``ResonaContext`` is an optional helper for access to the current user, chat,
arguments, settings and shared services without repeating lookups.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from telegram import Chat, Message, Update, User
from telegram.ext import Application, ContextTypes

from resona.core.rich import (
    RichContent,
    send_rich_message,
    supports_rich_messages,
    to_plain_text,
)
from resona.core.utils import truncate

if TYPE_CHECKING:
    from resona.config.settings import Settings
    from resona.core.availability import AvailabilityController
    from resona.services import Services

logger = logging.getLogger("resona.context")


@dataclass(slots=True)
class ResonaContext:
    """Read-only view over a single Telegram update."""

    update: Update
    ptb: ContextTypes.DEFAULT_TYPE

    @classmethod
    def from_update(
        cls,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> ResonaContext:
        return cls(update=update, ptb=context)

    @property
    def application(self) -> Application:
        return self.ptb.application

    @property
    def bot(self) -> Any:
        return self.ptb.bot

    @property
    def user(self) -> User | None:
        return self.update.effective_user

    @property
    def chat(self) -> Chat | None:
        return self.update.effective_chat

    @property
    def message(self) -> Message | None:
        return self.update.effective_message

    @property
    def chat_id(self) -> int | None:
        chat = self.chat
        return chat.id if chat else None

    @property
    def user_id(self) -> int | None:
        user = self.user
        return user.id if user else None

    @property
    def is_private(self) -> bool:
        chat = self.chat
        return bool(chat and chat.type == Chat.PRIVATE)

    @property
    def args(self) -> list[str]:
        """Arguments following the command, from python-telegram-bot."""
        return list(getattr(self.ptb, "args", []) or [])

    @property
    def settings(self) -> Settings | None:
        return self.application.bot_data.get("settings")

    @property
    def availability(self) -> AvailabilityController | None:
        return self.application.bot_data.get("resona_availability")

    @property
    def services(self) -> Services:
        services = self.application.bot_data.get("services")
        if services is None:
            raise RuntimeError("Resona services are not configured.")
        return services

    @property
    def bot_data(self) -> dict[str, Any]:
        return self.application.bot_data

    async def reply(self, text: str, **kwargs: Any) -> Message | None:
        """Reply to the originating message, when there is one."""
        message = self.message
        if message is None:
            return None
        return await message.reply_text(text, **kwargs)

    async def reply_rich(self, content: RichContent) -> Message | None:
        """Reply with a rich payload, falling back to plain text on any failure."""
        message = self.message
        if message is None:
            return None

        settings = self.settings
        enabled = settings is None or settings.RICH_MESSAGES_ENABLED

        if enabled and supports_rich_messages(self.bot):
            try:
                await send_rich_message(
                    self.bot,
                    message.chat_id,
                    content.payload,
                    reply_to_message_id=message.message_id,
                )
                return None
            except Exception:
                logger.warning(
                    "Rich message rejected; falling back to plain text.",
                    exc_info=True,
                )

        fallback = content.fallback_text or to_plain_text(content.payload)
        return await message.reply_text(truncate(fallback, 4000))
