"""Game account metadata persistence."""

from __future__ import annotations

from resona.core.utils import utcnow
from resona.database.collections import GameAccountDocument
from resona.database.repositories.base import BaseRepository


class GameAccountRepository(BaseRepository):
    """Stores known in-game accounts for each user."""

    async def upsert(
        self,
        *,
        telegram_id: int,
        game: str,
        uid: str,
        nickname: str | None = None,
        server: str | None = None,
        level: int | None = None,
    ) -> GameAccountDocument:
        now = utcnow()
        query = {"telegram_id": telegram_id, "game": game, "uid": uid}

        await self._collection.update_one(
            query,
            {
                "$set": {
                    "nickname": nickname,
                    "server": server,
                    "level": level,
                    "updated_at": now,
                },
                "$setOnInsert": {"created_at": now, "is_primary": False},
            },
            upsert=True,
        )

        record = await self._collection.find_one(query)
        if record is None:  # pragma: no cover - defensive
            raise RuntimeError("Game account upsert did not persist a record.")
        return GameAccountDocument.model_validate(record)

    async def get(
        self, telegram_id: int, game: str, uid: str
    ) -> GameAccountDocument | None:
        record = await self._collection.find_one(
            {"telegram_id": telegram_id, "game": game, "uid": uid}
        )
        return (
            GameAccountDocument.model_validate(record) if record is not None else None
        )

    async def list_for_user(
        self, telegram_id: int, game: str | None = None
    ) -> list[GameAccountDocument]:
        query: dict[str, object] = {"telegram_id": telegram_id}
        if game is not None:
            query["game"] = game

        cursor = self._collection.find(query).sort("created_at", 1)
        records = await cursor.to_list(None)
        return [GameAccountDocument.model_validate(record) for record in records]

    async def set_primary(self, telegram_id: int, game: str, uid: str) -> None:
        """Mark one account as primary, clearing the flag on its siblings."""
        await self._collection.update_many(
            {"telegram_id": telegram_id, "game": game},
            {"$set": {"is_primary": False, "updated_at": utcnow()}},
        )
        await self._collection.update_one(
            {"telegram_id": telegram_id, "game": game, "uid": uid},
            {"$set": {"is_primary": True, "updated_at": utcnow()}},
        )

    async def mark_synced(self, telegram_id: int, game: str, uid: str) -> None:
        await self._collection.update_one(
            {"telegram_id": telegram_id, "game": game, "uid": uid},
            {"$set": {"last_synced_at": utcnow(), "updated_at": utcnow()}},
        )

    async def delete(self, telegram_id: int, game: str, uid: str | None = None) -> int:
        query: dict[str, object] = {"telegram_id": telegram_id, "game": game}
        if uid is not None:
            query["uid"] = uid
            result = await self._collection.delete_one(query)
        else:
            result = await self._collection.delete_many(query)
        return int(getattr(result, "deleted_count", 0))

    async def delete_all(self, telegram_id: int) -> int:
        result = await self._collection.delete_many({"telegram_id": telegram_id})
        return int(getattr(result, "deleted_count", 0))
