"""Central exception handling for all handlers."""

from __future__ import annotations

import logging
from typing import Any

from telegram.ext import Application, ContextTypes

from resona.core.errors import UserError

logger = logging.getLogger("resona.errors")


async def handle_error(update: Any, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Report handler exceptions.

    :class:`~resona.core.errors.UserError` messages are safe to show; anything
    else is only logged so internal details are never leaked to users.
    """
    error = context.error
    if error is None:
        return

    if isinstance(error, UserError):
        await _reply(update, str(error))
        return

    logger.error(
        "Unhandled exception while processing update.",
        exc_info=error,
    )
    await _reply(update, "Something went wrong. Please try again later.")


async def _reply(update: Any, text: str) -> None:
    try:
        if getattr(update, "callback_query", None) is not None:
            await update.callback_query.answer(text, show_alert=True)
        elif getattr(update, "effective_message", None) is not None:
            await update.effective_message.reply_text(text)
    except Exception:
        logger.debug("Failed to report error to the user.", exc_info=True)


def register_error_handler(application: Application) -> None:
    """Attach the central error handler."""
    application.add_error_handler(handle_error)
