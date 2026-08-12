"""Canonical JSON serialization and digest utilities.

The canonical serializer (design sections 1/6) defines:

- UTF-8 with ``ensure_ascii = false`` (raw Unicode scalar output),
- no insignificant whitespace,
- deterministic key ordering (keys sorted within each object),
- only required quote/backslash escaping (prose rejects controls first),
- strict rejection of lone surrogates before encoding.

``canonical_digest`` hashes the canonical bytes with SHA-256 and returns a
lowercase hex string.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .unicode import validate_scalar_string


class CanonicalEncodeError(ValueError):
    """Raised when a value cannot be encoded canonically (e.g. lone surrogate)."""


def _ordered(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _ordered(v) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))}
    if isinstance(value, (list, tuple)):
        return [_ordered(v) for v in value]
    return value


def canonical_bytes(value: Any) -> bytes:
    """Serialize ``value`` to canonical UTF-8 JSON bytes.

    The object is deep-copied with sorted keys, then encoded with
    ``ensure_ascii = False``, ``separators=(",", ":")``, and no whitespace.
    Every string inside is validated as a Unicode scalar string first.
    """

    def _check(v: Any) -> None:
        if isinstance(v, str):
            validate_scalar_string(v)
        elif isinstance(v, dict):
            for k, item in v.items():
                _check(k)
                _check(item)
        elif isinstance(v, (list, tuple)):
            for item in v:
                _check(item)

    _check(value)
    ordered = _ordered(value)
    try:
        text = json.dumps(
            ordered,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        raise CanonicalEncodeError(f"cannot canonical-encode value: {exc}") from exc
    return text.encode("utf-8")


def canonical_text(value: Any) -> str:
    return canonical_bytes(value).decode("utf-8")


def canonical_digest(value: Any) -> str:
    """SHA-256 hex digest of the canonical JSON bytes."""
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def canonical_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_canonical_json(data: bytes, *, where: str = "json") -> Any:
    """Decode strict-UTF-8 repository JSON and validate scalar values."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CanonicalEncodeError(f"{where}: invalid UTF-8: {exc}") from exc
    validate_scalar_string(text, where=where)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise CanonicalEncodeError(f"{where}: invalid JSON: {exc}") from exc
