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
