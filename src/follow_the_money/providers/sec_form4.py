"""Bounded, deterministic SEC Form 4 ownership evidence core.

The module is deliberately Provider-specific.  It performs no HTTP and does
not infer ownership changes, transaction value, filing lineage, or market
meaning.  The adapter supplies one selected submissions row and one raw
ownership XML document at a time.
"""

from __future__ import annotations

import re
import unicodedata
import xml.etree.ElementTree as ET
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ..schema import SchemaError
from ..semantic import MeasuredNumericFact
from .http import stable_item_id
from .sec_13f import _iso, _timestamp
from .urls import sec_archive_cik

FORM4_SCHEMA_VERSION = "X0609"
MAX_FORM4_FILINGS_PER_WINDOW = 20
MAX_FOOTNOTES = 99
MAX_FOOTNOTE_CODE_POINTS = 4_000
MAX_REMARKS_CHARACTERS = 2_000
_ACCESSION = re.compile(r"^\d{10}-\d{2}-\d{6}$")
_CIK = re.compile(r"^\d{10}$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_FORM4_DOCUMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*\.xml$")
_ALLOWED_XSL_PREFIX = "xslF345X06"


@dataclass(frozen=True, slots=True)
class Form4ListingCandidate:
    """One validated row from an issuer's recent submissions listing."""

    issuer_cik: str
    accession_number: str
    form: str
    filed_at: str
    report_period: str
    accepted_at: str
    primary_document: str
    source_row_index: int

    @property
    def filing_date(self) -> str:
        return self.filed_at[:10]


@dataclass(frozen=True, slots=True)
class NormalizedForm4:
    """Pure normalized Form 4 evidence and its authoritative source URL."""

    candidate: Form4ListingCandidate
    payload: dict[str, Any]
    source_url: str


def _text(value: Any, *, where: str, required: bool = True) -> str | None:
    if value is None:
        if required:
            raise SchemaError(f"{where}: text is required")
        return None
    if not isinstance(value, str):
        raise SchemaError(f"{where}: text is invalid")
    normalized = unicodedata.normalize("NFC", re.sub(r"\s+", " ", value)).strip()
    if not normalized and required:
        raise SchemaError(f"{where}: text is required")
    return normalized or None


def _window_bounds(window: Mapping[str, Any] | Sequence[str]) -> tuple[datetime, datetime]:
    if isinstance(window, Mapping):
        start_value = window.get("start")
        end_value = window.get("end")
    elif len(window) == 2:
        start_value, end_value = window
    else:
        raise SchemaError("Form 4 window must contain start and end")
    if not isinstance(start_value, str) or not isinstance(end_value, str):
        raise SchemaError("Form 4 window bounds are required")
    start = _timestamp(start_value)
    end = _timestamp(end_value)
    if not start < end:
        raise SchemaError("Form 4 window must be strictly advancing")
    return start, end


def _required_list(recent: Mapping[str, Any], name: str) -> list[Any]:
    value = recent.get(name)
    if not isinstance(value, list):
        raise SchemaError(f"SEC Form 4 recent.{name} must be an aligned list")
    return value


