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

from fpdf import FPDF as _BaseFPDF
from fpdf.enums import XPos, YPos


class _PliegoFPDF(_BaseFPDF):
    """FPDF subclass with a localized page-number footer."""

    def __init__(self, *args, page_numbers: bool = True, lang: str = "en",
                 **kwargs):
        super().__init__(*args, **kwargs)
        self._show_page_numbers = page_numbers
        self._footer_lang = lang
        self._footer_family = "helvetica"

    def footer(self) -> None:
        if not self._show_page_numbers or self.page_no() == 1:
            return
        label = "Página" if self._footer_lang.startswith("es") else "Page"
        self.set_y(-12)
        self.set_font(self._footer_family, size=8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 6, f"{label} {self.page_no()}", align="C")
        self.set_text_color(0, 0, 0)

from ..doc import (
    BlockQuote,
    BulletList,
    CodeBlock,
    Document,
    Emphasis,
    Figure,
    HorizontalRule,
    Image,
    InlineCode,
    Link,
    ListItem,
    OrderedList,
    Paragraph,
    Section,
    Strong,
    Table,
    TableCell,
    TableRow,
    Text,
)


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
# Section numbering
# ---------------------------------------------------------------------------


def _format_segment(n: int, kind: str) -> str:
    """Format a counter per a section-numbering segment.

    v0.2 supports '1' (arabic) and 'a' (lowercase alpha, base-26 wrap to 'aa').
    Other segment kinds fall through to arabic for now.
    """
    if kind == "a":
        out = ""
        n0 = n - 1
        while True:
            out = chr(ord("a") + n0 % 26) + out
            n0 = n0 // 26 - 1
            if n0 < 0:
                break
        return out
    return str(n)


