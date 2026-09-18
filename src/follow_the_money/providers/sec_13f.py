"""Pure, deterministic SEC Form 13F-HR selection and comparison logic.

This module intentionally has no HTTP or Provider orchestration dependency.
It accepts decoded submissions metadata and bounded complete-submission bytes.
"""

from __future__ import annotations

import re
import unicodedata
import xml.etree.ElementTree as ET
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from follow_the_money.semantic import (  # pyright: ignore[reportMissingImports]
    MeasuredNumericFact,
    add_canonical,
    derive_subtraction,
    scale_power_of_ten,
)

from ..schema import SchemaError

TRANSITION_DATE = "2023-01-03"
_CUSIP = re.compile(r"[0-9A-Z*@#]{9}")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass(frozen=True)
class FilingCandidate:
    cik: str
    accession_number: str
    form: str
    report_period: str
    filed_at: str
    accepted_at: str
    primary_document: str | None = None

    @property
    def filing_date(self) -> str:
        return self.filed_at[:10]


@dataclass(frozen=True)
class NormalizedFiling:
    candidate: FilingCandidate
    value_normalization: dict[str, str]
    holdings: tuple[dict[str, Any], ...]
    source_url: str


def _timestamp(value: str) -> datetime:
    text = str(value).strip()
    if len(text) == 8 and text.isdigit():
        text = f"{text[:4]}-{text[4:6]}-{text[6:]}T00:00:00+00:00"
    elif len(text) == 10 and _DATE.fullmatch(text):
        text += "T00:00:00+00:00"
    elif text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        result = datetime.fromisoformat(text)
    except ValueError as exc:
        raise SchemaError(f"SEC timestamp is invalid: {value!r}") from exc
    if result.tzinfo is None:
        result = result.replace(tzinfo=UTC)
    return result.astimezone(UTC)


def _iso(value: str) -> str:
    result = _timestamp(value)
    return result.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _local(element: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in element.iter() if child.tag.rsplit("}", 1)[-1] == name]


def _text(element: ET.Element, name: str, *, required: bool = False) -> str | None:
    matches = _local(element, name)
    values = [((match.text or "").strip()) for match in matches if (match.text or "").strip()]
    if not values:
        if required:
            raise SchemaError(f"SEC INFORMATION TABLE missing {name}")
        return None
    if len(set(values)) != 1:
        raise SchemaError(f"SEC INFORMATION TABLE has conflicting {name}")
    return values[0]


def _normalize_cusip(value: Any) -> str:
    text = unicodedata.normalize("NFC", str(value)).strip().upper()
    text = text.replace(" ", "").replace("-", "")
    if not _CUSIP.fullmatch(text):
        raise SchemaError(f"SEC CUSIP is invalid: {value!r}")
    return text


def _normalize_put_call(value: Any) -> str | None:
    if value is None or not str(value).strip():
        return None
    text = str(value).strip().upper()
    if text not in {"PUT", "CALL"}:
        raise SchemaError(f"SEC put/call value is invalid: {value!r}")
    return text


def _normalize_amount_type(value: Any) -> str:
    text = str(value).strip().upper()
    if text not in {"SH", "PRN"}:
        raise SchemaError(f"SEC amount type is invalid: {value!r}")
    return text


def _security_key(row: Mapping[str, Any]) -> tuple[str, str, str]:
    return (
        _normalize_cusip(row.get("cusip")),
        _normalize_put_call(row.get("put_call")) or "",
        _normalize_amount_type(row.get("amount_type")),
    )


def _display_value(row: Mapping[str, Any], field: str) -> str:
    return unicodedata.normalize("NFC", str(row.get(field) or "").strip())


