"""Permission enforcement."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from telegram import Chat

from resona.config.settings import Settings
from resona.wrappers.permissions import check_permission


def _settings(*, owner: int = 1, admins: str = "") -> Settings:
    return Settings(
        BOT_TOKEN="test",
        BOT_OWNER_ID=owner,
        MONGO_URI="mongodb://localhost:27017",
        BOT_ADMIN_IDS=admins,
    )


def _update(user_id: int, chat_type: str = Chat.PRIVATE):
    update = MagicMock()
    update.effective_user.id = user_id
    update.effective_chat.type = chat_type
    update.effective_chat.id = -1000
    return update


def _context(settings: Settings, member_status: str = "administrator"):
    context = MagicMock()
    context.application.bot_data = {"settings": settings}
    context.bot.get_chat_member = AsyncMock(
        return_value=SimpleNamespace(status=member_status)
    )
    return context


async def test_everyone_permission_allows_any_user() -> None:
    context = _context(_settings())
    assert await check_permission(_update(999), context, "everyone") is True


async def test_owner_permission_is_restricted_to_configured_owner() -> None:
    context = _context(_settings(owner=42))
    assert await check_permission(_update(42), context, "owner") is True
    assert await check_permission(_update(7), context, "owner") is False


async def test_bot_admin_permission_includes_owner_and_configured_admins() -> None:
    context = _context(_settings(owner=1, admins="10,11"))
    assert await check_permission(_update(1), context, "bot_admin") is True
    assert await check_permission(_update(10), context, "bot_admin") is True
    assert await check_permission(_update(12), context, "bot_admin") is False


async def test_group_admin_permission_is_denied_in_private_chats() -> None:
    context = _context(_settings(owner=1))
    assert (
        await check_permission(_update(50, Chat.PRIVATE), context, "group_admin")
        is False
    )


async def test_group_admin_permission_uses_chat_membership() -> None:
    context = _context(_settings(owner=1), member_status="administrator")
    assert (
        await check_permission(_update(50, Chat.SUPERGROUP), context, "group_admin")
        is True
    )


async def test_group_admin_permission_fails_closed_on_api_error() -> None:
    context = _context(_settings(owner=1))
    context.bot.get_chat_member = AsyncMock(side_effect=RuntimeError("telegram down"))
    assert (
        await check_permission(_update(50, Chat.SUPERGROUP), context, "group_admin")
        is False
    )


async def test_unknown_permission_is_denied() -> None:
    context = _context(_settings())
    assert await check_permission(_update(1), context, "made_up") is False
