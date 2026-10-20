"""The rich-message transport uses the verified PTB request hook."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from resona.core.rich import (
    InputRichMessage,
    RichMessageTooLarge,
    RichMessageUnsupported,
    edit_rich_message,
    send_rich_message,
    stream_draft,
    supports_rich_messages,
)
from resona.core.rich.limits import MAX_CHARACTERS


class FakeBot:
    def __init__(self) -> None:
        self._post = AsyncMock(return_value={"message_id": 1})


async def test_send_rich_message_posts_the_documented_fields() -> None:
    bot = FakeBot()
    payload = InputRichMessage(html="<b>Hi</b>")

    result = await send_rich_message(bot, 42, payload, reply_to_message_id=7)

    assert result == {"message_id": 1}
    bot._post.assert_awaited_once_with(
        "sendRichMessage",
        {
            "chat_id": 42,
            "rich_message": {"html": "<b>Hi</b>"},
            "disable_notification": False,
            "protect_content": False,
            "reply_parameters": {"message_id": 7},
        },
    )


async def test_edit_rich_message_uses_edit_message_text() -> None:
    bot = FakeBot()

    await edit_rich_message(bot, 42, 9, InputRichMessage(html="<b>New</b>"))

    bot._post.assert_awaited_once_with(
        "editMessageText",
        {
            "chat_id": 42,
            "message_id": 9,
            "rich_message": {"html": "<b>New</b>"},
        },
    )


async def test_stream_draft_posts_a_non_zero_draft_id() -> None:
    bot = FakeBot()

    await stream_draft(bot, 42, 3, InputRichMessage(markdown="partial"))

    bot._post.assert_awaited_once_with(
        "sendRichMessageDraft",
        {
            "chat_id": 42,
            "draft_id": 3,
            "rich_message": {"markdown": "partial"},
        },
    )


async def test_stream_draft_rejects_zero_draft_id() -> None:
    with pytest.raises(ValueError, match="non-zero"):
        await stream_draft(FakeBot(), 42, 0, InputRichMessage(markdown="x"))


async def test_oversized_payload_is_rejected_before_the_request() -> None:
    bot = FakeBot()
    payload = InputRichMessage(html="x" * (MAX_CHARACTERS + 1))

    with pytest.raises(RichMessageTooLarge):
        await send_rich_message(bot, 42, payload)

    bot._post.assert_not_awaited()


async def test_bot_without_the_request_hook_is_reported() -> None:
    class PlainBot:
        pass

    assert supports_rich_messages(PlainBot()) is False
    with pytest.raises(RichMessageUnsupported):
        await send_rich_message(PlainBot(), 42, InputRichMessage(html="x"))


def test_supports_rich_messages_checks_the_hook() -> None:
    assert supports_rich_messages(FakeBot()) is True
    assert supports_rich_messages(object()) is False
