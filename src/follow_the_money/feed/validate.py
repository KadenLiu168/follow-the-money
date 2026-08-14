"""Semantic Feed validation on top of ``feed.schema.json``.

JSON Schema enforces shape; this module enforces the cross-field semantics
from design sections 1/4:

- Supported schema major (fail closed on unknown versions).
- Strictly advancing half-open window ``window.start < evidence_cutoff_at``.
- Wall-clock order ``collection_started_at <= evidence_cutoff_at <=
  non-null request/retrieved_at <= collection_completed_at <= generated_at``;
  work with no observed response keeps null ``retrieved_at``.
- Stable serialization: provider outcomes in ascending ``provider_id``
  (exactly one per provider) and items in the ``(knowledge_available_at,
  id)`` total order.
- Canonical digest/run-ID recomputation from an explicit allowlisted
  semantic projection (``content_digest``/``run_id`` are derived, never
  hashed); ``run_id`` derives from the fixed cutoff plus the digest.
- Legacy read compatibility: an already-published schema-v1 artifact whose
  identity validates only under the former whole-envelope projection remains
  consumable; producers never write that legacy form after this change.
- Raw numeric tokens bounded to 64 bytes / 24 significant digits / exponent
  in [-12, 12]; canonical persisted values are plain decimals with no
  exponent, no negative zero, at most 64 bytes/24 digits, magnitude <= 1e18.
- Rejection of intelligence fields (importance, direction, price-in, regime,
  impact, ranking) in Feed items.
"""

from __future__ import annotations

import itertools
import re
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from ..canonical import canonical_digest
from ..schema import SchemaError, validate_against

FEED_SCHEMA = "feed.schema.json"
SUPPORTED_FEED_MAJOR = 1

#: Top-level semantic projection members. Execution-audit metadata
#: (``collection_started_at``, ``collection_completed_at``, ``generated_at``,
#: provider ``retrieved_at``, ``git``, ``content_digest``, ``run_id``) and any
#: undeclared execution metadata stay outside the projection. A new semantic
#: field must be deliberately added here and to the identity tests.
SEMANTIC_PROJECTION_MEMBERS = (
    "schema_version",
    "window",
    "evidence_cutoff_at",
    "provider_outcomes",
    "producer",
    "feed_config",
    "feed_schema",
    "provider_contracts",
    "items",
    "pipeline",
)

_RAW_NUMERIC = re.compile(r"^[+-]?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?$")
_CANONICAL_NUMERIC = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")

_MAX_BYTES = 64
_MAX_SIGNIFICANT_DIGITS = 24
_MAX_EXPONENT = 12
_MAX_MAGNITUDE = 10**18

_FORBIDDEN_INTELLIGENCE_KEYS = {
    "importance",
    "direction",
    "price_in",
    "regime",
    "impact",
    "ranking",
    "score",
    "status",
    "signal",
    "recommendation",
}


def _parse_ts(value: str, where: str) -> datetime:
    try:
        dt = datetime.fromisoformat(value)
    except ValueError as exc:
        raise SchemaError(f"{where}: invalid RFC 3339 timestamp {value!r}: {exc}") from exc
    if dt.tzinfo is None:
        raise SchemaError(f"{where}: timestamp must carry a timezone: {value!r}")
    return dt


def validate_numeric_token(token: str, *, where: str) -> None:
    """Validate a raw numeric token before Decimal construction."""
    if not _RAW_NUMERIC.match(token):
        raise SchemaError(f"{where}: invalid raw numeric token {token!r}")
    mantissa = token.lstrip("+-")
    exponent = 0
    if "e" in mantissa.lower():
        mantissa, _, exp_part = mantissa.lower().partition("e")
        exponent = int(exp_part)
    if exponent < -_MAX_EXPONENT or exponent > _MAX_EXPONENT:
        raise SchemaError(f"{where}: exponent out of range [-12, 12]: {token!r}")
    digits = mantissa.replace(".", "").lstrip("0") or "0"
    if len(digits) > _MAX_SIGNIFICANT_DIGITS:
        raise SchemaError(f"{where}: more than 24 significant digits: {token!r}")
    if len(token) > _MAX_BYTES:
        raise SchemaError(f"{where}: token longer than 64 bytes: {token!r}")


