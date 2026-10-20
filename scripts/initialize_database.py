"""Initialize the MongoDB database and its indexes.

Safe to run repeatedly: index creation is idempotent.

Usage:
    python scripts/initialize_database.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import logging

from resona.config.logging import setup_logging
from resona.config.settings import validate_settings
from resona.core.errors import ConfigurationError
from resona.database import Database

logger = logging.getLogger("resona.scripts.initialize_database")


async def initialize() -> None:
    settings = validate_settings()
    database = Database(settings.MONGO_URI, settings.MONGO_DATABASE)

    try:
        await database.connect()
        logger.info(
            "Database %r is ready.",
            settings.MONGO_DATABASE,
        )
    finally:
        await database.close()


def main() -> None:
    setup_logging()
    try:
        asyncio.run(initialize())
    except ConfigurationError as exc:
        logger.error("Cannot initialize the database.\n%s", exc)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