def _listing_date(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not _DATE.fullmatch(value):
        raise SchemaError(f"SEC Form 4 {field} is invalid")
    try:
        _timestamp(value)
    except SchemaError as exc:
        raise SchemaError(f"SEC Form 4 {field} is invalid") from exc
    return value


def select_form4_filings(
    raw: Mapping[str, Any],
    window: Mapping[str, Any] | Sequence[str],
    *,
    max_filings_per_window: int = MAX_FORM4_FILINGS_PER_WINDOW,
) -> tuple[Form4ListingCandidate, ...]:
    """Select every exact Form 4/4-A in the complete half-open window.

    The recent listing is accepted only after all aligned selection fields are
    present, accessions are unique, and its oldest precise acceptance time
    proves coverage of ``window.start``. Selected rows are canonically sorted
    by ``(accepted_at, accession_number)`` for deterministic requests; the SEC
    source row order is not used as a time-ordering guarantee.
    """
    start, cutoff = _window_bounds(window)
    filings = raw.get("filings") if isinstance(raw, Mapping) else None
    recent = filings.get("recent") if isinstance(filings, Mapping) else None
    if not isinstance(recent, Mapping):
        raise SchemaError("SEC submissions response has no recent Form 4 listing")
    root_cik = raw.get("cik")
    if not isinstance(root_cik, str) or not _CIK.fullmatch(root_cik):
        raise SchemaError("SEC Form 4 submissions issuer CIK is invalid")
    names = (
        "form",
        "filingDate",
        "reportDate",
        "accessionNumber",
        "acceptanceDateTime",
        "primaryDocument",
    )
    fields = {name: _required_list(recent, name) for name in names}
    lengths = {len(value) for value in fields.values()}
    if len(lengths) != 1:
        raise SchemaError("SEC Form 4 recent fields are not aligned")
    length = next(iter(lengths))
    if length == 0:
        raise SchemaError("SEC Form 4 recent listing cannot prove window coverage")
    rows: list[Form4ListingCandidate] = []
    seen_accessions: set[str] = set()
    acceptance_times: list[datetime] = []
    for index in range(length):
        form = fields["form"][index]
        filed = fields["filingDate"][index]
        report = fields["reportDate"][index]
        accession = fields["accessionNumber"][index]
        accepted = fields["acceptanceDateTime"][index]
        primary = fields["primaryDocument"][index]
        if not isinstance(form, str) or not form or form != form.strip():
            raise SchemaError("SEC Form 4 form is invalid")
        if (
            not isinstance(accession, str)
            or not _ACCESSION.fullmatch(accession)
            or accession in seen_accessions
        ):
            raise SchemaError("SEC Form 4 accession is malformed or duplicated")
        seen_accessions.add(accession)
        if not isinstance(accepted, str):
            raise SchemaError("SEC Form 4 acceptance time is invalid")
        accepted_dt = _timestamp(accepted)
        acceptance_times.append(accepted_dt)
        if form not in {"4", "4/A"} or not start <= accepted_dt < cutoff:
            continue
        filed = _listing_date(filed, field="filing date")
        report = _listing_date(report, field="report date")
        if not isinstance(primary, str) or not primary.strip():
            raise SchemaError("SEC Form 4 selected row has no primary document")
        rows.append(
            Form4ListingCandidate(
                issuer_cik=root_cik,
                accession_number=accession,
                form=form,
                filed_at=_iso(filed),
                report_period=report,
                accepted_at=_iso(accepted),
                primary_document=primary,
                source_row_index=index,
            )
        )
    if min(acceptance_times) > start:
        raise SchemaError("SEC Form 4 recent listing does not cover window.start")
    if len(rows) > max_filings_per_window:
        raise SchemaError("SEC Form 4 eligible filing bound is exceeded")
    rows.sort(key=lambda row: (row.accepted_at, row.accession_number))
    return tuple(rows)


# Compatibility-friendly names for fixture-focused callers.
select_form4_candidates = select_form4_filings
select_current_form4_filings = select_form4_filings


def derive_form4_xml_url(issuer_cik: str, accession_number: str, primary_document: str) -> str:
    """Derive the raw archive XML URL from a safe SEC primary locator."""
    if not _CIK.fullmatch(issuer_cik):
        raise SchemaError("SEC Form 4 issuer CIK is invalid")
    if not _ACCESSION.fullmatch(accession_number):
        raise SchemaError("SEC Form 4 accession is invalid")
    if not isinstance(primary_document, str) or primary_document != primary_document.strip():
        raise SchemaError("SEC Form 4 primary document locator is invalid")
    if not primary_document or "\\" in primary_document:
        raise SchemaError("SEC Form 4 primary document locator is unsafe")
    parts = primary_document.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise SchemaError("SEC Form 4 primary document locator has unsafe nesting")
    if len(parts) == 1:
        basename = parts[0]
    elif len(parts) == 2 and parts[0] == _ALLOWED_XSL_PREFIX:
        basename = parts[1]
    else:
        raise SchemaError("SEC Form 4 primary document locator has unexpected nesting")
    if not _FORM4_DOCUMENT.fullmatch(basename):
        raise SchemaError("SEC Form 4 primary document must be an XML basename")
    if any(marker in primary_document for marker in ("://", "@", "?", "#")):
        raise SchemaError("SEC Form 4 primary document locator contains a URL component")
    return (
        f"https://www.sec.gov/Archives/edgar/data/{sec_archive_cik(issuer_cik)}/"
        f"{accession_number.replace('-', '')}/{basename}"
    )


# The longer name makes the trust-boundary seam explicit in tests.
derive_raw_ownership_xml_url = derive_form4_xml_url


def _local(tag: str) -> str:
    if not isinstance(tag, str):
        raise SchemaError("SEC Form 4 XML contains an invalid tag")
    if tag.startswith("{"):
        raise SchemaError("SEC Form 4 XML contains an unsupported namespace")
    return tag


def _children(parent: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in list(parent) if _local(child.tag) == name]


def _one(parent: ET.Element, name: str, *, required: bool = True) -> ET.Element | None:
    matches = _children(parent, name)
    if len(matches) > 1:
        raise SchemaError(f"SEC Form 4 XML contains duplicate {name}")
    if not matches:
        if required:
            raise SchemaError(f"SEC Form 4 XML is missing {name}")
        return None
    return matches[0]


def _reject_children(parent: ET.Element, allowed: set[str], *, where: str) -> None:
    for child in list(parent):
        name = _local(child.tag)
        if name not in allowed:
            raise SchemaError(f"{where} contains unsupported {name}")


def _footnote_sort_key(value: str) -> tuple[int, str]:
    return len(value), value


def _refs(element: ET.Element | None, *, where: str) -> tuple[str, ...]:
    if element is None:
        return ()
    result: list[str] = []
    for child in list(element):
        if _local(child.tag) == "value":
            result.extend(_refs(child, where=where))
            continue
        if _local(child.tag) != "footnoteId":
            continue
        if set(child.attrib) != {"id"}:
            raise SchemaError(f"{where} has malformed footnote reference")
        identifier = child.attrib.get("id", "")
        if not re.fullmatch(r"F(?:[1-9]|[1-9]\d)", identifier):
            raise SchemaError(f"{where} has malformed footnote ID")
        if identifier in result:
            raise SchemaError(f"{where} has duplicate footnote reference")
        result.append(identifier)
    return tuple(sorted(result, key=_footnote_sort_key))


def _scalar(
    element: ET.Element | None, *, where: str, required: bool = True
) -> tuple[str | None, tuple[str, ...]]:
    if element is None:
        if required:
            raise SchemaError(f"{where} is required")
        return None, ()
    refs = _refs(element, where=where)
    children = [child for child in list(element) if _local(child.tag) != "footnoteId"]
    if len(children) > 1:
        raise SchemaError(f"{where} has unsupported mixed content")
    if children:
        if _local(children[0].tag) != "value":
            raise SchemaError(f"{where} has unsupported content")
        if children[0].attrib:
            raise SchemaError(f"{where}.value has unsupported attributes")
        if list(children[0]):
            raise SchemaError(f"{where}.value has unsupported mixed content")
        text = children[0].text
    else:
        text = element.text
    value = _text(text, where=where, required=required)
    return value, refs


def _date_scalar(
    element: ET.Element | None, *, where: str, required: bool = True
) -> tuple[str | None, tuple[str, ...]]:
    value, refs = _scalar(element, where=where, required=required)
    if value is not None:
        if not _DATE.fullmatch(value):
            raise SchemaError(f"{where} is not an ISO date")
        try:
            _timestamp(value)
        except SchemaError as exc:
            raise SchemaError(f"{where} is not an ISO date") from exc
    return value, refs


def _bool_scalar(
    element: ET.Element | None, *, where: str, required: bool = False
) -> tuple[bool, tuple[str, ...]]:
    value, refs = _scalar(element, where=where, required=required)
    if value is None:
        return False, refs
    normalized = value.lower()
    if normalized not in {"true", "false", "1", "0"}:
        raise SchemaError(f"{where} must be true or false")
    return normalized in {"true", "1"}, refs


def _numeric_value(
    parent: ET.Element,
    name: str,
    *,
    unit: str,
    where: str,
    required: bool = True,
) -> tuple[dict[str, Any] | None, tuple[str, ...]]:
    element = _one(parent, name, required=required)
    if element is None:
        return None, ()
    refs = _refs(element, where=f"{where}.{name}")
    value, nested_refs = _scalar(element, where=f"{where}.{name}", required=False)
    all_refs = tuple(sorted(set(refs) | set(nested_refs), key=_footnote_sort_key))
    if value is None:
        if not all_refs:
            raise SchemaError(f"{where}.{name} has an unsupported null numeric value")
        return {"value": None, "unit": unit, "footnote_ids": list(all_refs)}, all_refs
    fact = MeasuredNumericFact.from_raw(
        name=f"{where}.{name}",
        raw_value=value.replace(",", ""),
        unit=unit,
        source_fields=(name,),
        nonnegative=True,
    )
    return {"value": fact.value, "unit": unit, "footnote_ids": list(all_refs)}, all_refs


def _amount(
    parent: ET.Element,
    names: tuple[str, str],
    *,
    units: tuple[str, str],
    where: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, tuple[str, ...]]]:
    present = [name for name in names if _children(parent, name)]
    if len(present) != 1:
        raise SchemaError(f"{where} must contain exactly one mutually exclusive amount branch")
    selected = present[0]
    first, second = names
    first_value, first_refs = _numeric_value(
        parent, first, unit=units[0], where=where, required=False
    )
    second_value, second_refs = _numeric_value(
        parent, second, unit=units[1], where=where, required=False
    )
    if first_value is None and second_value is None:
        raise SchemaError(f"{where} amount branch is empty")
    if selected == first:
        return (
            {"branch": "shares", "shares": first_value, "total_value": None},
            {"branch": "shares", "shares": first_value, "value": None},
            {first: first_refs, second: second_refs},
        )
    return (
        {"branch": "total_value", "shares": None, "total_value": second_value},
        {"branch": "value", "shares": None, "value": second_value},
        {first: first_refs, second: second_refs},
    )


