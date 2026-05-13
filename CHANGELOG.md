# Changelog

## [0.3.0] — 2026-05-13

### Added
- GFM tables (header + body, equal column widths).
- Block-level figures (paragraph-with-only-an-image promoted to Figure;
  centered at 60% body width with italic caption from alt text).
- Inline images render as `[alt]` italic placeholders within running text.
- Table of contents — auto-generated, two-pass fpdf2 output, honors
  `pliego.toc` + `pliego.toc-depth`. Localized header (Índice / Contents).
- Page numbers in footer (skipped on cover). Localized label (Página / Page).
  Disable via `pliego.page-numbers: false`.
- Spanish hyphenation via pyphen — long words get soft-hyphen breaks at
  wrap points. Supports es/en/pt/fr/de/it/ca/gl; passthrough otherwise.
- Quarto → pliego migration guide (`docs/migrating-from-quarto.md`).
- Ecuador architecture report integration test: a real ~80KB Spanish
  technical report renders end-to-end as a 31-page PDF (cover + ToC +
  body + glossary table + page numbers).
- Top-level paragraphs / figures (content before the first heading) are
  now allowed; they ride a synthetic untitled preamble section.

### Changed
- Renderer now uses a `_PliegoFPDF` subclass to hook the footer.
- `start_section()` is now called for every heading (gives PDF outline +
  ToC entries for free, regardless of whether ToC is rendered).
- New dependency: `pyphen>=0.14`.

## [0.2.0] — 2026-05-13

### Added
- Inline formatting: bold, italic, links (clickable), inline code.
- Multi-level headings + nested sections (h1–h6); only h1 starts a new page.
- Computed section numbering per the `pliego.section-numbering` format string
  (arabic + lowercase alpha; empty string disables).
- Bulleted + numbered lists with arbitrary nesting; ordered lists honor `start=`.
- Block quotes with left vertical rule and italic body.
- Horizontal rules.
- Fenced code blocks with light grey background (no syntax highlighting yet).
- Mono font (DejaVu Sans Mono) auto-discovered alongside DejaVu Sans.
- Integration fixture exercising every v0.2 feature end-to-end.

### Changed
- Renderer: `_render_inlines` uses fpdf2's `write()` so inline spans toggle
  font style smoothly within a paragraph.

## [0.1.0] — 2026-05-13

### Added
- Initial scaffolding.
- Minimal vertical slice: frontmatter + h1 + paragraph → PDF.
- fpdf2 backend with DejaVu Sans auto-discovery.
