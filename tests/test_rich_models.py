"""Validation of typed rich-message payloads."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from resona.core.rich import (
    DividerBlock,
    HeadingBlock,
    InputRichMessage,
    ParagraphBlock,
    PreformattedBlock,
    RichContent,
)


def test_input_rich_message_accepts_html() -> None:
    message = InputRichMessage(html="<b>Hi</b>")

    assert message.html == "<b>Hi</b>"
    assert message.markdown is None
    assert message.blocks is None


def test_input_rich_message_requires_exactly_one_content_field() -> None:
    with pytest.raises(ValidationError, match="exactly one"):
        InputRichMessage()

    with pytest.raises(ValidationError, match="exactly one"):
        InputRichMessage(html="<b>Hi</b>", markdown="**Hi**")


def test_blocks_use_the_type_discriminator() -> None:
    message = InputRichMessage(
        blocks=[
            {"type": "heading", "text": "Title", "size": 1},
            {"type": "paragraph", "text": "Body"},
            {"type": "pre", "text": "print(1)", "language": "python"},
            {"type": "divider"},
        ]
    )

    assert isinstance(message.blocks[0], HeadingBlock)
    assert isinstance(message.blocks[1], ParagraphBlock)
    assert isinstance(message.blocks[2], PreformattedBlock)
    assert isinstance(message.blocks[3], DividerBlock)
    assert message.blocks[0].model_dump() == {
        "type": "heading",
        "text": "Title",
        "size": 1,
    }
    assert message.blocks[3].model_dump() == {"type": "divider"}


def test_heading_size_is_bounded() -> None:
    with pytest.raises(ValidationError):
        HeadingBlock(text="Title", size=7)


def test_rich_content_keeps_payload_and_fallback_together() -> None:
    content = RichContent(InputRichMessage(html="<b>Hi</b>"), "Hi")

    assert content.payload.html == "<b>Hi</b>"
    assert content.fallback_text == "Hi"
