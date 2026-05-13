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