def _compute_numbering(section_tree: list, format_str: str) -> dict[int, str]:
    """Walk the section tree; return ``{id(section): "1.1.a"}``.

    Empty ``format_str`` disables numbering.
    """
    if not format_str:
        return {}
    segments = format_str.split(".")
    out: dict[int, str] = {}

    def walk(sections: list, counters: list[int]) -> None:
        n = 0
        for s in sections:
            if not hasattr(s, "level"):
                continue
            n += 1
            new_counters = counters + [n]
            parts = []
            for i, c in enumerate(new_counters):
                seg_kind = segments[i] if i < len(segments) else "1"
                parts.append(_format_segment(c, seg_kind))
            out[id(s)] = ".".join(parts)
            sub_sections = [c for c in s.children if hasattr(c, "level")]
            if sub_sections:
                walk(s.children, new_counters)

    walk(section_tree, [])
    return out


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

        self.pdf = _PliegoFPDF(
            format=papersize, unit="mm",
            page_numbers=cfg.pliego.page_numbers,
            lang=cfg.lang,
        )
        self.pdf.set_margins(left=margin_x, top=margin_y, right=margin_x)
        self.pdf.set_auto_page_break(auto=True, margin=margin_y)
        self._setup_fonts()
        self.pdf._footer_family = self.body_family
        self.numbering = _compute_numbering(
            doc.children, cfg.pliego.section_numbering
        )

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
            self.pdf.add_font(
                "body", style="BI",
                fname=str(font_dir / "DejaVuSans-BoldOblique.ttf"),
            )
            self.pdf.add_font(
                "mono", style="", fname=str(font_dir / "DejaVuSansMono.ttf")
            )
            self.body_family = "body"
            self.mono_family = "mono"
        else:
            # Fallback: core fonts. Non-ASCII text may render incorrectly.
            self.body_family = "helvetica"
            self.mono_family = "courier"
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
        if section.level == 1:
            pdf.add_page()
        size = self.body_pt * (2.2 - 0.2 * section.level)
        pdf.set_font(self.body_family, style="B", size=size)
        title_text = self._inline_text_only_list(section.title)
        number = self.numbering.get(id(section))
        full_title = f"{number}. {title_text}" if number else title_text
        pdf.multi_cell(
            0, 10, full_title,
            new_x=XPos.LMARGIN, new_y=YPos.NEXT,
        )
        pdf.ln(2)
        pdf.set_font(self.body_family, size=self.body_pt)
        for child in section.children:
            if isinstance(child, Paragraph):
                self._render_paragraph(child)
            elif isinstance(child, Section):
                self._render_section(child)
            elif isinstance(child, BulletList):
                self._render_bullet_list(child, depth=0)
            elif isinstance(child, OrderedList):
                self._render_ordered_list(child, depth=0)
            elif isinstance(child, BlockQuote):
                self._render_block_quote(child)
            elif isinstance(child, HorizontalRule):
                self._render_horizontal_rule()
            elif isinstance(child, CodeBlock):
                self._render_code_block(child)
            elif isinstance(child, Table):
                self._render_table(child)
            elif isinstance(child, Figure):
                self._render_figure(child)
            else:
                raise NotImplementedError(
                    f"Block {type(child).__name__} not supported in v0.3."
                )

    def _render_figure(self, fig: "Figure") -> None:
        pdf = self.pdf
        pdf.ln(self.body_pt * 0.4)
        body_w = pdf.w - pdf.l_margin - pdf.r_margin
        img_w = body_w * 0.6
        x = pdf.l_margin + (body_w - img_w) / 2
        try:
            pdf.image(fig.src, x=x, w=img_w)
        except Exception:
            y = pdf.get_y()
            pdf.set_draw_color(180, 180, 180)
            pdf.rect(x, y, img_w, 30, "D")
            pdf.set_xy(x, y + 12)
            pdf.set_font(self.body_family, style="I", size=self.body_pt * 0.9)
            pdf.cell(img_w, 6, f"[no se pudo cargar: {fig.src}]", align="C")
            pdf.set_y(y + 30)
        if fig.alt:
            pdf.ln(2)
            pdf.set_font(self.body_family, style="I", size=self.body_pt * 0.9)
            pdf.cell(0, 6, fig.alt, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
        pdf.ln(self.body_pt * 0.4)
        pdf.set_font(self.body_family, size=self.body_pt)

    def _render_table(self, table: "Table") -> None:
        pdf = self.pdf
        pdf.ln(self.body_pt * 0.3)
        pdf.set_font(self.body_family, size=self.body_pt)
        with pdf.table(
            text_align="LEFT",
            line_height=self.body_pt * 0.55,
        ) as t:
            header_row = t.row()
            for cell in table.header.cells:
                header_row.cell(self._inline_text_only_list(cell.children))
            for body_row in table.body:
                row = t.row()
                for cell in body_row.cells:
                    row.cell(self._inline_text_only_list(cell.children))
        pdf.ln(self.body_pt * 0.4)

    def _render_horizontal_rule(self) -> None:
        pdf = self.pdf
        pdf.ln(self.body_pt * 0.4)
        y = pdf.get_y()
        pdf.set_draw_color(180, 180, 180)
        pdf.set_line_width(0.3)
        pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
        pdf.ln(self.body_pt * 0.6)

    def _render_code_block(self, cb: "CodeBlock") -> None:
        pdf = self.pdf
        pdf.ln(self.body_pt * 0.2)
        size = self.body_pt * 0.85
        line_h = size * 0.55
        lines = cb.text.rstrip("\n").split("\n") or [""]
        y_start = pdf.get_y()
        height = line_h * len(lines) + line_h * 0.6
        pdf.set_fill_color(245, 245, 245)
        pdf.rect(
            pdf.l_margin, y_start,
            pdf.w - pdf.l_margin - pdf.r_margin, height, "F",
        )
        pdf.set_xy(pdf.l_margin + 2, y_start + line_h * 0.3)
        pdf.set_font(self.mono_family, size=size)
        for line in lines:
            pdf.cell(0, line_h, line, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_x(pdf.l_margin + 2)
        pdf.ln(line_h * 0.4)
        pdf.set_font(self.body_family, size=self.body_pt)

    def _render_block_quote(self, bq: "BlockQuote") -> None:
        pdf = self.pdf
        indent_mm = 8
        original_l_margin = pdf.l_margin
        y_start = pdf.get_y()
        pdf.set_left_margin(original_l_margin + indent_mm)
        pdf.set_x(original_l_margin + indent_mm)
        for child in bq.children:
            if isinstance(child, Paragraph):
                pdf.set_font(self.body_family, style="I", size=self.body_pt)
                self._render_inlines(child.children)
                pdf.ln(self.body_pt * 0.8)
            elif isinstance(child, BlockQuote):
                self._render_block_quote(child)
            elif isinstance(child, BulletList):
                self._render_bullet_list(child, depth=0)
            elif isinstance(child, OrderedList):
                self._render_ordered_list(child, depth=0)
        y_end = pdf.get_y()
        # Vertical rule on the left
        pdf.set_draw_color(120, 120, 120)
        pdf.set_line_width(0.6)
        rule_x = original_l_margin + 2
        pdf.line(rule_x, y_start, rule_x, max(y_end - 1, y_start + 1))
        pdf.set_left_margin(original_l_margin)
        pdf.set_x(original_l_margin)
        pdf.set_font(self.body_family, style="", size=self.body_pt)

    def _render_bullet_list(self, lst: "BulletList", depth: int = 0) -> None:
        self._render_list_generic(lst.items, depth, marker=lambda i: "•",
                                  marker_w=4)

    def _render_ordered_list(self, lst: "OrderedList", depth: int = 0) -> None:
        start = lst.start
        self._render_list_generic(
            lst.items, depth,
            marker=lambda i: f"{start + i}.",
            marker_w=6,
        )

    def _render_list_generic(self, items, depth, marker, marker_w) -> None:
        pdf = self.pdf
        indent_mm = 6 * (depth + 1)
        original_l_margin = pdf.l_margin
        for i, item in enumerate(items):
            pdf.set_left_margin(original_l_margin)
            pdf.set_x(original_l_margin + indent_mm - marker_w)
            pdf.set_font(self.body_family, size=self.body_pt)
            pdf.cell(marker_w, self.body_pt * 0.5, marker(i))
            pdf.set_left_margin(original_l_margin + indent_mm)
            pdf.set_x(original_l_margin + indent_mm)
            for child in item.children:
                if isinstance(child, Paragraph):
                    self._render_inlines(child.children)
                    pdf.ln(self.body_pt * 0.6)
                elif isinstance(child, BulletList):
                    self._render_bullet_list(child, depth + 1)
                elif isinstance(child, OrderedList):
                    self._render_ordered_list(child, depth + 1)
        pdf.set_left_margin(original_l_margin)
        pdf.set_x(original_l_margin)

    def _render_paragraph(self, para: Paragraph) -> None:
        self._render_inlines(para.children)
        self.pdf.ln(self.body_pt * 0.8)

    def _render_inlines(
        self, inlines: list, base_size: float | None = None
    ) -> None:
        """Write inline content via fpdf2's write(), toggling font style for
        Strong, Emphasis, Link, InlineCode."""
        size = base_size or self.body_pt
        pdf = self.pdf
        line_h = size * 0.5
        for inline in inlines:
            if isinstance(inline, Text):
                pdf.set_font(self.body_family, style="", size=size)
                pdf.write(line_h, inline.text)
            elif isinstance(inline, Strong):
                pdf.set_font(self.body_family, style="B", size=size)
                pdf.write(line_h, self._inline_text_only_list(inline.children))
            elif isinstance(inline, Emphasis):
                pdf.set_font(self.body_family, style="I", size=size)
                pdf.write(line_h, self._inline_text_only_list(inline.children))
            elif isinstance(inline, Link):
                pdf.set_font(self.body_family, style="U", size=size)
                pdf.set_text_color(0, 0, 200)
                pdf.write(
                    line_h, self._inline_text_only_list(inline.children),
                    link=inline.href,
                )
                pdf.set_text_color(0, 0, 0)
            elif isinstance(inline, InlineCode):
                pdf.set_font(self.mono_family, style="", size=size * 0.9)
                pdf.write(line_h, inline.text)
            elif isinstance(inline, Image):
                pdf.set_font(self.body_family, style="I", size=size)
                pdf.write(line_h, f"[{inline.alt or 'image'}]")
            else:
                raise NotImplementedError(
                    f"Inline {type(inline).__name__} not supported in v0.2."
                )
        # Restore body font for whatever comes next
        pdf.set_font(self.body_family, style="", size=self.body_pt)

    def _inline_text_only(self, inline) -> str:
        """Flatten an inline node to plain text (no formatting)."""
        if isinstance(inline, (Text, InlineCode)):
            return inline.text
        if isinstance(inline, Image):
            return inline.alt
        if hasattr(inline, "children"):
            return "".join(self._inline_text_only(c) for c in inline.children)
        return ""

    def _inline_text_only_list(self, inlines: list) -> str:
        return "".join(self._inline_text_only(i) for i in inlines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def render_pdf(doc: Document) -> bytes:
    """Render an IR ``Document`` to PDF bytes."""
    return _FPDFRenderer(doc).build()
