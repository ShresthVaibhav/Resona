"""Unit tests for handler helpers that do not need Telegram objects."""

from __future__ import annotations

from datetime import UTC, datetime

from resona.database.collections import UserSettingsDocument
from resona.handlers.account import _split_link_arguments
from resona.handlers.profile import _parse_toggle, _render_settings


def test_split_link_arguments_rejoins_cookie_header() -> None:
    parsed = _split_link_arguments(
        ["genshin", "ltuid_v2=1;", "ltoken_v2=secret;", "ltmid_v2=mid"]
    )

    assert parsed == ("genshin", None, "ltuid_v2=1; ltoken_v2=secret; ltmid_v2=mid")


def test_split_link_arguments_reads_optional_uid() -> None:
    parsed = _split_link_arguments(["hsr", "800000001", "ltuid_v2=1;", "ltoken_v2=x"])

    assert parsed == ("hsr", "800000001", "ltuid_v2=1; ltoken_v2=x")


def test_split_link_arguments_without_arguments() -> None:
    assert _split_link_arguments([]) is None


def test_parse_toggle_accepts_common_spellings() -> None:
    for value in ("on", "TRUE", "yes", "enable", "1"):
        assert _parse_toggle(value) is True
    for value in ("off", "false", "No", "disable", "0"):
        assert _parse_toggle(value) is False


def test_parse_toggle_rejects_other_values() -> None:
    assert _parse_toggle("maybe") is None


def test_render_settings_shows_defaults() -> None:
    now = datetime.now(UTC)
    settings = UserSettingsDocument(telegram_id=1, created_at=now, updated_at=now)

    rendered = _render_settings(settings)

    assert "Language: en" in rendered
    assert "Timezone: UTC" in rendered
    assert "Default game: none" in rendered
    assert "Notifications: on" in rendered
    assert "Event digest: off" in rendered
    assert "/settings event_digest" in rendered
