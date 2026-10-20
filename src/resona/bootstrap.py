"""Startup orchestration and entry point."""

from __future__ import annotations

import logging

from resona.application import build_application
from resona.config.constants import PROJECT_NAME, PROJECT_VERSION
from resona.config.logging import setup_logging
from resona.config.settings import validate_settings
from resona.core.errors import ConfigurationError


def main() -> None:
    """Validate configuration, build the application and start polling."""
    setup_logging()
    logger = logging.getLogger("resona")

    try:
        settings = validate_settings()
    except ConfigurationError as exc:
        logger.error("Resona cannot start.\n%s", exc)
        raise SystemExit(2) from exc

    setup_logging(settings.LOG_LEVEL)
    logger.info(
        "Starting %s v%s (%s).",
        PROJECT_NAME,
        PROJECT_VERSION,
        settings.ENVIRONMENT,
    )

    application = build_application(settings)

    try:
        application.run_polling(drop_pending_updates=settings.DROP_PENDING_UPDATES)
    except Exception:
        logger.exception("Resona stopped unexpectedly.")
        raise


if __name__ == "__main__":
    main()
