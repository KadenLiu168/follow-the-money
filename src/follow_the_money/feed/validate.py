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
import unicodedata
from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from follow_the_money.semantic import (  # pyright: ignore[reportMissingImports]
    subtract_canonical as _subtract_canonical,
)
from follow_the_money.semantic import (  # pyright: ignore[reportMissingImports]
    validate_canonical_numeric as _validate_canonical_numeric,
)
from follow_the_money.semantic import (
    validate_numeric_token as _validate_numeric_token,
)
from follow_the_money.semantic.context import SemanticContext
from follow_the_money.semantic.macro import build_macro_context
from follow_the_money.semantic.news import build_news_context
from follow_the_money.semantic.policy import build_policy_context

from ..canonical import canonical_digest
from ..config.model import REQUIRED_COVERAGE_GROUPS, FreshnessContract
from ..providers.http import stable_item_id
from ..providers.sec_form4 import FORM4_SCHEMA_VERSION
from ..providers.urls import sec_archive_cik
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

#: SEC Archive paths carry the unpadded integer CIK, the canonical form the
#: producers derive with ``providers.urls.sec_archive_cik``. Used where the
#: locator is checked for canonical shape; where the filer/issuer CIK is known
#: the regex is built from the helper itself.
_SEC_ARCHIVE_CIK_PATTERN = r"(?:0|[1-9][0-9]{0,9})"

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

# Numeric bounds and parsing authority live in follow_the_money.semantic.numeric.

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
    "sentiment",
    "confidence",
    "holding_delta",
    "transaction_value",
    "calculated_transaction_value",
    "inferred_holding_delta",
    "amendment_effectiveness",
    "amends_accession",
    "effective_version",
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
    """Compatibility entry point for the semantic numeric authority."""
    _validate_numeric_token(token, where=where)


def validate_canonical_numeric(value: str, *, where: str) -> None:
    """Compatibility entry point for the semantic numeric authority."""
    _validate_canonical_numeric(value, where=where)


def validate_feed(
    feed: Mapping[str, Any],
    *,
    allow_previous: bool = False,
    current_production: bool = False,
) -> None:
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
        _validate_semantic_contexts(feed, current_production=current_production)
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


_FORM4_REFERENCE_FIELDS = frozenset(
    {
        "security_title",
        "transaction_date",
        "deemed_execution_date",
        "transaction_form_type",
        "transaction_code",
        "equity_swap_involved",
        "timeliness",
        "transactionShares",
        "transactionTotalValue",
        "transactionPricePerShare",
        "transactionAcquiredDisposedCode",
        "exerciseDate",
        "expirationDate",
        "conversionOrExercisePrice",
        "underlyingSecurityTitle",
        "underlyingSecurityShares",
        "underlyingSecurityValue",
        "sharesOwnedFollowingTransaction",
        "valueOwnedFollowingTransaction",
        "directOrIndirectOwnership",
        "natureOfOwnership",
    }
)


def _form4_footnote_key(value: str) -> tuple[int, str]:
    return len(value), value


def _validate_form4_text(value: Any, *, where: str, max_length: int) -> None:
    if not isinstance(value, str) or not value.strip():
        raise SchemaError(f"{where}: Form 4 text is required")
    normalized = unicodedata.normalize("NFC", re.sub(r"\s+", " ", value).strip())
    if normalized != value or len(value) > max_length:
        raise SchemaError(f"{where}: Form 4 text is not normalized or bounded")


def _validate_form4_optional_text(value: Any, *, where: str, max_length: int) -> None:
    if value is not None:
        _validate_form4_text(value, where=where, max_length=max_length)


def _validate_form4_date(value: Any, *, where: str, required: bool = True) -> None:
    if value is None and not required:
        return
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise SchemaError(f"{where}: Form 4 date is invalid")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise SchemaError(f"{where}: Form 4 date is invalid") from exc


def _validate_form4_numeric(value: Any, *, where: str, unit: str) -> None:
    if not isinstance(value, Mapping):
        raise SchemaError(f"{where}: Form 4 numeric value is invalid")
    refs = value.get("footnote_ids")
    if not isinstance(refs, list) or refs != sorted(refs, key=_form4_footnote_key):
        raise SchemaError(f"{where}: Form 4 footnote IDs are not ordered")
    if len(refs) != len(set(refs)):
        raise SchemaError(f"{where}: Form 4 footnote IDs are duplicated")
    if value.get("unit") != unit:
        raise SchemaError(f"{where}: Form 4 numeric unit is invalid")
    raw = value.get("value")
    if raw is None:
        if not refs:
            raise SchemaError(f"{where}: null Form 4 numeric value lacks footnote support")
        return
    number = _decimal(value, where=where, unit=unit)
    if number < 0:
        raise SchemaError(f"{where}: Form 4 source numeric value is negative")


def _validate_form4_amount(value: Any, *, where: str, post: bool = False) -> None:
    if not isinstance(value, Mapping):
        raise SchemaError(f"{where}: Form 4 amount is required")
    if post:
        branch_units = {"shares": "shares", "value": "usd"}
        invalid_branch = "post-transaction amount branch is invalid"
    else:
        branch_units = {"shares": "shares", "total_value": "usd"}
        invalid_branch = "transaction amount branch is invalid"
    branch = value.get("branch")
    if branch not in branch_units:
        raise SchemaError(f"{where}: {invalid_branch}")
    for field, unit in branch_units.items():
        child = value.get(field)
        if field == branch:
            if child is None:
                raise SchemaError(f"{where}.{field}: selected amount branch is missing")
            _validate_form4_numeric(child, where=f"{where}.{field}", unit=unit)
        elif child is not None:
            raise SchemaError(f"{where}.{field}: non-selected amount branch must be null")


def _validate_form4_field_references(value: Any, *, where: str, footnote_ids: set[str]) -> None:
    if not isinstance(value, list):
        raise SchemaError(f"{where}: field references are required")
    fields: list[str] = []
    for index, reference in enumerate(value):
        if not isinstance(reference, Mapping):
            raise SchemaError(f"{where}[{index}] is invalid")
        field = reference.get("field")
        refs = reference.get("footnote_ids")
        if not isinstance(field, str) or field not in _FORM4_REFERENCE_FIELDS or field in fields:
            raise SchemaError(f"{where}[{index}] field identity is invalid or duplicated")
        if not isinstance(refs, list) or refs != sorted(refs, key=_form4_footnote_key):
            raise SchemaError(f"{where}[{index}] footnote IDs are not ordered")
        if any(ref not in footnote_ids for ref in refs):
            raise SchemaError(f"{where}[{index}] has a dangling footnote reference")
        fields.append(field)
    if fields != sorted(fields):
        raise SchemaError(f"{where} is not ordered by field")


def _validate_form4_ownership(value: Any, *, where: str) -> None:
    if not isinstance(value, Mapping):
        raise SchemaError(f"{where}: ownership nature is required")
    direct = value.get("direct_or_indirect")
    nature = value.get("nature_of_ownership")
    if direct not in {"direct", "indirect"} or not (isinstance(nature, str) or nature is None):
        raise SchemaError(f"{where}: ownership nature is invalid")
    _validate_form4_optional_text(nature, where=f"{where}.nature_of_ownership", max_length=300)
    if direct == "indirect" and not nature:
        raise SchemaError(f"{where}: indirect ownership requires nature text")


def _validate_form4_underlying(value: Any, *, where: str) -> None:
    if not isinstance(value, Mapping) or not isinstance(value.get("title"), str):
        raise SchemaError(f"{where}: underlying security is invalid")
    amount = value.get("amount")
    if not isinstance(amount, Mapping):
        raise SchemaError(f"{where}: underlying amount is required")
    _validate_form4_amount(amount, where=f"{where}.amount", post=True)


