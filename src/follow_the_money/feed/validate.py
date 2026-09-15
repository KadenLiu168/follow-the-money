"""Semantic Feed validation on top of ``feed.schema.json``.

JSON Schema enforces shape; this module enforces the cross-field semantics
from design sections 1/4:

- Supported logical schema majors (v3 read compatibility and v4 production).
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
- Legacy read compatibility: an already-published schema-v3 Feed remains
  available only to the bounded migration path; producers write the v4
  availability-capable five-domain form.
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
from decimal import Decimal, InvalidOperation
from typing import Any

from ..canonical import canonical_digest
from ..config.model import REQUIRED_COVERAGE_GROUPS, FreshnessContract
from ..schema import SchemaError, validate_against
from .freshness import FreshnessError, evaluate_freshness

FEED_SCHEMA = "feed.schema.json"
SUPPORTED_FEED_MAJOR = 4
SUPPORTED_FEED_MAJORS = (3, 4)
PREVIOUS_FEED_MAJOR = 3
REQUIRED_PROVIDER_IDS = frozenset(
    {
        "federal_reserve",
        "bls",
        "pboc",
        "nbs",
        "sse",
        "szse",
        "sec_edgar",
        "cftc",
    }
)
SUPPORTED_PAYLOAD_TYPES = frozenset({"news", "macro_release", "policy", "positioning", "filing"})

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


def _is_true(value: Any) -> bool:
    return isinstance(value, bool) and value


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


def validate_feed(feed: Mapping[str, Any], *, allow_previous: bool = False) -> None:
    """Full semantic validation of the current Feed object.

    The previous major is accepted only by explicit bounded migration callers.
    """
    validate_against(FEED_SCHEMA, feed)

    schema_version = feed.get("schema_version")
    if schema_version not in SUPPORTED_FEED_MAJORS:
        raise SchemaError(f"unsupported Feed schema_version {schema_version!r}")
    if schema_version == PREVIOUS_FEED_MAJOR and not allow_previous:
        raise SchemaError("previous Feed schema requires bounded migration")
    if schema_version in {PREVIOUS_FEED_MAJOR, SUPPORTED_FEED_MAJOR}:
        _validate_availability_outcomes(feed)
    if schema_version == SUPPORTED_FEED_MAJOR:
        _validate_five_domain_surface(feed)
        _validate_versioned_semantics(feed)
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
    _validate_numerics(feed.get("items", []), legacy=schema_version == PREVIOUS_FEED_MAJOR)

    # No intelligence fields inside items.
    for item in feed.get("items", []):
        payload = item.get("payload", {})
        for key in _FORBIDDEN_INTELLIGENCE_KEYS:
            if key in payload:
                raise SchemaError(f"intelligence field {key!r} rejected in Feed item")

    # The v3 migration input may carry legacy calendar metadata; v4 cannot.
    if schema_version == PREVIOUS_FEED_MAJOR:
        _validate_calendar_horizon(feed)


def _validate_five_domain_surface(feed: Mapping[str, Any]) -> None:
    """Enforce the closed v4 Provider and payload surface."""
    if "calendar_horizon_end" in feed:
        raise SchemaError("v4 Feed must not contain calendar_horizon_end")

    raw_contracts = feed.get("provider_contracts")
    raw_outcomes = feed.get("provider_outcomes")
    if not isinstance(raw_contracts, list) or not isinstance(raw_outcomes, list):
        raise SchemaError("v4 Feed Provider contracts and outcomes must be lists")
    contracts: list[Any] = raw_contracts
    outcomes: list[Any] = raw_outcomes
    contract_ids = {entry.get("provider_id") for entry in contracts if isinstance(entry, Mapping)}
    outcome_ids = {
        outcome.get("provider_id") for outcome in outcomes if isinstance(outcome, Mapping)
    }
    if contract_ids != REQUIRED_PROVIDER_IDS or outcome_ids != REQUIRED_PROVIDER_IDS:
        raise SchemaError("v4 Feed must contain exactly the eight required Providers")

    payload_types_by_provider: dict[str, set[str]] = {}
    for index, entry in enumerate(contracts):
        snapshot = entry.get("snapshot") if isinstance(entry, Mapping) else None
        provider_id = entry.get("provider_id") if isinstance(entry, Mapping) else None
        if not isinstance(provider_id, str) or not isinstance(snapshot, Mapping):
            raise SchemaError(f"provider_contracts[{index}] is invalid")
        version = snapshot.get("contract_version", 1)
        if isinstance(version, bool) or not isinstance(version, int):
            raise SchemaError(f"provider_contracts[{index}] contract_version is invalid")
        from ..providers.manifest import SUPPORTED_CONTRACT_VERSIONS

        if version not in SUPPORTED_CONTRACT_VERSIONS.get(provider_id, frozenset()):
            raise SchemaError(
                f"provider_contracts[{index}] unsupported contract version for {provider_id!r}"
            )
        payload_types = snapshot.get("payload_types")
        if (
            not isinstance(payload_types, list)
            or not payload_types
            or any(payload not in SUPPORTED_PAYLOAD_TYPES for payload in payload_types)
        ):
            raise SchemaError(f"provider_contracts[{index}] declares a removed payload domain")
        removed_contract_fields = {
            "calendar_capability",
            "calendar_horizon_end",
            "calendar_horizon_hours",
            "flow",
            "market_data",
            "market_lookback_hours",
            "market_roles",
            "role_mappings",
            "adjustment_policy",
            "max_observations",
            "availability_lag_seconds",
            "yahoo_market",
        }
        if removed_contract_fields.intersection(snapshot):
            raise SchemaError(
                f"provider_contracts[{index}] contains removed market/calendar contract fields"
            )
        if provider_id in payload_types_by_provider:
            raise SchemaError("v4 Provider contracts contain duplicate provider IDs")
        payload_types_by_provider[provider_id] = set(payload_types)

    feed_config = feed.get("feed_config")
    snapshot = feed_config.get("snapshot") if isinstance(feed_config, Mapping) else None
    if not isinstance(snapshot, Mapping):
        raise SchemaError("v4 Feed configuration snapshot is invalid")
    coverage = snapshot.get("coverage")
    if not isinstance(coverage, list):
        raise SchemaError("v4 Feed configuration must contain a coverage snapshot")
    groups = {row.get("group") for row in coverage if isinstance(row, Mapping)}
    if groups != REQUIRED_COVERAGE_GROUPS:
        raise SchemaError("v4 Feed coverage must contain exactly the five required groups")
    removed_config_fields = {
        "calendar",
        "calendar_horizon_end",
        "calendar_horizon_hours",
        "flow",
        "market_data",
        "market_lookback_hours",
        "market_roles",
        "role_mappings",
        "sessions",
        "yahoo_market",
    }
    if removed_config_fields.intersection(snapshot):
        raise SchemaError("v4 Feed configuration contains removed fields")
    feed_limits = snapshot.get("feed")
    if isinstance(feed_limits, Mapping) and removed_config_fields.intersection(feed_limits):
        raise SchemaError("v4 Feed configuration contains removed fields")
    for index, row in enumerate(coverage):
        if not isinstance(row, Mapping):
            raise SchemaError(f"feed_config.snapshot.coverage[{index}] is invalid")
        values = (row.get("group"), row.get("capability"))
        if any(
            isinstance(value, str)
            and any(term in value.lower() for term in ("calendar", "flow", "market", "yahoo"))
            for value in values
        ):
            raise SchemaError("v4 Feed coverage contains a removed claim")

    for index, item in enumerate(feed.get("items", [])):
        payload = item.get("payload") if isinstance(item, Mapping) else None
        provider_id = item.get("provider_id") if isinstance(item, Mapping) else None
        if not isinstance(payload, Mapping) or payload.get("type") not in SUPPORTED_PAYLOAD_TYPES:
            raise SchemaError(f"items[{index}] uses a removed Feed payload domain")
        if not isinstance(provider_id, str):
            raise SchemaError(f"items[{index}].provider_id is invalid")
        if payload.get("type") not in payload_types_by_provider.get(provider_id, set()):
            raise SchemaError(f"items[{index}] is outside its Provider payload contract")


def _decimal(value: Any, *, where: str, unit: str | None = None) -> Decimal:
    if not isinstance(value, Mapping) or not isinstance(value.get("value"), str):
        raise SchemaError(f"{where}: typed canonical numeric value is required")
    if unit is not None and value.get("unit") != unit:
        raise SchemaError(f"{where}: unit must be {unit!r}")
    validate_canonical_numeric(value["value"], where=f"{where}.value")
    try:
        number = Decimal(value["value"])
    except InvalidOperation as exc:
        raise SchemaError(f"{where}: numeric value is invalid") from exc
    if not number.is_finite():
        raise SchemaError(f"{where}: numeric value is not finite")
    return number


def _semantic_key(value: Mapping[str, Any]) -> tuple[str, str, str]:
    security = value["security"]
    return (
        security["cusip"],
        security["put_call"] or "",
        security["amount_type"],
    )


def _validate_value_normalization(
    descriptor: Any, filing_date: Any, units: Mapping[str, Any], where: str
) -> None:
    if not isinstance(descriptor, Mapping):
        raise SchemaError(f"{where}: value_normalization is required")
    source_unit = descriptor.get("source_unit")
    formula_id = descriptor.get("formula_id")
    expected = (
        ("usd_thousands", "identity")
        if filing_date < "2023-01-03"
        else ("usd", "usd_divided_by_1000")
    )
    if (source_unit, formula_id) != expected:
        raise SchemaError(f"{where}: value normalization does not match official filing date")
    expected_unit = "usd_thousands" if source_unit == "usd_thousands" else "usd"
    if (
        units.get(
            "13f_value_before_2023_01_03"
            if filing_date < "2023-01-03"
            else "13f_value_from_2023_01_03"
        )
        != expected_unit
        or units.get("reported_value_usd_thousands") != "usd_thousands"
    ):
        raise SchemaError(f"{where}: SEC v2 unit contract is inconsistent")


def _validate_sec_values(value: Any, *, where: str, nonnegative: bool) -> None:
    if not isinstance(value, Mapping):
        raise SchemaError(f"{where}: holding values must be an object")
    for field, expected_unit in (
        ("reported_amount", "shares"),
        ("reported_value_usd_thousands", "usd_thousands"),
    ):
        number = _decimal(value.get(field), where=f"{where}.{field}", unit=expected_unit)
        if nonnegative and number < 0:
            raise SchemaError(f"{where}.{field}: source value must be nonnegative")


def _validate_sec_v2_item(
    item: Mapping[str, Any], *, cutoff: datetime, units: Mapping[str, Any], where: str
) -> None:
    payload = item.get("payload")
    if not isinstance(payload, Mapping):
        raise SchemaError(f"{where}: filing payload is invalid")
    identity = payload.get("company_identity")
    if (
        not isinstance(identity, Mapping)
        or not isinstance(identity.get("cik"), str)
        or not re.fullmatch(r"\d{10}", identity["cik"])
        or not identity.get("name")
    ):
        raise SchemaError(f"{where}: official company identity is required")
    if payload.get("company") != identity["cik"] or payload.get("form") != "13F-HR":
        raise SchemaError(f"{where}: SEC company/form identity is invalid")
    report_period = payload.get("report_period")
    filed_at = payload.get("filed_at")
    accepted_at = payload.get("accepted_at")
    if not isinstance(report_period, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", report_period):
        raise SchemaError(f"{where}: report_period is invalid")
    if not isinstance(filed_at, str) or not isinstance(accepted_at, str):
        raise SchemaError(f"{where}: filing dates are required")
    filed_dt = _parse_ts(filed_at, f"{where}.filed_at")
    accepted_dt = _parse_ts(accepted_at, f"{where}.accepted_at")
    if accepted_dt >= cutoff:
        raise SchemaError(f"{where}: accepted_at must precede evidence cutoff")
    _validate_value_normalization(
        payload.get("value_normalization"),
        filed_dt.date().isoformat(),
        units,
        f"{where}.value_normalization",
    )
    comparison = payload.get("comparison")
    holdings = payload.get("holdings")
    if not isinstance(comparison, Mapping) or not isinstance(holdings, list):
        raise SchemaError(f"{where}: SEC v2 comparison and holdings are required")
    if comparison.get("status") not in {"available", "unavailable"}:
        raise SchemaError(f"{where}.comparison.status is invalid")
    has_previous = comparison["status"] == "available"
    previous_fields = (
        "previous_accession_number",
        "previous_report_period",
        "previous_accepted_at",
        "previous_filed_at",
        "previous_source_url",
        "previous_value_normalization",
    )
    for field_name in previous_fields:
        value = comparison.get(field_name)
        if has_previous and value is None:
            raise SchemaError(f"{where}.comparison.{field_name} is required when available")
        if not has_previous and value is not None:
            raise SchemaError(f"{where}.comparison.{field_name} must be null when unavailable")
    if has_previous:
        if comparison.get("reason") is not None:
            raise SchemaError(f"{where}.comparison.reason must be null when available")
        if comparison["previous_report_period"] == report_period:
            raise SchemaError(f"{where}: previous report period must differ")
        previous_filed = _parse_ts(
            comparison["previous_filed_at"], f"{where}.comparison.previous_filed_at"
        )
        _validate_value_normalization(
            comparison["previous_value_normalization"],
            previous_filed.date().isoformat(),
            units,
            f"{where}.comparison.previous_value_normalization",
        )
    elif comparison.get("reason") != "no_previous_comparable_filing":
        raise SchemaError(f"{where}.comparison.reason is invalid")

    current_keys: set[tuple[str, str, str]] = set()
    ordered_keys: list[tuple[str, str, str]] = []
    for index, row in enumerate(holdings):
        if not isinstance(row, Mapping) or not isinstance(row.get("security"), Mapping):
            raise SchemaError(f"{where}.holdings[{index}] is invalid")
        key = _semantic_key(row)
        if not re.fullmatch(r"[0-9A-Z*@#]{9}", key[0]):
            raise SchemaError(f"{where}.holdings[{index}].security.cusip is invalid")
        if ordered_keys and key <= ordered_keys[-1]:
            raise SchemaError(f"{where}.holdings are not ordered by canonical security key")
        ordered_keys.append(key)
        current = row.get("current")
        previous = row.get("previous")
        delta = row.get("delta")
        change = row.get("change_type")
        if current is not None:
            _validate_sec_values(
                current, where=f"{where}.holdings[{index}].current", nonnegative=True
            )
            current_keys.add(key)
        if previous is not None:
            _validate_sec_values(
                previous, where=f"{where}.holdings[{index}].previous", nonnegative=True
            )
        if delta is not None:
            _validate_sec_values(delta, where=f"{where}.holdings[{index}].delta", nonnegative=False)
        if not has_previous:
            if previous is not None or delta is not None or change is not None:
                raise SchemaError(
                    f"{where}.holdings[{index}] has comparison data without a previous filing"
                )
            continue
        if current is None and previous is None:
            raise SchemaError(f"{where}.holdings[{index}] has no current or previous side")
        if current is None:
            if delta is not None or change != "no_longer_reported":
                raise SchemaError(f"{where}.holdings[{index}] previous-only semantics are invalid")
        elif previous is None:
            if delta is not None or change != "new":
                raise SchemaError(f"{where}.holdings[{index}] current-only semantics are invalid")
        else:
            if not isinstance(delta, Mapping):
                raise SchemaError(f"{where}.holdings[{index}] matched delta is required")
            amount_delta = _decimal(
                delta["reported_amount"], where=f"{where}.holdings[{index}].delta.reported_amount"
            )
            value_delta = _decimal(
                delta["reported_value_usd_thousands"],
                where=f"{where}.holdings[{index}].delta.reported_value_usd_thousands",
                unit="usd_thousands",
            )
            current_amount = _decimal(
                current["reported_amount"],
                where=f"{where}.holdings[{index}].current.reported_amount",
            )
            previous_amount = _decimal(
                previous["reported_amount"],
                where=f"{where}.holdings[{index}].previous.reported_amount",
            )
            current_value = _decimal(
                current["reported_value_usd_thousands"],
                where=f"{where}.holdings[{index}].current.reported_value_usd_thousands",
                unit="usd_thousands",
            )
            previous_value = _decimal(
                previous["reported_value_usd_thousands"],
                where=f"{where}.holdings[{index}].previous.reported_value_usd_thousands",
                unit="usd_thousands",
            )
            if (
                amount_delta != current_amount - previous_amount
                or value_delta != current_value - previous_value
            ):
                raise SchemaError(f"{where}.holdings[{index}] delta is not current minus previous")
            if amount_delta > 0:
                expected_change = "increased"
            elif amount_delta < 0:
                expected_change = "decreased"
            else:
                expected_change = "unchanged"
            if change != expected_change:
                raise SchemaError(f"{where}.holdings[{index}] change_type must use reported amount")
    if not has_previous and current_keys != set(ordered_keys):
        raise SchemaError(f"{where}: unavailable comparison has invalid current holdings")


def _validate_cftc_metrics(
    value: Any, *, where: str, nonnegative_components: bool
) -> dict[str, Decimal]:
    if not isinstance(value, Mapping):
        raise SchemaError(f"{where}: CFTC metrics are required")
    fields = (
        "noncommercial_long",
        "noncommercial_short",
        "noncommercial_spreading",
        "open_interest",
        "net_noncommercial",
    )
    values: dict[str, Decimal] = {}
    for field in fields:
        number = _decimal(value.get(field), where=f"{where}.{field}", unit="contracts")
        if nonnegative_components and field != "net_noncommercial" and number < 0:
            raise SchemaError(f"{where}.{field}: source metric must be nonnegative")
        values[field] = number
    if values["net_noncommercial"] != values["noncommercial_long"] - values["noncommercial_short"]:
        raise SchemaError(f"{where}.net_noncommercial derivation is invalid")
    return values


def _validate_cftc_v2_item(item: Mapping[str, Any], *, where: str) -> str:
    payload = item.get("payload")
    if not isinstance(payload, Mapping):
        raise SchemaError(f"{where}: positioning payload is invalid")
    identity = payload.get("market_identity")
    if (
        not isinstance(identity, Mapping)
        or not isinstance(identity.get("cftc_contract_market_code"), str)
        or not identity["cftc_contract_market_code"].strip()
    ):
        raise SchemaError(f"{where}: market identity is required")
    code = identity["cftc_contract_market_code"]
    name = identity.get("contract_market_name")
    if not isinstance(name, str) or not name.strip():
        raise SchemaError(f"{where}: contract market name is required")
    current = _validate_cftc_metrics(
        payload.get("current_metrics"),
        where=f"{where}.current_metrics",
        nonnegative_components=True,
    )
    position = _decimal(payload.get("position"), where=f"{where}.position", unit="contracts")
    if position != current["noncommercial_long"]:
        raise SchemaError(f"{where}.position must equal current noncommercial long")
    raw_as_of = payload.get("as_of")
    if not isinstance(raw_as_of, str):
        raise SchemaError(f"{where}.as_of is invalid")
    as_of = _parse_ts(raw_as_of, f"{where}.as_of")
    previous = payload.get("previous_metrics")
    delta = payload.get("delta_metrics")
    comparison = payload.get("comparison")
    if not isinstance(comparison, Mapping) or comparison.get("status") not in {
        "available",
        "unavailable",
    }:
        raise SchemaError(f"{where}.comparison is invalid")
    if (
        payload.get("derivations", {}).get("net_noncommercial", {}).get("formula_id")
        != "noncommercial_long_minus_short"
    ):
        raise SchemaError(f"{where}: net derivation descriptor is invalid")
    if comparison["status"] == "unavailable":
        expected_reason = (
            "market_absent_from_previous_report"
            if comparison.get("previous_as_of") is not None
            else "no_previous_comparable_report"
        )
        if previous is not None or delta is not None or comparison.get("reason") != expected_reason:
            raise SchemaError(f"{where}: unavailable CFTC comparison is invalid")
    else:
        previous_values = _validate_cftc_metrics(
            previous, where=f"{where}.previous_metrics", nonnegative_components=True
        )
        delta_values = _validate_cftc_metrics(
            delta, where=f"{where}.delta_metrics", nonnegative_components=False
        )
        for field in current:
            if delta_values[field] != current[field] - previous_values[field]:
                raise SchemaError(f"{where}.delta_metrics.{field} is not current minus previous")
        if comparison.get("reason") is not None or comparison.get("previous_as_of") is None:
            raise SchemaError(f"{where}.comparison available fields are invalid")
        if _parse_ts(comparison["previous_as_of"], f"{where}.comparison.previous_as_of") >= as_of:
            raise SchemaError(f"{where}.comparison.previous_as_of must precede current as_of")
    return code


def _validate_versioned_semantics(feed: Mapping[str, Any]) -> None:
    contracts: dict[str, Mapping[str, Any]] = {}
    for entry in feed.get("provider_contracts", []):
        if not isinstance(entry, Mapping):
            continue
        provider_id = entry.get("provider_id")
        snapshot = entry.get("snapshot")
        if not isinstance(provider_id, str) or not isinstance(snapshot, Mapping):
            continue
        contracts[provider_id] = snapshot
    semantic_fields = {
        "sec_edgar": {
            "company_identity",
            "report_period",
            "accepted_at",
            "value_normalization",
            "comparison",
            "holdings",
        },
        "cftc": {
            "market_identity",
            "current_metrics",
            "previous_metrics",
            "delta_metrics",
            "comparison",
            "derivations",
        },
    }
    cutoff = _parse_ts(feed["evidence_cutoff_at"], "evidence_cutoff_at")
    items_by_provider: dict[str, list[Mapping[str, Any]]] = {}
    for item in feed.get("items", []):
        if isinstance(item, Mapping) and isinstance(item.get("provider_id"), str):
            items_by_provider.setdefault(item["provider_id"], []).append(item)
    # A Provider embedding a v2 contract must satisfy its contract-level
    # requirements even when the run retained no items for it; otherwise a
    # blocked-exempt or empty SEC/CFTC outcome would skip them entirely.
    v2_provider_ids = {
        provider_id
        for provider_id, contract in contracts.items()
        if contract.get("contract_version") == 2
    }
    for provider_id in sorted(set(items_by_provider) | v2_provider_ids):
        items = items_by_provider.get(provider_id, [])
        contract = contracts[provider_id]
        version = contract.get("contract_version", 1)
        if version == 1 and provider_id in semantic_fields:
            for item in items:
                payload = item.get("payload", {})
                if isinstance(payload, Mapping) and semantic_fields[provider_id].intersection(
                    payload
                ):
                    raise SchemaError(f"{provider_id} v1 item contains v2 semantic fields")
        if version != 2:
            continue
        if provider_id == "sec_edgar":
            units = contract.get("units")
            if not isinstance(units, Mapping) or set(units) != {
                "13f_value_before_2023_01_03",
                "13f_value_from_2023_01_03",
                "reported_value_usd_thousands",
            }:
                raise SchemaError("SEC v2 unit contract is missing or not closed")
            ciks: list[str] = []
            for item in items:
                _validate_sec_v2_item(
                    item, cutoff=cutoff, units=units, where=f"items[{item.get('id')!r}]"
                )
                ciks.append(item["payload"]["company_identity"]["cik"])
            if len(ciks) != len(set(ciks)):
                raise SchemaError("SEC v2 company CIKs are not unique")
            config = feed.get("feed_config", {}).get("snapshot", {})
            watched = config.get("watched_companies") if isinstance(config, Mapping) else None
            if not isinstance(watched, list) or any(
                not isinstance(row, Mapping) for row in watched
            ):
                raise SchemaError(
                    "SEC v2 requires watched_companies in feed configuration snapshot"
                )
            watched_ciks = [row.get("cik") for row in watched]
            if any(not isinstance(cik, str) or not cik for cik in watched_ciks):
                raise SchemaError("SEC v2 watched company CIK is invalid")
            outcome: Mapping[str, Any] = next(
                (
                    o
                    for o in feed.get("provider_outcomes", [])
                    if o.get("provider_id") == "sec_edgar"
                ),
                {},
            )
            watched_cik_set = set(watched_ciks)
            if not set(ciks).issubset(watched_cik_set):
                raise SchemaError("SEC v2 item CIK is outside watched companies")
            complete = outcome.get("state") == "healthy" or (
                outcome.get("state") == "empty" and _is_true(contract.get("empty_valid_for_window"))
            )
            if complete and set(ciks) != watched_cik_set:
                raise SchemaError("SEC v2 complete slice does not equal watched CIK set")
        elif provider_id == "cftc":
            if not isinstance(contract.get("units"), Mapping) or contract.get("units") != {
                "contracts": "contracts"
            }:
                raise SchemaError("CFTC v2 unit contract is missing or not closed")
            keys: list[str] = []
            for item in items:
                keys.append(_validate_cftc_v2_item(item, where=f"items[{item.get('id')!r}]"))
            if len(keys) != len(set(keys)):
                raise SchemaError("CFTC v2 market codes are not unique")
    # ``status`` is valid inside typed comparison objects; the top-level
    # check above still rejects it as an item payload field.
    forbidden = (_FORBIDDEN_INTELLIGENCE_KEYS - {"status"}) | {
        "bullish",
        "bearish",
        "crowded",
        "risk_on",
        "risk_off",
        "prediction",
    }

    def scan(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                if key in forbidden:
                    raise SchemaError(f"intelligence field {key!r} rejected in semantic payload")
                scan(child)
        elif isinstance(value, list):
            for child in value:
                scan(child)

    for item in feed.get("items", []):
        scan(item.get("payload", {}))


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
        empty_permitted = isinstance(snapshot, Mapping) and _is_true(
            snapshot.get("empty_valid_for_window")
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
            and not _is_true(row.get("optional"))
            and complete_count < effective_minimum
        ):
            raise SchemaError(f"coverage group {row.get('group')!r} is below its effective minimum")


def _validate_freshness_outcomes(feed: Mapping[str, Any]) -> None:
    """Validate the closed v3/v4 freshness result and its nullability rules."""
    legacy = feed.get("schema_version") == PREVIOUS_FEED_MAJOR
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
        allowed_cadences = {"weekly", "scheduled", "event_driven"}
        if legacy:
            allowed_cadences.add("market_session")
        if not isinstance(contract_cadence, str) or contract_cadence not in allowed_cadences:
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
        allowed_cadences = {"weekly", "scheduled", "event_driven"}
        if legacy:
            allowed_cadences.add("market_session")
        if cadence not in allowed_cadences:
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
            outcome.get("state") == "empty" and _is_true(snapshot.get("empty_valid_for_window"))
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
                    legacy=legacy,
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


def _validate_numerics(items: list[Any], *, legacy: bool = False) -> None:
    keys = ["actual", "consensus", "previous", "position"]
    if legacy:
        keys.append("net_flow")
    for idx, item in enumerate(items):
        payload = item.get("payload", {})
        where = f"items[{idx}].payload"
        for key in keys:
            value = payload.get(key)
            if isinstance(value, dict) and value.get("value") is not None:
                validate_canonical_numeric(str(value["value"]), where=f"{where}.{key}.value")
        if legacy:
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
