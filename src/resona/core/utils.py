"""Common utilities."""

from __future__ import annotations

from datetime import UTC, datetime

from resona.config.constants import TELEGRAM_MESSAGE_LIMIT

_MARKDOWN_SPECIAL = r"_*[]()~`>#+-=|{}.!"
_HTML_SPECIAL = {"&": "&amp;", "<": "&lt;", ">": "&gt;"}


def escape_markdown(text: str) -> str:
    """Escape text for Telegram MarkdownV2."""
    return "".join(f"\\{char}" if char in _MARKDOWN_SPECIAL else char for char in text)


def escape_html(text: str) -> str:
    """Escape text for Telegram HTML parse mode."""
    return "".join(_HTML_SPECIAL.get(char, char) for char in text)


def truncate(
    text: str, limit: int = TELEGRAM_MESSAGE_LIMIT, *, suffix: str = "…"
) -> str:
    """Shorten ``text`` to at most ``limit`` characters."""
    if limit <= 0:
        return ""
    if len(text) <= limit:
        return text
    if len(suffix) >= limit:
        return text[:limit]
    return text[: limit - len(suffix)] + suffix


def chunk_text(text: str, limit: int = TELEGRAM_MESSAGE_LIMIT) -> list[str]:
    """Split ``text`` into chunks of at most ``limit`` characters.

    Splitting prefers newline boundaries so messages stay readable.
    """
    if limit <= 0:
        raise ValueError("limit must be positive")

    chunks: list[str] = []
    remaining = text
    while len(remaining) > limit:
        split_at = remaining.rfind("\n", 0, limit)
        if split_at <= 0:
            split_at = limit
        chunks.append(remaining[:split_at])
        remaining = remaining[split_at:].lstrip("\n")
    if remaining:
        chunks.append(remaining)
    return chunks


def format_duration(seconds: float) -> str:
    """Render a duration as a compact human string, e.g. ``2h 5m``."""
    seconds = int(max(0, seconds))
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    parts: list[str] = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds or not parts:
        parts.append(f"{seconds}s")
    return " ".join(parts)


def utcnow() -> datetime:
    """Timezone-aware current UTC time."""
    return datetime.now(UTC)


def safe_int(value: object, default: int | None = None) -> int | None:
    """Parse ``value`` as an int, returning ``default`` when not possible."""
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default