def _validate_form4_entry(
    entry: Any,
    *,
    table: str,
    ordinal: int,
    accession: str,
    form: str,
    footnote_ids: set[str],
) -> None:
    if not isinstance(entry, Mapping):
        raise SchemaError(f"{table}[{ordinal}] is invalid")
    if entry.get("source_ordinal") != ordinal:
        raise SchemaError(f"{table}[{ordinal}] source ordinal is not consecutive")
    expected_id = stable_item_id("sec_edgar", f"{accession}|{table}|{ordinal}")
    if entry.get("entry_id") != expected_id:
        raise SchemaError(f"{table}[{ordinal}] entry identity is invalid")
    _validate_form4_text(
        entry.get("security_title"), where=f"{table}[{ordinal}].security_title", max_length=300
    )
    _validate_form4_amount(
        entry.get("post_transaction_amount"),
        where=f"{table}[{ordinal}].post_transaction_amount",
        post=True,
    )
    _validate_form4_ownership(
        entry.get("ownership_nature"), where=f"{table}[{ordinal}].ownership_nature"
    )
    _validate_form4_field_references(
        entry.get("field_references"),
        where=f"{table}[{ordinal}].field_references",
        footnote_ids=footnote_ids,
    )
    derivative = table == "derivative"
    if derivative:
        if not isinstance(entry.get("derivative_terms"), Mapping):
            raise SchemaError(f"{table}[{ordinal}] derivative terms are required")
        terms = entry["derivative_terms"]
        _validate_form4_date(
            terms.get("exercise_date"),
            where=f"{table}[{ordinal}].exercise_date",
            required=False,
        )
        _validate_form4_date(
            terms.get("expiration_date"),
            where=f"{table}[{ordinal}].expiration_date",
            required=False,
        )
        conversion_price = terms.get("conversion_or_exercise_price")
        if conversion_price is not None:
            _validate_form4_numeric(
                conversion_price,
                where=f"{table}[{ordinal}].conversion_or_exercise_price",
                unit="usd_per_share",
            )
        if not isinstance(entry.get("underlying_security"), Mapping):
            raise SchemaError(f"{table}[{ordinal}] underlying security is required")
        _validate_form4_underlying(
            entry["underlying_security"], where=f"{table}[{ordinal}].underlying_security"
        )
    elif "derivative_terms" in entry or "underlying_security" in entry:
        raise SchemaError(f"{table}[{ordinal}] contains derivative-only fields")
    if entry.get("entry_kind") == "holding":
        return
    if entry.get("entry_kind") != "transaction":
        raise SchemaError(f"{table}[{ordinal}] entry kind is invalid")
    _validate_form4_date(
        entry.get("transaction_date"), where=f"{table}[{ordinal}].transaction_date"
    )
    _validate_form4_date(
        entry.get("deemed_execution_date"),
        where=f"{table}[{ordinal}].deemed_execution_date",
        required=False,
    )
    coding = entry.get("transaction_coding")
    if not isinstance(coding, Mapping) or coding.get("transaction_form_type") != form:
        raise SchemaError(f"{table}[{ordinal}] transaction coding is invalid")
    _validate_form4_text(
        coding.get("transaction_code"),
        where=f"{table}[{ordinal}].transaction_code",
        max_length=16,
    )
    _validate_form4_optional_text(
        entry.get("timeliness"), where=f"{table}[{ordinal}].timeliness", max_length=64
    )
    if not isinstance(coding.get("equity_swap_involved"), bool):
        raise SchemaError(f"{table}[{ordinal}] equity-swap flag is invalid")
    _validate_form4_amount(
        entry.get("transaction_amount"), where=f"{table}[{ordinal}].transaction_amount"
    )
    price = entry.get("price_per_share")
    if price is not None:
        _validate_form4_numeric(
            price, where=f"{table}[{ordinal}].price_per_share", unit="usd_per_share"
        )
    if entry.get("acquisition_disposition_code") not in {"A", "D"}:
        raise SchemaError(f"{table}[{ordinal}] acquisition/disposition code is invalid")


def _validate_sec_v3_item(
    item: Mapping[str, Any],
    *,
    start: datetime,
    cutoff: datetime,
    watched_issuers: set[str],
    where: str,
) -> str:
    payload = item.get("payload")
    if not isinstance(payload, Mapping) or payload.get("filing_subtype") != "form4":
        raise SchemaError(f"{where}: SEC v3 Form 4 subtype is required")
    form = payload.get("form")
    if form not in {"4", "4/A"}:
        raise SchemaError(f"{where}: Form 4 form is invalid")
    company = payload.get("company")
    issuer = payload.get("issuer")
    if not isinstance(company, str) or not re.fullmatch(r"\d{10}", company):
        raise SchemaError(f"{where}: Form 4 issuer CIK is invalid")
    if company not in watched_issuers:
        raise SchemaError(f"{where}: Form 4 issuer is outside watched issuers")
    if not isinstance(issuer, Mapping) or issuer.get("cik") != company:
        raise SchemaError(f"{where}: Form 4 issuer identity is invalid")
    for key, max_length in (("name", 300), ("trading_symbol", 32)):
        _validate_form4_text(issuer.get(key), where=f"{where}.issuer.{key}", max_length=max_length)
    accession = payload.get("accession_number")
    if not isinstance(accession, str) or not re.fullmatch(r"\d{10}-\d{2}-\d{6}", accession):
        raise SchemaError(f"{where}: Form 4 accession is invalid")
    if item.get("id") != stable_item_id("sec_edgar", accession):
        raise SchemaError(f"{where}: Form 4 item identity is invalid")
    accepted_at = payload.get("accepted_at")
    filed_at = payload.get("filed_at")
    report_period = payload.get("report_period")
    accepted = (
        _parse_ts(accepted_at, f"{where}.accepted_at") if isinstance(accepted_at, str) else None
    )
    if accepted is None or not start <= accepted < cutoff:
        raise SchemaError(f"{where}: Form 4 acceptance time is outside the current window")
    if not isinstance(filed_at, str):
        raise SchemaError(f"{where}: Form 4 filed_at is invalid")
    _parse_ts(filed_at, f"{where}.filed_at")
    _validate_form4_date(report_period, where=f"{where}.report_period")
    source = item.get("source")
    if not isinstance(source, Mapping):
        raise SchemaError(f"{where}: Form 4 source is invalid")
    if (
        source.get("published_at") != accepted_at
        or source.get("knowledge_available_at") != accepted_at
    ):
        raise SchemaError(f"{where}: Form 4 source time is not the precise acceptance time")
    source_url = source.get("url")
    expected_accession_path = accession.replace("-", "")
    if not isinstance(source_url, str) or not re.fullmatch(
        rf"https://www\.sec\.gov/Archives/edgar/data/{re.escape(sec_archive_cik(company))}/"
        rf"{re.escape(expected_accession_path)}/[A-Za-z0-9][A-Za-z0-9_.-]*\.xml",
        source_url,
    ):
        raise SchemaError(f"{where}: Form 4 source URL is not the official raw XML URL")
    owners = payload.get("reporting_owners")
    if not isinstance(owners, list) or not owners:
        raise SchemaError(f"{where}: Form 4 reporting owners are required")
    owner_ciks: list[str] = []
    for index, owner in enumerate(owners):
        if not isinstance(owner, Mapping) or not re.fullmatch(r"\d{10}", str(owner.get("cik", ""))):
            raise SchemaError(f"{where}.reporting_owners[{index}] is invalid")
        _validate_form4_text(
            owner.get("name"), where=f"{where}.reporting_owners[{index}].name", max_length=300
        )
        relationship = owner.get("relationship")
        if not isinstance(relationship, Mapping):
            raise SchemaError(f"{where}.reporting_owners[{index}].relationship is invalid")
        flags = [
            relationship.get(key) for key in ("director", "officer", "ten_percent_owner", "other")
        ]
        if not all(isinstance(flag, bool) for flag in flags) or not any(flags):
            raise SchemaError(f"{where}.reporting_owners[{index}] relationship is incomplete")
        _validate_form4_optional_text(
            relationship.get("officer_title"),
            where=f"{where}.reporting_owners[{index}].officer_title",
            max_length=300,
        )
        _validate_form4_optional_text(
            relationship.get("other_text"),
            where=f"{where}.reporting_owners[{index}].other_text",
            max_length=300,
        )
        if relationship.get("officer") and not relationship.get("officer_title"):
            raise SchemaError(f"{where}.reporting_owners[{index}] officer title is required")
        if relationship.get("other") and not relationship.get("other_text"):
            raise SchemaError(f"{where}.reporting_owners[{index}] other text is required")
        owner_ciks.append(owner["cik"])
    if owner_ciks != sorted(owner_ciks) or len(owner_ciks) != len(set(owner_ciks)):
        raise SchemaError(f"{where}: reporting owners are not unique and ordered")
    footnotes = payload.get("footnotes")
    if not isinstance(footnotes, list):
        raise SchemaError(f"{where}: Form 4 footnotes are required")
    footnote_keys: list[str] = []
    for footnote in footnotes:
        if not isinstance(footnote, Mapping) or not isinstance(footnote.get("id"), str):
            raise SchemaError(f"{where}: Form 4 footnote is invalid")
        identifier = footnote["id"]
        if identifier in footnote_keys or not re.fullmatch(r"F(?:[1-9]|[1-9]\d)", identifier):
            raise SchemaError(f"{where}: Form 4 footnote ID is invalid")
        text = footnote.get("text")
        normalized = re.sub(r"\s+", " ", str(text)).strip() if isinstance(text, str) else ""
        if not text or unicodedata.normalize("NFC", normalized) != text or len(text) > 4000:
            raise SchemaError(f"{where}: Form 4 footnote text is not normalized or bounded")
        footnote_keys.append(identifier)
    if footnote_keys != sorted(footnote_keys, key=_form4_footnote_key):
        raise SchemaError(f"{where}: Form 4 footnotes are not ordered")
    footnote_ids = set(footnote_keys)
    for table in ("non_derivative_entries", "derivative_entries"):
        entries = payload.get(table)
        if not isinstance(entries, list):
            raise SchemaError(f"{where}.{table} is required")
        kind = "non_derivative" if table.startswith("non_") else "derivative"
        for ordinal, entry in enumerate(entries):
            _validate_form4_entry(
                entry,
                table=kind,
                ordinal=ordinal,
                accession=accession,
                form=form,
                footnote_ids=footnote_ids,
            )
    if not payload.get("non_derivative_entries") and not payload.get("derivative_entries"):
        raise SchemaError(f"{where}: Form 4 contains no entries")
    if payload.get("is_amendment") != (form == "4/A"):
        raise SchemaError(f"{where}: Form 4 amendment flag is invalid")
    original = payload.get("date_of_original_submission")
    if form == "4/A":
        _validate_form4_date(original, where=f"{where}.date_of_original_submission")
    if form == "4" and original is not None:
        raise SchemaError(f"{where}: original submission date is not valid for Form 4")
    remarks = payload.get("remarks")
    _validate_form4_optional_text(remarks, where=f"{where}.remarks", max_length=2000)
    if payload.get("raw_metadata") != {}:
        raise SchemaError(f"{where}: generic Form 4 metadata is prohibited")
    return accession


