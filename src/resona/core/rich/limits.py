"""Limits published for Bot API rich messages.

Source: https://core.telegram.org/bots/api/rich-messages (rich message limits).
"""

from __future__ import annotations

from typing import Any

from resona.core.rich.models import InputRichMessage

MAX_CHARACTERS = 32_768
MAX_BLOCKS = 500
MAX_NESTING = 16
MAX_MEDIA = 50
MAX_TABLE_COLUMNS = 20


class RichMessageError(Exception):
    """Base class for rich-message problems."""


class RichMessageTooLarge(RichMessageError):
    """The payload exceeds a documented Bot API limit."""


class RichMessageUnsupported(RichMessageError):
    """The running python-telegram-bot build cannot call the rich endpoints."""


def validate_payload(payload: InputRichMessage) -> InputRichMessage:
    """Raise :class:`RichMessageTooLarge` when a documented limit is exceeded."""
    text = payload.html if payload.html is not None else payload.markdown
    if text is not None and len(text) > MAX_CHARACTERS:
        raise RichMessageTooLarge(
            f"rich message text is {len(text)} characters; limit is {MAX_CHARACTERS}"
        )

    if payload.blocks is not None:
        blocks, depth = _measure(payload.blocks)
        if blocks > MAX_BLOCKS:
            raise RichMessageTooLarge(
                f"rich message has {blocks} blocks; limit is {MAX_BLOCKS}"
            )
        if depth > MAX_NESTING:
            raise RichMessageTooLarge(
                f"rich message nests {depth} levels; limit is {MAX_NESTING}"
            )

    return payload


def _measure(blocks: list[Any], depth: int = 1) -> tuple[int, int]:
    """Count blocks and the deepest nesting level in a block tree."""
    count = 0
    deepest = depth

    for block in blocks:
        count += 1
        data = block.model_dump() if hasattr(block, "model_dump") else block
        if not isinstance(data, dict):
            continue

        for key in ("blocks", "items", "rows"):
            nested = data.get(key)
            if isinstance(nested, list) and nested:
                nested_count, nested_depth = _measure(nested, depth + 1)
                count += nested_count
                deepest = max(deepest, nested_depth)

    return count, deepest
