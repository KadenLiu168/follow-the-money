"""Deterministic Provider snapshot reference-time and freshness rules."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

from ..config.model import FreshnessContract


class FreshnessError(ValueError):
    """A Provider slice has no valid cadence authority."""


_DATA_AS_OF_FIELDS = {
    "macro_release": ("released_at",),
    "flow": ("as_of",),
    "positioning": ("as_of",),
    "filing": ("filed_at",),
    "calendar": ("scheduled_at",),
}


def parse_reference_timestamp(value: object, where: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise FreshnessError(f"{where}: missing reference timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise FreshnessError(f"{where}: invalid reference timestamp {value!r}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise FreshnessError(f"{where}: reference timestamp must carry a timezone")
    return parsed.astimezone(UTC)


def payload_reference_times(item: Mapping[str, Any]) -> tuple[datetime, ...]:
    payload = item.get("payload")
    if not isinstance(payload, Mapping):
        raise FreshnessError("item payload is missing")
    payload_type = payload.get("type")
    if payload_type == "market_data":
        observations = payload.get("observations")
        if not isinstance(observations, list) or not observations:
            raise FreshnessError("market_data has no observations")
        return tuple(
            parse_reference_timestamp(obs.get("as_of"), "market_data.observations[].as_of")
            for obs in observations
            if isinstance(obs, Mapping)
        )
    if payload_type == "news":
        value = payload.get("occurred_at")
        return (parse_reference_timestamp(value, "news.occurred_at"),)
    if payload_type == "policy":
        value = payload.get("effective_at")
        if value is None:
            value = payload.get("announced_at")
        return (parse_reference_timestamp(value, "policy.effective_at/announced_at"),)
    fields = _DATA_AS_OF_FIELDS.get(str(payload_type))
    if fields is None:
        raise FreshnessError(f"unsupported payload type for data_as_of: {payload_type!r}")
    value = next((payload.get(field) for field in fields if payload.get(field) is not None), None)
    return (parse_reference_timestamp(value, f"{payload_type}.{fields[0]}"),)


def source_reference_time(item: Mapping[str, Any]) -> datetime:
    source = item.get("source")
    if not isinstance(source, Mapping):
        raise FreshnessError("item source is missing")
    value = source.get("updated_at")
    if value is None:
        value = source.get("published_at")
    return parse_reference_timestamp(value, "source.updated_at/published_at")


def reference_time_for_item(
    item: Mapping[str, Any],
    reference_time: str,
    *,
    checked_at: str | None = None,
) -> datetime:
    if reference_time == "data_as_of":
        return max(payload_reference_times(item))
    if reference_time == "source_updated_at":
        return source_reference_time(item)
    if reference_time == "checked_at":
        return parse_reference_timestamp(checked_at, "checked_at")
    raise FreshnessError(f"unsupported reference_time: {reference_time!r}")


def evaluate_freshness(
    items: Sequence[Mapping[str, Any]],
    contract: FreshnessContract,
    evidence_cutoff_at: str | datetime,
    *,
    carried_forward: bool = False,
    checked_at: str | None = None,
) -> str:
    """Return the closed freshness status for one selected Provider slice."""
    if not items:
        raise FreshnessError("cannot evaluate freshness without a selected snapshot")
    cutoff = (
        parse_reference_timestamp(evidence_cutoff_at, "evidence_cutoff_at")
        if isinstance(evidence_cutoff_at, str)
        else evidence_cutoff_at.astimezone(UTC)
    )
    if not isinstance(evidence_cutoff_at, str) and (
        evidence_cutoff_at.tzinfo is None or evidence_cutoff_at.utcoffset() is None
    ):
        raise FreshnessError("evidence_cutoff_at must carry a timezone")
    if contract.cadence not in {"weekly", "scheduled", "event_driven", "market_session"}:
        raise FreshnessError(f"unsupported cadence: {contract.cadence!r}")
    if contract.reference_time not in {"data_as_of", "source_updated_at", "checked_at"}:
        raise FreshnessError(f"unsupported reference_time: {contract.reference_time!r}")
    if contract.cadence == "event_driven":
        if contract.reference_time != "checked_at" or contract.valid_for_seconds is not None:
            raise FreshnessError("event_driven contract must use checked_at without an age window")
        checked = parse_reference_timestamp(checked_at, "checked_at")
        if checked < cutoff:
            raise FreshnessError("checked_at precedes evidence_cutoff_at")
        return "valid_unchanged" if carried_forward else "fresh"

    if contract.valid_for_seconds is None or contract.valid_for_seconds <= 0:
        raise FreshnessError("bounded cadence requires a positive validity window")
    if contract.cadence == "market_session" and contract.reference_time != "data_as_of":
        raise FreshnessError("market_session must use data_as_of")
    if contract.reference_time == "checked_at":
        raise FreshnessError("bounded cadence cannot use checked_at")
    references = [
        reference_time_for_item(item, contract.reference_time, checked_at=checked_at)
        for item in items
    ]
    latest = max(references)
    if latest > cutoff:
        raise FreshnessError("reference time is after evidence_cutoff_at")
    stale = cutoff - latest > timedelta(seconds=contract.valid_for_seconds)
    if stale:
        return "stale"
    return "valid_unchanged" if carried_forward else "fresh"


# Short aliases keep the mapping/evaluator seam obvious to callers.
resolve_reference_time = reference_time_for_item
assess_freshness = evaluate_freshness
