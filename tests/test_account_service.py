"""Account linking, unlinking and client construction."""

from __future__ import annotations

from typing import Any, ClassVar

import genshin
import pytest
from cryptography.fernet import Fernet

from resona.config.settings import Settings
from resona.core.errors import (
    ConfigurationError,
    CredentialsMissingError,
    UserError,
)
from resona.database.repositories import (
    CredentialsRepository,
    GameAccountRepository,
)
from resona.services.accounts import AccountService
from tests.fakes import FakeCollection


class FakeGameAccount:
    def __init__(
        self,
        game_biz: str,
        uid: int,
        *,
        nickname: str = "Traveler",
        level: int = 60,
        server: str = "os_asia",
        server_name: str = "Asia",
    ) -> None:
        self.game_biz = game_biz
        self.uid = uid
        self.nickname = nickname
        self.level = level
        self.server = server
        self.server_name = server_name


class FakeClient:
    """Stands in for ``genshin.Client`` during account lookups."""

    accounts: ClassVar[list[FakeGameAccount]] = []
    error: ClassVar[Exception | None] = None
    fail_regions: ClassVar[set[Any]] = set()
    instances: ClassVar[list[FakeClient]] = []

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.kwargs = kwargs
        cookies = kwargs.get("cookies") or {}
        self.hoyolab_id = (
            int(cookies["ltuid_v2"]) if cookies.get("ltuid_v2", "").isdigit() else None
        )
        FakeClient.instances.append(self)

    async def get_game_accounts(self) -> list[FakeGameAccount]:
        if self.kwargs.get("region") in FakeClient.fail_regions:
            raise genshin.InvalidCookies()
        if FakeClient.error is not None:
            raise FakeClient.error
        return list(FakeClient.accounts)


