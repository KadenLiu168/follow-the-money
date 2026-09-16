"""Bounded SEC Schedule 13D/G evidence core.

This module is Provider-specific and pure: it performs no HTTP, does not
resolve entities, and does not infer amendment lineage, group totals, intent,
or market meaning.  The adapter supplies one validated submissions listing and
one selected structured document at a time.
"""

from __future__ import annotations

import re
import unicodedata
import xml.etree.ElementTree as ET
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from ..schema import SchemaError
from ..semantic import MeasuredNumericFact, derive_subtraction
from .sec_13f import _iso, _timestamp

SUPPORTED_FORMS = frozenset({"SCHEDULE 13D", "SCHEDULE 13D/A", "SCHEDULE 13G", "SCHEDULE 13G/A"})
SUPPORTED_SCHEMA_FORMAT = "edgarSubmission"
SUPPORTED_SCHEMA_VERSIONS = ("X0202",)
DEFAULT_LOCATOR_PREFIXES = ("xslSCHEDULE_13G_X01", "xslSCHEDULE_13G_X02")
MAX_FILINGS_PER_WINDOW = 7
MAX_HISTORY_FILES = 1
MAX_HISTORICAL_CANDIDATE_DOCUMENTS = 64
MAX_REPORTING_POSITIONS = 32
_ACCESSION = re.compile(r"^\d{10}-\d{2}-\d{6}$")
_CIK = re.compile(r"^\d{10}$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_XML_BASENAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*\.xml$")
_ALLOWED_NAMESPACES = frozenset(
    {
        "",
        "http://www.sec.gov/edgar/schemas/ownership-submission",
        "http://www.sec.gov/edgar/schemas/ownership-submission/2020",
    }
)
_ALLOWED_XML_TAGS = frozenset(
    {
        "edgarSubmission",
        "schemaVersion",
        "headerData",
        "submissionType",
        "formType",
        "documentType",
        "accessionNumber",
        "filerCik",
        "reportingFilerCik",
        "filerInfo",
        "filer",
        "credentials",
        "contact",
        "phone",
        "email",
        "formData",
        "coverPage",
        "issuerInfo",
        "issuer",
        "issuerCik",
        "issuerName",
        "classTitle",
        "titleOfClass",
        "securityTitle",
        "cusip",
        "classCusip",
        "reportingPersons",
        "reportingPerson",
        "reportingPersonName",
        "personName",
        "name",
        "rptOwnerName",
        "reportingPersonCik",
        "personCik",
        "cik",
        "rptOwnerCik",
        "personType",
        "groupMember",
        "isGroupMember",
        "sharesOwned",
        "aggregateAmount",
        "shares",
        "percentOfClass",
        "percentOfClassOutstanding",
        "classPercent",
        "votingPower",
        "dispositivePower",
        "group",
        "groupName",
        "aggregateShares",
        "amendmentNumber",
        "amendmentNo",
        "signatureInfo",
        "signature",
        "address",
        "street",
        "city",
        "state",
        "postalCode",
    }
)


@dataclass(frozen=True, slots=True)
class BeneficialOwnershipListingCandidate:
    """One validated row from a reporting filer's submissions listing."""

    filer_cik: str
    accession_number: str
    form: str
    filed_at: str
    accepted_at: str
    primary_document: str
    source_row_index: int

    @property
    def schedule_family(self) -> str:
        return "13D" if "13D" in self.form else "13G"

    @property
    def is_amendment(self) -> bool:
        return self.form.endswith("/A")


@dataclass(frozen=True, slots=True)
class BeneficialOwnershipSnapshot:
    """Parsed current/previous filing snapshot with private numeric facts."""

    payload: dict[str, Any]
    position_facts: tuple[dict[str, Any], ...]
    filer_cik: str
    issuer_cik: str | None
    class_key: tuple[str, str] | None
    accepted_at: str
    accession_number: str
    source_url: str
    supported: bool = True


@dataclass(frozen=True, slots=True)
class NormalizedBeneficialOwnership:
    """Pure normalized Schedule 13D/G evidence."""

    candidate: BeneficialOwnershipListingCandidate
    payload: dict[str, Any]
    source_url: str
    snapshot: BeneficialOwnershipSnapshot


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
        start_value, end_value = window.get("start"), window.get("end")
    elif len(window) == 2:
        start_value, end_value = window
    else:
        raise SchemaError("Schedule 13D/G window must contain start and end")
    if not isinstance(start_value, str) or not isinstance(end_value, str):
        raise SchemaError("Schedule 13D/G window bounds are required")
    start, end = _timestamp(start_value), _timestamp(end_value)
    if not start < end:
        raise SchemaError("Schedule 13D/G window must be strictly advancing")
    return start, end


def _precise_timestamp(value: Any, *, where: str) -> datetime:
    if (
        not isinstance(value, str)
        or "T" not in value
        or not re.search(r"(?:Z|[+-]\d{2}:\d{2})$", value)
    ):
        raise SchemaError(f"{where} must be a precise timezone-aware timestamp")
    return _timestamp(value)


def _aligned(recent: Mapping[str, Any], name: str) -> list[Any]:
    value = recent.get(name)
    if not isinstance(value, list):
        raise SchemaError(f"SEC Schedule 13D/G recent.{name} must be an aligned list")
    return value


def _listing_date(value: Any, *, where: str) -> str:
    if not isinstance(value, str) or not _DATE.fullmatch(value):
        raise SchemaError(f"{where} is invalid")
    try:
        _timestamp(value)
    except SchemaError as exc:
        raise SchemaError(f"{where} is invalid") from exc
    return value


