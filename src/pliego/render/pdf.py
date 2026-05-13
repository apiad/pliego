"""PDF renderer — IR → PDF bytes.

Backend: fpdf2 (chosen via Phase 0 spike). The fpdf2 primitives are wrapped
in ``_FPDFRenderer`` — never import fpdf elsewhere in pliego so a backend
swap stays a one-module change.

v0.1 supports only: cover (title/subtitle/date) + body sections with a
single inline text run per paragraph. Lists, tables, images, ToC, page
numbers, and Spanish hyphenation are plan 2.
"""
from __future__ import annotations

import re
from pathlib import Path

from fpdf import FPDF
from fpdf.enums import XPos, YPos

from ..doc import Document, Paragraph, Section, Text


# ---------------------------------------------------------------------------
# Font discovery
#
# fpdf2 core fonts (helvetica/times/courier) are Latin-1 only. Spanish text
# with em dashes, smart quotes, etc. crashes the core fonts. For v0.1 we
# discover a system Unicode TTF (DejaVu Sans family) at render time. If the
# system has no DejaVu, we fall back to fpdf2's core fonts and warn — the
# render may garble non-ASCII characters.
#
# A future task may bundle DejaVu inside the wheel for cross-platform
# determinism. Right now we depend on the host having it (true on Linux
# with `ttf-dejavu` and most macOS installs).
# ---------------------------------------------------------------------------

_DEJAVU_SEARCH = [
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/Library/Fonts/DejaVuSans.ttf",
    "/usr/local/share/fonts/DejaVuSans.ttf",
]


def _find_dejavu() -> Path | None:
    for p in _DEJAVU_SEARCH:
        if Path(p).is_file():
            return Path(p).parent
    return None


# ---------------------------------------------------------------------------
# Unit parsing
# ---------------------------------------------------------------------------

_UNIT_MM = {"mm": 1.0, "cm": 10.0, "in": 25.4, "pt": 25.4 / 72.0}


def _to_mm(value: str) -> float:
    """'2cm' → 20.0 (mm).  '10pt' → 3.527 (mm)."""
    m = re.fullmatch(r"\s*([0-9.]+)\s*(mm|cm|in|pt)\s*", value)
    if not m:
        raise ValueError(f"Cannot parse length: {value!r}")
    return float(m.group(1)) * _UNIT_MM[m.group(2)]


def _pt(value: str) -> float:
    """'10pt' → 10.0 (points)."""
    m = re.fullmatch(r"\s*([0-9.]+)\s*pt\s*", value)
    if not m:
        raise ValueError(f"Cannot parse pt size: {value!r}")
    return float(m.group(1))


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------


class _FPDFRenderer:
    def __init__(self, doc: Document):
        self.doc = doc
        cfg = doc.config
        self.body_pt = _pt(cfg.pliego.fontsize)
        margin_x = _to_mm(cfg.pliego.margin.x)
        margin_y = _to_mm(cfg.pliego.margin.y)
        papersize = cfg.pliego.papersize.upper()

        self.pdf = FPDF(format=papersize, unit="mm")
        self.pdf.set_margins(left=margin_x, top=margin_y, right=margin_x)
        self.pdf.set_auto_page_break(auto=True, margin=margin_y)
        self._setup_fonts()

    def _setup_fonts(self) -> None:
        font_dir = _find_dejavu()
        if font_dir is not None:
            self.pdf.add_font(
                "body", style="", fname=str(font_dir / "DejaVuSans.ttf")
            )
            self.pdf.add_font(
                "body", style="B", fname=str(font_dir / "DejaVuSans-Bold.ttf")
            )
            self.pdf.add_font(
                "body", style="I", fname=str(font_dir / "DejaVuSans-Oblique.ttf")
            )
            self.body_family = "body"
        else:
            # Fallback: core helvetica. Non-ASCII text may render incorrectly.
            self.body_family = "helvetica"
        self.pdf.set_font(self.body_family, size=self.body_pt)

    def build(self) -> bytes:
        self._render_cover()
        self._render_body()
        return bytes(self.pdf.output())

    # -- Cover -----------------------------------------------------------

    def _render_cover(self) -> None:
        cfg = self.doc.config
        pdf = self.pdf
        pdf.add_page()
        pdf.set_y(pdf.h * 0.33)
        pdf.set_font(self.body_family, style="B", size=self.body_pt * 2.4)
        pdf.multi_cell(
            0, 12, cfg.title,
            new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C",
        )
        if cfg.subtitle:
            pdf.ln(2)
            pdf.set_font(self.body_family, style="I", size=self.body_pt * 1.4)
            pdf.multi_cell(
                0, 8, cfg.subtitle,
                new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C",
            )
        pdf.ln(6)
        pdf.set_font(self.body_family, size=self.body_pt)
        pdf.cell(
            0, 6, cfg.date,
            new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C",
        )

    # -- Body ------------------------------------------------------------

    def _render_body(self) -> None:
        for block in self.doc.children:
            if isinstance(block, Section):
                self._render_section(block)
            else:
                raise NotImplementedError(
                    f"Top-level block {type(block).__name__} not supported in v0.1."
                )

    def _render_section(self, section: Section) -> None:
        pdf = self.pdf
        pdf.add_page()  # v0.1: each top-level section on its own page
        size = self.body_pt * (2.2 - 0.2 * section.level)
        pdf.set_font(self.body_family, style="B", size=size)
        title_text = _flatten_inlines(section.title)
        pdf.multi_cell(
            0, 10, title_text,
            new_x=XPos.LMARGIN, new_y=YPos.NEXT,
        )
        pdf.ln(2)
        pdf.set_font(self.body_family, size=self.body_pt)
        for child in section.children:
            if isinstance(child, Paragraph):
                self._render_paragraph(child)
            elif isinstance(child, Section):
                raise NotImplementedError(
                    "Nested sections not supported in v0.1."
                )
            else:
                raise NotImplementedError(
                    f"Block {type(child).__name__} not supported in v0.1."
                )

    def _render_paragraph(self, para: Paragraph) -> None:
        text = _flatten_inlines(para.children)
        self.pdf.multi_cell(
            0, self.body_pt * 0.45, text,
            new_x=XPos.LMARGIN, new_y=YPos.NEXT,
        )
        self.pdf.ln(self.body_pt * 0.3)


def _flatten_inlines(inlines: list) -> str:
    parts: list[str] = []
    for inline in inlines:
        if isinstance(inline, Text):
            parts.append(inline.text)
        else:
            raise NotImplementedError(
                f"Inline {type(inline).__name__} not supported in v0.1."
            )
    return "".join(parts)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def render_pdf(doc: Document) -> bytes:
    """Render an IR ``Document`` to PDF bytes."""
    return _FPDFRenderer(doc).build()
