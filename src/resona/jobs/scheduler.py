"""Scheduling of recurring background jobs."""

from __future__ import annotations

import logging
from datetime import UTC, time

from telegram.ext import Application

from resona.config.settings import Settings
from resona.jobs.cache import run_cache_maintenance
from resona.jobs.checkin import run_daily_checkin
from resona.jobs.event_digest import run_daily_event_digest

logger = logging.getLogger("resona.jobs.scheduler")

DAILY_CHECKIN_JOB = "daily_checkin"
DAILY_EVENT_DIGEST_JOB = "daily_event_digest"
CACHE_PURGE_JOB = "cache_purge"
CACHE_PURGE_INTERVAL = 3600


def register_jobs(application: Application) -> None:
    """Schedule every enabled job on the application's JobQueue."""
    settings: Settings | None = application.bot_data.get("settings")
    if settings is None:
        logger.warning("No settings found; background jobs were not scheduled.")
        return

    cache_enabled = getattr(settings, "CACHE_ENABLED", False)
    if (
        not settings.CHECKIN_ENABLED
        and not settings.EVENT_DIGEST_ENABLED
        and not cache_enabled
    ):
        logger.info("All background jobs are disabled.")
        return

    job_queue = application.job_queue
    if job_queue is None:
        logger.warning(
            "JobQueue is unavailable; install python-telegram-bot[job-queue] "
            "to enable background jobs."
        )
        return

    if settings.CHECKIN_ENABLED:
        run_at = time(
            settings.CHECKIN_HOUR_UTC,
            settings.CHECKIN_MINUTE_UTC,
            tzinfo=UTC,
        )
        job_queue.run_daily(
            run_daily_checkin,
            time=run_at,
            name=DAILY_CHECKIN_JOB,
            job_kwargs={"misfire_grace_time": 3600},
        )
        logger.info("Scheduled daily check-in at %s UTC.", run_at.strftime("%H:%M"))
    else:
        logger.info("Daily check-in job is disabled.")

    if settings.EVENT_DIGEST_ENABLED:
        run_at = time(
            settings.EVENT_DIGEST_HOUR_UTC,
            settings.EVENT_DIGEST_MINUTE_UTC,
            tzinfo=UTC,
        )
        job_queue.run_daily(
            run_daily_event_digest,
            time=run_at,
            name=DAILY_EVENT_DIGEST_JOB,
            job_kwargs={"misfire_grace_time": 3600},
        )
        logger.info("Scheduled event digest at %s UTC.", run_at.strftime("%H:%M"))
    else:
        logger.info("Daily event digest job is disabled.")

    if cache_enabled:
        job_queue.run_repeating(
            run_cache_maintenance,
            interval=CACHE_PURGE_INTERVAL,
            first=CACHE_PURGE_INTERVAL,
            name=CACHE_PURGE_JOB,
            job_kwargs={"misfire_grace_time": 600},
        )
        logger.info(
            "Scheduled cache maintenance every %s seconds.",
            CACHE_PURGE_INTERVAL,
        )
    else:
        logger.info("Cache maintenance job is disabled.")