def select_beneficial_ownership_filings(
    raw: Mapping[str, Any],
    window: Mapping[str, Any] | Sequence[str],
    *,
    max_filings_per_window: int = MAX_FILINGS_PER_WINDOW,
) -> tuple[BeneficialOwnershipListingCandidate, ...]:
    """Select exact Schedule 13D/G rows by precise acceptance time."""
    start, cutoff = _window_bounds(window)
    filings = raw.get("filings") if isinstance(raw, Mapping) else None
    recent = filings.get("recent") if isinstance(filings, Mapping) else None
    if not isinstance(recent, Mapping):
        raise SchemaError("SEC submissions response has no recent Schedule 13D/G listing")
    filer_cik = raw.get("cik")
    if not isinstance(filer_cik, str) or not _CIK.fullmatch(filer_cik):
        raise SchemaError("SEC Schedule 13D/G submissions filer CIK is invalid")
    if (
        isinstance(max_filings_per_window, bool)
        or not isinstance(max_filings_per_window, int)
        or max_filings_per_window <= 0
    ):
        raise SchemaError("SEC Schedule 13D/G current filing bound is invalid")
    names = (
        "form",
        "filingDate",
        "reportDate",
        "accessionNumber",
        "acceptanceDateTime",
        "primaryDocument",
    )
    fields = {name: _aligned(recent, name) for name in names}
    if len({len(value) for value in fields.values()}) != 1:
        raise SchemaError("SEC Schedule 13D/G recent fields are not aligned")
    if not fields["form"]:
        raise SchemaError("SEC Schedule 13D/G recent listing cannot prove window coverage")
    seen: set[str] = set()
    acceptance_times: list[datetime] = []
    selected: list[BeneficialOwnershipListingCandidate] = []
    for index, values in enumerate(zip(*(fields[name] for name in names), strict=True)):
        form, filed, report, accession, accepted, primary = values
        if not isinstance(form, str) or not form.strip():
            raise SchemaError("SEC Schedule 13D/G form is invalid")
        if not isinstance(filed, str) or not isinstance(report, str):
            raise SchemaError("SEC Schedule 13D/G listing dates are invalid")
        if (
            not isinstance(accession, str)
            or not _ACCESSION.fullmatch(accession)
            or accession in seen
        ):
            raise SchemaError("SEC Schedule 13D/G accession is malformed or duplicated")
        seen.add(accession)
        accepted_dt = _precise_timestamp(accepted, where="SEC Schedule 13D/G acceptance time")
        acceptance_times.append(accepted_dt)
        if form not in SUPPORTED_FORMS or not start <= accepted_dt < cutoff:
            continue
        _listing_date(filed, where="SEC Schedule 13D/G filing date")
        if not isinstance(primary, str) or not primary.strip():
            raise SchemaError("SEC Schedule 13D/G selected row has no primary document")
        selected.append(
            BeneficialOwnershipListingCandidate(
                filer_cik=filer_cik,
                accession_number=accession,
                form=form,
                filed_at=_iso(str(filed)),
                accepted_at=_iso(accepted),
                primary_document=primary,
                source_row_index=index,
            )
        )
    if min(acceptance_times) > start:
        raise SchemaError("SEC Schedule 13D/G recent listing does not cover window.start")
    if len(selected) > max_filings_per_window:
        raise SchemaError("SEC Schedule 13D/G eligible filing bound is exceeded")
    selected.sort(key=lambda row: (row.accepted_at, row.accession_number))
    return tuple(selected)


# Compatibility-friendly aliases for fixture-focused callers.
select_beneficial_ownership_candidates = select_beneficial_ownership_filings
select_current_beneficial_ownership_filings = select_beneficial_ownership_filings


def declared_beneficial_ownership_history_files(
    raw: Mapping[str, Any], *, max_history_files: int = MAX_HISTORY_FILES
) -> tuple[str, ...]:
    """Validate and return the declared SEC submissions history-file names."""
    filings = raw.get("filings") if isinstance(raw, Mapping) else None
    files = filings.get("files") if isinstance(filings, Mapping) else None
    if (
        isinstance(max_history_files, bool)
        or not isinstance(max_history_files, int)
        or max_history_files < 0
    ):
        raise SchemaError("SEC Schedule 13D/G history-file bound is invalid")
    if files is None:
        return ()
    if not isinstance(files, list) or len(files) > max_history_files:
        raise SchemaError("SEC Schedule 13D/G history-file bound is exceeded")
    names: list[str] = []
    for entry in files:
        if not isinstance(entry, Mapping) or not isinstance(entry.get("name"), str):
            raise SchemaError("SEC Schedule 13D/G history-file declaration is invalid")
        name = entry["name"]
        if not re.fullmatch(r"CIK[0-9]{10}-submissions-[0-9]{3}\.json", name) or name in names:
            raise SchemaError("SEC Schedule 13D/G history-file declaration is invalid")
        names.append(name)
    return tuple(names)


def _listing_recent(raw: Mapping[str, Any]) -> Mapping[str, Any]:
    filings = raw.get("filings") if isinstance(raw, Mapping) else None
    recent = filings.get("recent") if isinstance(filings, Mapping) else None
    if not isinstance(recent, Mapping):
        raise SchemaError("SEC Schedule 13D/G submissions listing is invalid")
    return recent


def _metadata_candidates(
    raw: Mapping[str, Any], *, cutoff: datetime
) -> tuple[BeneficialOwnershipListingCandidate, ...]:
    """Validate one recent/history aligned listing without window coverage."""
    filer_cik = raw.get("cik")
    if not isinstance(filer_cik, str) or not _CIK.fullmatch(filer_cik):
        raise SchemaError("SEC Schedule 13D/G submissions filer CIK is invalid")
    recent = _listing_recent(raw)
    names = (
        "form",
        "filingDate",
        "reportDate",
        "accessionNumber",
        "acceptanceDateTime",
        "primaryDocument",
    )
    fields = {name: _aligned(recent, name) for name in names}
    if len({len(value) for value in fields.values()}) != 1:
        raise SchemaError("SEC Schedule 13D/G listing fields are not aligned")
    seen: set[str] = set()
    candidates: list[BeneficialOwnershipListingCandidate] = []
    for index, values in enumerate(zip(*(fields[name] for name in names), strict=True)):
        form, filed, report, accession, accepted, primary = values
        if not isinstance(form, str) or not form.strip():
            raise SchemaError("SEC Schedule 13D/G form is invalid")
        if not isinstance(filed, str) or not isinstance(report, str):
            raise SchemaError("SEC Schedule 13D/G listing dates are invalid")
        if (
            not isinstance(accession, str)
            or not _ACCESSION.fullmatch(accession)
            or accession in seen
        ):
            raise SchemaError("SEC Schedule 13D/G accession is malformed or duplicated")
        seen.add(accession)
        accepted_dt = _precise_timestamp(accepted, where="SEC Schedule 13D/G acceptance time")
        if form not in SUPPORTED_FORMS or accepted_dt >= cutoff:
            continue
        _listing_date(filed, where="SEC Schedule 13D/G filing date")
        if not isinstance(primary, str) or not primary.strip():
            raise SchemaError("SEC Schedule 13D/G selected row has no primary document")
        candidates.append(
            BeneficialOwnershipListingCandidate(
                filer_cik=filer_cik,
                accession_number=accession,
                form=form,
                filed_at=_iso(filed),
                accepted_at=_iso(accepted),
                primary_document=primary,
                source_row_index=index,
            )
        )
    return tuple(sorted(candidates, key=lambda row: (row.accepted_at, row.accession_number)))


