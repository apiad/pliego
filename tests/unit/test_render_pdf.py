"""PDF renderer — IR → bytes."""
import io
import re
from pathlib import Path

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


def test_hyphenate_helper_inserts_soft_hyphens_for_spanish():
    from pliego._hyphen import hyphenate
    out = hyphenate("Esta es una palabra larguísima.", lang="es", min_len=6)
    # Soft hyphen is U+00AD; the long word should have at least one
    assert "­" in out
    # Short words pass through unchanged
    assert "Esta" in out


def test_hyphenate_passthrough_when_lang_unsupported():
    from pliego._hyphen import hyphenate
    out = hyphenate("Just a sentence.", lang="zz")
    assert "­" not in out
    assert out == "Just a sentence."


def test_render_paragraph_with_spanish_uses_hyphenation():
    """End-to-end: rendering long Spanish prose should preserve the source
    text under whitespace + hyphen normalization, regardless of where the
    line breaks happen."""
    cfg = DocConfig.from_frontmatter({
        "title": "x", "date": "2026-05-13", "lang": "es",
    })
    long_es = (
        "La arquitectura del clasificador determinista enruta hacia flujos "
        "especializados, pero escala mal en ancho. " * 4
    )
    doc = Document(config=cfg, children=[
        Section(level=1, title=[Text(text="H")], children=[
            Paragraph(children=[Text(text=long_es)]),
        ]),
    ])
    pdf_bytes = render_pdf(doc)
    reader = pypdf.PdfReader(io.BytesIO(bytes(pdf_bytes)))
    raw = "\n".join(p.extract_text() for p in reader.pages)
    flat = re.sub(r"[-­\s]+", " ", raw).strip()
    assert "clasificador determinista" in flat
    assert "especializados" in flat


def test_render_toc_when_enabled():
    cfg = DocConfig.from_frontmatter({
        "title": "Doc",
        "date": "2026-05-13",
        "lang": "es",
        "pliego": {"toc": True, "toc-depth": 2, "section-numbering": "1.1"},
    })
    h2 = Section(level=2, title=[Text(text="Contexto")], children=[
        Paragraph(children=[Text(text="P.")]),
    ])
    h1 = Section(level=1, title=[Text(text="Introducción")], children=[
        Paragraph(children=[Text(text="P.")]),
        h2,
    ])
    doc = Document(config=cfg, children=[h1])
    pdf_bytes = render_pdf(doc)
    reader = pypdf.PdfReader(io.BytesIO(bytes(pdf_bytes)))
    assert len(reader.pages) >= 3
    full_text = _ws("\n".join(p.extract_text() for p in reader.pages))
    assert "Índice" in full_text
    assert "Introducción" in full_text
    assert "Contexto" in full_text


def test_render_no_toc_by_default():
    cfg = DocConfig.from_frontmatter({"title": "x", "date": "2026-05-13"})
    doc = Document(config=cfg, children=[
        Section(level=1, title=[Text(text="H")], children=[
            Paragraph(children=[Text(text="P.")]),
        ]),
    ])
    pdf_bytes = render_pdf(doc)
    reader = pypdf.PdfReader(io.BytesIO(bytes(pdf_bytes)))
    full_text = _ws("\n".join(p.extract_text() for p in reader.pages))
    assert "Índice" not in full_text
    assert "Contents" not in full_text


def test_render_includes_page_numbers_in_body_not_cover():
    cfg = DocConfig.from_frontmatter({
        "title": "Doc",
        "date": "2026-05-13",
        "lang": "es",
    })
    doc = Document(config=cfg, children=[
        Section(level=1, title=[Text(text="Sección")], children=[
            Paragraph(children=[Text(text="Cuerpo.")]),
        ]),
    ])
    pdf_bytes = render_pdf(doc)
    reader = pypdf.PdfReader(io.BytesIO(bytes(pdf_bytes)))
    page1 = _ws(reader.pages[0].extract_text())
    page2 = _ws(reader.pages[1].extract_text())
    assert "Página" not in page1
    assert "Página 2" in page2


def test_render_figure():
    from pliego.doc import Figure
    cfg = DocConfig.from_frontmatter({"title": "x", "date": "2026-05-13"})
    img_src = str(Path(__file__).parent / "fixtures" / "sample.png")
    doc = Document(config=cfg, children=[
        Section(level=1, title=[Text(text="H")], children=[
            Figure(src=img_src, alt="Sample image"),
        ]),
    ])
    pdf_bytes = render_pdf(doc)
    reader = pypdf.PdfReader(io.BytesIO(bytes(pdf_bytes)))
    text = _ws("\n".join(p.extract_text() for p in reader.pages))
    assert "Sample image" in text


