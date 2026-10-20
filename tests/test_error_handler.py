"""Central error handling."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from resona.core.errors import CredentialsMissingError
from resona.wrappers.error_handler import handle_error


def _update():
    update = MagicMock()
    update.callback_query = None
    update.effective_message.reply_text = AsyncMock()
    return update


async def test_user_error_is_shown_to_the_user() -> None:
    update = _update()
    context = MagicMock()
    context.error = CredentialsMissingError()

    await handle_error(update, context)

    update.effective_message.reply_text.assert_awaited_once()
    sent = update.effective_message.reply_text.await_args.args[0]
    assert "link" in sent.lower()


async def test_internal_error_does_not_leak_details() -> None:
    update = _update()
    context = MagicMock()
    context.error = ValueError("secret internal detail")

    await handle_error(update, context)

    sent = update.effective_message.reply_text.await_args.args[0]
    assert "secret internal detail" not in sent


async def test_callback_query_errors_use_an_alert() -> None:
    update = MagicMock()
    update.callback_query.answer = AsyncMock()
    context = MagicMock()
    context.error = CredentialsMissingError()

    await handle_error(update, context)

    update.callback_query.answer.assert_awaited_once()
    assert update.callback_query.answer.await_args.kwargs.get("show_alert") is True


async def test_missing_error_is_ignored() -> None:
    update = _update()
    context = MagicMock()
    context.error = None

    await handle_error(update, context)

    update.effective_message.reply_text.assert_not_awaited()