def select_filings(
    raw: Mapping[str, Any], evidence_cutoff_at: str | datetime
) -> tuple[FilingCandidate, FilingCandidate | None]:
    """Select ``(current, previous)`` from SEC submissions ``recent`` rows."""
    if isinstance(evidence_cutoff_at, datetime):
        cutoff = evidence_cutoff_at.astimezone(UTC)
    else:
        cutoff = _timestamp(evidence_cutoff_at)
    filings = raw.get("filings") if isinstance(raw, Mapping) else None
    recent = filings.get("recent") if isinstance(filings, Mapping) else None
    if not isinstance(recent, Mapping):
        raise SchemaError("SEC submissions response has no recent filings")
    fields = {
        name: recent.get(name, [])
        for name in (
            "form",
            "filingDate",
            "reportDate",
            "accessionNumber",
            "acceptanceDateTime",
            "primaryDocument",
            "cik",
        )
    }
    lengths = [len(value) for value in fields.values() if isinstance(value, list)]
    if not lengths or max(lengths) == 0:
        raise SchemaError("SEC submissions response has no filings")
    candidates: list[FilingCandidate] = []
    for index in range(max(lengths)):

        def at(name: str, *, row_index: int = index) -> Any:
            value = fields[name]
            return value[row_index] if isinstance(value, list) and row_index < len(value) else None

        form = at("form")
        accepted = at("acceptanceDateTime")
        filed = at("filingDate")
        report = at("reportDate")
        accession = at("accessionNumber")
        if form != "13F-HR" or not all(
            isinstance(value, str) and value for value in (accepted, filed, report, accession)
        ):
            continue
        accepted_dt = _timestamp(accepted)
        if accepted_dt >= cutoff:
            continue
        if not _DATE.fullmatch(str(filed)) or not _DATE.fullmatch(str(report)):
            raise SchemaError("SEC filing or report date is invalid")
        candidate = FilingCandidate(
            cik=str(at("cik") or raw.get("cik") or "").zfill(10),
            accession_number=str(accession),
            form=form,
            report_period=str(report),
            filed_at=_iso(str(filed)),
            accepted_at=_iso(str(accepted)),
            primary_document=str(at("primaryDocument")) if at("primaryDocument") else None,
        )
        candidates.append(candidate)
    if not candidates:
        raise SchemaError("no eligible exact SEC 13F-HR before cutoff")
    candidates.sort(key=lambda candidate: (candidate.accepted_at, candidate.accession_number))
    current = candidates[-1]
    previous_candidates = [
        candidate
        for candidate in candidates[:-1]
        if candidate.report_period != current.report_period
    ]
    previous = previous_candidates[-1] if previous_candidates else None
    return current, previous


def _extract_document(body: bytes | str) -> ET.Element:
    text = body.decode("utf-8") if isinstance(body, bytes) else str(body)
    documents = re.findall(r"<XML\s*>(.*?)</XML\s*>", text, flags=re.IGNORECASE | re.DOTALL)
    if not documents:
        documents = [text]
    tables: list[ET.Element] = []
    for document in documents:
        candidate = document.strip()
        try:
            root = ET.fromstring(candidate)
        except ET.ParseError as exc:
            if re.search(r"informationTable", candidate, flags=re.IGNORECASE):
                raise SchemaError("SEC INFORMATION TABLE XML is malformed") from exc
            continue
        if root.tag.rsplit("}", 1)[-1] == "informationTable":
            tables.append(root)
    if len(tables) != 1:
        raise SchemaError("SEC submission must contain exactly one INFORMATION TABLE XML document")
    return tables[0]


def _header_value(text: str, label: str) -> str | None:
    patterns = (
        rf"<\s*{re.escape(label)}\s*>\s*([^<\r\n]+)",
        rf"(?:^|>)\s*{re.escape(label)}\s*:\s*([^\r\n<]+)",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1).strip()
    return None


