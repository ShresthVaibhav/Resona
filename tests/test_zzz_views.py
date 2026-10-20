"""Rendering tests for Zenless Zone Zero."""

from __future__ import annotations

from types import SimpleNamespace

from resona.games.zzz import views


def _account() -> SimpleNamespace:
    return SimpleNamespace(nickname="Proxy", uid="1300000001")


def test_render_notes_includes_stamina_and_progress() -> None:
    notes = SimpleNamespace(
        battery_charge=SimpleNamespace(current=100, max=240, seconds_till_full=3600),
        engagement=SimpleNamespace(current=500, max=1000),
        weekly_task=SimpleNamespace(cur_point=2, max_point=5),
        scratch_card_completed=False,
        video_store_state=SimpleNamespace(name="CURRENTLY_OPEN"),
        hollow_zero=SimpleNamespace(
            bounty_commission=SimpleNamespace(cur_completed=2, total=3),
            investigation_point=SimpleNamespace(num=300, total=500),
        ),
        member_card=SimpleNamespace(is_open=True),
    )

    rendered = views.render_notes(_account(), notes)

    assert "Battery: 100/240 (full in 1h)" in rendered
    assert "Engagement: 500/1000" in rendered
    assert "Weekly task: 2/5" in rendered
    assert "Scratch card: available" in rendered
    assert "Video store: Currently Open" in rendered
    assert "Hollow Zero bounty: 2/3" in rendered
    assert "Investigation points: 300/500" in rendered
    assert "Member card: active" in rendered


def test_render_characters_groups_by_rank() -> None:
    agents = [
        SimpleNamespace(
            name="Ellen",
            rarity="S",
            level=60,
            rank=1,
            specialty=SimpleNamespace(name="ATTACK"),
            element=SimpleNamespace(name="ICE"),
        ),
        SimpleNamespace(
            name="Anby",
            rarity="A",
            level=50,
            rank=6,
            specialty=SimpleNamespace(name="STUN"),
            element=SimpleNamespace(name="ELECTRIC"),
        ),
    ]

    rendered = views.render_characters(_account(), agents)

    assert "S-rank (1)" in rendered
    assert "Ellen - Lv. 60, M1, Attack, Ice" in rendered
    assert "A-rank (1)" in rendered
    assert "Anby - Lv. 50, M6, Stun, Electric" in rendered


def test_render_diary_shows_income() -> None:
    diary = SimpleNamespace(
        current_month="2026-10",
        data_month="2026-10",
        income=SimpleNamespace(
            polychrome_incomes=[
                SimpleNamespace(source="Shiyu Defense", num=1200, percent=40)
            ],
            currencies=[SimpleNamespace(name="Denny", num=1_000_000)],
        ),
    )

    rendered = views.render_diary(_account(), diary)

    assert "Zenless Zone Zero diary - 2026-10" in rendered
    assert "Shiyu Defense: 1,200 (40%)" in rendered
    assert "Denny: 1,000,000" in rendered


def test_render_endgame_shows_score_and_challenges() -> None:
    assault = SimpleNamespace(
        has_data=True,
        total_score=12_345,
        total_star=6,
        rank_percent=4.5,
        challenges=[
            SimpleNamespace(
                score=4000,
                star=2,
                total_star=3,
                boss=SimpleNamespace(name="Boss"),
            )
        ],
    )

    rendered = views.render_endgame(_account(), assault)

    assert "Score: 12,345" in rendered
    assert "Stars: 6" in rendered
    assert "Rank: top 4.5%" in rendered
    assert "Boss: 4,000 (2/3)" in rendered


def test_render_endgame_without_data() -> None:
    assault = SimpleNamespace(has_data=False)

    assert "No Deadly Assault data" in views.render_endgame(_account(), assault)