def _validate_sec_v3_items(
    items: list[Mapping[str, Any]],
    *,
    start: datetime,
    cutoff: datetime,
    contract: Mapping[str, Any],
    watched_issuers: set[str],
    watched_companies: set[str],
    outcome: Mapping[str, Any],
) -> None:
    units = contract.get("units")
    if not isinstance(units, Mapping) or set(units) != {
        "13f_value_before_2023_01_03",
        "13f_value_from_2023_01_03",
        "reported_value_usd_thousands",
    }:
        raise SchemaError("SEC v3 13F unit contract is missing or not closed")
    if contract.get("max_filings_per_window") != 20 or contract.get(
        "ownership_xml_schema_versions"
    ) != [FORM4_SCHEMA_VERSION]:
        raise SchemaError("SEC v3 Form 4 bounds/schema versions are not closed")
    thirteenf_ciks: list[str] = []
    accessions: set[str] = set()
    for item in items:
        payload = item.get("payload")
        if not isinstance(payload, Mapping):
            raise SchemaError("SEC v3 filing payload is invalid")
        if any(
            field in payload
            for field in (
                "document_url",
                "schedule_family",
                "amendment_number",
                "current_snapshot",
                "previous_snapshot",
            )
        ):
            raise SchemaError("SEC v3 item contains SEC v4-only beneficial-ownership fields")
        subtype = payload.get("filing_subtype")
        if subtype == "form13f":
            if any(
                field in payload
                for field in (
                    "issuer",
                    "reporting_owners",
                    "non_derivative_entries",
                    "derivative_entries",
                    "footnotes",
                )
            ):
                raise SchemaError("SEC v3 form13f contains Form 4 fields")
            _validate_sec_v2_item(
                item,
                cutoff=cutoff,
                units=units,
                where=f"items[{item.get('id')!r}]",
            )
            cik = item["payload"]["company_identity"]["cik"]
            thirteenf_ciks.append(cik)
            accession = item["payload"].get("accession_number")
        elif subtype == "form4":
            if any(field in payload for field in ("company_identity", "holdings", "comparison")):
                raise SchemaError("SEC v3 form4 contains legacy 13F fields")
            accession = _validate_sec_v3_item(
                item,
                start=start,
                cutoff=cutoff,
                watched_issuers=watched_issuers,
                where=f"items[{item.get('id')!r}]",
            )
        else:
            raise SchemaError("SEC v3 filing subtype is missing or unsupported")
        if not isinstance(accession, str) or accession in accessions:
            raise SchemaError("SEC v3 filing accessions are missing or duplicated")
        accessions.add(accession)
    if len(thirteenf_ciks) != len(set(thirteenf_ciks)):
        raise SchemaError("SEC v3 13F company CIKs are not unique")
    if not set(thirteenf_ciks).issubset(watched_companies):
        raise SchemaError("SEC v3 13F item CIK is outside watched companies")
    complete = outcome.get("state") == "healthy" or (
        outcome.get("state") == "empty" and _is_true(contract.get("empty_valid_for_window"))
    )
    if complete and set(thirteenf_ciks) != watched_companies:
        raise SchemaError("SEC v3 complete slice does not equal watched 13F CIK set")


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


_BO_FORMS = {"SCHEDULE 13D", "SCHEDULE 13D/A", "SCHEDULE 13G", "SCHEDULE 13G/A"}
_BO_REASONS = {
    "not_reported",
    "missing_operand",
    "ownership_class_identity_unavailable",
    "reporting_identity_not_comparable",
    "history_candidate_bound_exhausted",
    "previous_format_unsupported",
    "history_not_evaluated",
}
_BO_SOURCE_FIELDS = frozenset(
    {
        "beneficially_owned_shares",
        "ownership_percentage",
        "voting_power",
        "dispositive_power",
    }
)


def _validate_bo_text(value: Any, *, where: str, max_length: int, required: bool = True) -> None:
    if value is None and not required:
        return
    if not isinstance(value, str) or not value:
        raise SchemaError(f"{where}: text is invalid")
    normalized = unicodedata.normalize("NFC", re.sub(r"\s+", " ", value).strip())
    if normalized != value or len(value) > max_length:
        raise SchemaError(f"{where}: text is not normalized or bounded")


