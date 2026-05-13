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


def test_parses_nested_sections():
    src = dedent("""\
        ---
        title: x
        date: 2026-05-13
        ---

        # H1

        Para 1.

        ## H2

        Para 2.

        ### H3

        Para 3.

        ## H2b

        Para 4.

        # H1b

        Para 5.
    """)
    doc = parse(src)
    # Top level: two h1s
    assert len(doc.children) == 2
    h1, h1b = doc.children
    assert h1.title[0].text == "H1"
    assert h1.level == 1
    assert h1b.title[0].text == "H1b"
    # h1's children: para1, h2, h2b
    assert h1.children[0].kind == "paragraph"
    h2 = h1.children[1]
    assert h2.kind == "section" and h2.level == 2 and h2.title[0].text == "H2"
    # h2's children: para2, h3
    h3 = h2.children[1]
    assert h3.kind == "section" and h3.level == 3 and h3.title[0].text == "H3"
    # h2b is sibling of h2 under h1
    h2b = h1.children[2]
    assert h2b.kind == "section" and h2b.level == 2 and h2b.title[0].text == "H2b"


def test_parses_inline_formatting():
    src = dedent("""\
        ---
        title: x
        date: 2026-05-13
        ---

        # Heading

        Plain **bold** and *italic* with [link](https://example.com) and `code`.
    """)
    doc = parse(src)
    para = doc.children[0].children[0]
    kinds = [type(c).__name__ for c in para.children]
    assert "Strong" in kinds
    assert "Emphasis" in kinds
    assert "Link" in kinds
    assert "InlineCode" in kinds


def test_rejects_input_without_frontmatter():
    """v0.1: frontmatter is required (title + date)."""
    with pytest.raises(ValueError, match="frontmatter"):
        parse("# Just a heading\n\nNo frontmatter.\n")