def _post_amount(
    parent: ET.Element, *, where: str
) -> tuple[dict[str, Any], dict[str, tuple[str, ...]]]:
    shares, refs = _numeric_value(
        parent, "sharesOwnedFollowingTransaction", unit="shares", where=where, required=False
    )
    value, value_refs = _numeric_value(
        parent, "valueOwnedFollowingTransaction", unit="usd", where=where, required=False
    )
    if (shares is None) == (value is None):
        raise SchemaError(f"{where} must contain exactly one post-transaction amount branch")
    return (
        {
            "branch": "shares" if shares is not None else "value",
            "shares": shares,
            "value": value,
        },
        {
            "sharesOwnedFollowingTransaction": refs,
            "valueOwnedFollowingTransaction": value_refs,
        },
    )


def _ownership(
    parent: ET.Element, *, where: str
) -> tuple[dict[str, Any], dict[str, tuple[str, ...]]]:
    section = _one(parent, "ownershipNature")
    assert section is not None
    _reject_children(section, {"directOrIndirectOwnership", "natureOfOwnership"}, where=where)
    direct, direct_refs = _scalar(
        _one(section, "directOrIndirectOwnership"), where=f"{where}.directOrIndirectOwnership"
    )
    assert direct is not None
    code = direct.upper()
    if code not in {"D", "I"}:
        raise SchemaError(f"{where}.directOrIndirectOwnership is invalid")
    nature, nature_refs = _scalar(
        _one(section, "natureOfOwnership", required=False),
        where=f"{where}.natureOfOwnership",
        required=False,
    )
    if code == "I" and not nature:
        raise SchemaError(f"{where}: indirect ownership requires nature text")
    return (
        {
            "direct_or_indirect": "direct" if code == "D" else "indirect",
            "nature_of_ownership": nature,
        },
        {
            "directOrIndirectOwnership": direct_refs,
            "natureOfOwnership": nature_refs,
        },
    )


