"""Plain-text rendering for Genshin Impact."""

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


def _duration(seconds: float) -> str:
    return format_duration(seconds) if seconds > 0 else "ready"


def render_notes(account: GameAccountDocument, notes: Any) -> str:
    lines = [_header(account, "Genshin Impact"), ""]

    resin = f"Resin: {notes.current_resin}/{notes.max_resin}"
    if notes.current_resin < notes.max_resin:
        recovery = _duration(notes.remaining_resin_recovery_time.total_seconds())
        resin += f" (full in {recovery})"
    lines.append(resin)

    if notes.max_realm_currency:
        realm = (
            f"Realm currency: {notes.current_realm_currency}/{notes.max_realm_currency}"
        )
        if notes.current_realm_currency < notes.max_realm_currency:
            realm += (
                " (full in "
                f"{_duration(notes.remaining_realm_currency_recovery_time.total_seconds())})"
            )
        lines.append(realm)

    commissions = f"Commissions: {notes.completed_commissions}/{notes.max_commissions}"
    if not notes.claimed_commission_reward:
        commissions += " (reward unclaimed)"
    lines.append(commissions)

    if notes.max_resin_discounts:
        lines.append(
            "Weekly boss discounts: "
            f"{notes.remaining_resin_discounts}/{notes.max_resin_discounts} remaining"
        )

    transformer = notes.remaining_transformer_recovery_time
    if transformer is not None and transformer.total_seconds() > 0:
        lines.append(
            f"Parametric transformer: ready in {_duration(transformer.total_seconds())}"
        )

    if notes.max_expeditions:
        lines.append(f"Expeditions: {len(notes.expeditions)}/{notes.max_expeditions}")

    return "\n".join(lines)


def render_characters(account: GameAccountDocument, characters: Sequence[Any]) -> str:
    lines = [_header(account, "Genshin Impact"), ""]

    if not characters:
        lines.append("No characters were returned.")
        return "\n".join(lines)

    for rarity in (5, 4):
        group = [character for character in characters if character.rarity == rarity]
        if not group:
            continue

        lines.append(f"{rarity}-star ({len(group)})")
        for character in sorted(group, key=lambda item: (-item.level, item.name)):
            details = (
                f"  {character.name} - Lv. {character.level}, "
                f"C{character.constellation}, Friendship {character.friendship}"
            )
            weapon = character.weapon
            if weapon is not None:
                details += f", {weapon.name} R{weapon.refinement}"
            lines.append(details)
        lines.append("")

    return truncate("\n".join(lines).strip(), 3900)


def render_diary(account: GameAccountDocument, diary: Any) -> str:
    data = diary.data
    month = _month_name(diary.month)

    lines = [
        _header(account, f"Genshin Impact diary - {month}"),
        "",
        f"Primogems: {data.current_primogems:,} "
        f"(previous month {data.last_primogems:,}, {data.primogems_rate:+d}%)",
        f"Mora: {data.current_mora:,} "
        f"(previous month {data.last_mora:,}, {data.mora_rate:+d}%)",
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
    abyss: Any | None,
    theater: Any = _UNSET,
    stygian: Any = _UNSET,
) -> str:
    lines = [_header(account, "Genshin Impact endgame"), ""]

    if abyss is None:
        lines.append("Spiral Abyss: data is not public.")
    else:
        lines.extend(_render_abyss(abyss))

    if theater is not _UNSET:
        lines.append("")
        if theater is None:
            lines.append("Imaginarium Theater: data is not public.")
        else:
            lines.extend(_render_theater(theater))

    if stygian is not _UNSET:
        lines.append("")
        if stygian is None:
            lines.append("Stygian Onslaught: data is not public.")
        else:
            lines.extend(_render_stygian(stygian))

    return truncate("\n".join(lines), 3900)


def _render_abyss(abyss: Any) -> list[str]:
    lines = [f"Spiral Abyss - {abyss.season}"]

    if not abyss.unlocked:
        lines.append("  Spiral Abyss is not unlocked on this account yet.")
        return lines

    lines.append(f"  Max floor: {abyss.max_floor}")
    lines.append(f"  Stars: {abyss.total_stars}")
    lines.append(f"  Battles: {abyss.total_battles} ({abyss.total_wins} wins)")

    if abyss.floors:
        lines.append("")
        for floor in abyss.floors:
            lines.append(f"  Floor {floor.floor}: {floor.stars}/{floor.max_stars}")

    return lines


def _render_theater(theater: Any) -> list[str]:
    lines = ["Imaginarium Theater"]

    if not theater.unlocked:
        lines.append("  Not unlocked yet.")
        return lines
    if not theater.datas:
        lines.append("  No season data.")
        return lines

    dated = [
        item
        for item in theater.datas
        if getattr(getattr(item, "schedule", None), "end_datetime", None)
    ]
    data = (
        max(dated, key=lambda item: item.schedule.end_datetime)
        if dated
        else theater.datas[0]
    )

    if not data.has_data:
        lines.append("  No clears this season.")
        return lines

    stats = data.stats
    lines.append(f"  Best act: {stats.best_record}")
    lines.append(f"  Medals: {stats.medal_num}")
    lines.append(f"  Difficulty: {_enum_label(stats.difficulty)}")

    arcana = getattr(stats, "lunar_arcana_completed", 0)
    if arcana:
        lines.append(f"  Lunar Arcana: {arcana} completed")

    end = getattr(getattr(data, "schedule", None), "end_datetime", None)
    if end:
        lines.append(f"  Ends: {end:%Y-%m-%d}")

    return lines


def _render_stygian(seasons: Sequence[Any]) -> list[str]:
    if not seasons:
        return ["Stygian Onslaught", "  No active season."]

    lines: list[str] = []
    for season in seasons[:2]:
        lines.append(f"Stygian Onslaught - {season.season.name}")
        found = False
        for label, data in (
            ("Single", season.single_player),
            ("Multi", season.multi_player),
        ):
            if not data.has_data:
                continue
            found = True
            best = data.best_record
            if best is not None:
                lines.append(
                    f"  {label}: difficulty {best.difficulty}, "
                    f"{format_duration(best.time_used)}"
                )
            else:
                lines.append(f"  {label}: cleared")
        if not found:
            lines.append("  No clears this season.")

    return lines


def event_summaries(
    calendar: Any, *, within_days: int | None = None
) -> list[EventSummary]:
    """Active events, optionally limited to those ending within ``within_days``."""
    cutoff = within_days * 86400 if within_days is not None else None
    summaries: list[EventSummary] = []

    for event in (*calendar.events, *calendar.challenges):
        if event.is_finished:
            continue

        seconds = float(event.countdown_seconds or 0)
        if cutoff is not None and (seconds <= 0 or seconds > cutoff):
            continue

        summaries.append(EventSummary(event.name, seconds))

    summaries.sort(key=lambda item: item.seconds_remaining)
    return summaries


def render_events(account: GameAccountDocument, calendar: Any) -> str:
    lines = [_header(account, "Genshin Impact events"), ""]

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
    return _render_checkin(account, "Genshin Impact", reward, info)


def _month_name(month: int) -> str:
    try:
        return date(2000, month, 1).strftime("%B")
    except ValueError:
        return str(month)


def _enum_label(value: Any) -> str:
    name = getattr(value, "name", None)
    return name.replace("_", " ").title() if name else str(value)
