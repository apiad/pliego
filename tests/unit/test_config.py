"""DocConfig — frontmatter → typed config."""
import pytest
from pydantic import ValidationError

from pliego.config import DocConfig


def test_parses_minimal_frontmatter():
    cfg = DocConfig.from_frontmatter({
        "title": "Hola",
        "date": "2026-05-13",
    })
    assert cfg.title == "Hola"
    assert cfg.subtitle is None
    assert cfg.date == "2026-05-13"
    assert cfg.lang == "en"
    assert cfg.pliego.papersize == "a4"


def test_parses_full_frontmatter():
    cfg = DocConfig.from_frontmatter({
        "title": "Reporte",
        "subtitle": "Versión 1",
        "date": "2026-05-13",
        "lang": "es",
        "pliego": {
            "papersize": "a4",
            "margin": {"x": "2cm", "y": "2cm"},
            "fontsize": "10pt",
            "toc": True,
            "toc-depth": 2,
            "section-numbering": "1.1.a",
        },
    })
    assert cfg.lang == "es"
    assert cfg.pliego.fontsize == "10pt"
    assert cfg.pliego.toc is True
    assert cfg.pliego.toc_depth == 2
    assert cfg.pliego.section_numbering == "1.1.a"


def test_unknown_pliego_key_rejected():
    with pytest.raises(ValidationError):
        DocConfig.from_frontmatter({
            "title": "x",
            "date": "2026-05-13",
            "pliego": {"papersize": "a4", "unknown_key": 1},
        })


def test_unknown_top_level_key_passes_through_to_metadata():
    cfg = DocConfig.from_frontmatter({
        "title": "x",
        "date": "2026-05-13",
        "author": "Alex",  # not a pliego key — should land in metadata
    })
    assert cfg.metadata == {"author": "Alex"}
