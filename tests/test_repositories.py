"""Repository behaviour against an in-memory collection."""

from __future__ import annotations

import pytest

from resona.database.repositories import (
    CredentialsRepository,
    GameAccountRepository,
    SettingsRepository,
    UserRepository,
)
from tests.fakes import FakeCollection


def _users() -> UserRepository:
    return UserRepository(FakeCollection(unique_keys=[("telegram_id",)]))


def _settings() -> SettingsRepository:
    return SettingsRepository(FakeCollection(unique_keys=[("telegram_id",)]))


def _credentials() -> CredentialsRepository:
    return CredentialsRepository(
        FakeCollection(unique_keys=[("telegram_id", "game", "uid")])
    )


def _accounts() -> GameAccountRepository:
    return GameAccountRepository(
        FakeCollection(unique_keys=[("telegram_id", "game", "uid")])
    )


# -- users -------------------------------------------------------------------
async def test_get_returns_none_for_unknown_user() -> None:
    assert await _users().get(1) is None


async def test_get_or_create_is_idempotent() -> None:
    repository = _users()

    created = await repository.get_or_create(1, username="nitin", first_name="Nitin")
    again = await repository.get_or_create(1, username="changed")

    assert created.telegram_id == 1
    assert created.username == "nitin"
    assert again.username == "nitin"
    assert await repository.count() == 1


async def test_touch_updates_profile_and_last_seen() -> None:
    repository = _users()
    created = await repository.get_or_create(1, username="old")

    await repository.touch(1, username="new", first_name="Nitin")
    updated = await repository.get(1)

    assert updated is not None
    assert updated.username == "new"
    assert updated.first_name == "Nitin"
    assert updated.last_seen_at >= created.last_seen_at


async def test_set_blocked_and_delete() -> None:
    repository = _users()
    await repository.get_or_create(1)

    await repository.set_blocked(1, True)
    user = await repository.get(1)
    assert user is not None and user.is_blocked is True

    assert await repository.delete(1) is True
    assert await repository.get(1) is None
    assert await repository.delete(1) is False


# -- settings ----------------------------------------------------------------
async def test_settings_are_created_with_defaults() -> None:
    repository = _settings()

    settings = await repository.get(7)

    assert settings.telegram_id == 7
    assert settings.locale == "en"
    assert settings.notifications_enabled is True
    assert settings.event_digest_enabled is False
    assert settings.default_game is None


async def test_settings_get_is_stable() -> None:
    repository = _settings()
    first = await repository.get(7)
    second = await repository.get(7)
    assert first.created_at == second.created_at


async def test_settings_update_only_allowed_fields() -> None:
    repository = _settings()

    updated = await repository.update(
        7, locale="hi", notifications_enabled=False, event_digest_enabled=True
    )
    assert updated.locale == "hi"
    assert updated.notifications_enabled is False
    assert updated.event_digest_enabled is True

    with pytest.raises(ValueError, match="Cannot update"):
        await repository.update(7, created_at="not-allowed")


async def test_settings_delete() -> None:
    repository = _settings()
    await repository.get(7)
    assert await repository.delete(7) is True
    assert await repository.delete(7) is False


# -- credentials -------------------------------------------------------------
async def test_credentials_upsert_and_fetch() -> None:
    repository = _credentials()

    created = await repository.upsert(
        telegram_id=1,
        game="genshin",
        uid="800000001",
        encrypted_cookies="ciphertext-1",
        region="os_asia",
    )

    assert created.uid == "800000001"
    assert created.encrypted_cookies == "ciphertext-1"

    fetched = await repository.get(1, "genshin", "800000001")
    assert fetched is not None
    assert fetched.region == "os_asia"


async def test_credentials_upsert_replaces_cookies_and_keeps_created_at() -> None:
    repository = _credentials()
    first = await repository.upsert(
        telegram_id=1, game="genshin", uid="1", encrypted_cookies="old"
    )

    second = await repository.upsert(
        telegram_id=1, game="genshin", uid="1", encrypted_cookies="new"
    )

    assert second.created_at == first.created_at
    assert second.encrypted_cookies == "new"
    assert len(await repository.list_for_user(1)) == 1