def _validate_bo_numeric(
    value: Any,
    *,
    where: str,
    unit: str,
    snapshot: str,
    ordinal: int | None,
    required_source_ref: bool,
    allow_derivation: bool = False,
    expected_field: str | None = None,
    unavailable_reason: str | None = None,
) -> Decimal | None:
    if not isinstance(value, Mapping):
        raise SchemaError(f"{where}: beneficial-ownership numeric wrapper is required")
    status = value.get("status")
    if status not in {"reported", "unavailable"}:
        raise SchemaError(f"{where}.status is invalid")
    if value.get("unit") != unit:
        raise SchemaError(f"{where}.unit is invalid")
    refs = value.get("source_field_refs")
    if not isinstance(refs, list) or (required_source_ref and not refs):
        raise SchemaError(f"{where}.source_field_refs is invalid")
    if allow_derivation and refs:
        raise SchemaError(f"{where}.derived value must not expose source refs")
    seen_refs: set[tuple[Any, Any, Any]] = set()
    for index, ref in enumerate(refs):
        if not isinstance(ref, Mapping):
            raise SchemaError(f"{where}.source_field_refs[{index}] is invalid")
        ref_key = (ref.get("snapshot"), ref.get("source_ordinal"), ref.get("field"))
        if ref_key in seen_refs:
            raise SchemaError(f"{where}.source_field_refs[{index}] is duplicated")
        seen_refs.add(ref_key)
        if ref.get("snapshot") != snapshot:
            raise SchemaError(f"{where}.source_field_refs[{index}] has the wrong snapshot")
        if ordinal is not None and ref.get("source_ordinal") != ordinal:
            raise SchemaError(f"{where}.source_field_refs[{index}] has the wrong source ordinal")
        if expected_field is not None and ref.get("field") != expected_field:
            raise SchemaError(f"{where}.source_field_refs[{index}] has the wrong field")
        if not isinstance(ref.get("field"), str) or not re.fullmatch(
            r"(?:reporting_person|group)\[[0-9]+\]\.[A-Za-z0-9_]+", ref["field"]
        ):
            raise SchemaError(f"{where}.source_field_refs[{index}].field is not closed")
        prefix, _, _ = ref["field"].partition(".")
        allowed_fields = {f"{prefix}.{field}" for field in _BO_SOURCE_FIELDS}
        if prefix == "group[0]":
            allowed_fields = {"group[0].aggregate_shares"}
        if ref["field"] not in allowed_fields:
            raise SchemaError(f"{where}.source_field_refs[{index}].field is not supported")
    reason = value.get("reason")
    raw = value.get("value")
    if status == "reported":
        if not isinstance(raw, str) or reason is not None:
            raise SchemaError(f"{where}: reported value/reason state is invalid")
        number = _decimal(value, where=where, unit=unit)
        if unit in {"shares", "percent"} and number < 0:
            raise SchemaError(f"{where}: source value must be nonnegative")
        if unit == "percent" and not 0 <= number <= 100:
            raise SchemaError(f"{where}: percentage is outside [0, 100]")
        if "derivation" in value and not allow_derivation:
            raise SchemaError(f"{where}: measured value cannot carry derivation metadata")
        return number
    if (
        raw is not None
        or not isinstance(reason, str)
        or reason not in _BO_REASONS
        or (unavailable_reason is not None and reason != unavailable_reason)
    ):
        raise SchemaError(f"{where}: unavailable value/reason state is invalid")
    if "derivation" in value:
        raise SchemaError(f"{where}: unavailable value cannot carry derivation metadata")
    return None


def _bo_class_identity(snapshot: Mapping[str, Any]) -> tuple[str, str] | None:
    ownership_class = snapshot.get("ownership_class")
    if not isinstance(ownership_class, Mapping):
        return None
    basis = ownership_class.get("identity_basis")
    if basis == "cusip" and isinstance(ownership_class.get("cusip"), str):
        return ("cusip", ownership_class["cusip"])
    if basis == "class_title" and isinstance(ownership_class.get("title"), str):
        return ("class_title", ownership_class["title"])
    return None


