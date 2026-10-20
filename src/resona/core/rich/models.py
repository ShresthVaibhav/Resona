"""Typed payloads for Bot API 10.1+ rich messages.

Only the subset Resona sends is modelled. The API accepts exactly one of
``html``, ``markdown`` or ``blocks``; :class:`InputRichMessage` enforces that
rule before anything reaches Telegram.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ParagraphBlock(BaseModel):
    """A text paragraph (``<p>``)."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["paragraph"] = "paragraph"
    text: str


class HeadingBlock(BaseModel):
    """A section heading (``<h1>``-``<h6>``); size 1 is the largest."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["heading"] = "heading"
    text: str
    size: int = Field(default=2, ge=1, le=6)


class PreformattedBlock(BaseModel):
    """A preformatted block, optionally tagged with a language."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["pre"] = "pre"
    text: str
    language: str | None = None


class DividerBlock(BaseModel):
    """A horizontal divider (``<hr/>``)."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["divider"] = "divider"


RichBlock: TypeAlias = Annotated[
    ParagraphBlock | HeadingBlock | PreformattedBlock | DividerBlock,
    Field(discriminator="type"),
]


class InputRichMessage(BaseModel):
    """Describes a rich message to send."""

    model_config = ConfigDict(extra="forbid")

    html: str | None = None
    markdown: str | None = None
    blocks: list[RichBlock] | None = None
    is_rtl: bool | None = None
    skip_entity_detection: bool | None = None

    @model_validator(mode="after")
    def _exactly_one_content_field(self) -> InputRichMessage:
        selected = (
            self.html is not None,
            self.markdown is not None,
            self.blocks is not None,
        )
        if sum(selected) != 1:
            raise ValueError("use exactly one of html, markdown or blocks")
        return self


@dataclass(frozen=True, slots=True)
class RichContent:
    """A validated payload plus the plain-text representation to fall back to."""

    payload: InputRichMessage
    fallback_text: str
