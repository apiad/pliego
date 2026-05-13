# Migrating a Quarto document to pliego

pliego is a small subset of Quarto with its own frontmatter dialect. This guide is the minimum you need to flip an existing Quarto-rendered Spanish report over to pliego.

## What you keep

- Your body Markdown unchanged: headings, paragraphs, bold/italic/links/inline code, lists (bulleted + numbered, nested), block quotes, horizontal rules, fenced code blocks, GFM tables, images.
- Section numbering, ToC, Spanish language settings.

## Frontmatter mapping

| Quarto | pliego |
|--------|--------|
| `title: "..."` | same |
| `subtitle: "..."` | same |
| `author: "..."` | passes through to `metadata` (not rendered in v0.3) |
| `date: "YYYY-MM-DD"` | same |
| `lang: es` | same |
| `format: typst:` (block) | drop |
| `format.typst.papersize: a4` | `pliego.papersize: a4` |
| `format.typst.margin: { x: 2cm, y: 2cm }` | `pliego.margin: { x: 2cm, y: 2cm }` |
| `format.typst.fontsize: 10pt` | `pliego.fontsize: 10pt` |
| `format.typst.toc: true` | `pliego.toc: true` |
| `format.typst.toc-depth: 2` | `pliego.toc-depth: 2` |
| `format.typst.section-numbering: 1.1.a` | `pliego.section-numbering: "1.1.a"` |

### Before (Quarto)

```yaml
---
title: "Reporte técnico"
subtitle: "Análisis y propuesta"
date: "2026-05-13"
lang: es
format:
  typst:
    papersize: a4
    margin: { x: 2cm, y: 2cm }
    fontsize: 10pt
    toc: true
    toc-depth: 2
    section-numbering: 1.1.a
---
```

### After (pliego)

```yaml
---
title: "Reporte técnico"
subtitle: "Análisis y propuesta"
date: "2026-05-13"
lang: es
pliego:
  papersize: a4
  margin: { x: 2cm, y: 2cm }
  fontsize: 10pt
  toc: true
  toc-depth: 2
  section-numbering: "1.1.a"
---
```

## What's not supported (yet)

- **Quarto callouts** (`::: {.callout-note}`). Remove the `:::` fences and the title attribute; pliego renders the body content unchanged. Future plan.
- **Math** (`$...$`, `$$...$$`). Future plan.
- **Executable code cells** (`{python}` and friends). pliego only renders the fenced code as text; output is not captured. Future plan.
- **Cross-references** (`@fig-…`, `@tbl-…`). Render as literal text. Future plan.
- **Citations / bibliography**. Future plan.
- **Figure / table captions** beyond the default alt-text fallback. Future plan.

## Manually-numbered titles

If your Quarto source has manual numbers in titles (e.g. `## 1. Resumen ejecutivo`), set `pliego.section-numbering: ""` to disable pliego's auto-numbering. Otherwise pliego will prepend `1.` again, producing `1. 1. Resumen ejecutivo`.

## Running pliego

```bash
pip install pliego        # or: uv add pliego
pliego render report.md   # writes report.pdf next to the source
pliego render report.md -o out.pdf
```