def _validate_bo_snapshot(snapshot: Any, *, where: str, label: str) -> tuple[str, str, str | None]:
    if not isinstance(snapshot, Mapping):
        raise SchemaError(f"{where}: beneficial-ownership snapshot is required")
    form = snapshot.get("form")
    if form not in _BO_FORMS:
        raise SchemaError(f"{where}.form is invalid")
    family = snapshot.get("schedule_family")
    expected_family = "13D" if "13D" in form else "13G"
    if family != expected_family:
        raise SchemaError(f"{where}.schedule_family is invalid")
    accession = snapshot.get("accession_number")
    if not isinstance(accession, str) or not re.fullmatch(r"\d{10}-\d{2}-\d{6}", accession):
        raise SchemaError(f"{where}.accession_number is invalid")
    accepted = snapshot.get("accepted_at")
    filed = snapshot.get("filed_at")
    if not isinstance(accepted, str) or not isinstance(filed, str):
        raise SchemaError(f"{where}: source times are required")
    _parse_ts(accepted, f"{where}.accepted_at")
    _parse_ts(filed, f"{where}.filed_at")
    if label == "previous" and "comparison" in snapshot:
        raise SchemaError(f"{where}: previous snapshot must not carry comparison data")
    document_url = snapshot.get("document_url")
    if not isinstance(document_url, str) or not re.fullmatch(
        rf"https://www\.sec\.gov/Archives/edgar/data/{_SEC_ARCHIVE_CIK_PATTERN}/"
        rf"{accession.replace('-', '')}/[A-Za-z0-9][A-Za-z0-9_.-]*\.xml",
        document_url,
    ):
        raise SchemaError(f"{where}.document_url is not an official raw XML URL")
    issuer = snapshot.get("issuer")
    if not isinstance(issuer, Mapping):
        raise SchemaError(f"{where}.issuer is invalid")
    _validate_bo_text(issuer.get("name"), where=f"{where}.issuer.name", max_length=300)
    issuer_cik = issuer.get("cik")
    if issuer_cik is not None and (
        not isinstance(issuer_cik, str) or not re.fullmatch(r"\d{10}", issuer_cik)
    ):
        raise SchemaError(f"{where}.issuer.cik is invalid")
    ownership_class = snapshot.get("ownership_class")
    if not isinstance(ownership_class, Mapping):
        raise SchemaError(f"{where}.ownership_class is invalid")
    class_basis = ownership_class.get("identity_basis")
    if class_basis not in {"cusip", "class_title", "unavailable"}:
        raise SchemaError(f"{where}.ownership_class.identity_basis is invalid")
    cusip = ownership_class.get("cusip")
    title = ownership_class.get("title")
    if class_basis == "cusip" and (
        not isinstance(cusip, str) or not re.fullmatch(r"[0-9A-Z*@#]{9}", cusip)
    ):
        raise SchemaError(f"{where}.ownership_class CUSIP identity is invalid")
    if class_basis == "class_title" and (
        not isinstance(title, str) or not title or cusip is not None
    ):
        raise SchemaError(f"{where}.ownership_class title identity is invalid")
    if class_basis == "unavailable" and (cusip is not None or title is not None):
        raise SchemaError(f"{where}.ownership_class unavailable identity has operands")
    if title is not None:
        _validate_bo_text(title, where=f"{where}.ownership_class.title", max_length=300)
    if cusip is not None and (
        not isinstance(cusip, str)
        or cusip != cusip.upper()
        or any(char.isspace() for char in cusip)
    ):
        raise SchemaError(f"{where}.ownership_class.cusip is not canonical")
    positions = snapshot.get("reporting_positions")
    if not isinstance(positions, list) or not positions or len(positions) > 32:
        raise SchemaError(f"{where}.reporting_positions is invalid")
    for ordinal, position in enumerate(positions):
        pwhere = f"{where}.reporting_positions[{ordinal}]"
        if not isinstance(position, Mapping) or position.get("source_ordinal") != ordinal:
            raise SchemaError(f"{pwhere}: source ordinal is not consecutive")
        source_name = position.get("source_name")
        source_cik = position.get("source_cik")
        basis = position.get("identity_basis")
        _validate_bo_text(source_name, where=f"{pwhere}.source_name", max_length=300)
        if source_cik is not None and (
            not isinstance(source_cik, str) or not re.fullmatch(r"\d{10}", source_cik)
        ):
            raise SchemaError(f"{pwhere}.source_cik is invalid")
        if basis != ("source_cik" if source_cik is not None else "source_name"):
            raise SchemaError(f"{pwhere}.identity_basis is invalid")
        membership = position.get("group_membership")
        if not isinstance(membership, Mapping) or not isinstance(membership.get("is_member"), bool):
            raise SchemaError(f"{pwhere}.group_membership is invalid")
        _validate_bo_numeric(
            position.get("beneficially_owned_shares"),
            where=f"{pwhere}.beneficially_owned_shares",
            unit="shares",
            snapshot=label,
            ordinal=ordinal,
            required_source_ref=True,
            expected_field=f"reporting_person[{ordinal}].beneficially_owned_shares",
            unavailable_reason="not_reported",
        )
        _validate_bo_numeric(
            position.get("ownership_percentage"),
            where=f"{pwhere}.ownership_percentage",
            unit="percent",
            snapshot=label,
            ordinal=ordinal,
            required_source_ref=True,
            expected_field=f"reporting_person[{ordinal}].ownership_percentage",
            unavailable_reason="not_reported",
        )
        for field in ("voting_power", "dispositive_power"):
            if field in position:
                _validate_bo_numeric(
                    position[field],
                    where=f"{pwhere}.{field}",
                    unit="shares",
                    snapshot=label,
                    ordinal=ordinal,
                    required_source_ref=True,
                    expected_field=f"reporting_person[{ordinal}].{field}",
                    unavailable_reason="not_reported",
                )
        person_types = position.get("person_types")
        if not isinstance(person_types, list) or any(
            not isinstance(person_type, str) for person_type in person_types
        ):
            raise SchemaError(f"{pwhere}.person_types is invalid")
        for type_index, person_type in enumerate(person_types):
            _validate_bo_text(
                person_type,
                where=f"{pwhere}.person_types[{type_index}]",
                max_length=100,
            )
        if person_types != sorted(set(person_types)):
            raise SchemaError(f"{pwhere}.person_types are not canonical")
        refs = position.get("source_field_refs")
        if not isinstance(refs, list):
            raise SchemaError(f"{pwhere}.source_field_refs is invalid")
        expected_fields = {
            f"reporting_person[{ordinal}].beneficially_owned_shares",
            f"reporting_person[{ordinal}].ownership_percentage",
        }
        for field in ("voting_power", "dispositive_power"):
            if field in position:
                expected_fields.add(f"reporting_person[{ordinal}].{field}")
        actual_fields: list[str] = []
        for ref in refs:
            if (
                not isinstance(ref, Mapping)
                or ref.get("snapshot") != label
                or ref.get("source_ordinal") != ordinal
                or not isinstance(ref.get("field"), str)
            ):
                raise SchemaError(f"{pwhere}.source_field_refs is not document-local")
            actual_fields.append(ref["field"])
        if (
            len(actual_fields) != len(set(actual_fields))
            or set(actual_fields) != expected_fields
            or actual_fields != sorted(actual_fields)
        ):
            raise SchemaError(f"{pwhere}.source_field_refs do not cover measured fields")
        comparison = position.get("comparison")
        if label == "current":
            if not isinstance(comparison, Mapping):
                raise SchemaError(f"{pwhere}.comparison is required")
            status = comparison.get("status")
            if status not in {"available", "unavailable"}:
                raise SchemaError(f"{pwhere}.comparison.status is invalid")
            reason = comparison.get("reason")
            if status == "available" and reason is not None:
                raise SchemaError(f"{pwhere}.comparison.reason is invalid")
            if status == "unavailable" and reason not in _BO_REASONS:
                raise SchemaError(f"{pwhere}.comparison.reason is invalid")
            for field, unit in (
                ("shares_delta", "shares"),
                ("percentage_delta", "percentage_points"),
            ):
                _validate_bo_numeric(
                    comparison.get(field),
                    where=f"{pwhere}.comparison.{field}",
                    unit=unit,
                    snapshot="current",
                    ordinal=None,
                    required_source_ref=False,
                    allow_derivation=True,
                )
                delta = comparison[field]
                if (
                    status == "available"
                    and delta.get("status") == "reported"
                    and delta.get("derivation") != "current_minus_previous"
                ):
                    raise SchemaError(f"{pwhere}.comparison.{field} derivation is invalid")
                if status == "unavailable" and delta.get("value") is not None:
                    raise SchemaError(f"{pwhere}.comparison.{field} must be unavailable")
    group_evidence = snapshot.get("group_evidence")
    if group_evidence is not None:
        if not isinstance(group_evidence, Mapping):
            raise SchemaError(f"{where}.group_evidence is invalid")
        if (
            not isinstance(group_evidence.get("is_explicit"), bool)
            or not group_evidence["is_explicit"]
        ):
            raise SchemaError(f"{where}.group_evidence is invalid")
        _validate_bo_text(
            group_evidence.get("name"),
            where=f"{where}.group_evidence.name",
            max_length=300,
            required=False,
        )
        aggregate_shares = group_evidence.get("aggregate_shares")
        if aggregate_shares is not None:
            _validate_bo_numeric(
                aggregate_shares,
                where=f"{where}.group_evidence.aggregate_shares",
                unit="shares",
                snapshot=label,
                ordinal=0,
                required_source_ref=True,
                expected_field="group[0].aggregate_shares",
                unavailable_reason="not_reported",
            )
    is_amendment = snapshot.get("is_amendment")
    if is_amendment != form.endswith("/A"):
        raise SchemaError(f"{where}.is_amendment is invalid")
    if not is_amendment and snapshot.get("amendment_number") is not None:
        raise SchemaError(f"{where}: non-amendment has amendment number")
    return accession, accepted, issuer_cik


