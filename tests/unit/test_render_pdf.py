"""PDF renderer — IR → bytes."""
import io
import re

import pypdf


def _ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()

from pliego.config import DocConfig
from pliego.doc import Document, Paragraph, Section, Text
from pliego.render.pdf import render_pdf


def _make_minimal_doc() -> Document:
    cfg = DocConfig.from_frontmatter({
        "title": "Hola",
        "subtitle": "Versión de prueba",
        "date": "2026-05-13",
        "lang": "es",
    })
    return Document(
        config=cfg,
        children=[
            Section(
                level=1,
                title=[Text(text="Introducción")],
                children=[Paragraph(children=[Text(text="Hola mundo.")])],
            ),
        ],
    )


def test_render_returns_bytes():
    pdf_bytes = render_pdf(_make_minimal_doc())
    assert isinstance(pdf_bytes, (bytes, bytearray))
    assert bytes(pdf_bytes).startswith(b"%PDF-")


def test_render_has_two_pages():
    """Cover page + at least one body page."""
    pdf_bytes = render_pdf(_make_minimal_doc())
    reader = pypdf.PdfReader(io.BytesIO(bytes(pdf_bytes)))
    assert len(reader.pages) >= 2


def test_render_bulleted_list():
    from pliego.config import DocConfig
    from pliego.doc import (
        BulletList, Document, ListItem, Paragraph, Section, Text,
    )
    cfg = DocConfig.from_frontmatter({"title": "x", "date": "2026-05-13"})
    items = [
        ListItem(children=[Paragraph(children=[Text(text=f"item {i}")])])
        for i in (1, 2, 3)
    ]
    doc = Document(config=cfg, children=[
        Section(level=1, title=[Text(text="H")], children=[
            BulletList(items=items),
        ]),
    ])
    pdf_bytes = render_pdf(doc)
    reader = pypdf.PdfReader(io.BytesIO(bytes(pdf_bytes)))
    text = _ws("\n".join(p.extract_text() for p in reader.pages))
    assert "item 1" in text
    assert "item 2" in text
    assert "item 3" in text


def test_section_numbering_arabic_arabic_alpha():
    from pliego.config import DocConfig
    from pliego.doc import Document, Paragraph, Section, Text
    cfg = DocConfig.from_frontmatter({
        "title": "x",
        "date": "2026-05-13",
        "pliego": {"section-numbering": "1.1.a"},
    })
    h3 = Section(level=3, title=[Text(text="Sub")], children=[
        Paragraph(children=[Text(text="P.")]),
    ])
    h2 = Section(level=2, title=[Text(text="Inner")], children=[h3])
    h1 = Section(level=1, title=[Text(text="Outer")], children=[h2])
    doc = Document(config=cfg, children=[h1])
    pdf_bytes = render_pdf(doc)
    reader = pypdf.PdfReader(io.BytesIO(bytes(pdf_bytes)))
    text = _ws("\n".join(p.extract_text() for p in reader.pages))
    assert "1. Outer" in text
    assert "1.1. Inner" in text
    assert "1.1.a. Sub" in text


def test_section_numbering_disabled_when_empty_format():
    from pliego.config import DocConfig
    from pliego.doc import Document, Paragraph, Section, Text
    cfg = DocConfig.from_frontmatter({
        "title": "x",
        "date": "2026-05-13",
        "pliego": {"section-numbering": ""},
    })
    h1 = Section(level=1, title=[Text(text="Plain")], children=[
        Paragraph(children=[Text(text="P.")]),
    ])
    doc = Document(config=cfg, children=[h1])
    pdf_bytes = render_pdf(doc)
    reader = pypdf.PdfReader(io.BytesIO(bytes(pdf_bytes)))
    text = _ws("\n".join(p.extract_text() for p in reader.pages))
    assert "Plain" in text
    assert "1. Plain" not in text


def test_render_nested_sections_no_extra_page_breaks():
    """Only h1 starts a new page; h2/h3 flow inline."""
    from pliego.config import DocConfig
    from pliego.doc import Document, Paragraph, Section, Text
    cfg = DocConfig.from_frontmatter({"title": "x", "date": "2026-05-13"})
    h2 = Section(level=2, title=[Text(text="H2")], children=[
        Paragraph(children=[Text(text="P2.")]),
    ])
    h1 = Section(level=1, title=[Text(text="H1")], children=[
        Paragraph(children=[Text(text="P1.")]),
        h2,
    ])
    doc = Document(config=cfg, children=[h1])
    pdf_bytes = render_pdf(doc)
    reader = pypdf.PdfReader(io.BytesIO(bytes(pdf_bytes)))
    # Cover + h1 page (h2 flows on same page) = 2 pages
    assert len(reader.pages) == 2
    text = _ws("\n".join(p.extract_text() for p in reader.pages))
    assert "H1" in text and "H2" in text and "P1." in text and "P2." in text


def test_render_inline_formatting():
    from pliego.config import DocConfig
    from pliego.doc import (
        Document, Emphasis, InlineCode, Link, Paragraph, Section, Strong, Text,
    )
    cfg = DocConfig.from_frontmatter({"title": "x", "date": "2026-05-13"})
    doc = Document(config=cfg, children=[
        Section(level=1, title=[Text(text="H")], children=[
            Paragraph(children=[
                Text(text="Plain "),
                Strong(children=[Text(text="bold")]),
                Text(text=" "),
                Emphasis(children=[Text(text="italic")]),
                Text(text=" "),
                Link(href="https://x.test", children=[Text(text="link")]),
                Text(text=" "),
                InlineCode(text="code"),
                Text(text="."),
            ]),
        ]),
    ])
    pdf_bytes = render_pdf(doc)
    reader = pypdf.PdfReader(io.BytesIO(bytes(pdf_bytes)))
    text = _ws("\n".join(p.extract_text() for p in reader.pages))
    assert "Plain" in text
    assert "bold" in text
    assert "italic" in text
    assert "link" in text
    assert "code" in text


def test_render_contains_title_and_body_text():
    pdf_bytes = render_pdf(_make_minimal_doc())
    reader = pypdf.PdfReader(io.BytesIO(bytes(pdf_bytes)))
    full_text = _ws("\n".join(p.extract_text() for p in reader.pages))
    assert "Hola" in full_text
    assert "Introducción" in full_text
    assert "Hola mundo." in full_text
