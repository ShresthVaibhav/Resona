"""Account linking and authenticated game clients."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from resona.config.constants import GAME_LABELS, IMPLEMENTED_GAMES
from resona.core.errors import CredentialsMissingError, UserError
from resona.database.collections import GameAccountDocument
from resona.games.mapping import (
    business_ids,
    library_game,
    library_lang,
    region_from_business_id,
)
from resona.services.crypto import CookieCipher

if TYPE_CHECKING:
    from genshin import Client

    from resona.config.settings import Settings
    from resona.database.collections import CredentialsDocument
    from resona.database.repositories import (
        CredentialsRepository,
        GameAccountRepository,
    )

logger = logging.getLogger("resona.services.accounts")

# Each tuple lists acceptable names for one required cookie; the first is
# preferred. HoYoLAB's current cookies are the "_v2" variants.
_REQUIRED_COOKIES = (("ltuid_v2", "ltuid"), ("ltoken_v2", "ltoken"))

_GAME_CHOICES = ", ".join(IMPLEMENTED_GAMES)


class AccountService:
    """Links HoYoLAB cookies to Telegram users and builds API clients."""

    def __init__(
        self,
        settings: Settings,
        credentials: CredentialsRepository,
        accounts: GameAccountRepository,
    ) -> None:
        self._settings = settings
        self._credentials = credentials
        self._accounts = accounts
        self._cipher: CookieCipher | None = None

    @property
    def cipher(self) -> CookieCipher:
        """Lazily construct the cipher so startup works without a key."""
        if self._cipher is None:
            self._cipher = CookieCipher(self._settings.COOKIE_ENCRYPTION_KEY)
        return self._cipher

    async def _discover_accounts(
        self, cookies: dict[str, str]
    ) -> tuple[Client, list[Any]]:
        """Find game accounts, trying the global and Chinese regions.

        HoYoLAB serves the two regions from different hosts. Global cookies fail
        on the Chinese host and vice versa, so one retry covers both.
        """
        import genshin

        last_error: Exception | None = None
        for region in (genshin.Region.OVERSEAS, genshin.Region.CHINESE):
            client = genshin.Client(
                cookies=cookies,
                region=region,
                lang=library_lang(self._settings.DEFAULT_LOCALE),
            )
            try:
                accounts = list(await client.get_game_accounts())
            except genshin.InvalidCookies as exc:
                last_error = exc
                continue
            return client, accounts

        assert last_error is not None  # The loop always raises or returns.
        raise last_error

    async def link(
        self,
        telegram_id: int,
        game: str,
        cookie_header: str,
        uid: str | None = None,
    ) -> GameAccountDocument:
        """Validate cookies against HoYoLAB and persist the matching account."""
        if game not in IMPLEMENTED_GAMES:
            raise UserError(f"Unsupported game. Choose one of: {_GAME_CHOICES}.")

        if not cookie_header.strip():
            raise UserError("No cookies were provided.")

        import genshin

        cookies = genshin.parse_cookie(cookie_header)
        missing = [
            names[0]
            for names in _REQUIRED_COOKIES
            if not any(name in cookies for name in names)
        ]
        if missing:
            raise UserError(
                "The cookie header must include ltuid_v2 and ltoken_v2. "
                "Copy the full Cookie request header from HoYoLAB."
            )

        try:
            client, game_accounts = await self._discover_accounts(cookies)
        except genshin.InvalidCookies as exc:
            raise UserError(
                "Those cookies are invalid or expired. Copy them again from HoYoLAB."
            ) from exc
        except genshin.TooManyRequests as exc:
            raise UserError(
                "HoYoLAB is rate limiting requests. Please try again in a few minutes."
            ) from exc
        except genshin.GenshinException as exc:
            logger.warning("Account lookup failed for user %s: %s", telegram_id, exc)
            raise UserError(
                "HoYoLAB rejected the request. Please try again later."
            ) from exc

        wanted_business_ids = business_ids(game)
        candidates = [
            account
            for account in game_accounts
            if account.game_biz in wanted_business_ids
        ]

        if uid is not None:
            candidates = [
                account for account in candidates if str(account.uid) == str(uid)
            ]

        if not candidates:
            raise UserError(
                f"No {GAME_LABELS[game]} account is bound to those cookies."
            )

        if len(candidates) > 1:
            listing = ", ".join(str(account.uid) for account in candidates)
            raise UserError(
                f"Multiple {GAME_LABELS[game]} accounts were found ({listing}). "
                f"Send the UID as well: /link {game} <uid> <cookies>"
            )

        account = candidates[0]
        existing = await self._accounts.list_for_user(telegram_id, game)

        await self._credentials.upsert(
            telegram_id=telegram_id,
            game=game,
            uid=str(account.uid),
            encrypted_cookies=self.cipher.encrypt(cookie_header.strip()),
            region=region_from_business_id(game, account.game_biz),
            hoyolab_id=self._hoyolab_id(client, cookies),
        )

        document = await self._accounts.upsert(
            telegram_id=telegram_id,
            game=game,
            uid=str(account.uid),
            nickname=account.nickname,
            server=account.server_name or account.server,
            level=account.level,
        )

        if not existing:
            await self._accounts.set_primary(telegram_id, game, str(account.uid))
            document = (
                await self._accounts.get(telegram_id, game, str(account.uid))
                or document
            )

        return document

    async def unlink(self, telegram_id: int, game: str | None = None) -> int:
        """Remove credentials and account metadata, returning removed links."""
        if game is not None and game not in IMPLEMENTED_GAMES:
            raise UserError(f"Unsupported game. Choose one of: {_GAME_CHOICES}.")

        if game is None:
            removed = await self._credentials.delete_all(telegram_id)
            await self._accounts.delete_all(telegram_id)
            return removed

        removed = await self._credentials.delete(telegram_id, game)
        await self._accounts.delete(telegram_id, game)
        return removed

    async def list_accounts(
        self, telegram_id: int, game: str | None = None
    ) -> list[GameAccountDocument]:
        return await self._accounts.list_for_user(telegram_id, game)

    async def get_account(
        self, telegram_id: int, game: str, uid: str
    ) -> GameAccountDocument | None:
        """Return one linked account by UID."""
        return await self._accounts.get(telegram_id, game, uid)

    async def list_credentials(
        self, game: str | None = None
    ) -> list[CredentialsDocument]:
        """Every stored credential, used by background jobs."""
        return await self._credentials.list_all(game)

    async def primary_account(
        self, telegram_id: int, game: str
    ) -> GameAccountDocument | None:
        """Return the primary account for a game, or the first linked one."""
        accounts = await self._accounts.list_for_user(telegram_id, game)
        for account in accounts:
            if account.is_primary:
                return account
        return accounts[0] if accounts else None

    async def get_credentials(
        self, telegram_id: int, game: str, uid: str | None = None
    ) -> CredentialsDocument | None:
        return await self._credentials.get(telegram_id, game, uid)

    async def build_client(
        self, telegram_id: int, game: str, uid: str | None = None
    ) -> Client:
        """Return an authenticated client for a linked account."""
        import genshin

        if game not in IMPLEMENTED_GAMES:
            raise UserError(f"Unsupported game. Choose one of: {_GAME_CHOICES}.")

        credential = await self._credentials.get(telegram_id, game, uid)
        if credential is None:
            raise CredentialsMissingError()

        cookies = genshin.parse_cookie(
            self.cipher.decrypt(credential.encrypted_cookies)
        )
        region = (
            genshin.Region.CHINESE
            if credential.region == "cn"
            else genshin.Region.OVERSEAS
        )

        return genshin.Client(
            cookies=cookies,
            uid=int(credential.uid),
            game=library_game(game),
            region=region,
            lang=library_lang(self._settings.DEFAULT_LOCALE),
        )

    @staticmethod
    def _hoyolab_id(client: Client, cookies: dict[str, str]) -> int | None:
        if client.hoyolab_id is not None:
            return client.hoyolab_id
        raw = cookies.get("ltuid_v2") or cookies.get("ltuid")
        return int(raw) if raw and raw.isdigit() else None


__all__ = ["AccountService"]
