# src/resona/application.py

from __future__ import annotations

import logging

from telegram.ext import Application

from resona.config.settings import settings
from resona.wrappers import (
    register_bot_commands,
    register_handlers,
    validate_registry,
)

logger = logging.getLogger("resona.application")


def build_application() -> Application:
    """
    Build and configure the Resona Telegram application.

    Validates the wrapper registry before creating the application
    so command and alias conflicts prevent startup.
    """

    # Validate commands, aliases, and handler registrations.
    validate_registry()

    builder = Application.builder().token(settings.BOT_TOKEN)

    builder.concurrent_updates(settings.CONCURRENT_UPDATES)

    if settings.LOCAL_BOT_API:
        builder.base_url(settings.BOT_API_BASE_URL)
        builder.base_file_url(settings.BOT_API_FILE_URL)
        builder.local_mode(True)

    builder.post_init(register_bot_commands)

    application = builder.build()

    register_handlers(application)

    logger.info("Resona application initialized successfully.")

    return application