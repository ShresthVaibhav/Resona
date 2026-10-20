"""Shared game-module contract.

Every implemented game exposes the same small surface so the generic handlers
can dispatch without knowing which game they are talking to.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from resona.games.checkin import CheckinOutcome
    from resona.games.common import GameEventDigest


@runtime_checkable
class GameService(Protocol):
    """Operations every implemented game provides."""

    game: str

    async def notes(self, telegram_id: int) -> str: ...

    async def characters(self, telegram_id: int) -> str: ...

    async def checkin(self, telegram_id: int) -> str: ...

    async def checkin_account(self, telegram_id: int, uid: str) -> CheckinOutcome: ...

    async def diary(self, telegram_id: int) -> str: ...

    async def endgame(self, telegram_id: int) -> str: ...

    async def events(self, telegram_id: int) -> str: ...

    async def events_ending(
        self, telegram_id: int, *, within_days: int = 3
    ) -> GameEventDigest: ...

    async def wishes(self, telegram_id: int, *, authkey: str | None = None) -> str: ...
