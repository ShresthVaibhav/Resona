"""Plain-text rendering for Honkai: Star Rail."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any

from resona.core.utils import format_duration, truncate
from resona.games.common import EventSummary
from resona.games.common import account_header as _header
from resona.games.common import render_checkin as _render_checkin

if TYPE_CHECKING:
    from collections.abc import Sequence

    from resona.database.collections import GameAccountDocument


def render_notes(account: GameAccountDocument, notes: Any) -> str:
    lines = [_header(account, "Honkai: Star Rail"), ""]

    stamina = f"Stamina: {notes.current_stamina}/{notes.max_stamina}"
    if notes.current_stamina < notes.max_stamina:
        recovery = format_duration(notes.stamina_recover_time.total_seconds())
        stamina += f" (full in {recovery})"
    lines.append(stamina)

    lines.append(
        f"Expeditions: {notes.accepted_expedition_num}/{notes.total_expedition_num}"
    )

    if notes.max_weekly_discounts:
        lines.append(
            "Weekly boss discounts: "
            f"{notes.remaining_weekly_discounts}/{notes.max_weekly_discounts} remaining"
        )

    reserve = f"Reserve stamina: {notes.current_reserve_stamina}"
    if notes.is_reserve_stamina_full:
        reserve += " (full)"
    lines.append(reserve)

    if notes.max_train_score:
        lines.append(
            f"Train score: {notes.current_train_score}/{notes.max_train_score}"
        )
    if notes.max_rogue_score:
        lines.append(
            f"Rogue score: {notes.current_rogue_score}/{notes.max_rogue_score}"
        )

    return "\n".join(lines)


def render_characters(account: GameAccountDocument, response: Any) -> str:
    characters: Sequence[Any] = response.avatar_list
    lines = [_header(account, "Honkai: Star Rail"), ""]

    if not characters:
        lines.append("No characters were returned.")
        return "\n".join(lines)

    for rarity in (5, 4):
        group = [character for character in characters if character.rarity == rarity]
        if not group:
            continue

        lines.append(f"{rarity}-star ({len(group)})")
        for character in sorted(group, key=lambda item: (-item.level, item.name)):
            path = _enum_label(character.path)
            lines.append(
                f"  {character.name} - Lv. {character.level}, E{character.rank}, "
                f"{path}, {character.element}"
            )
        lines.append("")

    return truncate("\n".join(lines).strip(), 3900)


def render_diary(account: GameAccountDocument, diary: Any) -> str:
    data = diary.data
    lines = [
        _header(account, f"Honkai: Star Rail diary - {_month_name(diary.month)}"),
        "",
        f"Stellar Jade: {data.current_hcoin:,} "
        f"(previous month {data.last_hcoin:,}, {data.hcoin_rate:+d}%)",
        f"Rails Pass: {data.current_rails_pass:,} "
        f"(previous month {data.last_rails_pass:,}, {data.rails_rate:+d}%)",
        "",
        "Sources",
    ]

    categories = sorted(data.categories, key=lambda item: item.amount, reverse=True)
    for category in categories[:8]:
        lines.append(f"  {category.name}: {category.amount:,} ({category.percentage}%)")

    return "\n".join(lines)


_UNSET = object()


def render_endgame(
    account: GameAccountDocument,
    challenge: Any | None,
    rogue: Any = _UNSET,
    pure_fiction: Any = _UNSET,
    apc_shadow: Any = _UNSET,
    anomaly: Any = _UNSET,
) -> str:
    lines = [_header(account, "Honkai: Star Rail endgame"), ""]

    if challenge is None:
        lines.append("Memory of Chaos: data is not public.")
    else:
        lines.extend(_render_challenge(challenge))

    if rogue is not _UNSET:
        lines.append("")
        if rogue is None:
            lines.append("Simulated Universe: data is not public.")
        else:
            lines.extend(_render_rogue(rogue))

    if pure_fiction is not _UNSET:
        lines.append("")
        if pure_fiction is None:
            lines.append("Pure Fiction: data is not public.")
        else:
            lines.extend(_render_pure_fiction(pure_fiction))

    if apc_shadow is not _UNSET:
        lines.append("")
        if apc_shadow is None:
            lines.append("Apocalyptic Shadow: data is not public.")
        else:
            lines.extend(_render_apocalyptic_shadow(apc_shadow))

    if anomaly is not _UNSET:
        lines.append("")
        if anomaly is None:
            lines.append("Anomaly Arbitration: data is not public.")
        else:
            lines.extend(_render_anomaly(anomaly))

    return truncate("\n".join(lines), 3900)


def _render_challenge(challenge: Any) -> list[str]:
    lines = [f"Memory of Chaos - {challenge.name}"]

    if not challenge.has_data:
        lines.append("  No Memory of Chaos data for this season.")
        return lines

    lines.append(f"  Season: {challenge.season}")
    lines.append(f"  Stars: {challenge.total_stars}")
    lines.append(f"  Max floor: {challenge.max_floor}")

    if challenge.floors:
        lines.append("")
        for floor in challenge.floors:
            lines.append(f"  {floor.name}: {floor.star_num} stars")

    return lines


def _render_rogue(rogue: Any) -> list[str]:
    lines = ["Simulated Universe"]
    current = rogue.current_record

    if not current.has_data:
        lines.append("  No current season data.")
    else:
        lines.append(f"  Clears: {current.basic.finish_cnt}")
        if current.records:
            best = max(current.records, key=lambda record: record.score)
            lines.append(f"  Best score: {best.score:,} ({best.name})")
            lines.append(f"  Difficulty: {best.difficulty}")

    last = rogue.last_record
    if last.has_data and last.records:
        best = max(last.records, key=lambda record: record.score)
        lines.append(f"  Last season best: {best.score:,} ({best.name})")

    return lines


def _render_pure_fiction(data: Any) -> list[str]:
    lines = ["Pure Fiction"]

    if not data.has_data:
        lines.append("  No Pure Fiction data for this season.")
        return lines

    season = data.seasons[0] if data.seasons else None
    if season is not None:
        lines[0] += f" - {season.name}"

    lines.append(f"  Stars: {data.total_stars}")
    if data.starward_stars:
        lines.append(f"  Starward stars: {data.starward_stars}")
    lines.append(f"  Max floor: {data.max_floor}")
    lines.append(f"  Battles: {data.total_battles}")

    for floor in data.floors:
        lines.append(f"  {floor.name}: {floor.star_num} stars, {floor.score:,} score")

    return lines


def _render_apocalyptic_shadow(data: Any) -> list[str]:
    lines = ["Apocalyptic Shadow"]

    if not data.has_data:
        lines.append("  No Apocalyptic Shadow data for this season.")
        return lines

    season = data.seasons[0] if data.seasons else None
    if season is not None:
        lines[0] += f" - {season.name}"
        bosses = [
            boss.name
            for boss in (season.upper_boss, season.lower_boss, season.starward_boss)
            if boss is not None
        ]
        if bosses:
            lines.append(f"  Bosses: {', '.join(bosses)}")

    lines.append(f"  Stars: {data.total_stars}")
    if data.starward_stars:
        lines.append(f"  Starward stars: {data.starward_stars}")
    lines.append(f"  Max floor: {data.max_floor}")
    lines.append(f"  Battles: {data.total_battles}")

    for floor in data.floors:
        lines.append(f"  {floor.name}: {floor.star_num} stars, {floor.score:,} score")

    return lines


def _render_anomaly(data: Any) -> list[str]:
    lines = ["Anomaly Arbitration"]

    cleared = [record for record in data.records if record.has_data]
    if not cleared:
        lines.append("  No clears this season.")
        return lines

    for record in cleared[:2]:
        lines.append(f"  {record.season.name} - {record.boss.name}")
        lines.append(
            f"    Stars: boss {record.boss_stars}, mini bosses {record.mini_boss_stars}"
        )
        lines.append(f"    Cycles used: {record.cycles_used}")

        if record.boss_record is not None and record.boss_record.has_data:
            lines.append(
                f"    Boss record: {record.boss_record.stars} stars, "
                f"{record.boss_record.cycles_used} cycles"
            )

        if record.mini_boss_records:
            mini_cleared = sum(1 for item in record.mini_boss_records if item.has_data)
            lines.append(
                f"    Mini bosses cleared: {mini_cleared}/"
                f"{len(record.mini_boss_records)}"
            )

    return lines


def event_summaries(
    calendar: Any, *, within_days: int | None = None
) -> list[EventSummary]:
    """Active events, optionally limited to those ending within ``within_days``."""
    cutoff = within_days * 86400 if within_days is not None else None
    summaries: list[EventSummary] = []

    for event in (*calendar.events, *calendar.challenges):
        if event.all_finished:
            continue

        info = event.time_info
        end = getattr(info, "end", None) if info is not None else None
        now = getattr(info, "now", None) if info is not None else None
        if end is not None and now is not None:
            if end <= now:
                continue
            seconds = (end - now).total_seconds()
        else:
            seconds = 0.0

        if cutoff is not None and (seconds <= 0 or seconds > cutoff):
            continue

        summaries.append(EventSummary(event.name, seconds))

    summaries.sort(key=lambda item: item.seconds_remaining)
    return summaries


def render_events(account: GameAccountDocument, calendar: Any) -> str:
    lines = [_header(account, "Honkai: Star Rail events"), ""]

    summaries = event_summaries(calendar)
    if not summaries:
        lines.append("No active events right now.")
        return "\n".join(lines)

    for summary in summaries[:15]:
        suffix = (
            f" - ends in {format_duration(summary.seconds_remaining)}"
            if summary.seconds_remaining > 0
            else ""
        )
        lines.append(f"  {summary.name}{suffix}")

    return truncate("\n".join(lines), 3900)


def render_checkin(account: GameAccountDocument, reward: Any, info: Any) -> str:
    return _render_checkin(account, "Honkai: Star Rail", reward, info)


def _enum_label(value: Any) -> str:
    name = getattr(value, "name", None)
    return name.replace("_", " ").title() if name else str(value)


def _month_name(month: int) -> str:
    try:
        return date(2000, month, 1).strftime("%B")
    except ValueError:
        return str(month)
