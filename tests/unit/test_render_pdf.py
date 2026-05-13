"""PDF renderer — IR → bytes."""
import io

import pypdf

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


def test_render_contains_title_and_body_text():
    pdf_bytes = render_pdf(_make_minimal_doc())
    reader = pypdf.PdfReader(io.BytesIO(bytes(pdf_bytes)))
    full_text = "\n".join(p.extract_text() for p in reader.pages)
    assert "Hola" in full_text
    assert "Introducción" in full_text
    assert "Hola mundo." in full_text
