"""Pure rich-message builders used by profile, accounts and help."""

from __future__ import annotations

from resona.core.rich import (
    AccountEntry,
    CommandEntry,
    EventDigestSection,
    account_overview,
    event_digest_summary,
    help_page,
    profile_summary,
)


def test_profile_summary_escapes_user_text() -> None:
    content = profile_summary(
        name="<Admin>",
        username="admin&co",
        telegram_id=99,
        member_since="2026-01-02",
        linked_accounts=2,
        locale="en",
        timezone="UTC",
        default_game="Genshin Impact",
        notifications=True,
        event_digest=True,
    )

    assert "<h1>Profile</h1>" in content.payload.html
    assert "&lt;Admin&gt;" in content.payload.html
    assert "admin&amp;co" in content.payload.html
    assert "<b>Notifications:</b> on" in content.payload.html
    assert "<b>Event digest:</b> on" in content.payload.html
    assert "Name: <Admin> (@admin&co)" in content.fallback_text
    assert "Notifications: on" in content.fallback_text
    assert "Event digest: on" in content.fallback_text


def test_event_digest_summary_escapes_text_and_keeps_fallback() -> None:
    content = event_digest_summary(
        [
            EventDigestSection(
                label="Genshin <Impact>",
                name="Traveler & Co",
                events=(("Windblume <festival>", "1h"),),
            )
        ],
        days=3,
        errors=("HoYoLAB <error>",),
        fallback_text="fallback digest",
    )

    assert content is not None
    assert "<h1>Events ending in the next 3 days</h1>" in content.payload.html
    assert "Genshin &lt;Impact&gt;" in content.payload.html
    assert "Traveler &amp; Co" in content.payload.html
    assert "Windblume &lt;festival&gt;" in content.payload.html
    assert "HoYoLAB &lt;error&gt;" in content.payload.html
    assert content.fallback_text == "fallback digest"


def test_event_digest_summary_returns_none_without_events() -> None:
    content = event_digest_summary(
        [EventDigestSection("Genshin Impact", "Traveler", ())],
        days=3,
        fallback_text="fallback",
    )

    assert content is None


def test_account_overview_groups_games_and_marks_the_primary() -> None:
    content = account_overview(
        [
            (
                "Genshin Impact",
                [
                    AccountEntry(
                        name="Traveler",
                        uid="800000001",
                        server="Asia",
                        is_primary=True,
                    )
                ],
            ),
            ("Honkai: Star Rail", []),
        ]
    )

    assert "<h2>Genshin Impact</h2>" in content.payload.html
    assert "Traveler — UID 800000001 (Asia) [primary]" in content.payload.html
    assert "Honkai: Star Rail" not in content.payload.html
    assert "Traveler — UID 800000001 (Asia) [primary]" in content.fallback_text
    assert "/link" in content.fallback_text


def test_help_page_lists_aliases_and_descriptions() -> None:
    content = help_page(
        [
            (
                "Game",
                [
                    CommandEntry(
                        name="notes",
                        description="Show <notes>",
                        aliases=("stamina",),
                    )
                ],
            )
        ]
    )

    assert "<h2>Game</h2>" in content.payload.html
    assert "<b>/notes</b>" in content.payload.html
    assert "Show &lt;notes&gt;" in content.payload.html
    assert "(also /stamina)" in content.payload.html
    assert "/notes (also /stamina) - Show <notes>" in content.fallback_text