def _security(parent: ET.Element, *, name: str, where: str) -> tuple[str, tuple[str, ...]]:
    element = _one(parent, name)
    value, refs = _scalar(element, where=f"{where}.{name}")
    assert value is not None
    return value, refs


def _underlying(
    parent: ET.Element, *, where: str
) -> tuple[dict[str, Any], dict[str, tuple[str, ...]]]:
    section = _one(parent, "underlyingSecurity")
    assert section is not None
    _reject_children(
        section,
        {"underlyingSecurityTitle", "underlyingSecurityShares", "underlyingSecurityValue"},
        where=where,
    )
    title, title_refs = _scalar(
        _one(section, "underlyingSecurityTitle"), where=f"{where}.underlyingSecurityTitle"
    )
    assert title is not None
    amount, _unused, amount_refs = _amount(
        section,
        ("underlyingSecurityShares", "underlyingSecurityValue"),
        units=("shares", "usd"),
        where=where,
    )
    underlying_amount = {
        "branch": "shares" if amount["branch"] == "shares" else "value",
        "shares": amount["shares"],
        "value": amount["total_value"],
    }
    return (
        {"title": title, "amount": underlying_amount},
        {
            "underlyingSecurityTitle": title_refs,
            "underlyingSecurityShares": amount_refs["underlyingSecurityShares"],
            "underlyingSecurityValue": amount_refs["underlyingSecurityValue"],
        },
    )


