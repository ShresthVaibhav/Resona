"""Documented rich-message limits are enforced before sending."""

from __future__ import annotations

import pytest

from resona.core.rich import (
    InputRichMessage,
    ParagraphBlock,
    RichMessageTooLarge,
    validate_payload,
)
from resona.core.rich.limits import MAX_BLOCKS, MAX_CHARACTERS


def test_validate_payload_returns_an_acceptable_payload() -> None:
    payload = InputRichMessage(html="<b>Hi</b>")

    assert validate_payload(payload) is payload


def test_text_over_the_character_limit_is_rejected() -> None:
    payload = InputRichMessage(markdown="x" * (MAX_CHARACTERS + 1))

    with pytest.raises(RichMessageTooLarge, match="characters"):
        validate_payload(payload)


def test_too_many_blocks_are_rejected() -> None:
    payload = InputRichMessage(
        blocks=[ParagraphBlock(text="line") for _ in range(MAX_BLOCKS + 1)]
    )

    with pytest.raises(RichMessageTooLarge, match="blocks"):
        validate_payload(payload)
