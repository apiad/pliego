"""pliego CLI."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .parse import parse
from .render import render_pdf


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pliego",
        description="Pure-Python Markdown → PDF.",
    )
    parser.add_argument("--version", action="version", version=f"pliego {__version__}")
    sub = parser.add_subparsers(dest="cmd", required=True)
    render = sub.add_parser("render", help="Render a Markdown file to PDF.")
    render.add_argument("input", type=Path, help="Input .md file.")
    render.add_argument(
        "-o", "--output",
        type=Path,
        default=None,
        help="Output .pdf path. Default: <input>.pdf next to the source.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.cmd == "render":
        return _cmd_render(args.input, args.output)
    parser.print_help()
    return 2


def _cmd_render(input_path: Path, output_path: Path | None) -> int:
    if not input_path.exists():
        print(f"error: input not found: {input_path}", file=sys.stderr)
        return 1
    if output_path is None:
        output_path = input_path.with_suffix(".pdf")
    source = input_path.read_text(encoding="utf-8")
    doc = parse(source)
    pdf_bytes = render_pdf(doc)
    output_path.write_bytes(pdf_bytes)
    print(f"wrote {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