def _entry(
    element: ET.Element,
    *,
    table: str,
    ordinal: int,
    candidate: Form4ListingCandidate,
    derivative: bool,
) -> dict[str, Any]:
    kind = _local(element.tag)
    is_transaction = kind.endswith("Transaction")
    expected = (
        {
            "securityTitle",
            "transactionDate",
            "deemedExecutionDate",
            "transactionCoding",
            "transactionTimeliness",
            "transactionAmounts",
            "postTransactionAmounts",
            "ownershipNature",
        }
        if is_transaction
        else {
            "securityTitle",
            "postTransactionAmounts",
            "ownershipNature",
        }
    )
    if derivative:
        expected |= {
            "underlyingSecurity",
            "conversionOrExercisePrice",
            "exerciseDate",
            "expirationDate",
        }
    _reject_children(element, expected, where=f"{table}[{ordinal}]")
    title_name = "securityTitle"
    title, title_refs = _security(element, name=title_name, where=f"{table}[{ordinal}]")
    references: dict[str, tuple[str, ...]] = {"security_title": title_refs}
    entry: dict[str, Any] = {
        "entry_kind": "transaction" if is_transaction else "holding",
        "source_ordinal": ordinal,
        "entry_id": stable_item_id("sec_edgar", f"{candidate.accession_number}|{table}|{ordinal}"),
        "security_title": title,
    }
    if is_transaction:
        transaction_date, refs = _date_scalar(
            _one(element, "transactionDate"), where=f"{table}[{ordinal}].transactionDate"
        )
        assert transaction_date is not None
        entry["transaction_date"] = transaction_date
        references["transaction_date"] = refs
        deemed, refs = _date_scalar(
            _one(element, "deemedExecutionDate", required=False),
            where=f"{table}[{ordinal}].deemedExecutionDate",
            required=False,
        )
        entry["deemed_execution_date"] = deemed
        references["deemed_execution_date"] = refs
        coding = _one(element, "transactionCoding")
        assert coding is not None
        _reject_children(
            coding,
            {"transactionFormType", "transactionCode", "equitySwapInvolved"},
            where=f"{table}[{ordinal}].transactionCoding",
        )
        form_type, refs = _scalar(
            _one(coding, "transactionFormType"),
            where=f"{table}[{ordinal}].transactionFormType",
        )
        code, code_refs = _scalar(
            _one(coding, "transactionCode"), where=f"{table}[{ordinal}].transactionCode"
        )
        assert form_type is not None and code is not None
        if form_type != candidate.form:
            raise SchemaError(f"{table}[{ordinal}] transaction form type conflicts with filing")
        swap, swap_refs = _bool_scalar(
            _one(coding, "equitySwapInvolved"),
            where=f"{table}[{ordinal}].equitySwapInvolved",
            required=True,
        )
        timely, timely_refs = _scalar(
            _one(element, "transactionTimeliness", required=False),
            where=f"{table}[{ordinal}].transactionTimeliness",
            required=False,
        )
        entry["transaction_coding"] = {
            "transaction_form_type": form_type,
            "transaction_code": code,
            "equity_swap_involved": swap,
        }
        entry["timeliness"] = timely
        references.update(
            {
                "transaction_form_type": refs,
                "transaction_code": code_refs,
                "equity_swap_involved": swap_refs,
                "timeliness": timely_refs,
            }
        )
        amounts = _one(element, "transactionAmounts")
        assert amounts is not None
        _reject_children(
            amounts,
            {
                "transactionShares",
                "transactionTotalValue",
                "transactionPricePerShare",
                "transactionAcquiredDisposedCode",
            },
            where=f"{table}[{ordinal}].transactionAmounts",
        )
        transaction_amount, _post_compat, amount_refs = _amount(
            amounts,
            ("transactionShares", "transactionTotalValue"),
            units=("shares", "usd"),
            where=f"{table}[{ordinal}].transactionAmounts",
        )
        price, price_refs = _numeric_value(
            amounts,
            "transactionPricePerShare",
            unit="usd_per_share",
            where=f"{table}[{ordinal}].transactionAmounts",
            required=False,
        )
        acquired, acquired_refs = _scalar(
            _one(amounts, "transactionAcquiredDisposedCode"),
            where=f"{table}[{ordinal}].transactionAcquiredDisposedCode",
        )
        assert acquired is not None
        if acquired.upper() not in {"A", "D"}:
            raise SchemaError(f"{table}[{ordinal}] acquisition/disposition code is invalid")
        entry["transaction_amount"] = transaction_amount
        entry["price_per_share"] = price
        entry["acquisition_disposition_code"] = acquired.upper()
        references.update(
            {
                "transactionShares": amount_refs["transactionShares"],
                "transactionTotalValue": amount_refs["transactionTotalValue"],
                "transactionPricePerShare": price_refs,
                "transactionAcquiredDisposedCode": acquired_refs,
            }
        )
    if derivative:
        exercise, exercise_refs = _date_scalar(
            _one(element, "exerciseDate", required=False),
            where=f"{table}[{ordinal}].exerciseDate",
            required=False,
        )
        expiration, expiration_refs = _date_scalar(
            _one(element, "expirationDate", required=False),
            where=f"{table}[{ordinal}].expirationDate",
            required=False,
        )
        conversion, conversion_refs = _numeric_value(
            element,
            "conversionOrExercisePrice",
            unit="usd_per_share",
            where=f"{table}[{ordinal}]",
            required=False,
        )
        entry["derivative_terms"] = {
            "exercise_date": exercise,
            "expiration_date": expiration,
            "conversion_or_exercise_price": conversion,
        }
        references.update(
            {
                "exerciseDate": exercise_refs,
                "expirationDate": expiration_refs,
                "conversionOrExercisePrice": conversion_refs,
            }
        )
        underlying = _one(element, "underlyingSecurity", required=False)
        if underlying is not None:
            value, underlying_refs = _underlying(
                element, where=f"{table}[{ordinal}].underlyingSecurity"
            )
            entry["underlying_security"] = value
            references.update(underlying_refs)
    post = _one(element, "postTransactionAmounts")
    assert post is not None
    post_amount, post_refs = _post_amount(post, where=f"{table}[{ordinal}].postTransactionAmounts")
    ownership, ownership_refs = _ownership(element, where=f"{table}[{ordinal}].ownershipNature")
    entry["post_transaction_amount"] = post_amount
    entry["ownership_nature"] = ownership
    references.update(
        {
            "sharesOwnedFollowingTransaction": post_refs["sharesOwnedFollowingTransaction"],
            "valueOwnedFollowingTransaction": post_refs["valueOwnedFollowingTransaction"],
            "directOrIndirectOwnership": ownership_refs["directOrIndirectOwnership"],
            "natureOfOwnership": ownership_refs["natureOfOwnership"],
        }
    )
    entry["field_references"] = [
        {"field": field, "footnote_ids": list(ids)}
        for field, ids in sorted(references.items())
        if ids
    ]
    return entry


