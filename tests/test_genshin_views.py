"""Rendering tests using lightweight stand-ins for genshin.py models."""

from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace

from resona.games.genshin import views


def _account() -> SimpleNamespace:
    return SimpleNamespace(nickname="Traveler", uid="800000001")


def _notes() -> SimpleNamespace:
    return SimpleNamespace(
        current_resin=120,
        max_resin=160,
        remaining_resin_recovery_time=timedelta(hours=3, minutes=20),
        current_realm_currency=1200,
        max_realm_currency=2400,
        remaining_realm_currency_recovery_time=timedelta(days=1, hours=2),
        completed_commissions=2,
        max_commissions=4,
        claimed_commission_reward=False,
        remaining_resin_discounts=2,
        max_resin_discounts=3,
        remaining_transformer_recovery_time=timedelta(days=5, hours=3),
        expeditions=[SimpleNamespace()],
        max_expeditions=5,
    )


def test_render_notes_includes_recovery_and_tasks() -> None:
    rendered = views.render_notes(_account(), _notes())

    assert "Genshin Impact - Traveler (UID 800000001)" in rendered
    assert "Resin: 120/160 (full in 3h 20m)" in rendered
    assert "Realm currency: 1200/2400 (full in 1d 2h)" in rendered
    assert "Commissions: 2/4 (reward unclaimed)" in rendered
    assert "Weekly boss discounts: 2/3 remaining" in rendered
    assert "Parametric transformer: ready in 5d 3h" in rendered
    assert "Expeditions: 1/5" in rendered


def test_render_characters_groups_by_rarity() -> None:
    characters = [
        SimpleNamespace(
            name="Furina",
            rarity=5,
            level=90,
            constellation=2,
            friendship=10,
            weapon=SimpleNamespace(name="Splendor", refinement=1),
        ),
        SimpleNamespace(
            name="Bennett",
            rarity=4,
            level=80,
            constellation=6,
            friendship=8,
            weapon=None,
        ),
    ]

    rendered = views.render_characters(_account(), characters)

    assert "5-star (1)" in rendered
    assert "Furina - Lv. 90, C2, Friendship 10, Splendor R1" in rendered
    assert "4-star (1)" in rendered
    assert "Bennett - Lv. 80, C6, Friendship 8" in rendered


def test_render_characters_without_data() -> None:
    assert "No characters were returned." in views.render_characters(_account(), [])


def test_render_diary_shows_income_and_sources() -> None:
    diary = SimpleNamespace(
        month=10,
        data=SimpleNamespace(
            current_primogems=12_345,
            last_primogems=10_000,
            primogems_rate=23,
            current_mora=1_234_567,
            last_mora=1_000_000,
            mora_rate=23,
            categories=[
                SimpleNamespace(name="Daily commissions", amount=1200, percentage=40),
                SimpleNamespace(name="Events", amount=800, percentage=27),
            ],
        ),
    )

    rendered = views.render_diary(_account(), diary)

    assert "October" in rendered
    assert "Primogems: 12,345 (previous month 10,000, +23%)" in rendered
    assert "Daily commissions: 1,200 (40%)" in rendered


def test_render_endgame_shows_floor_progress() -> None:
    abyss = SimpleNamespace(
        season="12",
        unlocked=True,
        max_floor=12,
        total_stars=33,
        total_battles=12,
        total_wins=11,
        floors=[SimpleNamespace(floor=12, stars=6, max_stars=9)],
    )

    rendered = views.render_endgame(_account(), abyss)

    assert "Spiral Abyss - 12" in rendered
    assert "Max floor: 12" in rendered
    assert "Floor 12: 6/9" in rendered


def test_render_endgame_when_locked() -> None:
    abyss = SimpleNamespace(season="12", unlocked=False)

    assert "not unlocked" in views.render_endgame(_account(), abyss)


def test_render_endgame_includes_theater_and_stygian() -> None:
    from datetime import datetime

    abyss = SimpleNamespace(
        season="12",
        unlocked=True,
        max_floor=12,
        total_stars=33,
        total_battles=12,
        total_wins=11,
        floors=[],
    )
    theater = SimpleNamespace(
        unlocked=True,
        datas=[
            SimpleNamespace(
                has_data=True,
                schedule=SimpleNamespace(end_datetime=datetime(2026, 11, 1)),
                stats=SimpleNamespace(
                    best_record=10,
                    medal_num=3,
                    difficulty=SimpleNamespace(name="VISIONARY"),
                    lunar_arcana_completed=2,
                ),
            )
        ],
    )
    stygian = [
        SimpleNamespace(
            season=SimpleNamespace(name="Qiuhua"),
            single_player=SimpleNamespace(
                has_data=True,
                best_record=SimpleNamespace(difficulty=4, time_used=83),
            ),
            multi_player=SimpleNamespace(has_data=False),
        )
    ]

    rendered = views.render_endgame(_account(), abyss, theater, stygian)

    assert "Imaginarium Theater" in rendered
    assert "Best act: 10" in rendered
    assert "Medals: 3" in rendered
    assert "Difficulty: Visionary" in rendered
    assert "Ends: 2026-11-01" in rendered
    assert "Stygian Onslaught - Qiuhua" in rendered
    assert "Single: difficulty 4, 1m 23s" in rendered


def test_render_endgame_marks_unavailable_sections() -> None:
    rendered = views.render_endgame(_account(), None, None, None)

    assert "Spiral Abyss: data is not public." in rendered
    assert "Imaginarium Theater: data is not public." in rendered
    assert "Stygian Onslaught: data is not public." in rendered


def test_render_events_lists_active_events() -> None:
    calendar = SimpleNamespace(
        events=[
            SimpleNamespace(
                name="Windblume", is_finished=False, countdown_seconds=3600
            ),
            SimpleNamespace(name="Old event", is_finished=True, countdown_seconds=0),
        ],
        challenges=[],
    )

    rendered = views.render_events(_account(), calendar)

    assert "Windblume - ends in 1h" in rendered
    assert "Old event" not in rendered


def test_event_summaries_filters_to_upcoming_days() -> None:
    calendar = SimpleNamespace(
        events=[
            SimpleNamespace(
                name="Windblume", is_finished=False, countdown_seconds=3600
            ),
            SimpleNamespace(
                name="Long event", is_finished=False, countdown_seconds=10 * 86400
            ),
            SimpleNamespace(name="Unknown end", is_finished=False, countdown_seconds=0),
            SimpleNamespace(name="Old event", is_finished=True, countdown_seconds=3600),
        ],
        challenges=[],
    )

    summaries = views.event_summaries(calendar, within_days=3)

    assert [summary.name for summary in summaries] == ["Windblume"]


def test_render_checkin_reports_reward() -> None:
    reward = SimpleNamespace(name="Primogem", amount=20)
    info = SimpleNamespace(claimed_rewards=12)

    rendered = views.render_checkin(_account(), reward, info)

    assert "Claimed: Primogem x20." in rendered
    assert "Claimed this month: 12" in rendered


def test_render_checkin_when_already_claimed() -> None:
    info = SimpleNamespace(claimed_rewards=12)

    rendered = views.render_checkin(_account(), None, info)

    assert "already claimed" in rendered