def _select_historical_beneficial_ownership_filings(
    current_submissions: Mapping[str, Any],
    history_submissions: Sequence[Mapping[str, Any]],
    evidence_cutoff_at: str,
    *,
    max_history_files: int = MAX_HISTORY_FILES,
    max_candidate_documents: int = MAX_HISTORICAL_CANDIDATE_DOCUMENTS,
) -> tuple[tuple[BeneficialOwnershipListingCandidate, ...], bool]:
    cutoff = _timestamp(evidence_cutoff_at)
    if (
        isinstance(max_candidate_documents, bool)
        or not isinstance(max_candidate_documents, int)
        or max_candidate_documents <= 0
    ):
        raise SchemaError("SEC Schedule 13D/G historical candidate bound is invalid")
    declared = declared_beneficial_ownership_history_files(
        current_submissions, max_history_files=max_history_files
    )
    if len(history_submissions) != len(declared):
        raise SchemaError("SEC Schedule 13D/G history responses do not match declarations")
    candidates = list(_metadata_candidates(current_submissions, cutoff=cutoff))
    expected_cik = current_submissions.get("cik")
    for history in history_submissions:
        if history.get("cik") != expected_cik:
            raise SchemaError("SEC Schedule 13D/G history filer CIK is mismatched")
        candidates.extend(_metadata_candidates(history, cutoff=cutoff))
    deduplicated = deduplicate_beneficial_ownership_candidates(candidates)
    truncated = len(deduplicated) > max_candidate_documents
    return tuple(reversed(deduplicated[-max_candidate_documents:])), truncated


def select_historical_beneficial_ownership_filings(
    current_submissions: Mapping[str, Any],
    history_submissions: Sequence[Mapping[str, Any]],
    evidence_cutoff_at: str,
    *,
    max_history_files: int = MAX_HISTORY_FILES,
    max_candidate_documents: int = MAX_HISTORICAL_CANDIDATE_DOCUMENTS,
) -> tuple[BeneficialOwnershipListingCandidate, ...]:
    """Build a bounded newest-first stream from recent and declared history."""
    candidates, _ = _select_historical_beneficial_ownership_filings(
        current_submissions,
        history_submissions,
        evidence_cutoff_at,
        max_history_files=max_history_files,
        max_candidate_documents=max_candidate_documents,
    )
    return candidates


def select_historical_beneficial_ownership_filings_with_status(
    current_submissions: Mapping[str, Any],
    history_submissions: Sequence[Mapping[str, Any]],
    evidence_cutoff_at: str,
    *,
    max_history_files: int = MAX_HISTORY_FILES,
    max_candidate_documents: int = MAX_HISTORICAL_CANDIDATE_DOCUMENTS,
) -> tuple[tuple[BeneficialOwnershipListingCandidate, ...], bool]:
    """Return the bounded reverse stream and whether the bound truncated it."""
    return _select_historical_beneficial_ownership_filings(
        current_submissions,
        history_submissions,
        evidence_cutoff_at,
        max_history_files=max_history_files,
        max_candidate_documents=max_candidate_documents,
    )


# Explicit name for callers that treat this result as a reverse stream.
historical_beneficial_ownership_metadata_stream = select_historical_beneficial_ownership_filings


def deduplicate_beneficial_ownership_candidates(
    candidates: Sequence[BeneficialOwnershipListingCandidate],
) -> tuple[BeneficialOwnershipListingCandidate, ...]:
    """Deduplicate repeated accessions across watched filer listings."""
    by_accession: dict[str, BeneficialOwnershipListingCandidate] = {}
    for candidate in candidates:
        existing = by_accession.get(candidate.accession_number)
        if existing is not None and existing != candidate:
            if (
                existing.filer_cik,
                existing.form,
                existing.accepted_at,
                existing.primary_document,
            ) != (
                candidate.filer_cik,
                candidate.form,
                candidate.accepted_at,
                candidate.primary_document,
            ):
                raise SchemaError("SEC Schedule 13D/G duplicate accession has conflicting rows")
            continue
        by_accession[candidate.accession_number] = candidate
    return tuple(
        sorted(by_accession.values(), key=lambda row: (row.accepted_at, row.accession_number))
    )


def derive_beneficial_ownership_xml_url(
    filer_cik: str,
    accession_number: str,
    primary_document: str,
    *,
    allowed_locator_prefixes: Sequence[str] = DEFAULT_LOCATOR_PREFIXES,
) -> str:
    """Derive a raw archive URL only from a manifest-approved locator."""
    if not _CIK.fullmatch(filer_cik):
        raise SchemaError("SEC Schedule 13D/G filer CIK is invalid")
    if not _ACCESSION.fullmatch(accession_number):
        raise SchemaError("SEC Schedule 13D/G accession is invalid")
    if not isinstance(primary_document, str) or primary_document != primary_document.strip():
        raise SchemaError("SEC Schedule 13D/G primary document locator is invalid")
    if (
        not primary_document
        or "\\" in primary_document
        or any(marker in primary_document for marker in ("://", "@", "?", "#"))
    ):
        raise SchemaError("SEC Schedule 13D/G primary document locator is unsafe")
    parts = primary_document.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise SchemaError("SEC Schedule 13D/G primary document locator has unsafe nesting")
    if len(parts) == 1:
        basename = parts[0]
    elif len(parts) == 2 and parts[0] in set(allowed_locator_prefixes):
        basename = parts[1]
    else:
        raise SchemaError("SEC Schedule 13D/G primary document locator has unapproved nesting")
    if not _XML_BASENAME.fullmatch(basename):
        raise SchemaError("SEC Schedule 13D/G primary document must be an XML basename")
    return (
        f"https://www.sec.gov/Archives/edgar/data/{filer_cik}/"
        f"{accession_number.replace('-', '')}/{basename}"
    )


def derive_beneficial_ownership_historical_url(
    filer_cik: str,
    accession_number: str,
    primary_document: str,
    *,
    allowed_locator_prefixes: Sequence[str] = DEFAULT_LOCATOR_PREFIXES,
) -> str:
    """Derive a safe official URL for a historical unsupported document."""
    if not _CIK.fullmatch(filer_cik) or not _ACCESSION.fullmatch(accession_number):
        raise SchemaError("SEC Schedule 13D/G historical identity is invalid")
    if not isinstance(primary_document, str) or primary_document != primary_document.strip():
        raise SchemaError("SEC Schedule 13D/G historical locator is invalid")
    if (
        not primary_document
        or "\\" in primary_document
        or any(marker in primary_document for marker in ("://", "@", "?", "#"))
    ):
        raise SchemaError("SEC Schedule 13D/G historical locator is unsafe")
    parts = primary_document.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise SchemaError("SEC Schedule 13D/G historical locator has unsafe nesting")
    if len(parts) == 1:
        basename = parts[0]
    elif len(parts) == 2 and parts[0] in set(allowed_locator_prefixes):
        basename = parts[1]
    else:
        raise SchemaError("SEC Schedule 13D/G historical locator has unapproved nesting")
    if not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9_.-]*\.(?:xml|htm|html|txt)", basename, flags=re.IGNORECASE
    ):
        raise SchemaError("SEC Schedule 13D/G historical locator extension is invalid")
    return (
        f"https://www.sec.gov/Archives/edgar/data/{filer_cik}/"
        f"{accession_number.replace('-', '')}/{basename}"
    )


