# Changelog

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
