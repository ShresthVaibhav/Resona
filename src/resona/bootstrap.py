import logging

from resona.application import build_application
from resona.config.logging import setup_logging


def main() -> None:
    """Initialize and start Resona."""

    setup_logging()
    logger = logging.getLogger("resona")

    logger.info("Starting Resona...")

    try:
        application = build_application()
        application.run_polling()
    except Exception:
        logger.exception("Resona failed to start.")
        raise


if __name__ == "__main__":
    main()
