"""Application construction and lifecycle."""

from __future__ import annotations

import logging
from typing import Any

from telegram.ext import Application

from resona.config.settings import Settings, validate_settings
from resona.core.availability import AvailabilityController
from resona.core.ratelimit import RateLimiter
from resona.database import Database
from resona.handlers import load_handlers
from resona.jobs import register_jobs
from resona.services import Services
from resona.wrappers import (
    register_bot_commands,
    register_error_handler,
    register_handlers,
)

logger = logging.getLogger("resona.application")


async def _post_init(application: Application) -> None:
    """Connect shared services, then publish the command menu and jobs."""
    database = application.bot_data.get("db")
    if database is not None:
        await database.connect()
    register_jobs(application)
    await register_bot_commands(application)


async def _post_shutdown(application: Application) -> None:
    """Release shared services."""
    database = application.bot_data.get("db")
    if database is not None:
        await database.close()


def build_application(
    settings: Settings | None = None,
    *,
    database: Any | None = None,
) -> Application:
    """Build and configure the Resona Telegram application.

    Handlers are imported and the registry validated before the application is
    constructed, so a broken declaration prevents startup.
    """
    settings = settings or validate_settings()

    # Importing handler modules runs their decorators and fills the registry.
    load_handlers()

    builder = Application.builder().token(settings.BOT_TOKEN)
    builder.concurrent_updates(settings.CONCURRENT_UPDATES)

    if settings.LOCAL_BOT_API:
        builder.base_url(settings.BOT_API_BASE_URL)
        builder.base_file_url(settings.BOT_API_FILE_URL)
        builder.local_mode(True)

    builder.post_init(_post_init)
    builder.post_shutdown(_post_shutdown)

    application = builder.build()

    # Shared state available to every handler.
    application.bot_data["settings"] = settings
    application.bot_data["db"] = database or Database(
        settings.MONGO_URI,
        settings.MONGO_DATABASE,
    )
    application.bot_data["services"] = Services.from_database(
        application.bot_data["db"], settings
    )
    application.bot_data["resona_availability"] = AvailabilityController(
        maintenance=settings.MAINTENANCE_MODE,
        maintenance_message=settings.MAINTENANCE_MESSAGE,
    )
    application.bot_data["resona_ratelimiter"] = RateLimiter(
        settings.RATE_LIMIT_PER_MINUTE
    )
    application.bot_data["BOT_ADMIN_IDS"] = set(settings.admin_ids)

    register_handlers(application)
    register_error_handler(application)

    logger.info("Resona application initialized successfully.")
    return application
