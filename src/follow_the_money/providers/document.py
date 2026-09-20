"""Bounded official-document acquisition values and deterministic extraction.

This module owns only the small cross-Provider surface: the immutable
candidate/admitted-document/source-content values, the raw-response digest,
NFC and whitespace normalization, whole-block bounded assembly, and the four
explicit Provider container rules. There is no extractor registry.

Every extractor reads only its verified container and drops
script/style/non-content descendants while decoding character references.
Block boundaries are the declared paragraph element and the line break, so a
container whose verified markup mixes ``<p>`` paragraphs with bare
``<br>``-separated runs retains both. Each block is normalized to NFC, has its
intra-block whitespace folded, and is dropped when empty; source order is
preserved and blocks join with exactly ``\\n\\n``. Whole blocks are appended
while the 12,000-code-point budget (including separators) holds; later blocks
are omitted with ``truncated = true``. An oversized first block, a missing or
duplicated container, invalid UTF-8, non-HTML content, and attachment-only
pages all fail closed.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from typing import Any

SOURCE_CONTENT_FORMAT = "plain_text"
SOURCE_CONTENT_EXTRACTION_METHOD = "official_html_text_v1"
SOURCE_CONTENT_MAX_CODE_POINTS = 12000
_PARAGRAPH_SEPARATOR = "\n\n"
_EXCLUDED_DESCENDANTS = frozenset({"script", "style"})
_BLOCK_ELEMENTS = frozenset({"p"})
_VOID_ELEMENTS = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
)
_ATTACHMENT_SUFFIXES = (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".zip")

ContainerPredicate = Callable[
    [str, Mapping[str, str], Sequence[tuple[str, Mapping[str, str]]]], bool
]


class DocumentError(ValueError):
    """A required official detail document could not be admitted or extracted."""


@dataclass(frozen=True, slots=True)
class DocumentCandidate:
    """One deterministically discovered current-window detail candidate."""

    identity: str
    title: str
    url: str
    published_at: str


@dataclass(frozen=True, slots=True)
class AdmittedDocument:
    """One admitted official detail document and its exact response bytes."""

    candidate: DocumentCandidate
    final_url: str
    body: bytes

    @property
    def document_sha256(self) -> str:
        return document_digest(self.body)


@dataclass(frozen=True, slots=True)
class SourceContent:
    """The closed bounded official text evidence for one Feed item."""

    text: str
    truncated: bool
    document_sha256: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "format": SOURCE_CONTENT_FORMAT,
            "extraction_method": SOURCE_CONTENT_EXTRACTION_METHOD,
            "truncated": self.truncated,
            "document_sha256": self.document_sha256,
        }


@dataclass(frozen=True, slots=True)
class SourceContentAcquisition:
    """One Provider's discovery evidence and admitted detail documents."""

    candidates: tuple[DocumentCandidate, ...]
    documents: tuple[AdmittedDocument, ...]

    def __post_init__(self) -> None:
        if tuple(document.candidate for document in self.documents) != self.candidates:
            raise DocumentError("admitted documents do not match the selected candidates")


def select_candidates(
    candidates: Sequence[DocumentCandidate], *, window: Mapping[str, str], limit: int
) -> tuple[DocumentCandidate, ...]:
    """Collapse exact duplicates, select the window, order, and bound the count.

    An identity collision with different metadata fails closed. The safety
    bound is not a top-N selection: exceeding it fails before any detail
    request instead of silently dropping evidence.
    """
    unique: dict[str, DocumentCandidate] = {}
    for candidate in candidates:
        existing = unique.get(candidate.identity)
        if existing is None:
            unique[candidate.identity] = candidate
        elif existing != candidate:
            raise DocumentError("conflicting duplicate candidate identity metadata")
    selected = [
        candidate
        for candidate in unique.values()
        if in_half_open_window(candidate.published_at, window)
    ]
    selected.sort(key=lambda candidate: (candidate.published_at, candidate.identity), reverse=True)
    if len(selected) > limit:
        raise DocumentError(
            f"selected candidate count {len(selected)} exceeds the declared bound {limit}"
        )
    return tuple(selected)


