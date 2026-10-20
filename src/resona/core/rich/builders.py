"""Pure builders for the rich messages Resona sends.

Each builder returns :class:`RichContent`; ``payload`` is sent when rich
messages are available and ``fallback_text`` is sent verbatim otherwise.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from html import escape

from resona.core.rich.models import InputRichMessage, RichContent

_PROFILE_FOOTER = (
    "Use /accounts to manage linked accounts and /settings to change preferences."
)


@dataclass(frozen=True, slots=True)
class AccountEntry:
    """One linked game account shown by ``/accounts``."""

    name: str
    uid: str
    server: str | None = None
    is_primary: bool = False


@dataclass(frozen=True, slots=True)
class CommandEntry:
    """One registered command shown by ``/help``."""

    name: str
    description: str
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class EventDigestSection:
    """One game section in an event digest card."""

    label: str
    name: str
    events: tuple[tuple[str, str], ...]


def profile_summary(
    *,
    name: str,
    telegram_id: int,
    member_since: str,
    linked_accounts: int,
    locale: str,
    timezone: str,
    default_game: str,
    notifications: bool,
    event_digest: bool = False,
    username: str | None = None,
) -> RichContent:
    """Build the ``/profile`` card."""
    handle = f" (@{username})" if username else ""
    html_handle = f" (@{escape(username)})" if username else ""
    state = "on" if notifications else "off"
    digest_state = "on" if event_digest else "off"

    html = f"""<h1>Profile</h1>
<p><b>Name:</b> {escape(name)}{html_handle}</p>
<p><b>Telegram ID:</b> <code>{telegram_id}</code></p>
<p><b>Member since:</b> {escape(member_since)}</p>
<p><b>Linked accounts:</b> {linked_accounts}</p>
<h2>Preferences</h2>
<ul>
<li><b>Language:</b> {escape(locale)}</li>
<li><b>Timezone:</b> {escape(timezone)}</li>
<li><b>Default game:</b> {escape(default_game)}</li>
<li><b>Notifications:</b> {state}</li>
<li><b>Event digest:</b> {digest_state}</li>
</ul>
<footer>{_PROFILE_FOOTER}</footer>"""

    fallback = "\n".join(
        [
            "Profile",
            "",
            f"Name: {name}{handle}",
            f"Telegram ID: {telegram_id}",
            f"Member since: {member_since}",
            f"Linked accounts: {linked_accounts}",
            "",
            f"Language: {locale}",
            f"Timezone: {timezone}",
            f"Default game: {default_game}",
            f"Notifications: {state}",
            f"Event digest: {digest_state}",
            "",
            _PROFILE_FOOTER,
        ]
    )

    return _content(html, fallback)


def event_digest_summary(
    sections: Sequence[EventDigestSection],
    *,
    days: int,
    fallback_text: str,
    errors: Sequence[str] = (),
) -> RichContent | None:
    """Build the opt-in event digest card."""
    active = [section for section in sections if section.events]
    if not active:
        return None

    unit = "day" if days == 1 else "days"
    html_parts = [f"<h1>Events ending in the next {days} {unit}</h1>"]

    for section in active:
        html_parts.append(f"<h2>{escape(section.label)} - {escape(section.name)}</h2>")
        html_parts.append("<ul>")
        for name, remaining in section.events:
            html_parts.append(
                f"<li><b>{escape(name)}:</b> ends in {escape(remaining)}</li>"
            )
        html_parts.append("</ul>")

    if errors:
        html_parts.append(
            f"<p><b>Could not refresh:</b> {escape('; '.join(errors))}</p>"
        )

    html_parts.append("<footer>Turn this off with /settings event_digest off.</footer>")
    return _content("\n".join(html_parts), fallback_text)


def account_overview(
    sections: Sequence[tuple[str, Sequence[AccountEntry]]],
) -> RichContent:
    """Build the ``/accounts`` overview from game groups."""
    html_parts = ["<h1>Linked accounts</h1>"]
    fallback_parts = ["Linked accounts", ""]

    for label, entries in sections:
        if not entries:
            continue

        html_parts.append(f"<h2>{escape(label)}</h2>")
        html_parts.append("<ul>")
        fallback_parts.append(label)

        for entry in entries:
            details = f"{entry.name} — UID {entry.uid}"
            if entry.server:
                details += f" ({entry.server})"
            if entry.is_primary:
                details += " [primary]"
            html_parts.append(f"<li>{escape(details)}</li>")
            fallback_parts.append(f"  • {details}")

        html_parts.append("</ul>")
        fallback_parts.append("")

    html_parts.append(
        "<footer>Use /link to add another account or /unlink to remove one.</footer>"
    )
    fallback_parts.append("Use /link to add another account or /unlink to remove one.")

    return _content("\n".join(html_parts), "\n".join(fallback_parts))


def help_page(sections: Sequence[tuple[str, Sequence[CommandEntry]]]) -> RichContent:
    """Build the ``/help`` reference from registry categories."""
    html_parts = ["<h1>Resona commands</h1>"]
    fallback_parts = ["Resona commands", ""]

    for category, entries in sections:
        if not entries:
            continue

        html_parts.append(f"<h2>{escape(category)}</h2>")
        html_parts.append("<ul>")
        fallback_parts.append(category)

        for entry in entries:
            aliases = ""
            if entry.aliases:
                rendered = ", ".join(f"/{alias}" for alias in entry.aliases)
                aliases = f" (also {rendered})"
            html_parts.append(
                f"<li><b>/{escape(entry.name)}</b> — "
                f"{escape(entry.description)}{escape(aliases)}</li>"
            )
            fallback_parts.append(f"/{entry.name}{aliases} - {entry.description}")

        html_parts.append("</ul>")
        fallback_parts.append("")

    return _content("\n".join(html_parts), "\n".join(fallback_parts).strip())


def _content(html: str, fallback: str) -> RichContent:
    return RichContent(
        payload=InputRichMessage(html=html.strip()),
        fallback_text=fallback.strip(),
    )
