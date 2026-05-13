"""Soft-hyphenation wrapper around pyphen, with per-language caching.

We insert the Unicode SOFT HYPHEN character (U+00AD) into long words.
fpdf2's text-flow functions only render a visible hyphen at the break
position when a soft-hyphenated word does not fit on the current line —
so for short lines the output is unchanged, and for wrapped lines we
get clean word-internal breaks instead of overflow or awkward spacing.
"""
from __future__ import annotations

import re

try:
    import pyphen
except ImportError:  # pragma: no cover
    pyphen = None  # type: ignore[assignment]

_SOFT = "­"

# Map short ISO codes to pyphen's hyphenation dictionary identifiers.
_LANG_MAP = {
    "es": "es_ES",
    "en": "en_US",
    "pt": "pt_PT",
    "fr": "fr_FR",
    "de": "de_DE",
    "it": "it_IT",
    "ca": "ca",
    "gl": "gl",
}

_cache: dict[str, "pyphen.Pyphen | None"] = {}
_WORD_RE = re.compile(r"[\w'-]+", re.UNICODE)


def _get(lang: str):
    """Return a Pyphen instance for ``lang``, or None if unsupported."""
    if pyphen is None:
        return None
    short = lang.split("-")[0].split("_")[0].lower()
    if short in _cache:
        return _cache[short]
    code = _LANG_MAP.get(short)
    if code is None:
        _cache[short] = None
        return None
    try:
        inst = pyphen.Pyphen(lang=code)
    except KeyError:
        inst = None
    _cache[short] = inst
    return inst


def hyphenate(text: str, lang: str, min_len: int = 6) -> str:
    """Insert U+00AD into words >= ``min_len`` chars long.

    Returns ``text`` unchanged if hyphenation isn't available for ``lang``.
    """
    inst = _get(lang)
    if inst is None:
        return text

    def sub(m: re.Match) -> str:
        word = m.group(0)
        if len(word) < min_len:
            return word
        return inst.inserted(word, hyphen=_SOFT)

    return _WORD_RE.sub(sub, text)