def parse_complete_submission(
    body: bytes | str,
    candidate: FilingCandidate,
    *,
    source_url: str,
    require_submission_header: bool = False,
) -> NormalizedFiling:
    """Parse and aggregate one complete SEC submission; no network is used."""
    text = body.decode("utf-8") if isinstance(body, bytes) else str(body)
    header_cik = _header_value(text, "CENTRAL INDEX KEY")
    if header_cik is not None and header_cik.zfill(10) != candidate.cik.zfill(10):
        raise SchemaError("SEC complete submission CIK conflicts with submissions")
    header_accession = _header_value(text, "ACCESSION NUMBER")
    if header_accession is not None and header_accession != candidate.accession_number:
        raise SchemaError("SEC complete submission accession conflicts with submissions")
    header_form = _header_value(text, "CONFORMED SUBMISSION TYPE")
    if header_form is not None and header_form != candidate.form:
        raise SchemaError("SEC complete submission form conflicts with submissions")
    header_filed = _header_value(text, "FILED AS OF DATE")
    if require_submission_header and any(
        value is None for value in (header_cik, header_accession, header_form, header_filed)
    ):
        raise SchemaError("SEC complete submission header metadata is incomplete")
    if header_filed is not None and header_filed.replace("-", "")[:8] != candidate.filed_at[
        :10
    ].replace("-", ""):
        raise SchemaError("SEC complete submission FILED AS OF DATE conflicts with submissions")
    root = _extract_document(body)
    aggregate: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row_index, row in enumerate(_local(root, "infoTable")):
        raw = {
            "cusip": _text(row, "cusip", required=True),
            "put_call": _text(row, "putCall"),
            "amount_type": _text(row, "sshPrnamtType", required=True),
            "amount": _text(row, "sshPrnamt", required=True),
            "value": _text(row, "value", required=True),
            "issuer_name": _text(row, "nameOfIssuer") or "",
            "title_of_class": _text(row, "titleOfClass") or "",
            "figi": _text(row, "figi"),
        }
        key = _security_key(raw)
        amount_fact = MeasuredNumericFact.from_raw(
            name=f"holding[{row_index}].reported_amount",
            raw_value=str(raw["amount"]).replace(",", ""),
            unit="shares",
            source_fields=("sshPrnamt",),
            nonnegative=True,
        )
        raw_value_fact = MeasuredNumericFact.from_raw(
            name=f"holding[{row_index}].reported_value",
            raw_value=str(raw["value"]).replace(",", ""),
            unit="usd" if candidate.filing_date >= TRANSITION_DATE else "usd_thousands",
            source_fields=("value",),
            nonnegative=True,
        )
        entry = aggregate.get(key)
        display = {
            "issuer_name": _display_value(raw, "issuer_name"),
            "title_of_class": _display_value(raw, "title_of_class"),
            "figi": _display_value(raw, "figi") or None,
        }
        if entry is None:
            entry = {
                "key": key,
                "cusip": key[0],
                "put_call": key[1] or None,
                "amount_type": key[2],
                "amount_fact": amount_fact,
                "raw_value_fact": raw_value_fact,
                "display_candidates": [display],
            }
            aggregate[key] = entry
        else:
            entry["amount_fact"] = MeasuredNumericFact.from_canonical(
                name=f"holding[{row_index}].reported_amount",
                value=add_canonical(
                    entry["amount_fact"].value,
                    amount_fact.value,
                    where=f"holding[{row_index}].amount",
                    nonnegative=True,
                ),
                unit="shares",
                source_fields=("sshPrnamt",),
                nonnegative=True,
            )
            entry["raw_value_fact"] = MeasuredNumericFact.from_canonical(
                name=f"holding[{row_index}].reported_value",
                value=add_canonical(
                    entry["raw_value_fact"].value,
                    raw_value_fact.value,
                    where=f"holding[{row_index}].value",
                    nonnegative=True,
                ),
                unit=raw_value_fact.unit,
                source_fields=("value",),
                nonnegative=True,
            )
            entry["display_candidates"].append(display)
    if not aggregate:
        raise SchemaError("SEC INFORMATION TABLE contains no readable holdings")
    filing_date = candidate.filing_date
    if filing_date < TRANSITION_DATE:
        source_unit, formula_id = "usd_thousands", "identity"
    else:
        source_unit, formula_id = "usd", "usd_divided_by_1000"
    holdings: list[dict[str, Any]] = []
    for key in sorted(aggregate):
        entry = aggregate[key]
        displays = entry["display_candidates"]
        figis = {display["figi"] for display in displays if display["figi"]}
        if len(figis) > 1:
            raise SchemaError(f"SEC holding {key!r} has conflicting FIGI metadata")
        display = min(
            (display for display in displays),
            key=lambda value: (value["issuer_name"], value["title_of_class"], value["figi"] or ""),
        )
        value_fact = (
            entry["raw_value_fact"]
            if source_unit == "usd_thousands"
            else MeasuredNumericFact.from_canonical(
                name=f"holding[{key}].converted_value",
                value=scale_power_of_ten(
                    entry["raw_value_fact"].value,
                    -3,
                    where=f"holding[{key}].converted_value",
                    nonnegative=True,
                ),
                unit="usd_thousands",
                source_fields=("value",),
                nonnegative=True,
            )
        )
        holdings.append(
            {
                "security": {
                    "cusip": entry["cusip"],
                    "figi": next(iter(figis), None),
                    "issuer_name": display["issuer_name"],
                    "title_of_class": display["title_of_class"],
                    "put_call": entry["put_call"],
                    "amount_type": entry["amount_type"],
                },
                "reported_amount": {"value": entry["amount_fact"].value, "unit": "shares"},
                "reported_value_usd_thousands": {
                    "value": value_fact.value,
                    "unit": "usd_thousands",
                },
                "_numeric_facts": {
                    "reported_amount": entry["amount_fact"],
                    "reported_value_usd_thousands": value_fact,
                },
            }
        )
    return NormalizedFiling(
        candidate=candidate,
        value_normalization={"source_unit": source_unit, "formula_id": formula_id},
        holdings=tuple(holdings),
        source_url=source_url,
    )


