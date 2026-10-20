"""Encrypted game-account credentials persistence.

Only the encrypted cookie payload is stored here; encryption and decryption are
handled by the credential service so repositories never see plaintext secrets.
"""

from __future__ import annotations

from resona.core.utils import utcnow
from resona.database.collections import CredentialsDocument
from resona.database.repositories.base import BaseRepository


class CredentialsRepository(BaseRepository):
    """Stores one encrypted credential record per game account."""

    async def upsert(
        self,
        *,
        telegram_id: int,
        game: str,
        uid: str,
        encrypted_cookies: str,
        region: str | None = None,
        hoyolab_id: int | None = None,
    ) -> CredentialsDocument:
        now = utcnow()
        query = {"telegram_id": telegram_id, "game": game, "uid": uid}

        await self._collection.update_one(
            query,
            {
                "$set": {
                    "encrypted_cookies": encrypted_cookies,
                    "region": region,
                    "hoyolab_id": hoyolab_id,
                    "updated_at": now,
                },
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )

        record = await self._collection.find_one(query)
        if record is None:  # pragma: no cover - defensive
            raise RuntimeError("Credential upsert did not persist a record.")
        return CredentialsDocument.model_validate(record)

    async def get(
        self, telegram_id: int, game: str, uid: str | None = None
    ) -> CredentialsDocument | None:
        query: dict[str, object] = {"telegram_id": telegram_id, "game": game}
        if uid is not None:
            query["uid"] = uid

        record = await self._collection.find_one(query)
        return (
            CredentialsDocument.model_validate(record) if record is not None else None
        )

    async def list_for_user(
        self, telegram_id: int, game: str | None = None
    ) -> list[CredentialsDocument]:
        query: dict[str, object] = {"telegram_id": telegram_id}
        if game is not None:
            query["game"] = game

        cursor = self._collection.find(query).sort("created_at", 1)
        records = await cursor.to_list(None)
        return [CredentialsDocument.model_validate(record) for record in records]

    async def list_all(self, game: str | None = None) -> list[CredentialsDocument]:
        """Every credential, ordered by user so jobs can group them."""
        query: dict[str, object] = {}
        if game is not None:
            query["game"] = game

        cursor = self._collection.find(query).sort("telegram_id", 1)
        records = await cursor.to_list(None)
        return [CredentialsDocument.model_validate(record) for record in records]

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