def test_render_endgame_includes_shiyu_and_annihilation() -> None:
    from datetime import timedelta

    assault = SimpleNamespace(
        has_data=True,
        total_score=12_345,
        total_star=6,
        rank_percent=None,
        challenges=[],
    )
    shiyu = SimpleNamespace(
        passed_fifth_floor=True,
        brief_info=SimpleNamespace(
            score=50_000,
            max_score=60_000,
            rating="S",
            rank_percent="4.5%",
            total_clear_time=372,
        ),
    )
    annihilation = SimpleNamespace(
        unlocked=True,
        challenges=[
            SimpleNamespace(
                boss=SimpleNamespace(name="Boss"),
                rank=3,
                star=3,
                duration=timedelta(minutes=1, seconds=23),
            )
        ],
    )

    rendered = views.render_endgame(_account(), assault, shiyu, annihilation)

    assert "Shiyu Defense" in rendered
    assert "Fifth floor: cleared" in rendered
    assert "Score: 50,000/60,000" in rendered
    assert "Rating: S" in rendered
    assert "Rank: top 4.5%" in rendered
    assert "Clear time: 6m 12s" in rendered
    assert "Annihilation Simulacrum" in rendered
    assert "Boss: rank 3, 3 stars, 1m 23s" in rendered


def test_render_endgame_includes_lost_void() -> None:
    from datetime import timedelta

    assault = SimpleNamespace(has_data=False)
    lost_void = SimpleNamespace(
        unlocked=True,
        license=SimpleNamespace(cur_level=12, max_level=20),
        exploration_log=SimpleNamespace(current=4, total=8),
        commission_progress=SimpleNamespace(current=2, total=3),
        ultimate_challenge=SimpleNamespace(
            has_data=True,
            highest_difficulty="Withering Garden",
            total_clears=3,
            shortest_clear_time=timedelta(seconds=83),
        ),
        data_collected=[
            SimpleNamespace(
                type=SimpleNamespace(name="RESONIUM"),
                collected=2,
                total=5,
            )
        ],
        time_remaining=timedelta(hours=5),
    )

    rendered = views.render_endgame(_account(), assault, None, None, lost_void)

    assert "Lost Void" in rendered
    assert "License: 12/20" in rendered
    assert "Exploration log: 4/8" in rendered
    assert "Commission: 2/3" in rendered
    assert "Ultimate: Withering Garden, 3 clears" in rendered
    assert "Shortest clear: 1m 23s" in rendered
    assert "Data collected: Resonium 2/5" in rendered
    assert "Refresh in: 5h" in rendered


def test_render_endgame_marks_unavailable_sections() -> None:
    rendered = views.render_endgame(_account(), None, None, None, None)

    assert "Deadly Assault: data is not public." in rendered
    assert "Shiyu Defense: data is not public." in rendered
    assert "Annihilation Simulacrum: data is not public." in rendered
    assert "Lost Void: data is not public." in rendered


def test_render_events_lists_active_events() -> None:
    events = [
        SimpleNamespace(name="Active event", seconds_until_end=7200),
        SimpleNamespace(name="Finished event", seconds_until_end=0),
    ]

    rendered = views.render_events(_account(), events)

    assert "Active event - ends in 2h" in rendered
    assert "Finished event" not in rendered


def test_event_summaries_filters_to_upcoming_days() -> None:
    events = [
        SimpleNamespace(name="Soon", seconds_until_end=7200),
        SimpleNamespace(name="Later", seconds_until_end=10 * 86400),
        SimpleNamespace(name="Finished", seconds_until_end=0),
    ]

    summaries = views.event_summaries(events, within_days=3)

    assert [summary.name for summary in summaries] == ["Soon"]


def test_render_checkin_reports_reward() -> None:
    reward = SimpleNamespace(name="Polychrome", amount=20)
    info = SimpleNamespace(claimed_rewards=7)

    rendered = views.render_checkin(_account(), reward, info)

    assert "Zenless Zone Zero check-in" in rendered
    assert "Claimed: Polychrome x20." in rendered
    assert "Claimed this month: 7" in rendered
