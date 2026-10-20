"""Per-user settings persistence."""

from __future__ import annotations

from pymongo.errors import DuplicateKeyError

from resona.core.utils import utcnow
from resona.database.collections import UserSettingsDocument
from resona.database.repositories.base import BaseRepository


class SettingsRepository(BaseRepository):
    """Stores per-user preferences, creating defaults on first access."""

    UPDATABLE_FIELDS = frozenset(
        {
            "locale",
            "timezone",
            "default_game",
            "notifications_enabled",
            "event_digest_enabled",
        }
    )

    async def get(self, telegram_id: int) -> UserSettingsDocument:
        record = await self._collection.find_one({"telegram_id": telegram_id})
        if record is not None:
            return UserSettingsDocument.model_validate(record)
        return await self._create_defaults(telegram_id)

    async def update(self, telegram_id: int, **fields: object) -> UserSettingsDocument:
        unknown = set(fields) - self.UPDATABLE_FIELDS
        if unknown:
            raise ValueError(f"Cannot update settings fields: {sorted(unknown)}")

        await self.get(telegram_id)

        if fields:
            await self._collection.update_one(
                {"telegram_id": telegram_id},
                {"$set": {**fields, "updated_at": utcnow()}},
            )

        return await self.get(telegram_id)

    async def delete(self, telegram_id: int) -> bool:
        result = await self._collection.delete_one({"telegram_id": telegram_id})
        return bool(getattr(result, "deleted_count", 0))

    async def _create_defaults(self, telegram_id: int) -> UserSettingsDocument:
        now = utcnow()
        document = UserSettingsDocument(
            telegram_id=telegram_id, created_at=now, updated_at=now
        )

        try:
            await self._collection.insert_one(document.to_record())
        except DuplicateKeyError:
            record = await self._collection.find_one({"telegram_id": telegram_id})
            if record is None:
                raise
            return UserSettingsDocument.model_validate(record)

        return document
