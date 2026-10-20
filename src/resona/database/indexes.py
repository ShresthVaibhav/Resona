"""Index creation for the Resona database.

Index creation is idempotent, so it is safe to run at every startup and from
``scripts/initialize_database.py``.
"""

from __future__ import annotations

import logging
from typing import Any

from resona.database.collections import (
    COLLECTION_CREDENTIALS,
    COLLECTION_GAME_ACCOUNTS,
    COLLECTION_USER_SETTINGS,
    COLLECTION_USERS,
)

logger = logging.getLogger("resona.database.indexes")


async def ensure_indexes(database: Any) -> None:
    """Create every required index on ``database``."""
    await database[COLLECTION_USERS].create_index("telegram_id", unique=True)

    await database[COLLECTION_USER_SETTINGS].create_index("telegram_id", unique=True)

    await database[COLLECTION_CREDENTIALS].create_index(
        [("telegram_id", 1), ("game", 1), ("uid", 1)],
        unique=True,
    )
    await database[COLLECTION_CREDENTIALS].create_index(
        [("telegram_id", 1), ("game", 1)]
    )

    await database[COLLECTION_GAME_ACCOUNTS].create_index(
        [("telegram_id", 1), ("game", 1), ("uid", 1)],
        unique=True,
    )
    await database[COLLECTION_GAME_ACCOUNTS].create_index(
        [("telegram_id", 1), ("game", 1)]
    )

    logger.info("Database indexes verified.")
