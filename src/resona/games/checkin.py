"""Shared daily check-in behaviour for every game module."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from resona.core.errors import CredentialsMissingError
from resona.games.mapping import library_game
from resona.services.api import run_api

if TYPE_CHECKING:
    from resona.services.accounts import AccountService


@dataclass(frozen=True, slots=True)
class CheckinOutcome:
    """Result of signing one linked game account in."""

    game: str
    uid: str
    nickname: str | None
    claimed: bool


class AccountCheckinMixin:
    """Adds per-account check-in to a game service.

    Services inherit this after defining ``game`` and ``_accounts``.
    """

    game: str
    _accounts: AccountService

    async def checkin_account(self, telegram_id: int, uid: str) -> CheckinOutcome:
        """Claim the daily reward for one account, without rendering text."""
        account = await self._accounts.get_account(telegram_id, self.game, uid)
        if account is None:
            raise CredentialsMissingError()

        client = await self._accounts.build_client(telegram_id, self.game, uid)
        claimed = await run_api(_sign_in(client, self.game), action="Daily check-in")
        return CheckinOutcome(
            game=self.game,
            uid=uid,
            nickname=account.nickname,
            claimed=claimed,
        )


async def _sign_in(client: Any, game: str) -> bool:
    """Sign in once; ``False`` means the reward was already claimed today."""
    import genshin

    try:
        await client.claim_daily_reward(game=library_game(game), reward=False)
    except genshin.AlreadyClaimed:
        return False
    return True
