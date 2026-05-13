# 📄 pliego — pure-Python Markdown → PDF

**pliego** is a small, fast, pure-Python Markdown-to-PDF renderer. No C bindings, no LaTeX, no Pandoc. Designed as a tractable subset of Quarto for letters, technical reports, and small books.

## Status

`v0.1` — minimal vertical slice: frontmatter + a single heading + a single paragraph → PDF (cover + body). Feature expansion (lists, tables, images, multi-level headings, section numbering, ToC, Spanish hyphenation) is the next plan.

## Quick start

```bash
uv add pliego
pliego render report.md           # writes report.pdf next to the source
pliego render report.md -o out.pdf
```

A minimal `report.md`:

```markdown
---
title: My Report
subtitle: First draft
date: 2026-05-13
lang: es
---

# Introducción

Cuerpo del reporte.
```

## Why

Existing options for "Markdown → PDF" all drag heavy system dependencies (LaTeX, Pandoc, Typst, Cairo). pliego is pure Python — pip-installable, no C bindings, fast cold start.

It is **not** a LaTeX replacement. It is enough for letters, technical reports, and small books.

## License

MIT.
