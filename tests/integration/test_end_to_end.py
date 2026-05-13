"""End-to-end: real .md file → CLI → real .pdf, asserted via pypdf."""
import io
import re
import shutil
from pathlib import Path

import pypdf

from pliego.cli import main


def _normalize_ws(s: str) -> str:
    """fpdf2's justified multi_cell adds inter-word padding that pypdf
    surfaces as multiple spaces. Collapse whitespace for content assertions."""
    return re.sub(r"\s+", " ", s).strip()


FIXTURE = Path(__file__).parent / "fixtures" / "minimal_es.md"
STRUCTURED_FIXTURE = Path(__file__).parent / "fixtures" / "structured_es.md"


def test_renders_minimal_spanish_report(tmp_path: Path):
    src = tmp_path / "report.md"
    shutil.copy(FIXTURE, src)

    rc = main(["render", str(src)])
    assert rc == 0

    pdf_path = tmp_path / "report.pdf"
    assert pdf_path.exists()
    reader = pypdf.PdfReader(io.BytesIO(pdf_path.read_bytes()))
    assert len(reader.pages) >= 2

    full_text = _normalize_ws("\n".join(p.extract_text() for p in reader.pages))
    assert "Reporte de Prueba" in full_text
    assert "Introducción" in full_text
    assert "documento de prueba" in full_text


def test_renders_structured_spanish_document(tmp_path: Path):
    src = tmp_path / "structured.md"
    shutil.copy(STRUCTURED_FIXTURE, src)

    rc = main(["render", str(src)])
    assert rc == 0

    pdf_path = tmp_path / "structured.pdf"
    assert pdf_path.exists()
    reader = pypdf.PdfReader(io.BytesIO(pdf_path.read_bytes()))
    assert len(reader.pages) >= 3  # cover + at least 2 body pages

    full_text = _normalize_ws("\n".join(p.extract_text() for p in reader.pages))

    # Cover
    assert "Documento estructurado" in full_text
    assert "Prueba de pliego v0.2" in full_text
    # Section numbering
    assert "1. Introducción" in full_text
    assert "1.1. Contexto" in full_text
    assert "1.1.a. Sub-sección" in full_text
    assert "2. Listas" in full_text
    assert "3. Otros bloques" in full_text
    # Inline formatting (text flattens regardless of style)
    assert "negritas" in full_text
    assert "cursivas" in full_text
    assert "enlaces" in full_text
    assert "inline code" in full_text
    # Lists
    assert "primer elemento" in full_text
    assert "sub-elemento A" in full_text
    assert "paso uno" in full_text
    # Block quote
    assert "Una cita" in full_text
    # Code block
    assert "def hola" in full_text
    assert "Hola, {nombre}" in full_text
    # Closing line
    assert "Fin del documento" in full_text
