"""Plain-text rendering for Zenless Zone Zero."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from resona.core.utils import format_duration, truncate
from resona.games.common import EventSummary
from resona.games.common import account_header as _header
from resona.games.common import render_checkin as _render_checkin

if TYPE_CHECKING:
    from collections.abc import Sequence

    from resona.database.collections import GameAccountDocument


def render_notes(account: GameAccountDocument, notes: Any) -> str:
    lines = [_header(account, "Zenless Zone Zero"), ""]

    battery = notes.battery_charge
    charge = f"Battery: {battery.current}/{battery.max}"
    if battery.current < battery.max:
        charge += f" (full in {format_duration(battery.seconds_till_full)})"
    lines.append(charge)

    lines.append(f"Engagement: {notes.engagement.current}/{notes.engagement.max}")

    if notes.weekly_task is not None:
        lines.append(
            f"Weekly task: {notes.weekly_task.cur_point}/{notes.weekly_task.max_point}"
        )

    lines.append(
        "Scratch card: "
        + ("completed" if notes.scratch_card_completed else "available")
    )
    lines.append(f"Video store: {_enum_label(notes.video_store_state)}")

    hollow = notes.hollow_zero
    bounty = hollow.bounty_commission
    if bounty.total:
        lines.append(f"Hollow Zero bounty: {bounty.cur_completed}/{bounty.total}")
    survey = hollow.investigation_point
    if survey.total:
        lines.append(f"Investigation points: {survey.num}/{survey.total}")

    lines.append(
        f"Member card: {'active' if notes.member_card.is_open else 'inactive'}"
    )

    return "\n".join(lines)


def render_characters(account: GameAccountDocument, agents: Sequence[Any]) -> str:
    lines = [_header(account, "Zenless Zone Zero"), ""]

    if not agents:
        lines.append("No agents were returned.")
        return "\n".join(lines)

    for rarity in ("S", "A"):
        group = [agent for agent in agents if agent.rarity == rarity]
        if not group:
            continue

        lines.append(f"{rarity}-rank ({len(group)})")
        for agent in sorted(group, key=lambda item: (-item.level, item.name)):
            lines.append(
                f"  {agent.name} - Lv. {agent.level}, M{agent.rank}, "
                f"{_enum_label(agent.specialty)}, {_enum_label(agent.element)}"
            )
        lines.append("")

    return truncate("\n".join(lines).strip(), 3900)


def render_diary(account: GameAccountDocument, diary: Any) -> str:
    income = diary.income
    month = diary.data_month or diary.current_month

    lines = [_header(account, f"Zenless Zone Zero diary - {month}"), ""]

    if income.polychrome_incomes:
        lines.append("Polychrome income")
        for item in sorted(
            income.polychrome_incomes, key=lambda entry: entry.num, reverse=True
        )[:8]:
            lines.append(f"  {item.source}: {item.num:,} ({item.percent}%)")
        lines.append("")

    if income.currencies:
        lines.append("Currencies")
        for currency in income.currencies:
            lines.append(f"  {currency.name}: {currency.num:,}")

    return truncate("\n".join(lines).strip(), 3900)


_UNSET = object()


def render_endgame(
    account: GameAccountDocument,
    assault: Any | None,
    shiyu: Any = _UNSET,
    annihilation: Any = _UNSET,
    lost_void: Any = _UNSET,
) -> str:
    lines = [_header(account, "Zenless Zone Zero endgame"), ""]

    if assault is None:
        lines.append("Deadly Assault: data is not public.")
    else:
        lines.extend(_render_assault(assault))

    if shiyu is not _UNSET:
        lines.append("")
        if shiyu is None:
            lines.append("Shiyu Defense: data is not public.")
        else:
            lines.extend(_render_shiyu(shiyu))

    if annihilation is not _UNSET:
        lines.append("")
        if annihilation is None:
            lines.append("Annihilation Simulacrum: data is not public.")
        else:
            lines.extend(_render_annihilation(annihilation))

    if lost_void is not _UNSET:
        lines.append("")
        if lost_void is None:
            lines.append("Lost Void: data is not public.")
        else:
            lines.extend(_render_lost_void(lost_void))

    return truncate("\n".join(lines), 3900)


def _render_assault(assault: Any) -> list[str]:
    lines = ["Deadly Assault"]

    if not assault.has_data:
        lines.append("  No Deadly Assault data for this season.")
        return lines

    lines.append(f"  Score: {assault.total_score:,}")
    lines.append(f"  Stars: {assault.total_star}")
    if assault.rank_percent:
        lines.append(f"  Rank: top {assault.rank_percent}%")

    if assault.challenges:
        lines.append("")
        for challenge in assault.challenges:
            boss = challenge.boss.name if challenge.boss is not None else "Unknown"
            lines.append(
                f"  {boss}: {challenge.score:,} "
                f"({challenge.star}/{challenge.total_star})"
            )

    return lines


def _render_shiyu(shiyu: Any) -> list[str]:
    lines = ["Shiyu Defense"]

    if hasattr(shiyu, "brief_info"):
        lines.append(
            "  Fifth floor: "
            + ("cleared" if shiyu.passed_fifth_floor else "not cleared")
        )
        brief = shiyu.brief_info
        if brief is not None:
            lines.append(f"  Score: {brief.score:,}/{brief.max_score:,}")
            if brief.rating:
                lines.append(f"  Rating: {brief.rating}")
            if brief.rank_percent:
                lines.append(f"  Rank: top {brief.rank_percent}")
            if brief.total_clear_time:
                lines.append(f"  Clear time: {format_duration(brief.total_clear_time)}")
        return lines

    if not shiyu.has_data:
        lines.append("  No data this season.")
        return lines

    lines.append(f"  Max floor: {shiyu.max_floor}")
    if shiyu.fastest_clear_time:
        lines.append(f"  Fastest clear: {format_duration(shiyu.fastest_clear_time)}")
    ratings = ", ".join(f"{rank} x{count}" for rank, count in shiyu.ratings.items())
    if ratings:
        lines.append(f"  Ratings: {ratings}")

    return lines


def _render_annihilation(data: Any) -> list[str]:
    lines = ["Annihilation Simulacrum"]

    if not data.unlocked:
        lines.append("  Not unlocked yet.")
        return lines
    if not data.challenges:
        lines.append("  No clears this season.")
        return lines

    for challenge in data.challenges:
        duration = challenge.duration.total_seconds()
        lines.append(
            f"  {challenge.boss.name}: rank {challenge.rank}, "
            f"{challenge.star} stars, {format_duration(duration)}"
        )

    return lines


def _render_lost_void(data: Any) -> list[str]:
    lines = ["Lost Void"]

    if not data.unlocked:
        lines.append("  Not unlocked yet.")
        return lines

    license_info = data.license
    lines.append(f"  License: {license_info.cur_level}/{license_info.max_level}")

    exploration = data.exploration_log
    lines.append(f"  Exploration log: {exploration.current}/{exploration.total}")

    commission = data.commission_progress
    lines.append(f"  Commission: {commission.current}/{commission.total}")

    ultimate = data.ultimate_challenge
    if ultimate.has_data:
        lines.append(
            f"  Ultimate: {ultimate.highest_difficulty}, {ultimate.total_clears} clears"
        )
        if ultimate.shortest_clear_time:
            lines.append(
                "  Shortest clear: "
                f"{format_duration(ultimate.shortest_clear_time.total_seconds())}"
            )

    if data.data_collected:
        collected = ", ".join(
            f"{_enum_label(item.type)} {item.collected}/{item.total}"
            for item in data.data_collected
        )
        lines.append(f"  Data collected: {collected}")

    if data.time_remaining:
        lines.append(
            f"  Refresh in: {format_duration(data.time_remaining.total_seconds())}"
        )

    return lines


def event_summaries(
    events: Sequence[Any], *, within_days: int | None = None
) -> list[EventSummary]:
    """Active events, optionally limited to those ending within ``within_days``."""
    cutoff = within_days * 86400 if within_days is not None else None
    summaries: list[EventSummary] = []

    for event in events:
        seconds = float(event.seconds_until_end or 0)
        if seconds <= 0:
            continue
        if cutoff is not None and seconds > cutoff:
            continue
        summaries.append(EventSummary(event.name, seconds))

    summaries.sort(key=lambda item: item.seconds_remaining)
    return summaries


def render_events(account: GameAccountDocument, events: Sequence[Any]) -> str:
    lines = [_header(account, "Zenless Zone Zero events"), ""]

    summaries = event_summaries(events)
    if not summaries:
        lines.append("No active events right now.")
        return "\n".join(lines)

    for summary in summaries[:15]:
        lines.append(
            f"  {summary.name} - ends in {format_duration(summary.seconds_remaining)}"
        )

    return truncate("\n".join(lines), 3900)


def render_checkin(account: GameAccountDocument, reward: Any, info: Any) -> str:
    return _render_checkin(account, "Zenless Zone Zero", reward, info)


def _enum_label(value: Any) -> str:
    name = getattr(value, "name", None)
    return name.replace("_", " ").title() if name else str(value)
