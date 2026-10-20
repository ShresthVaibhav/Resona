"""Isolated compatibility layer for Bot API 10.1+ rich messages."""

from __future__ import annotations

from resona.core.rich.builders import (
    AccountEntry,
    CommandEntry,
    EventDigestSection,
    account_overview,
    event_digest_summary,
    help_page,
    profile_summary,
)
from resona.core.rich.client import (
    edit_rich_message,
    send_rich_message,
    stream_draft,
    supports_rich_messages,
)
from resona.core.rich.fallback import to_plain_text
from resona.core.rich.limits import (
    RichMessageError,
    RichMessageTooLarge,
    RichMessageUnsupported,
    validate_payload,
)
from resona.core.rich.models import (
    DividerBlock,
    HeadingBlock,
    InputRichMessage,
    ParagraphBlock,
    PreformattedBlock,
    RichContent,
)

__all__ = [
    "AccountEntry",
    "CommandEntry",
    "DividerBlock",
    "EventDigestSection",
    "HeadingBlock",
    "InputRichMessage",
    "ParagraphBlock",
    "PreformattedBlock",
    "RichContent",
    "RichMessageError",
    "RichMessageTooLarge",
    "RichMessageUnsupported",
    "account_overview",
    "edit_rich_message",
    "event_digest_summary",
    "help_page",
    "profile_summary",
    "send_rich_message",
    "stream_draft",
    "supports_rich_messages",
    "to_plain_text",
    "validate_payload",
]
