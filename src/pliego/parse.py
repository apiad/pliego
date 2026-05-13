"""Markdown source → IR. Built on markdown-it-py token streams."""
from __future__ import annotations

import yaml
from markdown_it import MarkdownIt
from mdit_py_plugins.front_matter import front_matter_plugin

from .config import DocConfig
from .doc import Document, Paragraph, Section, Text


def _make_parser() -> MarkdownIt:
    md = MarkdownIt("commonmark", {"breaks": False, "html": False})
    md.use(front_matter_plugin)
    return md


def parse(source: str) -> Document:
    """Parse Markdown source (with required frontmatter) into a Document IR.

    v0.1 supports only: frontmatter, h1 sections, paragraphs of plain text.
    Anything else raises a ``NotImplementedError`` pointing at the roadmap.
    """
    md = _make_parser()
    tokens = md.parse(source)

    if not tokens or tokens[0].type != "front_matter":
        raise ValueError("pliego requires YAML frontmatter (title + date).")

    frontmatter_raw = tokens[0].content
    frontmatter = yaml.safe_load(frontmatter_raw) or {}
    config = DocConfig.from_frontmatter(frontmatter)

    body_tokens = tokens[1:]
    children = _parse_blocks(body_tokens)
    return Document(config=config, children=children)


def _parse_blocks(tokens: list) -> list:
    """Walk top-level tokens into Sections (each heading opens a Section)
    and Paragraphs attached to the current section.

    v0.1: paragraphs must appear inside a heading; top-level paragraphs
    raise NotImplementedError.
    """
    blocks: list = []
    i = 0
    current_section: Section | None = None
    while i < len(tokens):
        t = tokens[i]
        if t.type == "heading_open":
            level = int(t.tag[1])  # 'h1' → 1
            inline_token = tokens[i + 1]
            title_inlines = _parse_inline(inline_token)
            i += 3  # heading_open, inline, heading_close
            current_section = Section(
                level=level, title=title_inlines, children=[]
            )
            blocks.append(current_section)
            continue
        if t.type == "paragraph_open":
            inline_token = tokens[i + 1]
            children = _parse_inline(inline_token)
            para = Paragraph(children=children)
            if current_section is None:
                raise NotImplementedError(
                    "Paragraphs outside a heading are not supported in v0.1."
                )
            current_section.children.append(para)
            i += 3  # paragraph_open, inline, paragraph_close
            continue
        raise NotImplementedError(
            f"Markdown construct '{t.type}' is not supported in pliego v0.1. "
            "See the roadmap in the design doc "
            "(2026-05-13-pliego-design.md)."
        )
    return blocks


def _parse_inline(inline_token) -> list[Text]:
    """v0.1: inline content is a single text run. Inline formatting
    (bold, italic, links, code) is plan 2.
    """
    parts: list[str] = []
    for child in inline_token.children or []:
        if child.type == "text":
            parts.append(child.content)
        else:
            raise NotImplementedError(
                f"Inline construct '{child.type}' is not supported in pliego v0.1."
            )
    return [Text(text="".join(parts))]