def _parse_owner(element: ET.Element, *, ordinal: int) -> dict[str, Any]:
    _reject_children(
        element,
        {"reportingOwnerId", "reportingOwnerAddress", "reportingOwnerRelationship"},
        where=f"reportingOwner[{ordinal}]",
    )
    identity = _one(element, "reportingOwnerId")
    assert identity is not None
    _reject_children(identity, {"rptOwnerCik", "rptOwnerName"}, where="reportingOwnerId")
    cik, _ = _scalar(_one(identity, "rptOwnerCik"), where="rptOwnerCik")
    name, _ = _scalar(_one(identity, "rptOwnerName"), where="rptOwnerName")
    assert cik is not None and name is not None
    if not _CIK.fullmatch(cik):
        raise SchemaError("SEC reporting owner CIK is invalid")
    address = _one(element, "reportingOwnerAddress", required=False)
    if address is not None:
        address_fields = (
            "rptOwnerNonUSAddressFlag",
            "rptOwnerStreet1",
            "rptOwnerStreet2",
            "rptOwnerCity",
            "rptOwnerState",
            "rptOwnerZipCode",
            "rptOwnerStateDescription",
        )
        _reject_children(address, set(address_fields), where="reportingOwnerAddress")
        _bool_scalar(
            _one(address, "rptOwnerNonUSAddressFlag", required=False),
            where="rptOwnerNonUSAddressFlag",
        )
        for field in address_fields[1:]:
            _scalar(
                _one(address, field, required=False),
                where=f"reportingOwnerAddress.{field}",
                required=False,
            )
    relationship = _one(element, "reportingOwnerRelationship")
    assert relationship is not None
    _reject_children(
        relationship,
        {"isDirector", "isOfficer", "isTenPercentOwner", "isOther", "officerTitle", "otherText"},
        where="reportingOwnerRelationship",
    )
    director, _ = _bool_scalar(_one(relationship, "isDirector", required=False), where="isDirector")
    officer, _ = _bool_scalar(_one(relationship, "isOfficer", required=False), where="isOfficer")
    ten_percent, _ = _bool_scalar(
        _one(relationship, "isTenPercentOwner", required=False), where="isTenPercentOwner"
    )
    other, _ = _bool_scalar(_one(relationship, "isOther", required=False), where="isOther")
    officer_title, _ = _scalar(
        _one(relationship, "officerTitle", required=False), where="officerTitle", required=False
    )
    other_text, _ = _scalar(
        _one(relationship, "otherText", required=False), where="otherText", required=False
    )
    if officer and not officer_title:
        raise SchemaError("SEC officer relationship requires officer title")
    if other and not other_text:
        raise SchemaError("SEC other relationship requires other text")
    if not any((director, officer, ten_percent, other)):
        raise SchemaError("SEC reporting owner has no asserted relationship")
    return {
        "cik": cik,
        "name": name,
        "relationship": {
            "director": director,
            "officer": officer,
            "ten_percent_owner": ten_percent,
            "other": other,
            "officer_title": officer_title,
            "other_text": other_text,
        },
    }