def in_half_open_window(value: str, window: Mapping[str, str]) -> bool:
    """Return whether ``value`` lies in ``[window.start, window.end)``."""
    try:
        parsed = datetime.fromisoformat(value)
        start = datetime.fromisoformat(window["start"])
        end = datetime.fromisoformat(window["end"])
    except (KeyError, TypeError, ValueError) as exc:
        raise DocumentError(f"invalid acquisition window or timestamp: {value!r}") from exc
    if None in {parsed.tzinfo, start.tzinfo, end.tzinfo}:
        raise DocumentError("acquisition window timestamps must carry a timezone")
    return start <= parsed < end


def document_digest(body: bytes) -> str:
    """Lowercase SHA-256 of the exact admitted raw response body bytes."""
    return hashlib.sha256(body).hexdigest()


def normalize_block(text: str) -> str:
    """Fold intra-block whitespace and normalize one block to NFC."""
    return unicodedata.normalize("NFC", " ".join(text.split()))


def assemble_source_content(
    blocks: Sequence[str], *, max_text_chars: int, document_sha256: str
) -> SourceContent:
    """Bound complete normalized blocks to the declared code-point budget."""
    if not re.fullmatch(r"[0-9a-f]{64}", document_sha256):
        raise DocumentError("a lowercase SHA-256 of the admitted document is required")
    if not blocks:
        raise DocumentError("official content container has no admissible text blocks")
    kept: list[str] = []
    used = 0
    truncated = False
    for block in blocks:
        addition = len(block) if not kept else len(_PARAGRAPH_SEPARATOR) + len(block)
        if used + addition > max_text_chars:
            if not kept:
                raise DocumentError(
                    "the first admissible content block exceeds the bounded text budget"
                )
            truncated = True
            break
        kept.append(block)
        used += addition
    return SourceContent(
        text=_PARAGRAPH_SEPARATOR.join(kept),
        truncated=truncated,
        document_sha256=document_sha256,
    )


class _ContainerBlockParser(HTMLParser):
    """Stateful standard-library parser for one verified content container."""

    def __init__(self, is_container: ContainerPredicate) -> None:
        super().__init__(convert_charrefs=True)
        self._is_container = is_container
        self._stack: list[tuple[str, Mapping[str, str]]] = []
        self._inside: int | None = None
        self._containers = 0
        self._blocks: list[str] = []
        self._buffer: list[str] | None = None
        self._suppressed = 0
        self._elements = 0
        self._attachments = 0
        self._attachment_depth = 0

    @property
    def containers(self) -> int:
        return self._containers

    @property
    def elements(self) -> int:
        return self._elements

    @property
    def blocks(self) -> tuple[str, ...]:
        return tuple(self._blocks)

    @property
    def attachment_only(self) -> bool:
        return bool(self._attachments) and not self._blocks

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        mapping = {key.lower(): (value or "") for key, value in attrs}
        self._elements += 1
        if self._is_container(tag, mapping, self._stack):
            self._containers += 1
            self._inside = 0 if self._inside is None else self._inside + 1
        elif self._inside is not None:
            if tag in _VOID_ELEMENTS:
                if tag == "br":
                    self._finish_block()
            else:
                self._inside += 1
                if tag in _EXCLUDED_DESCENDANTS:
                    self._suppressed += 1
                elif tag in _BLOCK_ELEMENTS:
                    self._finish_block()
                elif tag == "a" and _is_attachment(mapping.get("href", "")):
                    self._finish_block()
                    self._attachments += 1
                    self._attachment_depth += 1
        if tag not in _VOID_ELEMENTS:
            self._stack.append((tag, mapping))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_data(self, data: str) -> None:
        if self._inside is None or self._suppressed or self._attachment_depth:
            return
        if self._buffer is None:
            self._buffer = []
        self._buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self._inside is not None:
            if self._inside == 0:
                self._finish_block()
                self._inside = None
            else:
                if tag in _BLOCK_ELEMENTS:
                    self._finish_block()
                if tag in _EXCLUDED_DESCENDANTS and self._suppressed:
                    self._suppressed -= 1
                if tag == "a" and self._attachment_depth:
                    self._attachment_depth -= 1
                self._inside -= 1
        for index in range(len(self._stack) - 1, -1, -1):
            if self._stack[index][0] == tag:
                del self._stack[index:]
                return

    def _finish_block(self) -> None:
        if self._buffer is None:
            return
        block = normalize_block("".join(self._buffer))
        self._buffer = None
        if block:
            self._blocks.append(block)


