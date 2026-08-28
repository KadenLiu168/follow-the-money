"""Strict UTF-8 and Unicode-scalar validation for all repository strings.

Rules (design section 1):

- Repository JSON, config, LLM responses, and canonical artifacts encode and
  decode as strict UTF-8 with no replacement characters.
- After decoding, every string must contain only Unicode scalar values; lone
  high/low surrogates and category ``Cs`` are rejected before NFC, byte
  counting, hashing, rendering, or replay.
- Every LLM prose/reason/wording field additionally rejects categories
  ``Cc``, ``Cf``, ``Zl``, ``Zp``, is NFC-normalized, and is single-line.
"""

from __future__ import annotations

import re
import unicodedata

# Control/format/separator categories rejected in prose fields.
_PROSE_BAD_CATEGORIES = frozenset({"Cc", "Cf", "Cs", "Zl", "Zp"})

_WHITESPACE_RUN = re.compile(r"\s+")


class UnicodeError_(ValueError):
    """Raised when a string violates strict Unicode-scalar or prose rules."""


def validate_scalar_string(text: str, *, where: str = "string") -> str:
    """Return ``text`` unchanged after rejecting lone surrogates/Cs values."""
    for ch in text:
        cp = ord(ch)
        if 0xD800 <= cp <= 0xDFFF:
            raise UnicodeError_(f"{where}: lone surrogate U+{cp:04X} is not a Unicode scalar value")
        if unicodedata.category(ch) == "Cs":
            raise UnicodeError_(f"{where}: category Cs code point U+{cp:04X} is not a scalar value")
    return text


def validate_prose(text: str, *, where: str = "prose") -> str:
    """Validate an LLM prose/reason/wording fragment.

    Enforces scalar values, rejects ``Cc``/``Cf``/``Cs``/``Zl``/``Zp``,
    NFC-normalizes, collapses whitespace runs to one ASCII space, strips
    leading/trailing whitespace, and rejects embedded newlines.
    """
    validate_scalar_string(text, where=where)
    for ch in text:
        if unicodedata.category(ch) in _PROSE_BAD_CATEGORIES:
            raise UnicodeError_(
                f"{where}: prohibited Unicode category {unicodedata.category(ch)!r} "
                f"for U+{ord(ch):04X}"
            )
    normalized = unicodedata.normalize("NFC", text)
    one_line = _WHITESPACE_RUN.sub(" ", normalized).strip()
    if "\n" in one_line or "\r" in one_line:
        raise UnicodeError_(f"{where}: embedded newline after normalization")
    return one_line