@pytest.fixture(autouse=True)
def _fake_client(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeClient.accounts = []
    FakeClient.error = None
    FakeClient.fail_regions = set()
    FakeClient.instances = []
    monkeypatch.setattr(genshin, "Client", FakeClient)


def _settings() -> Settings:
    return Settings(
        BOT_TOKEN="123456:TEST-TOKEN",
        BOT_OWNER_ID=1,
        MONGO_URI="mongodb://localhost:27017",
        COOKIE_ENCRYPTION_KEY=Fernet.generate_key().decode(),
    )


def _service(
    settings: Settings | None = None,
) -> tuple[AccountService, CredentialsRepository, GameAccountRepository]:
    credentials = CredentialsRepository(
        FakeCollection(unique_keys=[("telegram_id", "game", "uid")])
    )
    accounts = GameAccountRepository(
        FakeCollection(unique_keys=[("telegram_id", "game", "uid")])
    )
    return (
        AccountService(settings or _settings(), credentials, accounts),
        credentials,
        accounts,
    )


COOKIES = "ltuid_v2=123; ltoken_v2=secret; ltmid_v2=mid"


async def test_link_stores_encrypted_cookies_and_metadata() -> None:
    FakeClient.accounts = [FakeGameAccount("hk4e_global", 800000001)]
    service, credentials, _ = _service()

    account = await service.link(1, "genshin", COOKIES)

    assert account.uid == "800000001"
    assert account.nickname == "Traveler"
    assert account.server == "Asia"
    assert account.level == 60
    assert account.is_primary is True

    stored = await credentials.get(1, "genshin", "800000001")
    assert stored is not None
    assert stored.region == "os"
    assert stored.hoyolab_id == 123
    assert stored.encrypted_cookies != COOKIES
    assert service.cipher.decrypt(stored.encrypted_cookies) == COOKIES


async def test_link_requires_uid_and_token_cookies() -> None:
    service, _, _ = _service()

    with pytest.raises(UserError, match="ltuid_v2 and ltoken_v2"):
        await service.link(1, "genshin", "session=only")


async def test_link_rejects_unsupported_game() -> None:
    service, _, _ = _service()

    with pytest.raises(UserError, match="Unsupported game"):
        await service.link(1, "honkai3rd", COOKIES)


async def test_link_reports_missing_game_account() -> None:
    FakeClient.accounts = [FakeGameAccount("hkrpg_global", 1)]
    service, _, _ = _service()

    with pytest.raises(UserError, match="No Genshin Impact account"):
        await service.link(1, "genshin", COOKIES)


async def test_link_requires_uid_when_several_accounts_match() -> None:
    FakeClient.accounts = [
        FakeGameAccount("hk4e_global", 1),
        FakeGameAccount("hk4e_global", 2),
    ]
    service, _, _ = _service()

    with pytest.raises(UserError, match="Multiple Genshin Impact accounts"):
        await service.link(1, "genshin", COOKIES)

    account = await service.link(1, "genshin", COOKIES, uid="2")
    assert account.uid == "2"


async def test_link_marks_chinese_region() -> None:
    FakeClient.accounts = [FakeGameAccount("hk4e_cn", 10)]
    service, credentials, _ = _service()

    await service.link(1, "genshin", COOKIES)

    stored = await credentials.get(1, "genshin", "10")
    assert stored is not None and stored.region == "cn"


async def test_link_retries_the_chinese_region() -> None:
    FakeClient.accounts = [FakeGameAccount("hk4e_cn", 11)]
    FakeClient.fail_regions = {genshin.Region.OVERSEAS}
    service, credentials, _ = _service()

    account = await service.link(1, "genshin", COOKIES)

    assert account.uid == "11"
    stored = await credentials.get(1, "genshin", "11")
    assert stored is not None and stored.region == "cn"


async def test_link_reuses_existing_primary() -> None:
    FakeClient.accounts = [FakeGameAccount("hk4e_global", 1)]
    service, _, _ = _service()

    first = await service.link(1, "genshin", COOKIES)
    second = await service.link(1, "genshin", COOKIES)

    assert first.is_primary is True
    assert second.is_primary is True


async def test_link_maps_invalid_cookies() -> None:
    FakeClient.error = genshin.InvalidCookies()
    service, _, _ = _service()

    with pytest.raises(UserError, match="invalid or expired"):
        await service.link(1, "genshin", COOKIES)


async def test_link_maps_rate_limits() -> None:
    FakeClient.error = genshin.TooManyRequests()
    service, _, _ = _service()

    with pytest.raises(UserError, match="rate limiting"):
        await service.link(1, "genshin", COOKIES)


async def test_unlink_scopes() -> None:
    FakeClient.accounts = [
        FakeGameAccount("hk4e_global", 1),
        FakeGameAccount("hkrpg_global", 2),
    ]
    service, credentials, accounts = _service()
    await service.link(1, "genshin", COOKIES)
    await service.link(1, "hsr", COOKIES)

    assert len(await service.list_accounts(1)) == 2
    assert await service.unlink(1, "genshin") == 1
    assert len(await service.list_accounts(1)) == 1
    assert await credentials.get(1, "genshin") is None

    assert await service.unlink(1) == 1
    assert await service.list_accounts(1) == []
    assert await accounts.list_for_user(1) == []


async def test_build_client_uses_stored_credentials() -> None:
    FakeClient.accounts = [FakeGameAccount("hk4e_global", 800000001)]
    service, _, _ = _service()
    await service.link(1, "genshin", COOKIES)

    client = await service.build_client(1, "genshin")

    assert isinstance(client, FakeClient)
    assert client.kwargs["uid"] == 800000001
    assert client.kwargs["game"] is genshin.Game.GENSHIN
    assert client.kwargs["region"] is genshin.Region.OVERSEAS
    assert client.kwargs["lang"] == "en-us"


async def test_build_client_requires_linked_account() -> None:
    service, _, _ = _service()

    with pytest.raises(CredentialsMissingError):
        await service.build_client(1, "genshin")


def test_encryption_key_is_validated_lazily() -> None:
    settings = _settings()
    settings.COOKIE_ENCRYPTION_KEY = ""
    service, _, _ = _service(settings)

    with pytest.raises(ConfigurationError):
        _ = service.cipher
