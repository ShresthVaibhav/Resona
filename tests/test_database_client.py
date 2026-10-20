"""Database client lifecycle and index creation."""

from __future__ import annotations

from resona.database import Database
from resona.database.collections import (
    COLLECTION_CREDENTIALS,
    COLLECTION_GAME_ACCOUNTS,
    COLLECTION_USER_SETTINGS,
    COLLECTION_USERS,
)
from tests.fakes import FakeMongoClient


def _database() -> Database:
    return Database(
        "mongodb://localhost:27017", "resona", client_factory=FakeMongoClient
    )


async def test_connect_pings_and_creates_indexes() -> None:
    database = _database()
    assert database.is_connected is False

    await database.connect()

    assert database.is_connected is True
    assert database.client.pinged is True

    collections = database.client["resona"].collections
    assert collections[COLLECTION_USERS].indexes
    assert collections[COLLECTION_USER_SETTINGS].indexes
    assert len(collections[COLLECTION_CREDENTIALS].indexes) == 2
    assert len(collections[COLLECTION_GAME_ACCOUNTS].indexes) == 2

    await database.close()
    assert database.client.closed is True
    assert database.is_connected is False


async def test_connect_is_idempotent() -> None:
    database = _database()
    await database.connect()
    users = database.client["resona"].collections[COLLECTION_USERS]
    index_count = len(users.indexes)

    await database.connect()

    assert len(users.indexes) == index_count


async def test_close_without_connect_is_safe() -> None:
    database = _database()
    await database.close()
    assert database.client.closed is True
    assert database.is_connected is False


async def test_context_manager_connects_and_closes() -> None:
    database = _database()

    async with database as opened:
        assert opened is database
        assert database.is_connected is True

    assert database.is_connected is False


def test_repositories_are_wired() -> None:
    database = _database()
    assert database.users is not None
    assert database.settings is not None
    assert database.credentials is not None
    assert database.game_accounts is not None