def test_render_table():
    from pliego.config import DocConfig
    from pliego.doc import (
        Document, Paragraph, Section, Table, TableCell, TableRow, Text,
    )
    cfg = DocConfig.from_frontmatter({"title": "x", "date": "2026-05-13"})
    table = Table(
        header=TableRow(cells=[
            TableCell(children=[Text(text="Columna A")]),
            TableCell(children=[Text(text="Columna B")]),
        ]),
        body=[
            TableRow(cells=[
                TableCell(children=[Text(text="uno")]),
                TableCell(children=[Text(text="dos")]),
            ]),
            TableRow(cells=[
                TableCell(children=[Text(text="tres")]),
                TableCell(children=[Text(text="cuatro")]),
            ]),
        ],
    )
    doc = Document(config=cfg, children=[
        Section(level=1, title=[Text(text="H")], children=[table]),
    ])
    pdf_bytes = render_pdf(doc)
    reader = pypdf.PdfReader(io.BytesIO(bytes(pdf_bytes)))
    text = _ws("\n".join(p.extract_text() for p in reader.pages))
    assert "Columna A" in text
    assert "uno" in text
    assert "cuatro" in text


def test_render_code_block():
    from pliego.config import DocConfig
    from pliego.doc import (
        CodeBlock, Document, Section, Text,
    )
    cfg = DocConfig.from_frontmatter({"title": "x", "date": "2026-05-13"})
    doc = Document(config=cfg, children=[
        Section(level=1, title=[Text(text="H")], children=[
            CodeBlock(text="def hello():\n    return 42\n", language="python"),
        ]),
    ])
    pdf_bytes = render_pdf(doc)
    reader = pypdf.PdfReader(io.BytesIO(bytes(pdf_bytes)))
    text = _ws("\n".join(p.extract_text() for p in reader.pages))
    assert "def hello():" in text
    assert "return 42" in text


def test_render_horizontal_rule_does_not_crash():
    from pliego.config import DocConfig
    from pliego.doc import (
        Document, HorizontalRule, Paragraph, Section, Text,
    )
    cfg = DocConfig.from_frontmatter({"title": "x", "date": "2026-05-13"})
    doc = Document(config=cfg, children=[
        Section(level=1, title=[Text(text="H")], children=[
            Paragraph(children=[Text(text="Antes.")]),
            HorizontalRule(),
            Paragraph(children=[Text(text="Después.")]),
        ]),
    ])
    pdf_bytes = render_pdf(doc)
    reader = pypdf.PdfReader(io.BytesIO(bytes(pdf_bytes)))
    text = _ws("\n".join(p.extract_text() for p in reader.pages))
    assert "Antes." in text
    assert "Después." in text


def test_render_block_quote():
    from pliego.config import DocConfig
    from pliego.doc import (
        BlockQuote, Document, Paragraph, Section, Text,
    )
    cfg = DocConfig.from_frontmatter({"title": "x", "date": "2026-05-13"})
    doc = Document(config=cfg, children=[
        Section(level=1, title=[Text(text="H")], children=[
            BlockQuote(children=[
                Paragraph(children=[Text(text="Quoted prose.")]),
            ]),
        ]),
    ])
    pdf_bytes = render_pdf(doc)
    reader = pypdf.PdfReader(io.BytesIO(bytes(pdf_bytes)))
    text = _ws("\n".join(p.extract_text() for p in reader.pages))
    assert "Quoted prose." in text


def test_render_ordered_list():
    from pliego.config import DocConfig
    from pliego.doc import (
        Document, ListItem, OrderedList, Paragraph, Section, Text,
    )
    cfg = DocConfig.from_frontmatter({"title": "x", "date": "2026-05-13"})
    items = [
        ListItem(children=[Paragraph(children=[Text(text=f"item {i}")])])
        for i in (1, 2, 3)
    ]
    doc = Document(config=cfg, children=[
        Section(level=1, title=[Text(text="H")], children=[
            OrderedList(items=items),
        ]),
    ])
    pdf_bytes = render_pdf(doc)
    reader = pypdf.PdfReader(io.BytesIO(bytes(pdf_bytes)))
    text = _ws("\n".join(p.extract_text() for p in reader.pages))
    assert "1. item 1" in text
    assert "2. item 2" in text
    assert "3. item 3" in text


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