# The longer name documents the trust-boundary seam.
derive_raw_beneficial_ownership_xml_url = derive_beneficial_ownership_xml_url


def _local(tag: Any) -> tuple[str, str]:
    if not isinstance(tag, str):
        raise SchemaError("SEC Schedule 13D/G XML contains an invalid tag")
    if tag.startswith("{"):
        namespace, _, name = tag[1:].partition("}")
        return namespace, name
    return "", tag


def _validate_tree(root: ET.Element, *, allowed_namespace_versions: Sequence[str]) -> str:
    namespace, name = _local(root.tag)
    if name != "edgarSubmission" or namespace not in _ALLOWED_NAMESPACES:
        raise SchemaError("SEC Schedule 13D/G XML root or namespace is unsupported")
    for element in root.iter():
        element_namespace, element_name = _local(element.tag)
        if element_namespace != namespace:
            raise SchemaError("SEC Schedule 13D/G XML mixes namespaces")
        if element_name not in _ALLOWED_XML_TAGS:
            raise SchemaError(f"SEC Schedule 13D/G XML contains unsupported {element_name}")
        if element.attrib:
            raise SchemaError("SEC Schedule 13D/G XML contains unsupported attributes")
        if list(element) and (element.text or "").strip():
            raise SchemaError("SEC Schedule 13D/G XML contains unsupported mixed content")
    version = _child_text(root, "schemaVersion", required=True)
    if version not in set(allowed_namespace_versions):
        raise SchemaError("SEC Schedule 13D/G XML schema version is unsupported")
    return namespace


def _children(parent: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in list(parent) if _local(child.tag)[1] == name]


def _one(parent: ET.Element, name: str, *, required: bool = True) -> ET.Element | None:
    matches = _children(parent, name)
    if len(matches) > 1:
        raise SchemaError(f"SEC Schedule 13D/G XML contains duplicate {name}")
    if not matches:
        if required:
            raise SchemaError(f"SEC Schedule 13D/G XML is missing {name}")
        return None
    return matches[0]


def _leaf_text(element: ET.Element | None, *, where: str, required: bool = True) -> str | None:
    if element is None:
        if required:
            raise SchemaError(f"{where} is required")
        return None
    if list(element):
        raise SchemaError(f"{where} contains unsupported mixed content")
    return _text(element.text, where=where, required=required)


def _child_text(parent: ET.Element, name: str, *, required: bool = True) -> str | None:
    return _leaf_text(_one(parent, name, required=required), where=name, required=required)


def _descendant(
    parent: ET.Element, names: Sequence[str], *, required: bool = False
) -> ET.Element | None:
    wanted = set(names)
    matches = [element for element in parent.iter() if _local(element.tag)[1] in wanted]
    if len(matches) > 1:
        raise SchemaError(f"SEC Schedule 13D/G contains duplicate {sorted(wanted)}")
    if not matches:
        if required:
            raise SchemaError(f"SEC Schedule 13D/G is missing one of {sorted(wanted)}")
        return None
    return matches[0]


def _descendant_text(
    parent: ET.Element, names: Sequence[str], *, where: str, required: bool = False
) -> str | None:
    return _leaf_text(_descendant(parent, names, required=required), where=where, required=required)


def _normalize_name(value: str) -> str:
    return " ".join(unicodedata.normalize("NFC", value).split())