class _HoldingComparison(dict[str, Any]):
    """Wire-shaped comparison row with non-serialized internal derivations."""

    __slots__ = ("derivations",)

    def __init__(self, payload: dict[str, Any], *, derivations: dict[str, Any] | None = None):
        super().__init__(payload)
        self.derivations = derivations or {}


def compare_holdings(
    current: NormalizedFiling, previous: NormalizedFiling | None
) -> list[dict[str, Any]]:
    """Compare aggregated holdings by canonical security key and amount."""
    current_by_key = {_security_key(row["security"]): row for row in current.holdings}
    previous_by_key = (
        {_security_key(row["security"]): row for row in previous.holdings} if previous else {}
    )
    result: list[dict[str, Any]] = []
    for key in sorted(set(current_by_key) | set(previous_by_key)):
        current_row = current_by_key.get(key)
        previous_row = previous_by_key.get(key)
        if current_row is not None:
            security = current_row["security"]
        else:
            assert previous_row is not None
            security = previous_row["security"]
        if previous is None:
            assert current_row is not None
            result.append(
                {
                    "security": security,
                    "current": current_row_values(current_row),
                    "previous": None,
                    "delta": None,
                    "change_type": None,
                }
            )
        elif current_row is None:
            assert previous_row is not None
            result.append(
                {
                    "security": security,
                    "current": None,
                    "previous": current_row_values(previous_row),
                    "delta": None,
                    "change_type": "no_longer_reported",
                }
            )
        elif previous_row is None:
            result.append(
                {
                    "security": security,
                    "current": current_row_values(current_row),
                    "previous": None,
                    "delta": None,
                    "change_type": "new",
                }
            )
        else:
            assert previous_row is not None
            current_values = current_row_values(current_row)
            previous_values = current_row_values(previous_row)
            assert current_values is not None and previous_values is not None
            current_facts = current_row["_numeric_facts"]
            previous_facts = previous_row["_numeric_facts"]
            amount_derivation = derive_subtraction(
                name=f"delta[{key}].amount",
                minuend=current_facts["reported_amount"],
                subtrahend=previous_facts["reported_amount"],
            )
            value_derivation = derive_subtraction(
                name=f"delta[{key}].value",
                minuend=current_facts["reported_value_usd_thousands"],
                subtrahend=previous_facts["reported_value_usd_thousands"],
            )
            amount_delta = amount_derivation.value
            value_delta = value_derivation.value
            result.append(
                _HoldingComparison(
                    {
                        "security": security,
                        "current": current_values,
                        "previous": previous_values,
                        "delta": {
                            "reported_amount": {"value": amount_delta, "unit": "shares"},
                            "reported_value_usd_thousands": {
                                "value": value_delta,
                                "unit": "usd_thousands",
                            },
                        },
                        "change_type": "increased"
                        if Decimal(amount_delta) > 0
                        else "decreased"
                        if Decimal(amount_delta) < 0
                        else "unchanged",
                    },
                    derivations={
                        "reported_amount": amount_derivation,
                        "reported_value_usd_thousands": value_derivation,
                    },
                )
            )
    return result


def current_row_values(row: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "reported_amount": dict(row["reported_amount"]),
        "reported_value_usd_thousands": dict(row["reported_value_usd_thousands"]),
    }


# Explicit aliases make the pure seam convenient for fixture-focused callers.
select_current_previous = select_filings
parse_information_table = parse_complete_submission
normalize_filing = parse_complete_submission
compare_filing_holdings = compare_holdings