def _validate_sec_v4_item(
    item: Mapping[str, Any],
    *,
    start: datetime,
    cutoff: datetime,
    watched_filers: set[str],
    where: str,
) -> str:
    payload = item.get("payload")
    if not isinstance(payload, Mapping) or payload.get("filing_subtype") != "beneficial_ownership":
        raise SchemaError(f"{where}: SEC v4 beneficial-ownership subtype is required")
    filer = payload.get("company")
    if (
        not isinstance(filer, str)
        or not re.fullmatch(r"\d{10}", filer)
        or filer not in watched_filers
    ):
        raise SchemaError(f"{where}: beneficial-ownership filer is outside watched filers")
    archive_filer = sec_archive_cik(filer)
    accession = payload.get("accession_number")
    if not isinstance(accession, str) or item.get("id") != stable_item_id("sec_edgar", accession):
        raise SchemaError(f"{where}: beneficial-ownership item identity is invalid")
    accepted = payload.get("accepted_at")
    if not isinstance(accepted, str):
        raise SchemaError(f"{where}.accepted_at is required")
    accepted_dt = _parse_ts(accepted, f"{where}.accepted_at")
    if not start <= accepted_dt < cutoff:
        raise SchemaError(f"{where}: acceptance time is outside the current window")
    current_accession, current_accepted, current_issuer = _validate_bo_snapshot(
        payload.get("current_snapshot"), where=f"{where}.current_snapshot", label="current"
    )
    if current_accession != accession or current_accepted != accepted:
        raise SchemaError(f"{where}: top-level and current snapshot identity differ")
    current_snapshot = payload["current_snapshot"]
    current_document_url = current_snapshot.get("document_url")
    if (
        not isinstance(current_document_url, str)
        or f"/{archive_filer}/{accession.replace('-', '')}/" not in current_document_url
    ):
        raise SchemaError(f"{where}: current document URL identity is invalid")
    if (
        payload.get("form") != current_snapshot.get("form")
        or payload.get("schedule_family") != current_snapshot.get("schedule_family")
        or payload.get("filed_at") != current_snapshot.get("filed_at")
        or payload.get("document_url") != current_document_url
        or payload.get("amendment_number") != current_snapshot.get("amendment_number")
    ):
        raise SchemaError(f"{where}: top-level current evidence is not retained exactly")
    source = item.get("source")
    if (
        not isinstance(source, Mapping)
        or source.get("id") != f"sec-{item.get('id')}"
        or source.get("name") != "SEC EDGAR"
        or source.get("tier") != "Tier 1"
        or source.get("kind") != "filing"
        or source.get("published_at") != accepted
        or source.get("knowledge_available_at") != accepted
    ):
        raise SchemaError(f"{where}: source identity/time is not retained")
    if source.get("url") != payload.get("document_url"):
        raise SchemaError(f"{where}: source URL is not the selected raw document")
    if payload.get("is_amendment") != payload["current_snapshot"].get("is_amendment"):
        raise SchemaError(f"{where}: amendment state is inconsistent")
    previous = payload.get("previous_snapshot")
    comparison = payload.get("comparison")
    if not isinstance(comparison, Mapping):
        raise SchemaError(f"{where}.comparison is required")
    status = comparison.get("status")
    if status not in {"available", "initial_filing", "unavailable"}:
        raise SchemaError(f"{where}.comparison.status is invalid")
    reason = comparison.get("reason")
    if status in {"available", "initial_filing"} and reason is not None:
        raise SchemaError(f"{where}.comparison.reason is invalid")
    if status == "unavailable" and reason not in _BO_REASONS:
        raise SchemaError(f"{where}.comparison.reason is invalid")
    if previous is None:
        previous_ref = comparison.get("previous")
        if status == "available":
            raise SchemaError(f"{where}: available comparison requires previous snapshot")
        if status == "unavailable" and reason == "previous_format_unsupported":
            if not isinstance(previous_ref, Mapping):
                raise SchemaError(f"{where}: unsupported previous reference is required")
            reference_accession = previous_ref.get("accession_number")
            reference_accepted = previous_ref.get("accepted_at")
            reference_url = previous_ref.get("document_url")
            if (
                not isinstance(reference_accession, str)
                or reference_accession == accession
                or not re.fullmatch(r"\d{10}-\d{2}-\d{6}", reference_accession)
                or not isinstance(reference_accepted, str)
                or _parse_ts(reference_accepted, f"{where}.comparison.previous.accepted_at")
                >= accepted_dt
                or not isinstance(reference_url, str)
                or not re.fullmatch(
                    rf"https://www\.sec\.gov/Archives/edgar/data/{re.escape(archive_filer)}/{reference_accession.replace('-', '')}/[A-Za-z0-9][A-Za-z0-9_.-]*\.(?:xml|htm|html|txt)",
                    reference_url,
                    flags=re.IGNORECASE,
                )
            ):
                raise SchemaError(f"{where}: unsupported previous reference is invalid")
        elif previous_ref is not None:
            raise SchemaError(f"{where}: comparison previous reference is unexpected")
    else:
        previous_accession, previous_accepted, previous_issuer = _validate_bo_snapshot(
            previous, where=f"{where}.previous_snapshot", label="previous"
        )
        if (
            previous_accession == accession
            or _parse_ts(previous_accepted, f"{where}.previous_snapshot.accepted_at") >= accepted_dt
        ):
            raise SchemaError(f"{where}: previous snapshot is not earlier and distinct")
        previous_ref = comparison.get("previous")
        if (
            not isinstance(previous_ref, Mapping)
            or previous_ref.get("accession_number") != previous_accession
            or previous_ref.get("accepted_at") != previous_accepted
            or previous_ref.get("document_url") != previous.get("document_url")
        ):
            raise SchemaError(f"{where}: comparison previous reference is invalid")
        previous_document_url = previous.get("document_url")
        if (
            not isinstance(previous_document_url, str)
            or f"/{archive_filer}/{previous_accession.replace('-', '')}/"
            not in previous_document_url
        ):
            raise SchemaError(f"{where}: previous document URL identity is invalid")
        if (
            current_issuer is None
            or previous_issuer is None
            or current_issuer != previous_issuer
            or _bo_class_identity(payload["current_snapshot"]) != _bo_class_identity(previous)
        ):
            raise SchemaError(f"{where}: previous issuer/class identity is not comparable")
        if status != "available":
            raise SchemaError(f"{where}: previous snapshot requires available comparison")
    current_snapshot = payload["current_snapshot"]
    previous_positions = (
        previous.get("reporting_positions") if isinstance(previous, Mapping) else None
    )
    previous_by_identity: dict[tuple[str, str], Mapping[str, Any]] = {}
    if isinstance(previous_positions, list):
        for ordinal, position in enumerate(previous_positions):
            if not isinstance(position, Mapping):
                raise SchemaError(
                    f"{where}.previous_snapshot.reporting_positions[{ordinal}] is invalid"
                )
            basis = position.get("identity_basis")
            identity = (
                position.get("source_cik") if basis == "source_cik" else position.get("source_name")
            )
            if not isinstance(identity, str):
                raise SchemaError(f"{where}: previous position identity is invalid")
            key = (str(basis), identity)
            if key in previous_by_identity:
                raise SchemaError(f"{where}: previous position identities are duplicated")
            previous_by_identity[key] = position
    current_identities: set[tuple[str, str]] = set()
    for ordinal, position in enumerate(current_snapshot["reporting_positions"]):
        if not isinstance(position, Mapping):
            raise SchemaError(f"{where}.current_snapshot.reporting_positions[{ordinal}] is invalid")
        basis = position.get("identity_basis")
        identity = (
            position.get("source_cik") if basis == "source_cik" else position.get("source_name")
        )
        if not isinstance(identity, str):
            raise SchemaError(f"{where}: current position identity is invalid")
        identity_key = (str(basis), identity)
        if identity_key in current_identities:
            raise SchemaError(f"{where}: current position identities are duplicated")
        current_identities.add(identity_key)
        comparison_value = position.get("comparison")
        if not isinstance(comparison_value, Mapping):
            raise SchemaError(
                f"{where}.current_snapshot.reporting_positions[{ordinal}].comparison is required"
            )
        comparison_status = comparison_value.get("status")
        if comparison_status not in {"available", "unavailable"}:
            raise SchemaError(f"{where}: position comparison status is invalid")
        prior = previous_by_identity.get(identity_key) if previous is not None else None
        if previous is None:
            if comparison_status == "available":
                raise SchemaError(f"{where}: position comparison requires previous snapshot")
            continue
        if prior is None:
            if (
                comparison_status != "unavailable"
                or comparison_value.get("reason") != "reporting_identity_not_comparable"
            ):
                raise SchemaError(f"{where}: unmatched position comparison is invalid")
            continue
        if comparison_status != "available":
            raise SchemaError(f"{where}: matched position comparison must be available")
        for field, delta_field in (
            ("beneficially_owned_shares", "shares_delta"),
            ("ownership_percentage", "percentage_delta"),
        ):
            current_value = position[field]
            previous_value = prior.get(field)
            delta = comparison_value[delta_field]
            if (
                isinstance(current_value, Mapping)
                and isinstance(previous_value, Mapping)
                and current_value.get("status") == "reported"
                and previous_value.get("status") == "reported"
            ):
                expected = _subtract_canonical(
                    current_value["value"],
                    previous_value["value"],
                    where=f"{where}.reporting_positions[{ordinal}].{delta_field}",
                )
                if delta.get("status") != "reported" or delta.get("value") != expected:
                    raise SchemaError(f"{where}: {delta_field} is not current minus previous")
            elif delta.get("status") != "unavailable":
                raise SchemaError(f"{where}: {delta_field} requires unavailable operands")
    return accession


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
            "filing_subtype",
            "issuer",
            "reporting_owners",
            "non_derivative_entries",
            "derivative_entries",
            "footnotes",
            "remarks",
            "is_amendment",
            "date_of_original_submission",
            "document_url",
            "schedule_family",
            "amendment_number",
            "current_snapshot",
            "previous_snapshot",
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
    window_start = _parse_ts(feed["window"]["start"], "window.start")
    items_by_provider: dict[str, list[Mapping[str, Any]]] = {}
    for item in feed.get("items", []):
        if isinstance(item, Mapping) and isinstance(item.get("provider_id"), str):
            items_by_provider.setdefault(item["provider_id"], []).append(item)
    # A Provider embedding a versioned semantic contract must satisfy its
    # contract-level requirements even when the run retained no items for it;
    # otherwise a blocked-exempt or empty outcome would skip them entirely.
    versioned_provider_ids = {
        provider_id
        for provider_id, contract in contracts.items()
        if contract.get("contract_version") in {2, 3, 4}
    }
    for provider_id in sorted(set(items_by_provider) | versioned_provider_ids):
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
        if version == 4:
            if provider_id != "sec_edgar":
                raise SchemaError(f"unsupported v4 semantic Provider {provider_id!r}")
            units = contract.get("units")
            if not isinstance(units, Mapping) or set(units) != {
                "13f_value_before_2023_01_03",
                "13f_value_from_2023_01_03",
                "reported_value_usd_thousands",
            }:
                raise SchemaError("SEC v4 unit contract is missing or not closed")
            if contract.get("max_filings_per_window") != 20 or contract.get(
                "ownership_xml_schema_versions"
            ) != [FORM4_SCHEMA_VERSION]:
                raise SchemaError("SEC v4 Form 4 bounds/schema versions are not closed")
            bo_bounds = {
                "max_filings_per_window": 7,
                "max_history_files": 1,
                "max_historical_candidate_documents": 64,
                "max_reporting_positions_per_filing": 32,
                "structured_formats": ["edgarSubmission"],
                "schema_versions": ["X0202"],
                "locator_prefixes": ["xslSCHEDULE_13G_X01", "xslSCHEDULE_13G_X02"],
            }
            bo_contract = contract.get("beneficial_ownership")
            if not isinstance(bo_contract, Mapping) or any(
                bo_contract.get(key) != value for key, value in bo_bounds.items()
            ):
                raise SchemaError("SEC v4 beneficial-ownership bounds/schema are not closed")
            config = feed.get("feed_config", {}).get("snapshot", {})
            watched_filers = (
                config.get("watched_beneficial_ownership_filers")
                if isinstance(config, Mapping)
                else None
            )
            if not isinstance(watched_filers, list) or not watched_filers:
                raise SchemaError("SEC v4 requires watched beneficial-ownership filers")
            filer_ciks: list[str] = []
            for row in watched_filers:
                cik = row.get("cik") if isinstance(row, Mapping) else None
                if not isinstance(cik, str) or not re.fullmatch(r"\d{10}", cik):
                    raise SchemaError(
                        "SEC v4 watched beneficial-ownership filer selection is invalid"
                    )
                filer_ciks.append(cik)
            if filer_ciks != sorted(filer_ciks) or len(filer_ciks) != len(set(filer_ciks)):
                raise SchemaError("SEC v4 watched beneficial-ownership filer selection is invalid")
            watched_filer_set = set(filer_ciks)
            v4_outcome: Mapping[str, Any] = next(
                (
                    o
                    for o in feed.get("provider_outcomes", [])
                    if o.get("provider_id") == "sec_edgar"
                ),
                {},
            )
            watched_companies = (
                config.get("watched_companies") if isinstance(config, Mapping) else None
            )
            watched_issuers = (
                config.get("watched_form4_issuers") if isinstance(config, Mapping) else None
            )
            if not isinstance(watched_companies, list) or not isinstance(watched_issuers, list):
                raise SchemaError("SEC v4 requires watched 13F companies and Form 4 issuers")
            v4_company_ciks = {
                row["cik"]
                for row in watched_companies
                if isinstance(row, Mapping) and isinstance(row.get("cik"), str)
            }
            v4_issuer_ciks = {
                row["cik"]
                for row in watched_issuers
                if isinstance(row, Mapping) and isinstance(row.get("cik"), str)
            }
            legacy_items = [
                item
                for item in items
                if isinstance(item.get("payload"), Mapping)
                and item["payload"].get("filing_subtype") in {"form13f", "form4"}
            ]
            _validate_sec_v3_items(
                legacy_items,
                start=window_start,
                cutoff=cutoff,
                contract=contract,
                watched_issuers=v4_issuer_ciks,
                watched_companies=v4_company_ciks,
                outcome=v4_outcome,
            )
            accessions: set[str] = set()
            for item in items:
                payload = item.get("payload")
                subtype = payload.get("filing_subtype") if isinstance(payload, Mapping) else None
                if subtype in {"form13f", "form4"}:
                    continue
                accession = _validate_sec_v4_item(
                    item,
                    start=window_start,
                    cutoff=cutoff,
                    watched_filers=watched_filer_set,
                    where=f"items[{item.get('id')!r}]",
                )
                if accession in accessions:
                    raise SchemaError("SEC v4 beneficial-ownership accessions are duplicated")
                accessions.add(accession)
            if (
                v4_outcome.get("state") == "healthy"
                and len(accessions) > bo_contract["max_filings_per_window"]
            ):
                raise SchemaError("SEC v4 beneficial-ownership current filing bound is exceeded")
            continue
        if version == 3:
            if provider_id != "sec_edgar":
                raise SchemaError(f"unsupported v3 semantic Provider {provider_id!r}")
            config = feed.get("feed_config", {}).get("snapshot", {})
            watched_issuers = (
                config.get("watched_form4_issuers") if isinstance(config, Mapping) else None
            )
            if not isinstance(watched_issuers, list):
                raise SchemaError("SEC v3 requires watched_form4_issuers in configuration snapshot")
            issuer_ciks = [
                row["cik"]
                for row in watched_issuers
                if isinstance(row, Mapping) and isinstance(row.get("cik"), str)
            ]
            if len(issuer_ciks) != len(watched_issuers) or any(
                not re.fullmatch(r"\d{10}", cik) for cik in issuer_ciks
            ):
                raise SchemaError("SEC v3 watched Form 4 issuer selection is invalid")
            if issuer_ciks != sorted(issuer_ciks) or len(issuer_ciks) != len(set(issuer_ciks)):
                raise SchemaError("SEC v3 watched Form 4 issuer selection is invalid")
            watched_companies = (
                config.get("watched_companies") if isinstance(config, Mapping) else None
            )
            if not isinstance(watched_companies, list) or any(
                not isinstance(row, Mapping) or not isinstance(row.get("cik"), str)
                for row in watched_companies
            ):
                raise SchemaError("SEC v3 requires watched_companies in configuration snapshot")
            watched_company_ciks = {row["cik"] for row in watched_companies}
            outcome: Mapping[str, Any] = next(
                (
                    o
                    for o in feed.get("provider_outcomes", [])
                    if o.get("provider_id") == "sec_edgar"
                ),
                {},
            )
            _validate_sec_v3_items(
                items,
                start=window_start,
                cutoff=cutoff,
                contract=contract,
                watched_issuers=set(issuer_ciks),
                watched_companies=watched_company_ciks,
                outcome=outcome,
            )
            continue
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
                payload = item.get("payload")
                if isinstance(payload, Mapping) and any(
                    field in payload
                    for field in (
                        "document_url",
                        "schedule_family",
                        "amendment_number",
                        "current_snapshot",
                        "previous_snapshot",
                    )
                ):
                    raise SchemaError(
                        "SEC v2 item contains SEC v4-only beneficial-ownership fields"
                    )
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
            v2_outcome: Mapping[str, Any] = next(
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
            complete = v2_outcome.get("state") == "healthy" or (
                v2_outcome.get("state") == "empty"
                and _is_true(contract.get("empty_valid_for_window"))
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


def _validate_context_order(context: Mapping[str, Any], *, where: str) -> None:
    entities = context.get("entities")
    if not isinstance(entities, list) or not all(
        isinstance(entity, Mapping) for entity in entities
    ):
        raise SchemaError(f"{where}.entities must be an array of objects")
    entity_keys = [
        (entity.get("role"), entity.get("name"), entity.get("type")) for entity in entities
    ]
    if entity_keys != sorted(entity_keys) or len(entity_keys) != len(set(entity_keys)):
        raise SchemaError(f"{where}.entities must be unique and in total order")
    facts = context.get("numeric_facts")
    if not isinstance(facts, list) or not all(isinstance(fact, Mapping) for fact in facts):
        raise SchemaError(f"{where}.numeric_facts must be an array of objects")
    fact_keys = [(fact.get("metric"), fact.get("role")) for fact in facts]
    if fact_keys != sorted(fact_keys) or len(fact_keys) != len(set(fact_keys)):
        raise SchemaError(f"{where}.numeric_facts must be unique and in total order")
    extension = context.get("extension")
    if not isinstance(extension, Mapping):
        raise SchemaError(f"{where}.extension must be an object")
    if extension.get("type") == "policy":
        scopes = extension.get("affected_scope")
        if not isinstance(scopes, list) or not all(isinstance(scope, str) for scope in scopes):
            raise SchemaError(f"{where}.extension.affected_scope must be an array of strings")
        if scopes != sorted(set(scopes)):
            raise SchemaError(f"{where}.extension.affected_scope must be unique and in total order")


def _validate_news_context(
    item: Mapping[str, Any], context: Mapping[str, Any], *, where: str
) -> None:
    try:
        expected = build_news_context(item["provider_id"], item["payload"], item["source"])
    except (SchemaError, TypeError, ValueError) as exc:
        raise SchemaError(f"{where}: Provider-local news mapping is unavailable") from exc
    if expected.to_dict() != context:
        raise SchemaError(f"{where}: semantic context does not match the closed Provider mapping")


def _macro_source_record(context: Mapping[str, Any]) -> dict[str, Any]:
    revision = context["extension"].get("revision")
    if revision is None:
        return {}
    period = context["extension"].get("period")
    period_value = period.get("period") if isinstance(period, Mapping) else None
    return {
        "revision": {
            "period": period_value,
            "previous": revision["previous"]["value"],
            "revised": revision["revised"]["value"],
            "unit": revision["previous"]["unit"],
        }
    }


def _validate_macro_context(
    item: Mapping[str, Any], context: Mapping[str, Any], *, where: str
) -> None:
    try:
        expected = build_macro_context(
            item["provider_id"], item["payload"], _macro_source_record(context)
        )
    except (SchemaError, TypeError, ValueError) as exc:
        raise SchemaError(f"{where}: Provider-local macro mapping is unavailable") from exc
    if expected.to_dict() != context:
        raise SchemaError(f"{where}: semantic context does not match the closed Provider mapping")


def _validate_policy_context(
    item: Mapping[str, Any], context: Mapping[str, Any], *, where: str
) -> None:
    try:
        expected = build_policy_context(item["provider_id"], item["payload"], item["source"])
    except (SchemaError, TypeError, ValueError) as exc:
        raise SchemaError(f"{where}: Provider-local policy mapping is unavailable") from exc
    if expected.to_dict() != context:
        raise SchemaError(f"{where}: semantic context does not match the closed Provider mapping")


def _reject_forbidden_context_members(value: Any, *, where: str) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if key in _FORBIDDEN_INTELLIGENCE_KEYS:
                raise SchemaError(f"{where}: forbidden analytical member {key!r}")
            _reject_forbidden_context_members(nested, where=f"{where}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _reject_forbidden_context_members(nested, where=f"{where}[{index}]")


def _validate_semantic_contexts(feed: Mapping[str, Any], *, current_production: bool) -> None:
    context_types = {"news", "macro_release", "policy"}
    affected_items_by_provider: dict[str, list[Mapping[str, Any]]] = {}
    for item in feed.get("items", []):
        if not isinstance(item, Mapping):
            continue
        payload = item.get("payload")
        if not isinstance(payload, Mapping):
            continue
        payload_type = payload.get("type")
        context = item.get("semantic_context")
        if payload_type not in context_types:
            if context is not None:
                raise SchemaError("semantic_context is outside the News/Macro/Policy boundary")
            continue
        provider_id = item.get("provider_id")
        if isinstance(provider_id, str):
            affected_items_by_provider.setdefault(provider_id, []).append(item)
        if context is None:
            continue
        where = f"items[{item.get('id')!r}].semantic_context"
        if not isinstance(context, Mapping):
            raise SchemaError(f"{where}: context must be an object")
        _reject_forbidden_context_members(context, where=where)
        parsed = SemanticContext.from_dict(context)
        if parsed.to_dict() != dict(context):
            raise SchemaError(f"{where}: context arrays/text are not canonical")
        _validate_context_order(context, where=where)
        extension_type = context["extension"]["type"]
        if extension_type != payload_type:
            raise SchemaError(f"{where}: extension type does not match payload type")
        if payload_type == "news":
            _validate_news_context(item, context, where=where)
        elif payload_type == "macro_release":
            _validate_macro_context(item, context, where=where)
        else:
            _validate_policy_context(item, context, where=where)

    if not current_production:
        return
    outcomes = {
        outcome.get("provider_id"): outcome
        for outcome in feed.get("provider_outcomes", [])
        if isinstance(outcome, Mapping)
    }
    for provider_id, items in affected_items_by_provider.items():
        missing_context = [item for item in items if "semantic_context" not in item]
        if not missing_context:
            continue
        if len(missing_context) != len(items):
            raise SchemaError(
                "current production cannot mix items with and without semantic_context"
            )
        outcome = outcomes.get(provider_id)
        freshness = outcome.get("freshness") if isinstance(outcome, Mapping) else None
        carried = (
            freshness.get("carried_forward_from_run_id") if isinstance(freshness, Mapping) else None
        )
        if not (
            isinstance(outcome, Mapping)
            and outcome.get("state") == "healthy"
            and outcome.get("availability") == "success"
            and _is_true(outcome.get("succeeded"))
            and not _is_true(outcome.get("partial"))
            and not _is_true(outcome.get("failed"))
            and isinstance(freshness, Mapping)
            and freshness.get("status") in {"valid_unchanged", "stale"}
            and isinstance(carried, str)
            and carried
        ):
            raise SchemaError(
                f"items for Provider {provider_id!r} require semantic_context in current production"
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