def _parse_footnotes(section: ET.Element | None) -> list[dict[str, str]]:
    if section is None:
        return []
    _reject_children(section, {"footnote"}, where="footnotes")
    if len(list(section)) > MAX_FOOTNOTES:
        raise SchemaError("SEC Form 4 contains more than 99 footnotes")
    result: list[dict[str, str]] = []
    seen: set[str] = set()
    for element in list(section):
        if set(element.attrib) != {"id"}:
            raise SchemaError("SEC footnote has malformed attributes")
        identifier = element.attrib.get("id", "")
        if not re.fullmatch(r"F(?:[1-9]|[1-9]\d)", identifier) or identifier in seen:
            raise SchemaError("SEC footnote ID is malformed or duplicated")
        if list(element):
            raise SchemaError("SEC footnote contains unsupported mixed content")
        text = _text(element.text, where=f"footnote {identifier}")
        assert text is not None
        if len(text) > MAX_FOOTNOTE_CODE_POINTS:
            raise SchemaError("SEC footnote exceeds 4,000 Unicode code points")
        seen.add(identifier)
        result.append({"id": identifier, "text": text})
    result.sort(key=lambda value: _footnote_sort_key(value["id"]))
    return result


def parse_form4_document(
    body: bytes | str,
    candidate: Form4ListingCandidate,
    *,
    source_url: str,
    allowed_schema_versions: Sequence[str] = (FORM4_SCHEMA_VERSION,),
) -> NormalizedForm4:
    """Admit and normalize one complete raw SEC ownership XML document."""
    if isinstance(body, bytes):
        try:
            text = body.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise SchemaError("SEC Form 4 ownership XML is not UTF-8") from exc
    else:
        text = body
    if not isinstance(text, str) or text.startswith("\ufeff"):
        raise SchemaError("SEC Form 4 ownership XML has a disallowed BOM")
    expected_source_url = derive_form4_xml_url(
        candidate.issuer_cik, candidate.accession_number, candidate.primary_document
    )
    if not isinstance(source_url, str) or source_url != expected_source_url:
        raise SchemaError("SEC Form 4 source URL does not match the selected raw XML")
    if "<!" in text or re.search(
        r"&(?!(?:amp|lt|gt|quot|apos);)(?:[A-Za-z][A-Za-z0-9]+|#\d+);", text
    ):
        raise SchemaError("SEC Form 4 ownership XML contains DTD/entity content")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise SchemaError("SEC Form 4 ownership XML is malformed") from exc
    if _local(root.tag) != "ownershipDocument":
        raise SchemaError("SEC Form 4 XML root must be ownershipDocument")
    for element in root.iter():
        tag = _local(element.tag)
        if tag in {"footnote", "footnoteId"}:
            if set(element.attrib) != {"id"}:
                raise SchemaError("SEC Form 4 XML footnote attributes are unsupported")
        elif element.attrib:
            raise SchemaError("SEC Form 4 XML attributes are unsupported")
    allowed_root = {
        "schemaVersion",
        "documentType",
        "periodOfReport",
        "notSubjectToSection16",
        "issuer",
        "reportingOwner",
        "aff10b5One",
        "nonDerivativeTable",
        "derivativeTable",
        "footnotes",
        "remarks",
        "ownerSignature",
        "dateOfOriginalSubmission",
    }
    _reject_children(root, allowed_root, where="ownershipDocument")
    schema_version, _ = _scalar(_one(root, "schemaVersion"), where="schemaVersion")
    if schema_version not in set(allowed_schema_versions):
        raise SchemaError("SEC Form 4 ownership XML schema version is unsupported")
    _bool_scalar(
        _one(root, "notSubjectToSection16", required=False),
        where="notSubjectToSection16",
    )
    _bool_scalar(_one(root, "aff10b5One", required=False), where="aff10b5One")
    signature = _one(root, "ownerSignature", required=False)
    if signature is not None:
        _reject_children(signature, {"signatureName", "signatureDate"}, where="ownerSignature")
        _scalar(_one(signature, "signatureName"), where="ownerSignature.signatureName")
        _date_scalar(_one(signature, "signatureDate"), where="ownerSignature.signatureDate")
    document_type, _ = _scalar(_one(root, "documentType"), where="documentType")
    period, _ = _date_scalar(_one(root, "periodOfReport"), where="periodOfReport")
    assert document_type is not None and period is not None
    if document_type != candidate.form:
        raise SchemaError("SEC Form 4 document type conflicts with submissions")
    if period != candidate.report_period:
        raise SchemaError("SEC Form 4 period of report conflicts with submissions")

    issuer_element = _one(root, "issuer")
    assert issuer_element is not None
    _reject_children(
        issuer_element,
        {"issuerCik", "issuerName", "issuerTradingSymbol"},
        where="issuer",
    )
    issuer_cik, _ = _scalar(_one(issuer_element, "issuerCik"), where="issuerCik")
    issuer_name, _ = _scalar(_one(issuer_element, "issuerName"), where="issuerName")
    symbol, _ = _scalar(_one(issuer_element, "issuerTradingSymbol"), where="issuerTradingSymbol")
    assert issuer_cik is not None and issuer_name is not None and symbol is not None
    if not _CIK.fullmatch(issuer_cik) or issuer_cik != candidate.issuer_cik:
        raise SchemaError("SEC Form 4 issuer CIK conflicts with submissions")

    owners = [
        _parse_owner(element, ordinal=index)
        for index, element in enumerate(_children(root, "reportingOwner"))
    ]
    if not owners:
        raise SchemaError("SEC Form 4 requires a reporting owner")
    if len({owner["cik"] for owner in owners}) != len(owners):
        raise SchemaError("SEC Form 4 reporting owners are duplicated")
    owners.sort(key=lambda owner: owner["cik"])

    footnotes = _parse_footnotes(_one(root, "footnotes", required=False))
    footnote_ids = {footnote["id"] for footnote in footnotes}
    remarks_element = _one(root, "remarks", required=False)
    remarks, _ = _scalar(remarks_element, where="remarks", required=False)
    if remarks is not None and len(remarks) > MAX_REMARKS_CHARACTERS:
        raise SchemaError("SEC Form 4 remarks exceed 2,000 characters")

    non_derivative: list[dict[str, Any]] = []
    non_table = _one(root, "nonDerivativeTable", required=False)
    if non_table is not None:
        _reject_children(
            non_table,
            {"nonDerivativeTransaction", "nonDerivativeHolding"},
            where="nonDerivativeTable",
        )
        for ordinal, element in enumerate(list(non_table)):
            non_derivative.append(
                _entry(
                    element,
                    table="non_derivative",
                    ordinal=ordinal,
                    candidate=candidate,
                    derivative=False,
                )
            )
    derivative: list[dict[str, Any]] = []
    derivative_table = _one(root, "derivativeTable", required=False)
    if derivative_table is not None:
        _reject_children(
            derivative_table,
            {"derivativeTransaction", "derivativeHolding"},
            where="derivativeTable",
        )
        for ordinal, element in enumerate(list(derivative_table)):
            derivative.append(
                _entry(
                    element,
                    table="derivative",
                    ordinal=ordinal,
                    candidate=candidate,
                    derivative=True,
                )
            )
    if not non_derivative and not derivative:
        raise SchemaError("SEC Form 4 contains no supported ownership entries")

    def validate_references(value: Any) -> None:
        if isinstance(value, Mapping):
            refs = value.get("footnote_ids")
            if isinstance(refs, list) and (
                len(refs) != len(set(refs)) or any(ref not in footnote_ids for ref in refs)
            ):
                raise SchemaError("SEC Form 4 footnote reference is dangling or duplicated")
            for child in value.values():
                validate_references(child)
        elif isinstance(value, list):
            for child in value:
                validate_references(child)

    normalized_entries = non_derivative + derivative
    validate_references(normalized_entries)
    is_amendment = candidate.form == "4/A"
    original_date, _ = _date_scalar(
        _one(root, "dateOfOriginalSubmission", required=False),
        where="dateOfOriginalSubmission",
        required=False,
    )
    if is_amendment and original_date is None:
        raise SchemaError("SEC Form 4/A requires dateOfOriginalSubmission")
    if not is_amendment and original_date is not None:
        raise SchemaError("SEC Form 4 must not contain dateOfOriginalSubmission")
    payload: dict[str, Any] = {
        "type": "filing",
        "filing_subtype": "form4",
        "form": candidate.form,
        "company": candidate.issuer_cik,
        "accession_number": candidate.accession_number,
        "filed_at": candidate.filed_at,
        "raw_metadata": {},
        "report_period": candidate.report_period,
        "accepted_at": candidate.accepted_at,
        "issuer": {"cik": issuer_cik, "name": issuer_name, "trading_symbol": symbol},
        "reporting_owners": owners,
        "non_derivative_entries": non_derivative,
        "derivative_entries": derivative,
        "footnotes": footnotes,
        "remarks": remarks,
        "is_amendment": is_amendment,
        "date_of_original_submission": original_date,
    }
    return NormalizedForm4(candidate=candidate, payload=payload, source_url=source_url)


parse_ownership_xml = parse_form4_document
normalize_form4 = parse_form4_document


def form4_feed_item(normalized: NormalizedForm4, *, source: Mapping[str, Any]) -> dict[str, Any]:
    """Build the Feed item while keeping source timing tied to acceptance."""
    item_id = stable_item_id("sec_edgar", normalized.candidate.accession_number)
    return {
        "id": item_id,
        "provider_id": "sec_edgar",
        "source": dict(source),
        "payload": normalized.payload,
    }