async def test_credentials_get_without_uid_returns_first_for_game() -> None:
    repository = _credentials()
    await repository.upsert(
        telegram_id=1, game="genshin", uid="1", encrypted_cookies="a"
    )
    await repository.upsert(telegram_id=1, game="hsr", uid="2", encrypted_cookies="b")

    fetched = await repository.get(1, "hsr")
    assert fetched is not None
    assert fetched.uid == "2"


async def test_credentials_list_filters_by_game() -> None:
    repository = _credentials()
    await repository.upsert(
        telegram_id=1, game="genshin", uid="1", encrypted_cookies="a"
    )
    await repository.upsert(telegram_id=1, game="hsr", uid="2", encrypted_cookies="b")
    await repository.upsert(
        telegram_id=2, game="genshin", uid="3", encrypted_cookies="c"
    )

    assert len(await repository.list_for_user(1)) == 2
    assert len(await repository.list_for_user(1, "genshin")) == 1


async def test_credentials_list_all_for_jobs() -> None:
    repository = _credentials()
    await repository.upsert(
        telegram_id=2, game="genshin", uid="1", encrypted_cookies="a"
    )
    await repository.upsert(telegram_id=1, game="hsr", uid="2", encrypted_cookies="b")

    all_credentials = await repository.list_all()
    genshin_only = await repository.list_all("genshin")

    assert [item.telegram_id for item in all_credentials] == [1, 2]
    assert len(genshin_only) == 1
    assert genshin_only[0].uid == "1"


async def test_credentials_delete_scopes() -> None:
    repository = _credentials()
    await repository.upsert(
        telegram_id=1, game="genshin", uid="1", encrypted_cookies="a"
    )
    await repository.upsert(
        telegram_id=1, game="genshin", uid="2", encrypted_cookies="b"
    )
    await repository.upsert(telegram_id=1, game="hsr", uid="3", encrypted_cookies="c")

    assert await repository.delete(1, "genshin", "1") == 1
    assert await repository.delete(1, "genshin") == 1
    assert await repository.delete_all(1) == 1
    assert await repository.list_for_user(1) == []


# -- game accounts -----------------------------------------------------------
async def test_game_account_upsert_defaults_to_not_primary() -> None:
    repository = _accounts()

    account = await repository.upsert(
        telegram_id=1, game="genshin", uid="1", nickname="Traveler", server="asia"
    )

    assert account.nickname == "Traveler"
    assert account.is_primary is False


async def test_set_primary_is_exclusive_within_a_game() -> None:
    repository = _accounts()
    await repository.upsert(telegram_id=1, game="genshin", uid="1")
    await repository.upsert(telegram_id=1, game="genshin", uid="2")
    await repository.upsert(telegram_id=1, game="hsr", uid="3")

    await repository.set_primary(1, "genshin", "2")

    accounts = {
        account.uid: account for account in await repository.list_for_user(1, "genshin")
    }
    assert accounts["1"].is_primary is False
    assert accounts["2"].is_primary is True

    other_game = await repository.get(1, "hsr", "3")
    assert other_game is not None and other_game.is_primary is False


async def test_mark_synced_sets_timestamp() -> None:
    repository = _accounts()
    await repository.upsert(telegram_id=1, game="genshin", uid="1")

    await repository.mark_synced(1, "genshin", "1")
    account = await repository.get(1, "genshin", "1")

    assert account is not None
    assert account.last_synced_at is not None


async def test_game_account_delete() -> None:
    repository = _accounts()
    await repository.upsert(telegram_id=1, game="genshin", uid="1")
    await repository.upsert(telegram_id=1, game="genshin", uid="2")

    assert await repository.delete(1, "genshin", "1") == 1
    assert await repository.delete(1, "genshin") == 1
    assert await repository.list_for_user(1) == []
