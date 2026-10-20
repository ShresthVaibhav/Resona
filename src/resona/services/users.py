"""User records and preferences."""

from __future__ import annotations

from typing import TYPE_CHECKING

from resona.database.collections import UserDocument, UserSettingsDocument

if TYPE_CHECKING:
    from telegram import User

    from resona.database.repositories import SettingsRepository, UserRepository


class UserService:
    """Keeps the user record and preferences in sync with Telegram."""

    def __init__(
        self,
        users: UserRepository,
        settings: SettingsRepository,
    ) -> None:
        self._users = users
        self._settings = settings

    async def ensure_user(self, user: User) -> UserDocument:
        """Create the user on first contact and refresh last-seen data."""
        document = await self._users.get_or_create(
            user.id,
            username=user.username,
            first_name=user.first_name,
            language_code=user.language_code,
        )
        refreshed = await self._users.touch(
            user.id,
            username=user.username,
            first_name=user.first_name,
            language_code=user.language_code,
        )
        await self._settings.get(user.id)
        return refreshed or document

    async def get(self, telegram_id: int) -> UserDocument | None:
        return await self._users.get(telegram_id)

    async def get_settings(self, telegram_id: int) -> UserSettingsDocument:
        return await self._settings.get(telegram_id)

    async def update_settings(
        self, telegram_id: int, **fields: object
    ) -> UserSettingsDocument:
        return await self._settings.update(telegram_id, **fields)
