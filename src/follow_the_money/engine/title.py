"""Title similarity (closed v1 algorithm) shared by dedupe and candidates."""

from __future__ import annotations

from ..feed.dedupe import normalize_title, title_jaccard

__all__ = ["normalize_title", "title_jaccard"]
