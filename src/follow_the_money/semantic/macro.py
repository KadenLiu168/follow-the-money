"""Pure NBS macro-release semantic-context mapping."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..schema import SchemaError
from .context import SemanticContext
from .numeric import canonicalize_numeric

NBS_SERIES = {
    "cn_industrial_production_yoy": "Industrial Production Year-over-Year",
}


def _period(payload: Mapping[str, Any]) -> str | None:
    raw = payload.get("observation_period")
    if raw is None:
        return None
    if not isinstance(raw, Mapping) or not isinstance(raw.get("period"), str):
        raise SchemaError("macro_release.observation_period is invalid")
    return raw["period"]


def _numeric_fact(role: str, value: Any, *, where: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise SchemaError(f"{where}: numeric value is missing")
    unit = value.get("unit")
    if not isinstance(unit, str) or not unit.strip():
        raise SchemaError(f"{where}.unit: unit is required")
    raw_value = value.get("value")
    unknown_reason = value.get("unknown_reason")
    if raw_value is None:
        if unknown_reason is None:
            unknown_reason = "missing"
        return {
            "metric": "observation",
            "role": role,
            "value": None,
            "unit": unit,
            "unknown_reason": unknown_reason,
        }
    return {
        "metric": "observation",
        "role": role,
        "value": canonicalize_numeric(raw_value, where=f"{where}.value"),
        "unit": unit,
        "unknown_reason": None,
    }


def _validate_units(facts: list[dict[str, Any]]) -> None:
    units = {fact["unit"] for fact in facts if fact["unknown_reason"] != "incompatible_unit"}
    if len(units) > 1:
        raise SchemaError("macro_release numeric facts use incompatible units")


def _revision(
    source_record: Mapping[str, Any], period: str | None
) -> tuple[dict[str, Any], list[dict[str, Any]]] | None:
    candidate = source_record.get("revision")
    if not isinstance(candidate, Mapping) or candidate.get("period") != period or period is None:
        return None
    previous = candidate.get("previous")
    revised = candidate.get("revised")
    unit = candidate.get("unit")
    if (
        not isinstance(unit, str)
        or not isinstance(previous, (str, int, float))
        or not isinstance(revised, (str, int, float))
    ):
        raise SchemaError(
            "macro_release.revision must contain same-period previous and revised values"
        )
    previous_value = canonicalize_numeric(previous, where="macro_release.revision.previous")
    revised_value = canonicalize_numeric(revised, where="macro_release.revision.revised")
    revision = {
        "previous": {"value": previous_value, "unit": unit},
        "revised": {"value": revised_value, "unit": unit},
    }
    facts = [
        {
            "metric": "observation",
            "role": "revision_previous",
            "value": previous_value,
            "unit": unit,
            "unknown_reason": None,
        },
        {
            "metric": "observation",
            "role": "revision_revised",
            "value": revised_value,
            "unit": unit,
            "unknown_reason": None,
        },
    ]
    return revision, facts


def build_macro_context(
    provider_id: str,
    payload: Mapping[str, Any],
    source_record: Mapping[str, Any],
) -> SemanticContext:
    """Build one closed context from one normalized NBS macro release."""
    if provider_id != "nbs":
        raise SchemaError(f"macro semantic mapping does not support Provider {provider_id!r}")
    if payload.get("type") != "macro_release":
        raise SchemaError("macro semantic mapping requires a macro_release payload")
    series_id = payload.get("series_id")
    if series_id not in NBS_SERIES:
        raise SchemaError(
            f"macro_release.series_id is outside the closed NBS vocabulary: {series_id!r}"
        )
    period = _period(payload)
    facts = [
        _numeric_fact("actual", payload.get("actual"), where="macro_release.actual"),
        _numeric_fact("consensus", payload.get("consensus"), where="macro_release.consensus"),
        _numeric_fact("previous", payload.get("previous"), where="macro_release.previous"),
    ]
    revision = _revision(source_record, period)
    revision_value = revision[0] if revision is not None else None
    if revision is not None:
        facts.extend(revision[1])
    _validate_units(facts)
    context = {
        "version": 1,
        "entities": [{"role": "subject", "name": "国家统计局", "type": "organization"}],
        "event": {
            "category": "official_statistical_release",
            "occurred_at": payload.get("released_at"),
        },
        "numeric_facts": facts,
        "extension": {
            "type": "macro_release",
            "indicator": {"id": series_id, "name": NBS_SERIES[series_id]},
            "period": {"period": period} if period is not None else None,
            "revision": revision_value,
        },
    }
    return SemanticContext.from_dict(context)


map_macro_context = build_macro_context

__all__ = ["NBS_SERIES", "build_macro_context", "map_macro_context"]
