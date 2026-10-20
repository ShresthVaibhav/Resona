"""Plain-text fallback rendering for rich payloads."""

from __future__ import annotations

from resona.core.rich import (
    DividerBlock,
    HeadingBlock,
    InputRichMessage,
    ParagraphBlock,
    to_plain_text,
)


def test_html_fallback_keeps_structure_and_decodes_entities() -> None:
    payload = InputRichMessage(
        html=(
            "<h1>Profile</h1>"
            "<p><b>Name:</b> A &amp; B</p>"
            "<ul><li>One</li><li>Two</li></ul>"
            "<hr/>"
            "<footer>End</footer>"
        )
    )

    text = to_plain_text(payload)

    assert "Profile" in text
    assert "A & B" in text
    assert "- One" in text
    assert "- Two" in text
    assert "---" in text
    assert "End" in text
    assert "<" not in text


def test_markdown_fallback_strips_marks_and_links() -> None:
    payload = InputRichMessage(
        markdown="# Title\n**bold** and [link](https://example.com)"
    )

    text = to_plain_text(payload)

    assert text == "Title\nbold and link"


def test_blocks_fallback_renders_each_block() -> None:
    payload = InputRichMessage(
        blocks=[
            HeadingBlock(text="Title", size=1),
            ParagraphBlock(text="Body"),
            DividerBlock(),
        ]
    )

    assert to_plain_text(payload) == "Title\n\nBody\n\n---"
