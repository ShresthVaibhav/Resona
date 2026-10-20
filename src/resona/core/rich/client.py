"""Thin transport for Bot API 10.1+ rich messages.

python-telegram-bot 22.8 targets Bot API 10.0, so ``sendRichMessage`` and
``sendRichMessageDraft`` do not exist as typed methods. The verified PTB 22.8
hook for arbitrary methods is :meth:`telegram.Bot._post`: it uses the bot's own
token, base URL (including local Bot API mode), request object and timeouts.
All use of that private hook stays in this module.
"""

from __future__ import annotations

import logging
from typing import Any

from resona.core.rich.limits import RichMessageUnsupported, validate_payload
from resona.core.rich.models import InputRichMessage

logger = logging.getLogger("resona.rich")


def supports_rich_messages(bot: Any) -> bool:
    """Return whether this bot exposes the request hook rich messages need."""
    return callable(getattr(bot, "_post", None))


async def send_rich_message(
    bot: Any,
    chat_id: int,
    message: InputRichMessage,
    *,
    reply_to_message_id: int | None = None,
    disable_notification: bool = False,
    protect_content: bool = False,
) -> Any:
    """Send a rich message and return the raw Bot API result."""
    data: dict[str, Any] = {
        "chat_id": chat_id,
        "rich_message": validate_payload(message).model_dump(exclude_none=True),
        "disable_notification": disable_notification,
        "protect_content": protect_content,
    }
    if reply_to_message_id is not None:
        data["reply_parameters"] = {"message_id": reply_to_message_id}

    return await _post(bot, "sendRichMessage", data)


async def edit_rich_message(
    bot: Any,
    chat_id: int,
    message_id: int,
    message: InputRichMessage,
) -> Any:
    """Replace the rich content of an existing message."""
    data: dict[str, Any] = {
        "chat_id": chat_id,
        "message_id": message_id,
        "rich_message": validate_payload(message).model_dump(exclude_none=True),
    }
    return await _post(bot, "editMessageText", data)


async def stream_draft(
    bot: Any,
    chat_id: int,
    draft_id: int,
    message: InputRichMessage,
) -> Any:
    """Stream a temporary rich draft; persist it later with ``sendRichMessage``."""
    if draft_id == 0:
        raise ValueError("draft_id must be non-zero")

    data: dict[str, Any] = {
        "chat_id": chat_id,
        "draft_id": draft_id,
        "rich_message": validate_payload(message).model_dump(exclude_none=True),
    }
    return await _post(bot, "sendRichMessageDraft", data)


async def _post(bot: Any, endpoint: str, data: dict[str, Any]) -> Any:
    post = getattr(bot, "_post", None)
    if not callable(post):
        raise RichMessageUnsupported(
            "this python-telegram-bot build cannot call arbitrary Bot API methods"
        )

    return await post(endpoint, data)
