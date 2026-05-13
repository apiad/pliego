"""CLI — `pliego render`."""
from pathlib import Path
from textwrap import dedent

from pliego.cli import main


_MINIMAL_MD = dedent("""\
    ---
    title: Hola
    date: 2026-05-13
    ---

    # Introducción

    Hola mundo.
""")


def test_render_writes_pdf_next_to_source(tmp_path: Path):
    src = tmp_path / "doc.md"
    src.write_text(_MINIMAL_MD)
    rc = main(["render", str(src)])
    assert rc == 0
    out = tmp_path / "doc.pdf"
    assert out.exists()
    assert out.read_bytes().startswith(b"%PDF-")


def test_render_respects_output_flag(tmp_path: Path):
    src = tmp_path / "doc.md"
    src.write_text(_MINIMAL_MD)
    out = tmp_path / "custom.pdf"
    rc = main(["render", str(src), "-o", str(out)])
    assert rc == 0
    assert out.exists()
    assert not (tmp_path / "doc.pdf").exists()


def test_render_returns_nonzero_on_missing_file(tmp_path: Path, capsys):
    rc = main(["render", str(tmp_path / "does-not-exist.md")])
    assert rc != 0
    err = capsys.readouterr().err
    assert "not found" in err.lower() or "no such" in err.lower()
