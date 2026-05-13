"""Parser — markdown source → IR."""
from textwrap import dedent

import pytest

from pliego.doc import Document, Paragraph, Section, Text
from pliego.parse import parse


def test_parses_frontmatter_and_h1_and_paragraph():
    src = dedent("""\
        ---
        title: Hola
        date: 2026-05-13
        lang: es
        ---

        # Introducción

        Este es un párrafo.
    """)
    doc = parse(src)
    assert doc.config.title == "Hola"
    assert doc.config.lang == "es"
    assert len(doc.children) == 1
    section = doc.children[0]
    assert isinstance(section, Section)
    assert section.level == 1
    assert section.title[0].text == "Introducción"
    assert len(section.children) == 1
    para = section.children[0]
    assert isinstance(para, Paragraph)
    assert para.children[0].text == "Este es un párrafo."


def test_rejects_input_without_frontmatter():
    """v0.1: frontmatter is required (title + date)."""
    with pytest.raises(ValueError, match="frontmatter"):
        parse("# Just a heading\n\nNo frontmatter.\n")
