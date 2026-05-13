"""Renderers: IR → output bytes. v0.1 ships only PDF."""
from .pdf import render_pdf

__all__ = ["render_pdf"]