def _is_attachment(href: str) -> bool:
    return href.lower().split("?", 1)[0].endswith(_ATTACHMENT_SUFFIXES)


def _has_class(attrs: Mapping[str, str], name: str) -> bool:
    return name in attrs.get("class", "").split()


def _decode(body: bytes, *, charset: str) -> str:
    try:
        return body.decode(charset)
    except UnicodeDecodeError as exc:
        raise DocumentError(f"response is not decodable as {charset}") from exc


def extract_blocks(
    body: bytes, *, charset: str, is_container: ContainerPredicate
) -> tuple[str, ...]:
    """Extract the verified container's declared content blocks in source order."""
    parser = _ContainerBlockParser(is_container)
    try:
        parser.feed(_decode(body, charset=charset))
        parser.close()
    except DocumentError:
        raise
    except Exception as exc:  # pragma: no cover - defensive parser boundary
        raise DocumentError(f"official document could not be parsed: {exc}") from exc
    if parser.elements == 0:
        raise DocumentError("official detail response is not HTML")
    if parser.containers == 0:
        raise DocumentError("official detail response lacks the verified content container")
    if parser.containers > 1:
        raise DocumentError("official detail response contains duplicate content containers")
    if parser.attachment_only:
        raise DocumentError("official detail source is attachment-only")
    if not parser.blocks:
        raise DocumentError("official content container has no admissible text blocks")
    return parser.blocks


def _federal_reserve_container(
    tag: str, attrs: Mapping[str, str], ancestors: Sequence[tuple[str, Mapping[str, str]]]
) -> bool:
    if tag != "div" or _has_class(attrs, "heading") or not _has_class(attrs, "col-sm-8"):
        return False
    return any(
        ancestor_tag == "div" and ancestor_attrs.get("id") == "article"
        for ancestor_tag, ancestor_attrs in ancestors
    )


def extract_federal_reserve(body: bytes, *, charset: str = "utf-8") -> tuple[str, ...]:
    """Federal Reserve press-release body column blocks."""
    return extract_blocks(body, charset=charset, is_container=_federal_reserve_container)


def extract_pboc(body: bytes, *, charset: str = "utf-8") -> tuple[str, ...]:
    """PBOC announcement ``div#zoom`` blocks."""
    return extract_blocks(
        body,
        charset=charset,
        is_container=lambda tag, attrs, _ancestors: tag == "div" and attrs.get("id") == "zoom",
    )


def extract_sse(body: bytes, *, charset: str = "utf-8") -> tuple[str, ...]:
    """SSE notice ``div.allZoom`` blocks."""
    return extract_blocks(
        body,
        charset=charset,
        is_container=lambda tag, attrs, _ancestors: tag == "div" and _has_class(attrs, "allZoom"),
    )


def extract_szse(body: bytes, *, charset: str = "utf-8") -> tuple[str, ...]:
    """SZSE notice ``div#desContent`` blocks."""
    return extract_blocks(
        body,
        charset=charset,
        is_container=lambda tag, attrs, _ancestors: (
            tag == "div" and attrs.get("id") == "desContent"
        ),
    )
