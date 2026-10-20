"""Honkai: Star Rail service backed by ``genshin.py``."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from resona.config.constants import GAME_HSR
from resona.core.errors import CredentialsMissingError
from resona.games.checkin import AccountCheckinMixin
from resona.games.common import GameEventDigest, cached_api, optional_api
from resona.games.gacha import GachaHistoryMixin
from resona.games.hsr import views
from resona.services.api import run_api

if TYPE_CHECKING:
    from resona.core.cache import TTLCache
    from resona.database.collections import GameAccountDocument
    from resona.services.accounts import AccountService


class StarRailService(AccountCheckinMixin, GachaHistoryMixin):
    """Reads notes, characters, diary, endgame and gacha data for one user."""

    game = GAME_HSR
    gacha_command = "warp"

    def __init__(
        self,
        accounts: AccountService,
        cache: TTLCache[Any, Any] | None = None,
    ) -> None:
        self._accounts = accounts
        self._cache = cache

    async def _context(self, telegram_id: int) -> tuple[Any, GameAccountDocument]:
        account = await self._accounts.primary_account(telegram_id, self.game)
        if account is None:
            raise CredentialsMissingError()

        client = await self._accounts.build_client(telegram_id, self.game, account.uid)
        return client, account

    async def notes(self, telegram_id: int) -> str:
        client, account = await self._context(telegram_id)
        notes = await run_api(
            client.get_starrail_notes(int(account.uid)),
            action="Real-time notes",
        )
        return views.render_notes(account, notes)

    async def characters(self, telegram_id: int) -> str:
        client, account = await self._context(telegram_id)
        response = await run_api(
            client.get_starrail_characters(int(account.uid), simple=True),
            action="Characters",
        )
        return views.render_characters(account, response)

    async def checkin(self, telegram_id: int) -> str:
        client, account = await self._context(telegram_id)
        reward = await run_api(self._claim(client), action="Daily check-in")
        info = await run_api(
            client.get_reward_info(game=self._library_game()),
            action="Check-in status",
        )
        return views.render_checkin(account, reward, info)

    async def diary(self, telegram_id: int) -> str:
        client, account = await self._context(telegram_id)
        diary = await run_api(
            client.get_starrail_diary(int(account.uid)),
            action="Traveler's diary",
        )
        return views.render_diary(account, diary)

    async def endgame(self, telegram_id: int) -> str:
        client, account = await self._context(telegram_id)
        uid = int(account.uid)
        challenge = await optional_api(
            client.get_starrail_challenge(uid),
            action="Memory of Chaos",
        )
        rogue = await optional_api(
            client.get_starrail_rogue(uid),
            action="Simulated Universe",
        )
        pure_fiction = await optional_api(
            client.get_starrail_pure_fiction(uid),
            action="Pure Fiction",
        )
        apc_shadow = await optional_api(
            client.get_apocalyptic_shadow(uid),
            action="Apocalyptic Shadow",
        )
        anomaly = await optional_api(
            client.get_anomaly_arbitration(uid),
            action="Anomaly Arbitration",
        )
        return views.render_endgame(
            account,
            challenge,
            rogue,
            pure_fiction,
            apc_shadow,
            anomaly,
        )

    async def _event_calendar(self, telegram_id: int) -> tuple[Any, Any]:
        client, account = await self._context(telegram_id)
        calendar = await cached_api(
            self._cache,
            ("events", self.game, account.uid),
            lambda: client.get_starrail_event_calendar(int(account.uid)),
            action="Event calendar",
        )
        return account, calendar

    async def events(self, telegram_id: int) -> str:
        account, calendar = await self._event_calendar(telegram_id)
        return views.render_events(account, calendar)

    async def events_ending(
        self, telegram_id: int, *, within_days: int = 3
    ) -> GameEventDigest:
        account, calendar = await self._event_calendar(telegram_id)
        return GameEventDigest(
            nickname=account.nickname,
            uid=account.uid,
            events=tuple(views.event_summaries(calendar, within_days=within_days)),
        )

    @staticmethod
    async def _claim(client: Any) -> Any:
        import genshin

        try:
            return await client.claim_daily_reward(game=genshin.Game.STARRAIL)
        except genshin.AlreadyClaimed:
            return None

    @staticmethod
    def _library_game() -> Any:
        import genshin

        return genshin.Game.STARRAIL
