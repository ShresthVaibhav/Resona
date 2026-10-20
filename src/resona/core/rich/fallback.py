"""Plain-text fallback for rich message payloads.

The fallback is deliberately approximate: it exists so a rejected rich payload
still produces a readable ``sendMessage`` rather than an error.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Any

from resona.core.rich.models import InputRichMessage

_BLOCK_TAGS = {
    "p",
    "div",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "ul",
    "ol",
    "li",
    "table",
    "tr",
    "td",
    "th",
    "blockquote",
    "pre",
    "details",
    "summary",
    "footer",
    "figcaption",
}

_MARKDOWN_LINK = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
_MARKDOWN_HEADING = re.compile(r"^\s{0,3}#{1,6}\s*", re.MULTILINE)
_MARKDOWN_MARKS = re.compile(r"[*_~`]+")


class _HtmlTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "br":
            self._newline()
        elif tag == "hr":
            self._newline()
            self.parts.append("---")
            self._newline()
        elif tag == "li":
            self._newline()
            self.parts.append("- ")
        elif tag in _BLOCK_TAGS:
            self._newline()

    def handle_endtag(self, tag: str) -> None:
        if tag in _BLOCK_TAGS:
            self._newline()

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def _newline(self) -> None:
        if self.parts and not self.parts[-1].endswith("\n"):
            self.parts.append("\n")


def to_plain_text(payload: InputRichMessage) -> str:
    """Render a rich payload as readable plain text."""
    if payload.html is not None:
        return _html_to_text(payload.html)
    if payload.markdown is not None:
        return _markdown_to_text(payload.markdown)
    return _blocks_to_text(payload.blocks or [])


def _html_to_text(html: str) -> str:
    parser = _HtmlTextExtractor()
    parser.feed(html)
    parser.close()
    return _clean("".join(parser.parts))


def _markdown_to_text(markdown: str) -> str:
    text = _MARKDOWN_LINK.sub(r"\1", markdown)
    text = _MARKDOWN_HEADING.sub("", text)
    text = _MARKDOWN_MARKS.sub("", text)
    return _clean(text)


def _blocks_to_text(blocks: list[Any]) -> str:
    parts: list[str] = []
    for block in blocks:
        data = block.model_dump() if hasattr(block, "model_dump") else block
        if not isinstance(data, dict):
            continue

        kind = data.get("type")
        if kind == "divider":
            parts.append("---")
        elif kind in {"paragraph", "heading", "pre"}:
            parts.append(str(data.get("text", "")))

    return _clean("\n\n".join(parts))


def _clean(text: str) -> str:
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
