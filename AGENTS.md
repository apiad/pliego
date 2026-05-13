# AGENTS.md — pliego

This repo is **pliego**, a pure-Python Markdown → PDF renderer.

## Spec & plan

Both live in the parent Workspace vault (Obsidian Sync, not git):

- Design: `vault/Atlas/Architecture/2026-05-13-pliego-design.md`
- v0.1 plan: `vault/Atlas/Architecture/plans/2026-05-13-pliego-vertical-slice.md`

If you don't have access to the vault, the design summary is in `docs/design.md`
(generated from the vault doc on each release).

## Layout

- `src/pliego/parse.py` — Markdown → IR (markdown-it-py)
- `src/pliego/doc.py` — IR types (Pydantic discriminated unions)
- `src/pliego/config.py` — frontmatter → DocConfig
- `src/pliego/render/pdf.py` — IR → PDF bytes (fpdf2 backend, chosen via Phase 0 spike)
- `src/pliego/cli.py` — `pliego render` entry point

## Conventions

- Python 3.12+, uv-managed, `pyproject.toml` is the source of truth.
- Conventional commits (`feat:`, `fix:`, `docs:`, etc.).
- TDD: failing test before implementation, every time.
- No magic — no plugin discovery, no entry-points, no autoloading in v0.1.

## Backend

PDF backend chosen via Phase 0 spike (see design doc § Backend decision): **fpdf2**.
The chosen backend's primitives are wrapped in `pliego.render.pdf` — never import
the backend directly elsewhere. This makes a later swap to reportlab or a
from-scratch writer a one-module change.

## What v0.1 is not

- Not a LaTeX replacement.
- No code-cell execution (v0.4).
- No HTML or Word output (v0.2 / v0.3).
- No plugin system (v0.5).
- No math (v0.6).