def _normalize_cusip(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.replace(" ", "").replace("-", "").upper()
    if not re.fullmatch(r"[0-9A-Z*@#]{9}", normalized):
        raise SchemaError("SEC Schedule 13D/G CUSIP is invalid")
    return normalized


def _source_ref(snapshot: str, ordinal: int, field: str) -> dict[str, Any]:
    if not re.fullmatch(r"[a-z_]+\[[0-9]+\]\.[A-Za-z0-9_]+", field):
        raise SchemaError("SEC Schedule 13D/G source field locator is invalid")
    return {"snapshot": snapshot, "source_ordinal": ordinal, "field": field}


def _numeric_wrapper(
    element: ET.Element | None,
    *,
    unit: str,
    name: str,
    ref: dict[str, Any],
    required: bool,
    nonnegative: bool,
    percentage: bool = False,
) -> tuple[dict[str, Any], MeasuredNumericFact | None]:
    raw = _leaf_text(element, where=name, required=False)
    refs = [ref]
    if raw is None:
        if required:
            return (
                {
                    "status": "unavailable",
                    "value": None,
                    "unit": unit,
                    "reason": "not_reported",
                    "source_field_refs": refs,
                },
                None,
            )
        raise SchemaError(f"{name} optional numeric field is empty")
    fact = MeasuredNumericFact.from_raw(
        name=name,
        raw_value=raw.replace(",", ""),
        unit=unit,
        source_fields=(ref["field"],),
        nonnegative=nonnegative,
    )
    if percentage:
        try:
            percentage_value = Decimal(fact.value)
        except InvalidOperation as exc:
            raise SchemaError(f"{name} percentage is invalid") from exc
        if not 0 <= percentage_value <= 100:
            raise SchemaError(f"{name} percentage is outside [0, 100]")
    return (
        {
            "status": "reported",
            "value": fact.value,
            "unit": unit,
            "reason": None,
            "source_field_refs": refs,
        },
        fact,
    )


def _unavailable(unit: str, reason: str, refs: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": "unavailable",
        "value": None,
        "unit": unit,
        "reason": reason,
        "source_field_refs": refs,
    }


def _parse_position(
    element: ET.Element,
    *,
    ordinal: int,
    snapshot: str,
    form: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    person = _descendant_text(
        element,
        ("reportingPersonName", "personName", "name", "rptOwnerName"),
        where=f"reporting_person[{ordinal}].source_name",
        required=True,
    )
    if person is None:
        raise SchemaError("SEC Schedule 13D/G reporting person name is required")
    person_cik = _descendant_text(
        element,
        ("reportingPersonCik", "personCik", "cik", "rptOwnerCik"),
        where=f"reporting_person[{ordinal}].source_cik",
        required=False,
    )
    if person_cik is not None and not _CIK.fullmatch(person_cik):
        raise SchemaError(f"reporting_person[{ordinal}].source_cik is invalid")
    normalized_name = _normalize_name(person)
    identity_basis = "source_cik" if person_cik is not None else "source_name"
    types = [
        _normalize_name(_leaf_text(child, where="person_type") or "")
        for child in _children(element, "personType")
    ]
    if len(types) > 4 or any(not value for value in types):
        raise SchemaError(f"reporting_person[{ordinal}].person_type is invalid")
    group_member_text = _descendant_text(
        element, ("groupMember", "isGroupMember"), where="group membership", required=False
    )
    group_member = False
    if group_member_text is not None:
        if group_member_text.lower() not in {"true", "false", "0", "1"}:
            raise SchemaError("SEC Schedule 13D/G group membership is invalid")
        group_member = group_member_text.lower() in {"true", "1"}
    base = f"reporting_person[{ordinal}]"
    shares_element = _descendant(
        element, ("sharesOwned", "aggregateAmount", "shares"), required=False
    )
    percent_element = _descendant(
        element, ("percentOfClass", "percentOfClassOutstanding", "classPercent"), required=False
    )
    shares_ref = _source_ref(
        snapshot, ordinal, f"reporting_person[{ordinal}].beneficially_owned_shares"
    )
    percent_ref = _source_ref(
        snapshot, ordinal, f"reporting_person[{ordinal}].ownership_percentage"
    )
    shares, shares_fact = _numeric_wrapper(
        shares_element,
        unit="shares",
        name=f"{base}.beneficially_owned_shares",
        ref=shares_ref,
        required=True,
        nonnegative=True,
    )
    percentage, percentage_fact = _numeric_wrapper(
        percent_element,
        unit="percent",
        name=f"{base}.ownership_percentage",
        ref=percent_ref,
        required=True,
        nonnegative=True,
        percentage=True,
    )
    values: dict[str, Any] = {
        "source_ordinal": ordinal,
        "source_name": normalized_name,
        "source_cik": person_cik,
        "identity_basis": identity_basis,
        "person_types": sorted(set(types)),
        "group_membership": {"is_member": group_member},
        "beneficially_owned_shares": shares,
        "ownership_percentage": percentage,
        "source_field_refs": sorted([shares_ref, percent_ref], key=lambda ref: ref["field"]),
    }
    facts = {
        "identity_key": ("cik", person_cik) if person_cik else ("name", normalized_name),
        "shares": shares_fact,
        "percentage": percentage_fact,
    }
    optional_fields = (
        ("votingPower", "voting_power", "shares"),
        ("dispositivePower", "dispositive_power", "shares"),
    )
    for xml_name, output_name, unit in optional_fields:
        optional = _descendant(element, (xml_name,), required=False)
        if optional is not None:
            ref = _source_ref(snapshot, ordinal, f"reporting_person[{ordinal}].{output_name}")
            wrapper, fact = _numeric_wrapper(
                optional,
                unit=unit,
                name=f"{base}.{output_name}",
                ref=ref,
                required=True,
                nonnegative=True,
            )
            values[output_name] = wrapper
            values["source_field_refs"].append(ref)
            facts[output_name] = fact
    values["source_field_refs"].sort(key=lambda ref: ref["field"])
    return values, facts


def _find_form_data(root: ET.Element) -> ET.Element:
    form_data = _one(root, "formData", required=False)
    return form_data if form_data is not None else root


def _parse_form_document(
    body: bytes | str,
    candidate: BeneficialOwnershipListingCandidate,
    *,
    source_url: str,
    allowed_schema_versions: Sequence[str],
    allowed_locator_prefixes: Sequence[str],
) -> NormalizedBeneficialOwnership:
    if isinstance(body, bytes):
        try:
            text = body.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise SchemaError("SEC Schedule 13D/G XML is not UTF-8") from exc
    else:
        text = body
    if not isinstance(text, str) or text.startswith("\ufeff"):
        raise SchemaError("SEC Schedule 13D/G XML has a disallowed BOM")
    expected_url = derive_beneficial_ownership_xml_url(
        candidate.filer_cik,
        candidate.accession_number,
        candidate.primary_document,
        allowed_locator_prefixes=allowed_locator_prefixes,
    )
    if source_url != expected_url:
        raise SchemaError("SEC Schedule 13D/G source URL does not match selected raw XML")
    if "<!" in text or re.search(
        r"&(?!(?:amp|lt|gt|quot|apos);)(?:[A-Za-z][A-Za-z0-9]+|#\d+);", text
    ):
        raise SchemaError("SEC Schedule 13D/G XML contains DTD/entity content")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise SchemaError("SEC Schedule 13D/G XML is malformed") from exc
    _validate_tree(root, allowed_namespace_versions=allowed_schema_versions)
    submission_type = _descendant_text(
        root, ("submissionType", "formType", "documentType"), where="submission_type", required=True
    )
    document_accession = _descendant_text(
        root, ("accessionNumber",), where="accession_number", required=False
    )
    if document_accession is not None and document_accession != candidate.accession_number:
        raise SchemaError("SEC Schedule 13D/G document accession conflicts with submissions")
    document_filer = _descendant_text(
        root, ("filerCik", "reportingFilerCik"), where="filer_cik", required=False
    )
    if document_filer is not None and document_filer != candidate.filer_cik:
        raise SchemaError("SEC Schedule 13D/G document filer CIK conflicts with submissions")
    if submission_type != candidate.form:
        raise SchemaError("SEC Schedule 13D/G document form conflicts with submissions")
    form_data = _find_form_data(root)
    issuer = _one(form_data, "issuerInfo", required=False)
    if issuer is None:
        issuer = _one(form_data, "issuer", required=False)
    if issuer is None:
        raise SchemaError("SEC Schedule 13D/G issuer information is required")
    issuer_cik = _descendant_text(issuer, ("issuerCik", "cik"), where="issuer.cik", required=False)
    issuer_name = _descendant_text(
        issuer, ("issuerName", "name"), where="issuer.name", required=True
    )
    if issuer_name is None:
        raise SchemaError("SEC Schedule 13D/G issuer name is required")
    if issuer_cik is not None and not _CIK.fullmatch(issuer_cik):
        raise SchemaError("SEC Schedule 13D/G issuer CIK is invalid")
    class_title = _descendant_text(
        issuer, ("classTitle", "titleOfClass", "securityTitle"), where="class_title", required=False
    )
    cusip = _normalize_cusip(
        _descendant_text(issuer, ("cusip", "classCusip"), where="cusip", required=False)
    )
    if cusip is not None:
        class_identity = {"cusip": cusip, "title": class_title, "identity_basis": "cusip"}
        class_key: tuple[str, str] | None = ("cusip", cusip)
    elif class_title is not None:
        normalized_title = _normalize_name(class_title)
        class_identity = {
            "cusip": None,
            "title": normalized_title,
            "identity_basis": "class_title",
        }
        class_key = ("class_title", normalized_title)
    else:
        class_identity = {"cusip": None, "title": None, "identity_basis": "unavailable"}
        class_key = None
    person_nodes = _children(form_data, "reportingPerson")
    if not person_nodes:
        section = _one(form_data, "reportingPersons", required=False)
        person_nodes = _children(section, "reportingPerson") if section is not None else []
    if not person_nodes:
        person_nodes = [
            element
            for element in form_data.iter()
            if _local(element.tag)[1] in {"reportingPerson", "reportingOwner"}
        ]
    if not person_nodes:
        raise SchemaError("SEC Schedule 13D/G requires a reporting person")
    if len(person_nodes) > MAX_REPORTING_POSITIONS:
        raise SchemaError("SEC Schedule 13D/G reporting-position bound is exceeded")
    positions: list[dict[str, Any]] = []
    facts: list[dict[str, Any]] = []
    for ordinal, person_node in enumerate(person_nodes):
        position, position_facts = _parse_position(
            person_node,
            ordinal=ordinal,
            snapshot="current",
            form=candidate.form,
        )
        positions.append(position)
        facts.append(position_facts)
    amendment_number_text = _descendant_text(
        form_data, ("amendmentNumber", "amendmentNo"), where="amendment_number", required=False
    )
    amendment_number: int | None = None
    if amendment_number_text is not None:
        try:
            amendment_number = int(amendment_number_text)
        except ValueError as exc:
            raise SchemaError("SEC Schedule 13D/G amendment number is invalid") from exc
        if amendment_number <= 0:
            raise SchemaError("SEC Schedule 13D/G amendment number is invalid")
    if candidate.is_amendment and amendment_number is None:
        # Some structured submissions expose only the /A form token.  The
        # source-supported amendment status remains valid without a number.
        amendment_number = None
    if not candidate.is_amendment and amendment_number is not None:
        raise SchemaError("non-amendment Schedule 13D/G must not contain amendment number")
    group_node = _one(form_data, "group", required=False)
    group_evidence = None
    if group_node is not None:
        group_name = _descendant_text(
            group_node, ("name", "groupName"), where="group.name", required=False
        )
        aggregate = _descendant_text(
            group_node,
            ("aggregateShares", "aggregateAmount"),
            where="group.aggregate_shares",
            required=False,
        )
        aggregate_wrapper = None
        if aggregate is not None:
            ref = _source_ref("current", 0, "group[0].aggregate_shares")
            aggregate_fact = MeasuredNumericFact.from_raw(
                name="group.aggregate_shares",
                raw_value=aggregate.replace(",", ""),
                unit="shares",
                source_fields=(ref["field"],),
                nonnegative=True,
            )
            aggregate_wrapper = {
                "status": "reported",
                "value": aggregate_fact.value,
                "unit": "shares",
                "reason": None,
                "source_field_refs": [ref],
            }
        group_evidence = {
            "name": group_name,
            "aggregate_shares": aggregate_wrapper,
            "is_explicit": True,
        }
    snapshot_payload = {
        "accession_number": candidate.accession_number,
        "form": candidate.form,
        "schedule_family": candidate.schedule_family,
        "filed_at": candidate.filed_at,
        "accepted_at": candidate.accepted_at,
        "document_url": source_url,
        "issuer": {"cik": issuer_cik, "name": _normalize_name(issuer_name)},
        "ownership_class": class_identity,
        "reporting_positions": positions,
        "group_evidence": group_evidence,
        "is_amendment": candidate.is_amendment,
        "amendment_number": amendment_number,
    }
    snapshot = BeneficialOwnershipSnapshot(
        payload=snapshot_payload,
        position_facts=tuple(facts),
        filer_cik=candidate.filer_cik,
        issuer_cik=issuer_cik,
        class_key=class_key,
        accepted_at=candidate.accepted_at,
        accession_number=candidate.accession_number,
        source_url=source_url,
    )
    payload = {
        "type": "filing",
        "filing_subtype": "beneficial_ownership",
        "form": candidate.form,
        "company": candidate.filer_cik,
        "accession_number": candidate.accession_number,
        "filed_at": candidate.filed_at,
        "accepted_at": candidate.accepted_at,
        "document_url": source_url,
        "schedule_family": candidate.schedule_family,
        "is_amendment": candidate.is_amendment,
        "amendment_number": amendment_number,
        "current_snapshot": snapshot_payload,
        "previous_snapshot": None,
        "comparison": {
            "status": "unavailable",
            "reason": "history_not_evaluated",
            "previous": None,
        },
    }
    return NormalizedBeneficialOwnership(
        candidate=candidate,
        payload=payload,
        source_url=source_url,
        snapshot=snapshot,
    )


def parse_schedule_13d_document(
    body: bytes | str,
    candidate: BeneficialOwnershipListingCandidate,
    *,
    source_url: str,
    allowed_schema_versions: Sequence[str] = SUPPORTED_SCHEMA_VERSIONS,
    allowed_locator_prefixes: Sequence[str] = DEFAULT_LOCATOR_PREFIXES,
) -> NormalizedBeneficialOwnership:
    if candidate.form not in {"SCHEDULE 13D", "SCHEDULE 13D/A"}:
        raise SchemaError("13D parser received a non-13D form")
    return _parse_form_document(
        body,
        candidate,
        source_url=source_url,
        allowed_schema_versions=allowed_schema_versions,
        allowed_locator_prefixes=allowed_locator_prefixes,
    )


def parse_schedule_13g_document(
    body: bytes | str,
    candidate: BeneficialOwnershipListingCandidate,
    *,
    source_url: str,
    allowed_schema_versions: Sequence[str] = SUPPORTED_SCHEMA_VERSIONS,
    allowed_locator_prefixes: Sequence[str] = DEFAULT_LOCATOR_PREFIXES,
) -> NormalizedBeneficialOwnership:
    if candidate.form not in {"SCHEDULE 13G", "SCHEDULE 13G/A"}:
        raise SchemaError("13G parser received a non-13G form")
    return _parse_form_document(
        body,
        candidate,
        source_url=source_url,
        allowed_schema_versions=allowed_schema_versions,
        allowed_locator_prefixes=allowed_locator_prefixes,
    )


def is_unsupported_historical_document(
    body: bytes | str,
    candidate: BeneficialOwnershipListingCandidate,
    *,
    allowed_schema_versions: Sequence[str],
) -> bool:
    """Recognize only declared legacy/non-XML history as unsupported format."""
    if candidate.primary_document.lower().endswith((".htm", ".html", ".txt")):
        return True
    if not isinstance(body, str):
        try:
            body = body.decode("utf-8")
        except UnicodeDecodeError:
            return False
    match = re.search(
        r"<(?:[A-Za-z_][A-Za-z0-9_.-]*:)?schemaVersion\b[^>]*>\s*([^<]+?)\s*</(?:[A-Za-z_][A-Za-z0-9_.-]*:)?schemaVersion>",
        body,
    )
    return match is not None and match.group(1).strip() not in set(allowed_schema_versions)


def parse_beneficial_ownership_document(
    body: bytes | str,
    candidate: BeneficialOwnershipListingCandidate,
    *,
    source_url: str,
    allowed_schema_versions: Sequence[str] = SUPPORTED_SCHEMA_VERSIONS,
    allowed_locator_prefixes: Sequence[str] = DEFAULT_LOCATOR_PREFIXES,
) -> NormalizedBeneficialOwnership:
    """Dispatch only to the exact form-specific 13D or 13G contract."""
    if candidate.schedule_family == "13D":
        return parse_schedule_13d_document(
            body,
            candidate,
            source_url=source_url,
            allowed_schema_versions=allowed_schema_versions,
            allowed_locator_prefixes=allowed_locator_prefixes,
        )
    return parse_schedule_13g_document(
        body,
        candidate,
        source_url=source_url,
        allowed_schema_versions=allowed_schema_versions,
        allowed_locator_prefixes=allowed_locator_prefixes,
    )


# Fixture/API aliases.
parse_13d_document = parse_schedule_13d_document
parse_13g_document = parse_schedule_13g_document
parse_ownership_document = parse_beneficial_ownership_document
normalize_beneficial_ownership = parse_beneficial_ownership_document


def _copy_snapshot(snapshot: BeneficialOwnershipSnapshot, *, label: str) -> dict[str, Any]:
    """Copy a parsed snapshot while rebinding document-local references."""
    import copy

    value = copy.deepcopy(snapshot.payload)
    for position in value["reporting_positions"]:
        for ref in position["source_field_refs"]:
            ref["snapshot"] = label
        for field in (
            "beneficially_owned_shares",
            "ownership_percentage",
            "voting_power",
            "dispositive_power",
        ):
            wrapper = position.get(field)
            if isinstance(wrapper, dict):
                for ref in wrapper["source_field_refs"]:
                    ref["snapshot"] = label
    group_evidence = value.get("group_evidence")
    if isinstance(group_evidence, dict):
        aggregate = group_evidence.get("aggregate_shares")
        if isinstance(aggregate, dict):
            for ref in aggregate.get("source_field_refs", []):
                ref["snapshot"] = label
    return value


def _fact_wrapper(
    current: dict[str, Any], previous: dict[str, Any] | None, *, unit: str, field: str
) -> dict[str, Any]:
    current_fact = current.get(field)
    previous_fact = previous.get(field) if previous else None
    if not isinstance(current_fact, MeasuredNumericFact) or not isinstance(
        previous_fact, MeasuredNumericFact
    ):
        return _unavailable(unit, "missing_operand", [])
    if unit == "percentage_points":
        current_fact = MeasuredNumericFact.from_canonical(
            name=f"current.{field}",
            value=current_fact.value,
            unit=unit,
            source_fields=current_fact.source_fields,
        )
        previous_fact = MeasuredNumericFact.from_canonical(
            name=f"previous.{field}",
            value=previous_fact.value,
            unit=unit,
            source_fields=previous_fact.source_fields,
        )
    derived = derive_subtraction(
        name=f"current_minus_previous.{field}",
        minuend=current_fact,
        subtrahend=previous_fact,
    )
    return {
        "status": "reported",
        "value": derived.value,
        "unit": unit,
        "reason": None,
        "source_field_refs": [],
        "derivation": "current_minus_previous",
    }


def resolve_previous_comparable(
    current: NormalizedBeneficialOwnership,
    previous: Sequence[NormalizedBeneficialOwnership],
) -> NormalizedBeneficialOwnership | None:
    """Return the nearest earlier filing matching filer, issuer, and class."""
    candidates = [
        value
        for value in previous
        if value.snapshot.supported
        and value.snapshot.filer_cik == current.snapshot.filer_cik
        and value.snapshot.issuer_cik == current.snapshot.issuer_cik
        and value.snapshot.class_key == current.snapshot.class_key
        and _timestamp(value.snapshot.accepted_at) < _timestamp(current.snapshot.accepted_at)
        and value.snapshot.accession_number != current.snapshot.accession_number
    ]
    return max(
        candidates,
        key=lambda value: (value.snapshot.accepted_at, value.snapshot.accession_number),
        default=None,
    )


@dataclass(frozen=True, slots=True)
class PreviousResolution:
    """Closed outcome for one current filing's previous-evidence lookup."""

    status: str
    previous: NormalizedBeneficialOwnership | None = None
    candidate: BeneficialOwnershipListingCandidate | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class SharedHistoricalCandidateIndex:
    """Immutable-in-use per-run index of parsed historical candidates."""

    parsed: Mapping[str, NormalizedBeneficialOwnership]
    unsupported: frozenset[str]
    resolutions: Mapping[str, PreviousResolution]


def resolve_previous_candidate(
    current: NormalizedBeneficialOwnership,
    candidates: Sequence[BeneficialOwnershipListingCandidate],
    parsed: Mapping[str, NormalizedBeneficialOwnership],
    *,
    unsupported_accessions: frozenset[str] = frozenset(),
    history_complete: bool = False,
    history_evaluated: bool = True,
    bound_exhausted: bool = False,
) -> PreviousResolution:
    """Resolve the nearest earlier candidate without skipping unsupported evidence."""
    if current.snapshot.issuer_cik is None:
        return PreviousResolution("unavailable", reason="reporting_identity_not_comparable")
    if current.snapshot.class_key is None:
        return PreviousResolution("unavailable", reason="ownership_class_identity_unavailable")
    ordered = sorted(
        candidates, key=lambda row: (row.accepted_at, row.accession_number), reverse=True
    )
    current_time = _timestamp(current.snapshot.accepted_at)
    for candidate in ordered:
        if candidate.filer_cik != current.snapshot.filer_cik:
            continue
        if candidate.accession_number == current.snapshot.accession_number:
            continue
        if _timestamp(candidate.accepted_at) >= current_time:
            continue
        if candidate.accession_number in unsupported_accessions:
            return PreviousResolution(
                "unavailable",
                candidate=candidate,
                reason="previous_format_unsupported",
            )
        previous = parsed.get(candidate.accession_number)
        if previous is None:
            continue
        if (
            previous.snapshot.issuer_cik == current.snapshot.issuer_cik
            and previous.snapshot.class_key == current.snapshot.class_key
        ):
            return PreviousResolution("available", previous=previous, candidate=candidate)
    if bound_exhausted:
        return PreviousResolution("unavailable", reason="history_candidate_bound_exhausted")
    if history_complete:
        return PreviousResolution("initial_filing")
    return PreviousResolution(
        "unavailable",
        reason="history_not_evaluated"
        if not history_evaluated
        else "history_candidate_bound_exhausted",
    )


def build_shared_historical_candidate_index(
    currents: Sequence[NormalizedBeneficialOwnership],
    candidates: Sequence[BeneficialOwnershipListingCandidate],
    load: Any,
    *,
    max_candidate_documents: int = MAX_HISTORICAL_CANDIDATE_DOCUMENTS,
    history_complete: bool = False,
    history_evaluated: bool = True,
    history_bound_exhausted: bool = False,
) -> SharedHistoricalCandidateIndex:
    """Fetch/parse each reverse candidate once and reuse it across current keys."""
    if (
        isinstance(max_candidate_documents, bool)
        or not isinstance(max_candidate_documents, int)
        or max_candidate_documents <= 0
    ):
        raise SchemaError("SEC Schedule 13D/G historical candidate bound is invalid")
    ordered = sorted(
        candidates, key=lambda row: (row.accepted_at, row.accession_number), reverse=True
    )
    parsed: dict[str, NormalizedBeneficialOwnership] = {}
    unsupported: set[str] = set()
    resolutions: dict[str, PreviousResolution] = {}
    unresolved = {current.snapshot.accession_number: current for current in currents}
    seen: set[str] = set()
    scanned = 0
    for accession, current in tuple(unresolved.items()):
        result = resolve_previous_candidate(
            current,
            (),
            parsed,
            unsupported_accessions=frozenset(unsupported),
            history_complete=False,
            history_evaluated=history_evaluated,
            bound_exhausted=False,
        )
        if result.reason in {
            "reporting_identity_not_comparable",
            "ownership_class_identity_unavailable",
        }:
            resolutions[accession] = result
            unresolved.pop(accession)
    for candidate in ordered:
        if candidate.accession_number in seen:
            continue
        seen.add(candidate.accession_number)
        if scanned >= max_candidate_documents or not unresolved:
            break
        scanned += 1
        value = load(candidate)
        if value is None:
            unsupported.add(candidate.accession_number)
        else:
            parsed[candidate.accession_number] = value
        for accession, current in tuple(unresolved.items()):
            result = resolve_previous_candidate(
                current,
                ordered[:scanned],
                parsed,
                unsupported_accessions=frozenset(unsupported),
                history_complete=False,
                history_evaluated=history_evaluated,
                bound_exhausted=False,
            )
            if result.status == "available" or result.reason in {
                "previous_format_unsupported",
                "reporting_identity_not_comparable",
                "ownership_class_identity_unavailable",
            }:
                resolutions[accession] = result
                unresolved.pop(accession)
    bound_exhausted = (
        history_bound_exhausted
        or len(ordered) > max_candidate_documents
        or (len(ordered) >= max_candidate_documents and not history_complete and history_evaluated)
    )
    for accession, current in unresolved.items():
        resolutions[accession] = resolve_previous_candidate(
            current,
            ordered[:scanned],
            parsed,
            unsupported_accessions=frozenset(unsupported),
            history_complete=history_complete and not bound_exhausted,
            history_evaluated=history_evaluated,
            bound_exhausted=bound_exhausted,
        )
    return SharedHistoricalCandidateIndex(
        parsed=parsed,
        unsupported=frozenset(unsupported),
        resolutions=resolutions,
    )


def compare_beneficial_ownership(
    current: NormalizedBeneficialOwnership,
    previous: NormalizedBeneficialOwnership | None,
    *,
    unavailable_reason: str | None = None,
    previous_reference: BeneficialOwnershipListingCandidate | None = None,
    previous_reference_url: str | None = None,
) -> NormalizedBeneficialOwnership:
    """Attach conservative comparison and exact current-minus-previous deltas."""
    import copy

    payload = copy.deepcopy(current.payload)
    current_snapshot = payload["current_snapshot"]
    if previous is None:
        status = "unavailable" if unavailable_reason else "initial_filing"
        reason = unavailable_reason
        if status == "unavailable" and reason is None:
            reason = "missing_operand"
        for position in current_snapshot["reporting_positions"]:
            position["comparison"] = {
                "status": "unavailable",
                "reason": "missing_operand",
                "shares_delta": _unavailable("shares", "missing_operand", []),
                "percentage_delta": _unavailable("percentage_points", "missing_operand", []),
            }
        previous_ref = None
        if previous_reference is not None:
            previous_ref = {
                "accession_number": previous_reference.accession_number,
                "accepted_at": previous_reference.accepted_at,
                "document_url": previous_reference_url
                or derive_beneficial_ownership_historical_url(
                    previous_reference.filer_cik,
                    previous_reference.accession_number,
                    previous_reference.primary_document,
                ),
            }
        payload["comparison"] = {"status": status, "reason": reason, "previous": previous_ref}
        return NormalizedBeneficialOwnership(
            candidate=current.candidate,
            payload=payload,
            source_url=current.source_url,
            snapshot=current.snapshot,
        )
    previous_snapshot = _copy_snapshot(previous.snapshot, label="previous")
    payload["previous_snapshot"] = previous_snapshot
    comparison = {
        "status": "available",
        "reason": None,
        "previous": {
            "accession_number": previous.snapshot.accession_number,
            "accepted_at": previous.snapshot.accepted_at,
            "document_url": previous.snapshot.source_url,
        },
    }
    previous_by_key = {fact["identity_key"]: fact for fact in previous.snapshot.position_facts}
    for ordinal, current_fact in enumerate(current.snapshot.position_facts):
        position = current_snapshot["reporting_positions"][ordinal]
        prior_fact = previous_by_key.get(current_fact["identity_key"])
        if prior_fact is None:
            position["comparison"] = {
                "status": "unavailable",
                "reason": "reporting_identity_not_comparable",
                "shares_delta": _unavailable("shares", "missing_operand", []),
                "percentage_delta": _unavailable("percentage_points", "missing_operand", []),
            }
            continue
        position["comparison"] = {
            "status": "available",
            "reason": None,
            "shares_delta": _fact_wrapper(current_fact, prior_fact, unit="shares", field="shares"),
            "percentage_delta": _fact_wrapper(
                current_fact, prior_fact, unit="percentage_points", field="percentage"
            ),
        }
    payload["comparison"] = comparison
    return NormalizedBeneficialOwnership(
        candidate=current.candidate,
        payload=payload,
        source_url=current.source_url,
        snapshot=current.snapshot,
    )


compare_ownership = compare_beneficial_ownership
