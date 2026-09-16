"""Pure deterministic CFTC Legacy Futures-Only COT semantics."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from follow_the_money.semantic import (  # pyright: ignore[reportMissingImports]
    DerivedNumericFact,
    MeasuredNumericFact,
    canonicalize_numeric,
    derive_subtraction,
)

from ..schema import SchemaError

PUBLICATION_HOUR = 15
PUBLICATION_MINUTE = 30
PUBLICATION_ZONE = "America/New_York"
METRIC_FIELDS = (
    "noncommercial_long",
    "noncommercial_short",
    "noncommercial_spreading",
    "open_interest",
    "net_noncommercial",
)


class CotError(SchemaError):
    """CFTC semantic input failed closed."""


def _report_date(value: Any) -> date:
    text = str(value).strip()
    if "T" in text:
        text = text.split("T", 1)[0]
    try:
        return date.fromisoformat(text[:10])
    except ValueError as exc:
        raise CotError(f"CFTC report date is invalid: {value!r}") from exc


def report_publication_time(value: Any) -> datetime:
    """Return the verified conservative Friday publication boundary in UTC."""
    report = _report_date(value)
    local = datetime.combine(report + timedelta(days=3), time(PUBLICATION_HOUR, PUBLICATION_MINUTE))
    local = local.replace(tzinfo=ZoneInfo(PUBLICATION_ZONE))
    return local.astimezone(UTC)


def publication_boundary(value: Any) -> str:
    return report_publication_time(value).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _cutoff(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        result = value
    else:
        text = str(value).replace("Z", "+00:00")
        try:
            result = datetime.fromisoformat(text)
        except ValueError as exc:
            raise CotError(f"CFTC cutoff is invalid: {value!r}") from exc
    if result.tzinfo is None:
        raise CotError("CFTC cutoff must be timezone-aware")
    return result.astimezone(UTC)


def select_report_dates(
    rows: Sequence[Mapping[str, Any]], evidence_cutoff_at: str | datetime
) -> tuple[str, str | None]:
    """Select latest and immediately previous eligible distinct report dates."""
    cutoff = _cutoff(evidence_cutoff_at)
    dates = {
        _report_date(row.get("report_date_as_yyyy_mm_dd")).isoformat()
        for row in rows
        if isinstance(row, Mapping)
        and row.get("report_date_as_yyyy_mm_dd") is not None
        and report_publication_time(row["report_date_as_yyyy_mm_dd"]) < cutoff
    }
    if not dates:
        raise CotError("no eligible CFTC report before cutoff")
    ordered = sorted(dates)
    return ordered[-1], ordered[-2] if len(ordered) > 1 else None


def _number(value: Any, *, where: str, nonnegative: bool = True) -> str:
    if value is None:
        raise CotError(f"{where}: numeric field is missing")
    try:
        return canonicalize_numeric(
            str(value).strip().replace(",", ""), where=where, nonnegative=nonnegative
        )
    except SchemaError as exc:
        raise CotError(f"{where}: numeric field is invalid") from exc


def _field(row: Mapping[str, Any], *names: str) -> Any:
    for name in names:
        if name in row:
            return row[name]
    return None


def _field_with_name(row: Mapping[str, Any], *names: str) -> tuple[Any, str]:
    for name in names:
        if name in row:
            return row[name], name
    return None, names[0]


class _MetricDelta(dict[str, Any]):
    """Wire-shaped metric delta with non-serialized derivation references."""

    __slots__ = ("derivations",)

    def __init__(self, payload: dict[str, Any], *, derivations: dict[str, DerivedNumericFact]):
        super().__init__(payload)
        self.derivations = derivations


class _PositioningPayload(dict[str, Any]):
    """Existing CFTC payload mapping with private in-memory provenance."""

    __slots__ = ("provenance",)

    def __init__(self, payload: dict[str, Any], *, provenance: dict[str, Any]):
        super().__init__(payload)
        self.provenance = provenance


def normalize_report_rows(
    rows: Sequence[Mapping[str, Any]], report_date: str
) -> dict[str, dict[str, Any]]:
    """Normalize one complete report, rejecting duplicate/ambiguous codes."""
    report_date = _report_date(report_date).isoformat()
    normalized: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise CotError(f"CFTC row {index} is not an object")
        raw_row_date = row.get("report_date_as_yyyy_mm_dd")
        if raw_row_date is None or _report_date(raw_row_date).isoformat() != report_date:
            raise CotError(f"CFTC row {index} does not match report date {report_date!r}")
        raw_code = _field(row, "cftc_contract_market_code", "contract_market_code")
        code = str(raw_code or "").strip()
        if not code:
            raise CotError(f"CFTC row {index} has no contract market code")
        if code in normalized:
            raise CotError(f"CFTC report has duplicate market code {code!r}")
        name = _field(row, "contract_market_name", "market_and_exchange_names")
        if not isinstance(name, str) or not name.strip():
            raise CotError(f"CFTC market {code!r} has no display name")
        long_raw, long_source = _field_with_name(
            row, "noncomm_positions_long_all", "noncommercial_long"
        )
        long = _number(long_raw, where=f"CFTC[{code}].long")
        long_fact = MeasuredNumericFact.from_canonical(
            name=f"CFTC[{code}].long",
            value=long,
            unit="contracts",
            source_fields=(long_source,),
            nonnegative=True,
        )
        short_raw, short_source = _field_with_name(
            row, "noncomm_positions_short_all", "noncommercial_short"
        )
        short = _number(short_raw, where=f"CFTC[{code}].short")
        short_fact = MeasuredNumericFact.from_canonical(
            name=f"CFTC[{code}].short",
            value=short,
            unit="contracts",
            source_fields=(short_source,),
            nonnegative=True,
        )
        spreading_raw, spreading_source = _field_with_name(
            row,
            # The official Socrata column is misspelled upstream; see
            # references/provider-source-verification.md. The corrected
            # spelling is retained only as a bounded alias in case CFTC
            # renames it.
            "noncomm_postions_spread_all",
            "noncomm_positions_spread_all",
            "noncommercial_spreading",
        )
        spreading = _number(spreading_raw, where=f"CFTC[{code}].spreading")
        open_interest_raw, open_interest_source = _field_with_name(
            row, "open_interest_all", "open_interest"
        )
        open_interest = _number(open_interest_raw, where=f"CFTC[{code}].open_interest")
        spreading_fact = MeasuredNumericFact.from_canonical(
            name=f"CFTC[{code}].spreading",
            value=spreading,
            unit="contracts",
            source_fields=(spreading_source,),
            nonnegative=True,
        )
        open_interest_fact = MeasuredNumericFact.from_canonical(
            name=f"CFTC[{code}].open_interest",
            value=open_interest,
            unit="contracts",
            source_fields=(open_interest_source,),
            nonnegative=True,
        )
        net_fact = derive_subtraction(
            name=f"CFTC[{code}].net",
            minuend=long_fact,
            subtrahend=short_fact,
        )
        normalized[code] = {
            "code": code,
            "name": name.strip(),
            "report_date": report_date,
            "stable_id": str(row.get("id") or row.get("_id") or f"{report_date}|{code}"),
            "metrics": {
                "noncommercial_long": {"value": long, "unit": "contracts"},
                "noncommercial_short": {"value": short, "unit": "contracts"},
                "noncommercial_spreading": {"value": spreading, "unit": "contracts"},
                "open_interest": {"value": open_interest, "unit": "contracts"},
                "net_noncommercial": {"value": net_fact.value, "unit": "contracts"},
            },
            "_numeric_facts": {
                "noncommercial_long": long_fact,
                "noncommercial_short": short_fact,
                "noncommercial_spreading": spreading_fact,
                "open_interest": open_interest_fact,
                "net_noncommercial": net_fact,
            },
        }
    if not normalized:
        raise CotError("CFTC report is empty and cannot prove complete acquisition")
    return normalized


def _delta(current: Mapping[str, Any], previous: Mapping[str, Any]) -> _MetricDelta:
    result: dict[str, Any] = {}
    derivations: dict[str, DerivedNumericFact] = {}
    current_facts = current["_numeric_facts"]
    previous_facts = previous["_numeric_facts"]
    for field in METRIC_FIELDS:
        derivation = derive_subtraction(
            name=f"CFTC delta {field}",
            minuend=current_facts[field],
            subtrahend=previous_facts[field],
        )
        result[field] = {"value": derivation.value, "unit": "contracts"}
        derivations[field] = derivation
    return _MetricDelta(result, derivations=derivations)


def compare_reports(
    current_rows: Sequence[Mapping[str, Any]],
    previous_rows: Sequence[Mapping[str, Any]] | None = None,
    *,
    current_date: str | None = None,
    previous_date: str | None = None,
) -> list[dict[str, Any]]:
    """Build current positioning payloads, matching only by market code."""
    if current_date is None:
        current_date = (
            _report_date(current_rows[0].get("report_date_as_yyyy_mm_dd")).isoformat()
            if current_rows
            else ""
        )
    if not current_date:
        raise CotError("CFTC current report date is required")
    current = normalize_report_rows(current_rows, current_date)
    previous = (
        normalize_report_rows(previous_rows, previous_date)
        if previous_rows is not None and previous_date is not None
        else {}
    )
    result: list[dict[str, Any]] = []
    for code in sorted(current):
        row = current[code]
        prior = previous.get(code)
        current_metrics = row["metrics"]
        if prior is None:
            comparison = {
                "status": "unavailable",
                "previous_as_of": f"{previous_date}T00:00:00.000Z" if previous_date else None,
                "reason": (
                    "market_absent_from_previous_report"
                    if previous_date
                    else "no_previous_comparable_report"
                ),
            }
            previous_metrics = None
            delta_metrics = None
        else:
            comparison = {
                "status": "available",
                "previous_as_of": f"{previous_date}T00:00:00.000Z",
                "reason": None,
            }
            previous_metrics = prior["metrics"]
            delta_metrics = _delta(row, prior)
        payload = _PositioningPayload(
            {
                "type": "positioning",
                "instrument_id": row["name"],
                "as_of": f"{current_date}T00:00:00.000Z",
                "position": dict(current_metrics["noncommercial_long"]),
                "raw_metadata": {},
                "market_identity": {
                    "cftc_contract_market_code": code,
                    "contract_market_name": row["name"],
                },
                "current_metrics": current_metrics,
                "previous_metrics": previous_metrics,
                "delta_metrics": delta_metrics,
                "comparison": comparison,
                "derivations": {
                    "net_noncommercial": {
                        "formula_id": "noncommercial_long_minus_short",
                    }
                },
            },
            provenance={
                "net_noncommercial": row["_numeric_facts"]["net_noncommercial"],
                "delta_metrics": delta_metrics.derivations if delta_metrics is not None else None,
            },
        )
        result.append({"stable_id": row["stable_id"], "payload": payload})
    return result


select_latest_previous_dates = select_report_dates
normalize_cot_rows = normalize_report_rows
build_positioning_items = compare_reports