def validate_canonical_numeric(value: str, *, where: str) -> None:
    """Validate a persisted canonical plain decimal string."""
    if not _CANONICAL_NUMERIC.match(value):
        raise SchemaError(f"{where}: not canonical plain decimal: {value!r}")
    if value.startswith("-"):
        digits = value[1:].replace(".", "").lstrip("0")
        if digits == "":
            raise SchemaError(f"{where}: negative zero is forbidden: {value!r}")
    if len(value) > _MAX_BYTES:
        raise SchemaError(f"{where}: canonical value longer than 64 bytes")
    body = value.lstrip("-")
    digits = body.replace(".", "").lstrip("0") or "0"
    if len(digits) > _MAX_SIGNIFICANT_DIGITS:
        raise SchemaError(f"{where}: more than 24 significant digits: {value!r}")
    int_part = body.split(".")[0].lstrip("0") or "0"
    # Magnitude guard: |value| <= 10^18. A 19-digit integer part is allowed
    # only for exactly 10^18; anything larger overflows the guard.
    if len(int_part) > 19 or (len(int_part) == 19 and int_part > "1000000000000000000"):
        raise SchemaError(f"{where}: magnitude exceeds 10^18: {value!r}")


def validate_feed(feed: Mapping[str, Any]) -> None:
    """Full semantic validation of a decoded Feed object."""
    validate_against(FEED_SCHEMA, feed)

    if feed.get("schema_version") != SUPPORTED_FEED_MAJOR:
        raise SchemaError(f"unsupported Feed schema_version {feed.get('schema_version')!r}")

    window = feed["window"]
    start = _parse_ts(window["start"], "window.start")
    cutoff = _parse_ts(feed["evidence_cutoff_at"], "evidence_cutoff_at")
    if not (start < cutoff):
        raise SchemaError(f"window must be strictly advancing: start={start} >= cutoff={cutoff}")

    started = _parse_ts(feed["collection_started_at"], "collection_started_at")
    completed = _parse_ts(feed["collection_completed_at"], "collection_completed_at")
    generated = _parse_ts(feed["generated_at"], "generated_at")
    order = [started, cutoff, completed, generated]
    for a, b in itertools.pairwise(order):
        if a > b:
            raise SchemaError(
                "Feed wall-clock order violated: "
                "collection_started_at <= evidence_cutoff_at <= collection_completed_at <= generated_at"
            )
    for outcome in feed.get("provider_outcomes", []):
        retrieved = outcome.get("retrieved_at")
        if retrieved is not None:
            rts = _parse_ts(retrieved, "retrieved_at")
            if not (cutoff <= rts <= completed):
                raise SchemaError("retrieved_at outside [cutoff, completed]")

    # Stable serialization: new semantic-identity Feeds contain exactly one
    # provider outcome per provider in ascending provider_id order. The former
    # concurrent writer could persist valid legacy-v1 artifacts in worker
    # completion order, so only an exact whole-envelope legacy identity keeps
    # its narrow read-compatibility exemption.
    if not _has_exact_legacy_identity(feed):
        previous_id: str | None = None
        for outcome in feed.get("provider_outcomes", []):
            pid = outcome.get("provider_id")
            if previous_id is not None and pid <= previous_id:
                raise SchemaError("provider_outcomes not in ascending provider_id order")
            previous_id = pid
    previous_item_key: tuple[str, str] | None = None
    for item in feed.get("items", []):
        source = item.get("source", {})
        item_key = (source.get("knowledge_available_at", ""), item["id"])
        if previous_item_key is not None and item_key < previous_item_key:
            raise SchemaError("items not in (source.knowledge_available_at, id) total order")
        previous_item_key = item_key

    # Numeric guards across all payloads.
    _validate_numerics(feed.get("items", []))

    # No intelligence fields inside items.
    for item in feed.get("items", []):
        payload = item.get("payload", {})
        for key in _FORBIDDEN_INTELLIGENCE_KEYS:
            if key in payload:
                raise SchemaError(f"intelligence field {key!r} rejected in Feed item")

    # Calendar horizon (v1 snapshot covers [cutoff, cutoff + 26h]).
    _validate_calendar_horizon(feed)


