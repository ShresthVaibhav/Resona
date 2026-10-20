"""Rendering tests for Honkai: Star Rail."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from resona.games.hsr import views


def _account() -> SimpleNamespace:
    return SimpleNamespace(nickname="Trailblazer", uid="800000002")


def test_render_notes_includes_stamina_and_scores() -> None:
    notes = SimpleNamespace(
        current_stamina=120,
        max_stamina=240,
        stamina_recover_time=timedelta(hours=3),
        accepted_expedition_num=2,
        total_expedition_num=8,
        remaining_weekly_discounts=1,
        max_weekly_discounts=3,
        current_reserve_stamina=500,
        is_reserve_stamina_full=False,
        current_train_score=4000,
        max_train_score=8000,
        current_rogue_score=1000,
        max_rogue_score=5000,
    )

    rendered = views.render_notes(_account(), notes)

    assert "Stamina: 120/240 (full in 3h)" in rendered
    assert "Expeditions: 2/8" in rendered
    assert "Weekly boss discounts: 1/3 remaining" in rendered
    assert "Reserve stamina: 500" in rendered
    assert "Train score: 4000/8000" in rendered
    assert "Rogue score: 1000/5000" in rendered


def test_render_characters_groups_by_rarity() -> None:
    response = SimpleNamespace(
        avatar_list=[
            SimpleNamespace(
                name="Seele",
                rarity=5,
                level=80,
                rank=2,
                path=SimpleNamespace(name="HUNT"),
                element="Quantum",
            ),
            SimpleNamespace(
                name="March 7th",
                rarity=4,
                level=70,
                rank=6,
                path=SimpleNamespace(name="PRESERVATION"),
                element="Ice",
            ),
        ]
    )

    rendered = views.render_characters(_account(), response)

    assert "5-star (1)" in rendered
    assert "Seele - Lv. 80, E2, Hunt, Quantum" in rendered
    assert "4-star (1)" in rendered
    assert "March 7th - Lv. 70, E6, Preservation, Ice" in rendered


def test_render_diary_shows_income_and_sources() -> None:
    diary = SimpleNamespace(
        month=10,
        data=SimpleNamespace(
            current_hcoin=12_345,
            last_hcoin=10_000,
            hcoin_rate=23,
            current_rails_pass=5,
            last_rails_pass=4,
            rails_rate=25,
            categories=[
                SimpleNamespace(name="Daily training", amount=1200, percentage=40)
            ],
        ),
    )

    rendered = views.render_diary(_account(), diary)

    assert "October" in rendered
    assert "Stellar Jade: 12,345 (previous month 10,000, +23%)" in rendered
    assert "Rails Pass: 5 (previous month 4, +25%)" in rendered
    assert "Daily training: 1,200 (40%)" in rendered


def test_render_endgame_shows_floor_progress() -> None:
    challenge = SimpleNamespace(
        name="Memory of Chaos",
        season="12",
        has_data=True,
        total_stars=33,
        max_floor=12,
        floors=[SimpleNamespace(name="Floor 12", star_num=3)],
    )

    rendered = views.render_endgame(_account(), challenge)

    assert "Memory of Chaos - Memory of Chaos" in rendered
    assert "Stars: 33" in rendered
    assert "Floor 12: 3 stars" in rendered


def test_render_endgame_without_data() -> None:
    challenge = SimpleNamespace(name="Memory of Chaos", has_data=False)

    assert "No Memory of Chaos data" in views.render_endgame(_account(), challenge)


def test_render_endgame_includes_rogue_records() -> None:
    challenge = SimpleNamespace(
        name="Memory of Chaos",
        season="12",
        has_data=True,
        total_stars=33,
        max_floor=12,
        floors=[],
    )
    rogue = SimpleNamespace(
        current_record=SimpleNamespace(
            has_data=True,
            basic=SimpleNamespace(finish_cnt=7),
            records=[
                SimpleNamespace(score=12_345, name="Swordplay", difficulty=5),
                SimpleNamespace(score=9_000, name="Cycle", difficulty=4),
            ],
        ),
        last_record=SimpleNamespace(
            has_data=True,
            records=[SimpleNamespace(score=8_000, name="Swarm", difficulty=4)],
        ),
    )

    rendered = views.render_endgame(_account(), challenge, rogue)

    assert "Simulated Universe" in rendered
    assert "Clears: 7" in rendered
    assert "Best score: 12,345 (Swordplay)" in rendered
    assert "Difficulty: 5" in rendered
    assert "Last season best: 8,000 (Swarm)" in rendered


def test_render_endgame_marks_unavailable_rogue() -> None:
    challenge = SimpleNamespace(name="Memory of Chaos", has_data=False)

    rendered = views.render_endgame(_account(), challenge, None)

    assert "Simulated Universe: data is not public." in rendered


def test_render_endgame_includes_pure_fiction_shadow_and_anomaly() -> None:
    challenge = SimpleNamespace(name="Memory of Chaos", has_data=False)
    pure_fiction = SimpleNamespace(
        has_data=True,
        seasons=[SimpleNamespace(name="Fiction season")],
        total_stars=12,
        starward_stars=2,
        max_floor="4",
        total_battles=8,
        floors=[SimpleNamespace(name="Floor 4", star_num=3, score=50_000)],
    )
    apc_shadow = SimpleNamespace(
        has_data=True,
        seasons=[
            SimpleNamespace(
                name="Shadow season",
                upper_boss=SimpleNamespace(name="Upper boss"),
                lower_boss=None,
                starward_boss=SimpleNamespace(name="Starward boss"),
            )
        ],
        total_stars=9,
        starward_stars=0,
        max_floor="4",
        total_battles=6,
        floors=[SimpleNamespace(name="Floor 4", star_num=3, score=40_000)],
    )
    anomaly = SimpleNamespace(
        records=[
            SimpleNamespace(
                has_data=True,
                season=SimpleNamespace(name="Arbitration season"),
                boss=SimpleNamespace(name="Arbitration boss"),
                boss_stars=3,
                mini_boss_stars=2,
                cycles_used=4,
                boss_record=SimpleNamespace(
                    has_data=True,
                    stars=3,
                    cycles_used=2,
                ),
                mini_boss_records=[
                    SimpleNamespace(has_data=True),
                    SimpleNamespace(has_data=False),
                ],
            )
        ]
    )

    rendered = views.render_endgame(
        _account(),
        challenge,
        None,
        pure_fiction,
        apc_shadow,
        anomaly,
    )

    assert "Pure Fiction - Fiction season" in rendered
    assert "Stars: 12" in rendered
    assert "Starward stars: 2" in rendered
    assert "Floor 4: 3 stars, 50,000 score" in rendered
    assert "Apocalyptic Shadow - Shadow season" in rendered
    assert "Bosses: Upper boss, Starward boss" in rendered
    assert "Anomaly Arbitration" in rendered
    assert "Arbitration season - Arbitration boss" in rendered
    assert "Stars: boss 3, mini bosses 2" in rendered
    assert "Boss record: 3 stars, 2 cycles" in rendered
    assert "Mini bosses cleared: 1/2" in rendered


def test_render_endgame_marks_new_modes_unavailable() -> None:
    challenge = SimpleNamespace(name="Memory of Chaos", has_data=False)

    rendered = views.render_endgame(_account(), challenge, None, None, None, None)

    assert "Pure Fiction: data is not public." in rendered
    assert "Apocalyptic Shadow: data is not public." in rendered
    assert "Anomaly Arbitration: data is not public." in rendered


def test_render_events_lists_active_events() -> None:
    now = datetime(2026, 10, 20, 12, tzinfo=UTC)
    calendar = SimpleNamespace(
        events=[
            SimpleNamespace(
                name="Active event",
                all_finished=False,
                time_info=SimpleNamespace(
                    start=now - timedelta(days=1),
                    end=now + timedelta(hours=5),
                    now=now,
                ),
            ),
            SimpleNamespace(
                name="Finished event",
                all_finished=True,
                time_info=None,
            ),
        ],
        challenges=[],
    )

    rendered = views.render_events(_account(), calendar)

    assert "Active event - ends in 5h" in rendered
    assert "Finished event" not in rendered


def test_event_summaries_filters_to_upcoming_days() -> None:
    now = datetime(2026, 10, 20, 12, tzinfo=UTC)
    calendar = SimpleNamespace(
        events=[
            SimpleNamespace(
                name="Soon",
                all_finished=False,
                time_info=SimpleNamespace(end=now + timedelta(hours=5), now=now),
            ),
            SimpleNamespace(
                name="Later",
                all_finished=False,
                time_info=SimpleNamespace(end=now + timedelta(days=10), now=now),
            ),
            SimpleNamespace(
                name="No timing",
                all_finished=False,
                time_info=None,
            ),
        ],
        challenges=[],
    )

    summaries = views.event_summaries(calendar, within_days=3)

    assert [summary.name for summary in summaries] == ["Soon"]


def test_render_checkin_reports_reward() -> None:
    reward = SimpleNamespace(name="Stellar Jade", amount=20)
    info = SimpleNamespace(claimed_rewards=7)

    rendered = views.render_checkin(_account(), reward, info)

    assert "Honkai: Star Rail check-in" in rendered
    assert "Claimed: Stellar Jade x20." in rendered
    assert "Claimed this month: 7" in rendered
