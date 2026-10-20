"""User persistence."""

from __future__ import annotations

from pymongo.errors import DuplicateKeyError

from resona.core.utils import utcnow
from resona.database.collections import UserDocument
from resona.database.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    """Stores one record per Telegram user."""

    async def get(self, telegram_id: int) -> UserDocument | None:
        record = await self._collection.find_one({"telegram_id": telegram_id})
        return UserDocument.model_validate(record) if record is not None else None

    async def get_or_create(
        self,
        telegram_id: int,
        *,
        username: str | None = None,
        first_name: str | None = None,
        language_code: str | None = None,
    ) -> UserDocument:
        existing = await self.get(telegram_id)
        if existing is not None:
            return existing

        now = utcnow()
        document = UserDocument(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            language_code=language_code,
            created_at=now,
            updated_at=now,
            last_seen_at=now,
        )

        try:
            await self._collection.insert_one(document.to_record())
        except DuplicateKeyError:
            # Another process created the user first.
            existing = await self.get(telegram_id)
            if existing is None:
                raise
            return existing

        return document

    async def touch(
        self,
        telegram_id: int,
        *,
        username: str | None = None,
        first_name: str | None = None,
        language_code: str | None = None,
    ) -> UserDocument | None:
        """Update the last-seen timestamp and any changed profile fields."""
        now = utcnow()
        updates: dict[str, object] = {"last_seen_at": now, "updated_at": now}
        if username is not None:
            updates["username"] = username
        if first_name is not None:
            updates["first_name"] = first_name
        if language_code is not None:
            updates["language_code"] = language_code

        await self._collection.update_one(
            {"telegram_id": telegram_id}, {"$set": updates}
        )
        return await self.get(telegram_id)

    async def set_blocked(self, telegram_id: int, blocked: bool) -> None:
        await self._collection.update_one(
            {"telegram_id": telegram_id},
            {"$set": {"is_blocked": blocked, "updated_at": utcnow()}},
        )

    async def delete(self, telegram_id: int) -> bool:
        result = await self._collection.delete_one({"telegram_id": telegram_id})
        return bool(getattr(result, "deleted_count", 0))

    async def count(self) -> int:
        return int(await self._collection.count_documents({}))
