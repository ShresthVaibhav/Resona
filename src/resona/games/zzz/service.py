"""Zenless Zone Zero service backed by ``genshin.py``."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from resona.config.constants import GAME_ZZZ
from resona.core.errors import CredentialsMissingError
from resona.games.checkin import AccountCheckinMixin
from resona.games.common import GameEventDigest, cached_api, optional_api
from resona.games.gacha import GachaHistoryMixin
from resona.games.zzz import views
from resona.services.api import run_api

if TYPE_CHECKING:
    from resona.core.cache import TTLCache
    from resona.database.collections import GameAccountDocument
    from resona.services.accounts import AccountService


class ZZZService(AccountCheckinMixin, GachaHistoryMixin):
    """Reads notes, agents, diary, endgame and gacha data for one user."""

    game = GAME_ZZZ
    gacha_command = "signals"

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
            client.get_zzz_notes(int(account.uid)),
            action="Real-time notes",
        )
        return views.render_notes(account, notes)

    async def characters(self, telegram_id: int) -> str:
        client, account = await self._context(telegram_id)
        agents = await run_api(
            client.get_zzz_agents(int(account.uid)),
            action="Agents",
        )
        return views.render_characters(account, agents)

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
            client.get_zzz_diary(int(account.uid)),
            action="Income diary",
        )
        return views.render_diary(account, diary)

    async def endgame(self, telegram_id: int) -> str:
        client, account = await self._context(telegram_id)
        uid = int(account.uid)
        assault = await optional_api(
            client.get_deadly_assault(uid),
            action="Deadly Assault",
        )
        shiyu = await optional_api(
            client.get_shiyu_defense(uid),
            action="Shiyu Defense",
        )
        annihilation = await optional_api(
            client.get_annihilation_simulacrum(uid),
            action="Annihilation Simulacrum",
        )
        lost_void = await optional_api(
            client.get_lost_void_summary(uid),
            action="Lost Void",
        )
        return views.render_endgame(account, assault, shiyu, annihilation, lost_void)

    async def _event_calendar(self, telegram_id: int) -> tuple[Any, Any]:
        client, account = await self._context(telegram_id)
        events = await cached_api(
            self._cache,
            ("events", self.game, account.uid),
            lambda: client.get_zzz_event_calendar(int(account.uid)),
            action="Event calendar",
        )
        return account, events

    async def events(self, telegram_id: int) -> str:
        account, events = await self._event_calendar(telegram_id)
        return views.render_events(account, events)

    async def events_ending(
        self, telegram_id: int, *, within_days: int = 3
    ) -> GameEventDigest:
        account, events = await self._event_calendar(telegram_id)
        return GameEventDigest(
            nickname=account.nickname,
            uid=account.uid,
            events=tuple(views.event_summaries(events, within_days=within_days)),
        )

    @staticmethod
    async def _claim(client: Any) -> Any:
        import genshin

        try:
            return await client.claim_daily_reward(game=genshin.Game.ZZZ)
        except genshin.AlreadyClaimed:
            return None

    @staticmethod
    def _library_game() -> Any:
        import genshin

        return genshin.Game.ZZZ
