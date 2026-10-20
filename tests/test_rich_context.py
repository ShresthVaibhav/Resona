"""ResonaContext decides between rich and plain replies."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

from resona.core.context import ResonaContext
from resona.core.rich import InputRichMessage, RichContent

_CONTENT = RichContent(InputRichMessage(html="<b>Hi</b>"), "Hi")


class FakeBot:
    def __init__(self) -> None:
        self._post = AsyncMock(return_value={"message_id": 1})


def _context(bot: FakeBot, *, enabled: bool = True) -> ResonaContext:
    application = SimpleNamespace(
        bot_data={"settings": SimpleNamespace(RICH_MESSAGES_ENABLED=enabled)}
    )
    ptb = SimpleNamespace(application=application, bot=bot, args=[])
    message = SimpleNamespace(
        chat_id=100,
        message_id=5,
        reply_text=AsyncMock(return_value="plain"),
    )
    update = SimpleNamespace(
        effective_message=message,
        effective_chat=None,
        effective_user=None,
    )
    return ResonaContext(update=update, ptb=ptb)


async def test_reply_rich_sends_the_payload() -> None:
    bot = FakeBot()
    ctx = _context(bot)

    await ctx.reply_rich(_CONTENT)

    bot._post.assert_awaited_once()
    assert bot._post.await_args.args[0] == "sendRichMessage"
    assert bot._post.await_args.args[1]["chat_id"] == 100
    assert bot._post.await_args.args[1]["reply_parameters"] == {"message_id": 5}
    ctx.message.reply_text.assert_not_awaited()


async def test_reply_rich_falls_back_when_the_api_rejects_it() -> None:
    bot = FakeBot()
    bot._post.side_effect = RuntimeError("Bad Request")
    ctx = _context(bot)

    await ctx.reply_rich(_CONTENT)

    ctx.message.reply_text.assert_awaited_once_with("Hi")


async def test_reply_rich_respects_the_feature_flag() -> None:
    bot = FakeBot()
    ctx = _context(bot, enabled=False)

    await ctx.reply_rich(_CONTENT)

    bot._post.assert_not_awaited()
    ctx.message.reply_text.assert_awaited_once_with("Hi")


async def test_reply_rich_is_a_noop_without_a_message() -> None:
    bot = FakeBot()
    ctx = _context(bot)
    ctx.update.effective_message = None

    assert await ctx.reply_rich(_CONTENT) is None
    bot._post.assert_not_awaited()
