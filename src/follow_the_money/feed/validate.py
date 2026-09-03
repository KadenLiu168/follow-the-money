"""Semantic Feed validation on top of ``feed.schema.json``.

JSON Schema enforces shape; this module enforces the cross-field semantics
from design sections 1/4:

- Supported logical schema majors (v2 read compatibility and v3 production).
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
- Legacy read compatibility: an already-published schema-v2 artifact remains
  consumable under its original freshness contract; producers write the v3
  availability-capable form.
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
from ..config.model import FreshnessContract
from ..schema import SchemaError, validate_against
from .freshness import FreshnessError, evaluate_freshness

FEED_SCHEMA = "feed.schema.json"
SUPPORTED_FEED_MAJOR = 3
SUPPORTED_FEED_MAJORS = (2, 3)
PREVIOUS_FEED_MAJOR = 2

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

    if feed.get("schema_version") not in SUPPORTED_FEED_MAJORS:
        raise SchemaError(f"unsupported Feed schema_version {feed.get('schema_version')!r}")
    if feed.get("schema_version") in {PREVIOUS_FEED_MAJOR, SUPPORTED_FEED_MAJOR}:
        if feed.get("schema_version") == SUPPORTED_FEED_MAJOR:
            _validate_availability_outcomes(feed)
        _validate_freshness_outcomes(feed)

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

    # Stable serialization: supported semantic-identity Feeds contain exactly
    # one provider outcome per provider in ascending provider_id order.
    previous_id: str | None = None
    seen_provider_ids: set[str] = set()
    for outcome in feed.get("provider_outcomes", []):
        pid = outcome.get("provider_id")
        if pid in seen_provider_ids:
            raise SchemaError(
                "provider_outcomes contain duplicate provider_id; order is not ascending provider_id"
            )
        seen_provider_ids.add(pid)
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

    # Calendar horizon covers [cutoff, cutoff + 26h] when present.
    _validate_calendar_horizon(feed)


def _is_blocked_exempt(outcome: Mapping[str, Any]) -> bool:
    return (
        outcome.get("availability") == "blocked"
        and outcome.get("upstream_http_status") in {401, 403}
        and outcome.get("state") == "failed"
        and outcome.get("accepted") == 0
        and outcome.get("rejected") == 0
    )


def _configured_coverage_groups(feed: Mapping[str, Any], provider_id: str) -> list[str]:
    feed_config = feed.get("feed_config")
    snapshot = feed_config.get("snapshot") if isinstance(feed_config, Mapping) else None
    coverage = snapshot.get("coverage") if isinstance(snapshot, Mapping) else None
    if coverage is None:
        return []
    if not isinstance(coverage, list):
        raise SchemaError("feed_config.snapshot.coverage is invalid")
    groups: set[str] = set()
    for index, row in enumerate(coverage):
        if not isinstance(row, Mapping):
            raise SchemaError(f"feed_config.snapshot.coverage[{index}] is invalid")
        group = row.get("group")
        members = row.get("members")
        if (
            not isinstance(group, str)
            or not isinstance(members, list)
            or any(not isinstance(member, str) for member in members)
        ):
            raise SchemaError(f"feed_config.snapshot.coverage[{index}] is invalid")
        if provider_id in members:
            groups.add(group)
    return sorted(groups)


def _validate_availability_outcomes(feed: Mapping[str, Any]) -> None:
    """Validate v3 availability fields and their pipeline/coverage semantics."""
    contracts = {
        entry.get("provider_id"): entry.get("snapshot")
        for entry in feed.get("provider_contracts", [])
        if isinstance(entry, Mapping)
    }
    complete_ids: set[str] = set()
    blocked_ids: set[str] = set()
    seen_ids: set[str] = set()
    item_provider_ids = {
        item.get("provider_id") for item in feed.get("items", []) if isinstance(item, Mapping)
    }
    for index, outcome in enumerate(feed.get("provider_outcomes", [])):
        provider_id = outcome.get("provider_id")
        if not isinstance(provider_id, str):
            raise SchemaError(f"provider_outcomes[{index}].provider_id is invalid")
        if provider_id in seen_ids:
            raise SchemaError("provider_outcomes contain duplicate provider_id")
        seen_ids.add(provider_id)
        state = outcome.get("state")
        flags = {
            "succeeded": state in {"healthy", "empty", "partial"},
            "empty": state == "empty",
            "partial": state == "partial",
            "failed": state == "failed",
            "skipped": state == "skipped",
        }
        if any(outcome.get(key) is not value for key, value in flags.items()):
            raise SchemaError(f"provider_outcomes[{index}] state flags disagree with state")

        availability = outcome.get("availability")
        reason = outcome.get("availability_reason")
        if reason is not None and len(reason.encode("utf-8")) > 256:
            raise SchemaError(f"provider_outcomes[{index}].availability_reason is too long")
        status = outcome.get("upstream_http_status")
        if status is not None and outcome.get("retrieved_at") is None:
            raise SchemaError(
                f"provider_outcomes[{index}].upstream_http_status requires retrieved_at"
            )
        snapshot = contracts.get(provider_id)
        empty_permitted = (
            isinstance(snapshot, Mapping) and snapshot.get("empty_valid_for_window") is True
        )
        complete = state == "healthy" or (state == "empty" and empty_permitted)

        if availability == "disabled":
            raise SchemaError("disabled Provider cannot have a planned outcome")
        if availability == "success":
            if not complete or reason is not None or status is not None:
                raise SchemaError("availability=success disagrees with Provider outcome")
        elif availability == "blocked":
            if status not in {401, 403} or state not in {"failed", "partial"}:
                raise SchemaError("availability=blocked requires HTTP 401/403 and incomplete work")
            if not isinstance(reason, str) or not reason or str(status) not in reason:
                raise SchemaError(
                    "blocked availability requires a reason identifying its HTTP status"
                )
            if (
                state == "failed"
                and outcome.get("accepted") == 0
                and outcome.get("rejected", 0) > 0
            ):
                raise SchemaError("blocked availability cannot contain rejected data")
            if _is_blocked_exempt(outcome):
                blocked_ids.add(provider_id)
                if provider_id in item_provider_ids:
                    raise SchemaError("blocked-exempt Provider cannot retain evidence items")
        elif availability == "failed":
            if complete or status in {401, 403}:
                raise SchemaError("availability=failed disagrees with Provider outcome")
        else:
            raise SchemaError("Provider availability is invalid")

        expected_groups = _configured_coverage_groups(feed, provider_id)
        groups = outcome.get("affected_coverage_groups")
        if groups != sorted(set(groups)) or groups != expected_groups:
            raise SchemaError(
                f"provider_outcomes[{index}].affected_coverage_groups does not match configuration"
            )
        if complete:
            complete_ids.add(provider_id)

    pipeline_status = feed["pipeline"]["status"]
    if pipeline_status == "degraded" and not blocked_ids:
        raise SchemaError("pipeline.status=degraded requires a blocked-exempt Provider")
    if blocked_ids and pipeline_status == "healthy":
        raise SchemaError("blocked-exempt Provider requires pipeline.status=degraded")

    for outcome in feed.get("provider_outcomes", []):
        if (
            not (
                outcome.get("state") in {"healthy", "empty"}
                and outcome.get("provider_id") in complete_ids
            )
            and outcome.get("provider_id") not in blocked_ids
            and pipeline_status != "failure"
        ):
            raise SchemaError("incomplete Provider work requires pipeline.status=failure")

    feed_config = feed.get("feed_config")
    config_snapshot = feed_config.get("snapshot") if isinstance(feed_config, Mapping) else None
    coverage = config_snapshot.get("coverage") if isinstance(config_snapshot, Mapping) else None
    if coverage is not None and not isinstance(coverage, list):
        raise SchemaError("feed_config.snapshot.coverage is invalid")
    for index, row in enumerate(coverage or []):
        if not isinstance(row, Mapping):
            raise SchemaError(f"feed_config.snapshot.coverage[{index}] is invalid")
        members = row.get("members", [])
        minimum = row.get("minimum")
        if (
            not isinstance(members, list)
            or not isinstance(minimum, int)
            or isinstance(minimum, bool)
        ):
            raise SchemaError(f"feed_config.snapshot.coverage[{index}] is invalid")
        blocked_count = sum(1 for member in members if member in blocked_ids)
        effective_minimum = max(0, minimum - blocked_count)
        complete_count = sum(1 for member in members if member in complete_ids)
        if (
            pipeline_status != "failure"
            and row.get("optional") is not True
            and complete_count < effective_minimum
        ):
            raise SchemaError(f"coverage group {row.get('group')!r} is below its effective minimum")


def _validate_freshness_outcomes(feed: Mapping[str, Any]) -> None:
    """Validate the closed v2/v3 freshness result and its nullability rules."""
    contracts: dict[str, Mapping[str, Any]] = {}
    resolved_contracts: dict[str, FreshnessContract] = {}
    previous_contract_id: str | None = None
    for index, entry in enumerate(feed.get("provider_contracts", [])):
        if not isinstance(entry, Mapping):
            raise SchemaError(f"provider_contracts[{index}] is invalid")
        provider_id = entry.get("provider_id")
        if not isinstance(provider_id, str) or not provider_id:
            raise SchemaError(f"provider_contracts[{index}].provider_id is invalid")
        if provider_id in contracts or (
            previous_contract_id is not None and provider_id <= previous_contract_id
        ):
            raise SchemaError("Provider contracts must be unique and ordered by provider_id")
        previous_contract_id = provider_id
        snapshot = entry.get("snapshot")
        if not isinstance(snapshot, Mapping) or snapshot.get("provider_id") != provider_id:
            raise SchemaError("embedded Provider contract identity is invalid")
        if entry.get("hash") != canonical_digest(snapshot):
            raise SchemaError("embedded Provider contract hash does not match its snapshot")
        contract_freshness = snapshot.get("freshness")
        if not isinstance(contract_freshness, Mapping):
            raise SchemaError("embedded Provider contract is missing freshness")
        contract_cadence = contract_freshness.get("cadence")
        contract_reference = contract_freshness.get("reference_time")
        valid_for = contract_freshness.get("valid_for_seconds")
        if not isinstance(contract_cadence, str) or contract_cadence not in {
            "weekly",
            "scheduled",
            "event_driven",
            "market_session",
        }:
            raise SchemaError("embedded Provider freshness cadence is invalid")
        if not isinstance(contract_reference, str) or contract_reference not in {
            "data_as_of",
            "source_updated_at",
            "checked_at",
        }:
            raise SchemaError("embedded Provider freshness reference_time is invalid")
        if contract_cadence == "event_driven":
            if set(contract_freshness) != {"cadence", "reference_time"}:
                raise SchemaError("embedded Provider event_driven contract is not closed")
            if contract_reference != "checked_at":
                raise SchemaError("embedded event_driven contract is invalid")
        else:
            if set(contract_freshness) != {
                "cadence",
                "reference_time",
                "valid_for_seconds",
            }:
                raise SchemaError("embedded Provider bounded contract is not closed")
            if contract_reference == "checked_at":
                raise SchemaError("embedded bounded contract cannot use checked_at")
            if contract_cadence == "market_session" and contract_reference != "data_as_of":
                raise SchemaError("embedded market_session contract must use data_as_of")
            if isinstance(valid_for, bool) or not isinstance(valid_for, int) or valid_for <= 0:
                raise SchemaError("embedded bounded contract needs a positive validity window")
        contracts[provider_id] = entry
        resolved_contracts[provider_id] = FreshnessContract(
            cadence=contract_cadence,
            reference_time=contract_reference,
            valid_for_seconds=valid_for,
        )

    items_by_provider: dict[str, list[Mapping[str, Any]]] = {}
    for item in feed.get("items", []):
        if isinstance(item, Mapping) and isinstance(item.get("provider_id"), str):
            items_by_provider.setdefault(item["provider_id"], []).append(item)
    seen: set[str] = set()
    for index, outcome in enumerate(feed.get("provider_outcomes", [])):
        freshness = outcome.get("freshness")
        if not isinstance(freshness, Mapping):
            raise SchemaError(f"provider_outcomes[{index}].freshness is required")
        cadence = freshness.get("cadence")
        status = freshness.get("status")
        origin = freshness.get("origin_contract_hash")
        carried = freshness.get("carried_forward_from_run_id")
        if cadence not in {"weekly", "scheduled", "event_driven", "market_session"}:
            raise SchemaError(f"provider_outcomes[{index}].freshness.cadence is invalid")
        if status not in {"fresh", "valid_unchanged", "stale", "no_snapshot", "not_evaluated"}:
            raise SchemaError(f"provider_outcomes[{index}].freshness.status is invalid")
        if origin is not None and (
            not isinstance(origin, str) or not re.fullmatch(r"[0-9a-f]{64}", origin)
        ):
            raise SchemaError(
                f"provider_outcomes[{index}].freshness.origin_contract_hash is invalid"
            )
        if carried is not None and (not isinstance(carried, str) or not carried):
            raise SchemaError(
                f"provider_outcomes[{index}].freshness.carried_forward_from_run_id is invalid"
            )
        if status in {"no_snapshot", "not_evaluated"} and (
            origin is not None or carried is not None
        ):
            raise SchemaError(
                f"provider_outcomes[{index}].freshness {status} must have null provenance"
            )
        if status == "fresh" and (origin is None or carried is not None):
            raise SchemaError(
                "fresh freshness must have origin_contract_hash and no carry-forward run"
            )
        if status == "valid_unchanged" and (origin is None or carried is None):
            raise SchemaError("valid_unchanged freshness must identify its carried slice")
        if status == "stale" and origin is None:
            raise SchemaError("stale freshness must identify its originating contract")
        provider_id = outcome.get("provider_id")
        if provider_id in seen:
            raise SchemaError("provider_outcomes contain duplicate provider_id")
        seen.add(provider_id)
        contract = contracts.get(provider_id)
        resolved_contract = resolved_contracts.get(provider_id)
        if contract is None or resolved_contract is None:
            raise SchemaError("Provider outcome has no matching embedded Provider contract")
        snapshot = contract["snapshot"]
        complete = outcome.get("state") == "healthy" or (
            outcome.get("state") == "empty" and snapshot.get("empty_valid_for_window") is True
        )
        if not complete and status != "not_evaluated":
            raise SchemaError("incomplete Provider outcomes must be not_evaluated")
        if complete and status == "not_evaluated":
            raise SchemaError("not_evaluated requires incomplete Provider work")
        if resolved_contract.cadence != cadence:
            raise SchemaError("freshness cadence does not match embedded Provider contract")
        contract_hash = contract.get("hash")
        if status in {"fresh", "stale"} and carried is None and origin != contract_hash:
            raise SchemaError("current freshness origin does not match embedded Provider contract")
        if (
            status == "not_evaluated"
            and feed["pipeline"]["status"] != "failure"
            and not _is_blocked_exempt(outcome)
        ):
            raise SchemaError("incomplete Provider work requires pipeline.status=failure")

        selected_items = items_by_provider.get(provider_id, [])
        if status == "not_evaluated":
            # Incomplete runs may retain current accepted evidence for
            # diagnostics, but it is never a selected snapshot.
            continue
        if not selected_items:
            if status != "no_snapshot":
                raise SchemaError("freshness with no Provider items must be no_snapshot")
        elif resolved_contract is not None:
            try:
                expected = evaluate_freshness(
                    selected_items,
                    resolved_contract,
                    feed["evidence_cutoff_at"],
                    carried_forward=carried is not None,
                    checked_at=outcome.get("retrieved_at"),
                )
            except FreshnessError as exc:
                raise SchemaError(f"invalid Provider freshness authority: {exc}") from exc
            if status != expected:
                raise SchemaError(
                    f"freshness status {status!r} does not match selected Provider slice ({expected!r})"
                )

    unknown_item_providers = set(items_by_provider) - seen
    if unknown_item_providers:
        raise SchemaError("Feed items have no matching Provider outcome")
    if set(contracts) != seen:
        raise SchemaError("Provider contracts do not exactly match Provider outcomes")


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


def assert_feed_identity(feed: Mapping[str, Any]) -> None:
    """Fail closed unless the embedded identity matches the semantic projection exactly."""
    digest, run_id = recompute_feed_identity(feed)
    if feed.get("content_digest") != digest:
        raise SchemaError("content_digest does not match canonical projection")
    if feed.get("run_id") != run_id:
        raise SchemaError("run_id does not derive from cutoff+digest")
