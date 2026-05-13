"""Document IR — the contract between parser and renderers.

Minimal for v0.1: Document, Section, Paragraph, Text. Feature expansion
(lists, tables, images, inline formatting) lives in plan 2.
"""
from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

from .config import DocConfig


class Text(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["text"] = "text"
    text: str


# Future: Strong, Emphasis, Link, InlineCode — added in plan 2.
Inline = Annotated[Text, Field(discriminator="kind")]


class Paragraph(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["paragraph"] = "paragraph"
    children: list[Inline]


# Forward-ref the Section type so the union can name it.
Block = Annotated[Union["Section", Paragraph], Field(discriminator="kind")]


class Section(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["section"] = "section"
    level: int = Field(ge=1, le=6)
    title: list[Inline]
    children: list[Block]


class Document(BaseModel):
    model_config = ConfigDict(extra="forbid")
    config: DocConfig
    children: list[Block]


Section.model_rebuild()
Document.model_rebuild()
