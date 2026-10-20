"""Periodic cache maintenance."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from telegram.ext import ContextTypes

logger = logging.getLogger("resona.jobs.cache")


async def run_cache_maintenance(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove expired entries so the cache does not grow indefinitely."""
    services = context.application.bot_data.get("services")
    if services is None:
        logger.warning("Cache maintenance skipped: services are not configured.")
        return

    cache = services.cache
    if cache is None:
        logger.warning("Cache maintenance skipped: no cache is configured.")
        return

    removed = cache.purge_expired()
    if removed:
        logger.info("Purged %d expired cache entries.", removed)


__all__ = ["run_cache_maintenance"]