def _validate_numerics(items: list[Any]) -> None:
    for idx, item in enumerate(items):
        payload = item.get("payload", {})
        where = f"items[{idx}].payload"
        for key in ("actual", "consensus", "previous", "net_flow", "position"):
            value = payload.get(key)
            if isinstance(value, dict) and value.get("value") is not None:
                validate_canonical_numeric(str(value["value"]), where=f"{where}.{key}.value")
        for obs in payload.get("observations", []):
            validate_canonical_numeric(str(obs["value"]), where=f"{where}.observations[].value")
            if obs.get("volume") is not None:
                validate_canonical_numeric(
                    str(obs["volume"]), where=f"{where}.observations[].volume"
                )


def _validate_calendar_horizon(feed: Mapping[str, Any]) -> None:
    horizon = feed.get("calendar_horizon_end")
    if horizon is None:
        return  # optional metadata; full calendar snapshot tests enforce 26h
    cutoff = _parse_ts(feed["evidence_cutoff_at"], "evidence_cutoff_at")
    horizon_dt = _parse_ts(horizon, "calendar_horizon_end")
    if horizon_dt < cutoff:
        raise SchemaError("calendar_horizon_end before evidence_cutoff_at")


def semantic_feed_projection(feed: Mapping[str, Any]) -> dict[str, Any]:
    """The explicit allowlisted semantic projection of a Feed.

    Contains ``schema_version``, ``window``, ``evidence_cutoff_at``, ordered
    semantic provider outcomes (every serialized outcome field except
    ``retrieved_at``), ``producer``, ``feed_config``, ``feed_schema``,
    ``provider_contracts``, normalized ``items``, and the pipeline semantic
    result (``status`` plus structured ``coverage_gap``; free-form warnings
    are execution reporting and never promote into identity). Execution-audit
    timestamps, ``git``, ``content_digest``, ``run_id``, and undeclared
    execution metadata are excluded.
    """
    projection: dict[str, Any] = {}
    for member in SEMANTIC_PROJECTION_MEMBERS:
        projection[member] = feed[member]
    projection["provider_outcomes"] = [
        {k: v for k, v in outcome.items() if k != "retrieved_at"}
        for outcome in feed["provider_outcomes"]
    ]
    pipeline = feed["pipeline"]
    semantic_pipeline: dict[str, Any] = {"status": pipeline["status"]}
    if "coverage_gap" in pipeline:
        semantic_pipeline["coverage_gap"] = pipeline["coverage_gap"]
    projection["pipeline"] = semantic_pipeline
    return projection


def recompute_feed_identity(feed: Mapping[str, Any]) -> tuple[str, str]:
    """Return ``(content_digest, run_id)`` recomputed from the semantic
    projection. ``run_id`` derives from the fixed cutoff plus the digest."""
    digest = canonical_digest(semantic_feed_projection(feed))
    cutoff = feed["evidence_cutoff_at"]
    run_id = f"{cutoff}::{digest[:32]}"
    return digest, run_id


def _recompute_legacy_identity(feed: Mapping[str, Any]) -> tuple[str, str]:
    digest = canonical_digest(
        {k: v for k, v in feed.items() if k not in ("content_digest", "run_id")}
    )
    cutoff = feed["evidence_cutoff_at"]
    run_id = f"{cutoff}::{digest[:32]}"
    return digest, run_id


def _has_exact_legacy_identity(feed: Mapping[str, Any]) -> bool:
    if feed.get("schema_version") != SUPPORTED_FEED_MAJOR:
        return False
    digest, run_id = _recompute_legacy_identity(feed)
    return feed.get("content_digest") == digest and feed.get("run_id") == run_id


def assert_feed_identity(feed: Mapping[str, Any]) -> None:
    """Fail closed unless the embedded identity matches the semantic
    projection exactly, or — for an already-published supported-major
    artifact — the former whole-envelope projection exactly."""
    digest, run_id = recompute_feed_identity(feed)
    if _has_exact_legacy_identity(feed):
        return
    if feed.get("content_digest") != digest:
        raise SchemaError("content_digest does not match canonical projection")
    if feed.get("run_id") != run_id:
        raise SchemaError("run_id does not derive from cutoff+digest")
