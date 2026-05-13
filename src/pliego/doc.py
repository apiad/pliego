"""Document IR — the contract between parser and renderers.

Plan 2 expansion: Strong/Emphasis/Link/InlineCode for inline formatting;
BulletList/OrderedList/ListItem; BlockQuote; HorizontalRule; CodeBlock.
"""
from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

from .config import DocConfig


# --- Inline -----------------------------------------------------------------


class Text(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["text"] = "text"
    text: str


class Strong(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["strong"] = "strong"
    children: list["Inline"]


class Emphasis(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["emphasis"] = "emphasis"
    children: list["Inline"]


class Link(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["link"] = "link"
    href: str
    children: list["Inline"]


class InlineCode(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["inline_code"] = "inline_code"
    text: str


Inline = Annotated[
    Union[Text, Strong, Emphasis, Link, InlineCode],
    Field(discriminator="kind"),
]


# --- Block ------------------------------------------------------------------


class Paragraph(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["paragraph"] = "paragraph"
    children: list[Inline]


class ListItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["list_item"] = "list_item"
    children: list["Block"]


class BulletList(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["bullet_list"] = "bullet_list"
    items: list[ListItem]


class OrderedList(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["ordered_list"] = "ordered_list"
    items: list[ListItem]
    start: int = 1


class BlockQuote(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["block_quote"] = "block_quote"
    children: list["Block"]


class HorizontalRule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["horizontal_rule"] = "horizontal_rule"


class CodeBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["code_block"] = "code_block"
    text: str
    language: str = ""


Block = Annotated[
    Union[
        "Section",
        Paragraph,
        BulletList,
        OrderedList,
        BlockQuote,
        HorizontalRule,
        CodeBlock,
    ],
    Field(discriminator="kind"),
]


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


Strong.model_rebuild()
Emphasis.model_rebuild()
Link.model_rebuild()
ListItem.model_rebuild()
BulletList.model_rebuild()
OrderedList.model_rebuild()
BlockQuote.model_rebuild()
Section.model_rebuild()
Document.model_rebuild()
