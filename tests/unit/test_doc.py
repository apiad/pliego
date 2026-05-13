"""IR — Document tree types."""
import pytest
from pydantic import ValidationError

from pliego.config import DocConfig
from pliego.doc import Document, Paragraph, Section, Text


def test_minimal_document():
    cfg = DocConfig.from_frontmatter({"title": "x", "date": "2026-05-13"})
    doc = Document(
        config=cfg,
        children=[
            Section(
                level=1,
                title=[Text(text="Intro")],
                children=[
                    Paragraph(children=[Text(text="Hello.")]),
                ],
            ),
        ],
    )
    assert doc.children[0].level == 1
    assert doc.children[0].title[0].text == "Intro"
    assert doc.children[0].children[0].children[0].text == "Hello."


def test_inline_formatting_types():
    from pliego.doc import Emphasis, InlineCode, Link, Strong, Text
    s = Strong(children=[Text(text="bold")])
    e = Emphasis(children=[Text(text="italic")])
    l = Link(href="https://example.com", children=[Text(text="link")])
    c = InlineCode(text="code")
    assert s.children[0].text == "bold"
    assert e.children[0].text == "italic"
    assert l.href == "https://example.com"
    assert c.text == "code"


def test_section_level_range():
    """Sections must be h1–h6."""
    with pytest.raises(ValidationError):
        Section(level=7, title=[Text(text="x")], children=[])
    with pytest.raises(ValidationError):
        Section(level=0, title=[Text(text="x")], children=[])
