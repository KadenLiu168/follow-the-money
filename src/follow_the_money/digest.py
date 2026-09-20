"""Deterministic, non-persisted preparation for Host-Agent digest input."""

from __future__ import annotations

import argparse
import copy
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any

from .canonical import canonical_bytes
from .config.model import SUPPORTED_FEED_PAYLOAD_TYPES
from .feed.remote import FeedRemoteError, consume_published_feed

CONTEXT_VERSION = 2
DOMAIN_ORDER = SUPPORTED_FEED_PAYLOAD_TYPES
SCOPE_ORDER: tuple[str, ...] = (
    "news",
    "macro_release",
    "policy",
    "cftc",
    "form13f",
    "form4",
    "beneficial_ownership",
)
SCOPE_DOMAIN: Mapping[str, str] = MappingProxyType(
    {
        "news": "news",
        "macro_release": "macro_release",
        "policy": "policy",
        "cftc": "positioning",
        "form13f": "filing",
        "form4": "filing",
        "beneficial_ownership": "filing",
    }
)
DOMAIN_UNIT_TYPE: Mapping[str, str] = MappingProxyType(
    {
        "news": "news_publication",
        "macro_release": "macro_release",
        "policy": "policy_document",
        "positioning": "positioning_report",
        "filing": "sec_filing",
    }
)
UNIT_TYPES = frozenset(DOMAIN_UNIT_TYPE.values())
# Feed domain -> (event-time kind, path of the closed current-membership authority).
MEMBERSHIP_AUTHORITY: Mapping[str, tuple[str, tuple[str, ...]]] = MappingProxyType(
    {
        "news": ("published_at", ("source", "published_at")),
        "macro_release": ("released_at", ("payload", "released_at")),
        "policy": ("announced_at", ("payload", "announced_at")),
        "filing": ("accepted_at", ("payload", "accepted_at")),
    }
)
FILING_SUBTYPES = frozenset({"form13f", "form4", "beneficial_ownership"})
DOMAIN_STATES = frozenset(
    {
        "current_updates_available",
        "no_current_update",
        "carried_reference_state",
        "stale_reference_state",
        "current_membership_unproven",
        "provider_unavailable",
        "domain_empty",
    }
)
LIMITATION_CODES: tuple[str, ...] = ("provider_unavailable", "coverage_gap")


class DigestPreparationError(ValueError):
    """A validated Feed could not be prepared into the v2 DigestContext."""


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(child) for key, child in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(child) for child in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(child) for key, child in value.items()}
    if isinstance(value, tuple):
        return [_thaw(child) for child in value]
    return copy.deepcopy(value)


def _mapping(value: Any, where: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise DigestPreparationError(f"{where}: object is required")
    return value


def _sequence(value: Any, where: str) -> Sequence[Any]:
    if not isinstance(value, (list, tuple)):
        raise DigestPreparationError(f"{where}: array is required")
    return value


def _copy_keys(value: Any, keys: Sequence[str], where: str) -> dict[str, Any]:
    source = _mapping(value, where)
    return {key: copy.deepcopy(source[key]) for key in keys if key in source}


def _copy_required(value: Any, key: str, where: str) -> Any:
    source = _mapping(value, where)
    if key not in source:
        raise DigestPreparationError(f"{where}.{key}: missing from validated Feed")
    return copy.deepcopy(source[key])


def _timestamp(value: Any, where: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise DigestPreparationError(f"{where}: missing timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise DigestPreparationError(f"{where}: invalid timestamp {value!r}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise DigestPreparationError(f"{where}: timestamp must carry a timezone")
    return parsed.astimezone(UTC)


def _nested(value: Any, path: Sequence[str]) -> Any:
    current = value
    for key in path:
        if not isinstance(current, Mapping) or key not in current:
            return None
        current = current[key]
    return current


def _unique_paths(paths: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(paths))


COMMON_PATHS = (
    "id",
    "provider_id",
    "source.id",
    "source.name",
    "source.tier",
    "source.kind",
    "source.url",
    "source.published_at",
    "source.updated_at",
    "source.knowledge_available_at",
    "source.original_publisher",
    "source.syndication_origin",
    "source_lineage[].id",
    "source_lineage[].provider_id",
    "source_lineage[].source_id",
    "source_lineage[].original_publisher",
    "source_lineage[].syndication_origin",
)
SEMANTIC_PATHS = (
    "semantic_context.version",
    "semantic_context.entities[].role",
    "semantic_context.entities[].name",
    "semantic_context.entities[].type",
    "semantic_context.event.category",
    "semantic_context.event.occurred_at",
    "semantic_context.numeric_facts[].metric",
    "semantic_context.numeric_facts[].role",
    "semantic_context.numeric_facts[].value",
    "semantic_context.numeric_facts[].unit",
    "semantic_context.numeric_facts[].unknown_reason",
)
SEMANTIC_NEWS_PATHS = (
    "semantic_context.extension.type",
    "semantic_context.extension.document.title",
    "semantic_context.extension.document.type",
)
SEMANTIC_MACRO_PATHS = (
    "semantic_context.extension.type",
    "semantic_context.extension.indicator.id",
    "semantic_context.extension.indicator.name",
    "semantic_context.extension.period.period",
    "semantic_context.extension.revision.previous.value",
    "semantic_context.extension.revision.previous.unit",
    "semantic_context.extension.revision.revised.value",
    "semantic_context.extension.revision.revised.unit",
)
SEMANTIC_POLICY_PATHS = (
    "semantic_context.extension.type",
    "semantic_context.extension.policy_type",
    "semantic_context.extension.action",
    "semantic_context.extension.effective_at",
    "semantic_context.extension.affected_scope[]",
)
POSITIONING_PATHS = ("payload.as_of",)
FILING_COMMON_PATHS = (
    "payload.type",
    "payload.filing_subtype",
    "payload.form",
    "payload.company",
    "payload.accession_number",
    "payload.filed_at",
    "payload.company_identity.cik",
    "payload.company_identity.name",
    "payload.company_identity.tickers[]",
    "payload.report_period",
    "payload.accepted_at",
    "payload.value_normalization.source_unit",
    "payload.value_normalization.formula_id",
    "payload.document_url",
    "payload.is_amendment",
    "payload.amendment_number",
)
FILING_13F_PATHS = (
    "payload.comparison.status",
    "payload.comparison.previous_accession_number",
    "payload.comparison.previous_report_period",
    "payload.comparison.previous_accepted_at",
    "payload.comparison.previous_filed_at",
    "payload.comparison.previous_source_url",
    "payload.comparison.previous_value_normalization.source_unit",
    "payload.comparison.previous_value_normalization.formula_id",
    "payload.comparison.reason",
    *(
        f"payload.holdings[].security.{field}"
        for field in ("cusip", "figi", "issuer_name", "title_of_class", "put_call", "amount_type")
    ),
    *(
        f"payload.holdings[].{side}.reported_{field}.{part}"
        for side in ("current", "previous", "delta")
        for field in ("amount", "value_usd_thousands")
        for part in ("value", "unit", "unknown_reason")
    ),
    "payload.holdings[].change_type",
)
FORM4_ENTRY_PATHS = (
    "payload.issuer.cik",
    "payload.issuer.name",
    "payload.issuer.trading_symbol",
    "payload.reporting_owners[].cik",
    "payload.reporting_owners[].name",
    *(
        f"payload.reporting_owners[].relationship.{field}"
        for field in (
            "director",
            "officer",
            "ten_percent_owner",
            "other",
            "officer_title",
            "other_text",
        )
    ),
    "payload.non_derivative_entries[]",
    "payload.derivative_entries[]",
    *(
        f"payload.{table}[].{field}"
        for table in ("non_derivative_entries", "derivative_entries")
        for field in (
            "entry_kind",
            "source_ordinal",
            "entry_id",
            "security_title",
            "post_transaction_amount",
            "ownership_nature",
            "derivative_terms",
            "underlying_security",
            "field_references[]",
            "transaction_date",
            "deemed_execution_date",
            "transaction_coding",
            "timeliness",
            "transaction_amount",
            "price_per_share",
            "acquisition_disposition_code",
        )
    ),
    *(
        f"payload.{table}[].transaction_coding.{field}"
        for table in ("non_derivative_entries", "derivative_entries")
        for field in ("transaction_form_type", "transaction_code", "equity_swap_involved")
    ),
    *(
        f"payload.{table}[].ownership_nature.{field}"
        for table in ("non_derivative_entries", "derivative_entries")
        for field in ("direct_or_indirect", "nature_of_ownership")
    ),
    *(
        f"payload.{table}[].derivative_terms.{field}"
        for table in ("non_derivative_entries", "derivative_entries")
        for field in ("exercise_date", "expiration_date", "conversion_or_exercise_price")
    ),
    *(
        f"payload.{table}[].underlying_security.{field}"
        for table in ("non_derivative_entries", "derivative_entries")
        for field in ("title", "amount")
    ),
    "payload.footnotes[].id",
    "payload.footnotes[].text",
    "payload.remarks",
    "payload.date_of_original_submission",
)
BENEFICIAL_PATHS = (
    "payload.schedule_family",
    *(
        f"payload.{side}_snapshot.{field}"
        for side in ("current", "previous")
        for field in (
            "accession_number",
            "form",
            "schedule_family",
            "filed_at",
            "accepted_at",
            "document_url",
            "issuer",
            "ownership_class",
            "reporting_positions[]",
            "group_evidence",
            "is_amendment",
            "amendment_number",
        )
    ),
    "payload.comparison.status",
    "payload.comparison.reason",
    "payload.comparison.previous.accession_number",
    "payload.comparison.previous.accepted_at",
    "payload.comparison.previous.document_url",
    *(
        f"payload.{side}_snapshot.issuer.{field}"
        for side in ("current", "previous")
        for field in ("cik", "name")
    ),
    *(
        f"payload.{side}_snapshot.ownership_class.{field}"
        for side in ("current", "previous")
        for field in ("cusip", "title", "identity_basis")
    ),
    *(
        f"payload.current_snapshot.reporting_positions[].{field}"
        for field in (
            "source_ordinal",
            "source_name",
            "source_cik",
            "identity_basis",
            "person_types[]",
            "group_membership.is_member",
            "source_field_refs[]",
            "comparison.status",
            "comparison.reason",
            "comparison.shares_delta",
            "comparison.percentage_delta",
        )
    ),
    *(
        f"payload.current_snapshot.reporting_positions[].{metric}.{field}"
        for metric in (
            "beneficially_owned_shares",
            "ownership_percentage",
            "voting_power",
            "dispositive_power",
        )
        for field in ("status", "value", "unit", "reason", "source_field_refs[]", "derivation")
    ),
)

#: Reader-relevant bounded official source content. Extraction provenance
#: (``extraction_method``, ``document_sha256``) stays Feed-only.
SOURCE_CONTENT_PATHS: tuple[str, ...] = (
    "payload.source_content.text",
    "payload.source_content.format",
    "payload.source_content.truncated",
)

ELIGIBLE_PATHS: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "news": _unique_paths(
            COMMON_PATHS
            + (
                "payload.type",
                "payload.title",
                "payload.snippet",
                "payload.occurred_at",
                *SOURCE_CONTENT_PATHS,
            )
            + SEMANTIC_PATHS
            + SEMANTIC_NEWS_PATHS
        ),
        "macro_release": _unique_paths(
            COMMON_PATHS
            + (
                "payload.type",
                "payload.series_id",
                "payload.released_at",
                "payload.observation_period",
                "payload.actual.value",
                "payload.actual.unit",
                "payload.actual.unknown_reason",
                "payload.consensus.value",
                "payload.consensus.unit",
                "payload.consensus.unknown_reason",
                "payload.previous.value",
                "payload.previous.unit",
                "payload.previous.unknown_reason",
                *SOURCE_CONTENT_PATHS,
            )
            + SEMANTIC_PATHS
            + SEMANTIC_MACRO_PATHS
        ),
        "policy": _unique_paths(
            COMMON_PATHS
            + (
                "payload.type",
                "payload.title",
                "payload.announced_at",
                "payload.effective_at",
                *SOURCE_CONTENT_PATHS,
            )
            + SEMANTIC_PATHS
            + SEMANTIC_POLICY_PATHS
        ),
        "positioning": _unique_paths(POSITIONING_PATHS),
        "filing": _unique_paths(
            COMMON_PATHS
            + FILING_COMMON_PATHS
            + FILING_13F_PATHS
            + FORM4_ENTRY_PATHS
            + BENEFICIAL_PATHS
        ),
    }
)


def eligible_paths(domain: str, filing_subtype: str | None = None) -> tuple[str, ...]:
    """Return the implementation-declared closed path inventory."""
    if domain not in ELIGIBLE_PATHS:
        raise DigestPreparationError(f"unsupported Feed domain: {domain!r}")
    if domain != "filing" or filing_subtype is None:
        return ELIGIBLE_PATHS[domain]
    suffix = {
        "form13f": FILING_13F_PATHS,
        "form4": FORM4_ENTRY_PATHS,
        "beneficial_ownership": BENEFICIAL_PATHS,
    }.get(filing_subtype)
    if suffix is None:
        raise DigestPreparationError(f"unsupported filing subtype: {filing_subtype!r}")
    return _unique_paths(COMMON_PATHS + FILING_COMMON_PATHS + suffix)


def _project_semantic_context(value: Any, domain: str) -> dict[str, Any]:
    context = _mapping(value, "semantic_context")
    projected = _copy_keys(context, ("version",), "semantic_context")
    if "entities" in context:
        projected["entities"] = [
            _copy_keys(entity, ("role", "name", "type"), "semantic_context.entities[]")
            for entity in _sequence(context["entities"], "semantic_context.entities")
        ]
    if "event" in context:
        projected["event"] = _copy_keys(
            context["event"], ("category", "occurred_at"), "semantic_context.event"
        )
    if "numeric_facts" in context:
        projected["numeric_facts"] = [
            _copy_keys(
                fact,
                ("metric", "role", "value", "unit", "unknown_reason"),
                "semantic_context.numeric_facts[]",
            )
            for fact in _sequence(context["numeric_facts"], "semantic_context.numeric_facts")
        ]
    extension = _mapping(
        _copy_required(context, "extension", "semantic_context"), "semantic_context.extension"
    )
    extension_projected = _copy_keys(extension, ("type",), "semantic_context.extension")
    if domain == "news" and "document" in extension:
        extension_projected["document"] = _copy_keys(
            extension["document"], ("title", "type"), "semantic_context.extension.document"
        )
    elif domain == "macro_release":
        if "indicator" in extension:
            extension_projected["indicator"] = _copy_keys(
                extension["indicator"], ("id", "name"), "semantic_context.extension.indicator"
            )
        if "period" in extension:
            period = extension["period"]
            extension_projected["period"] = (
                None
                if period is None
                else _copy_keys(period, ("period",), "semantic_context.extension.period")
            )
        if "revision" in extension:
            revision = extension["revision"]
            if revision is None:
                extension_projected["revision"] = None
            else:
                revision_map = _mapping(revision, "semantic_context.extension.revision")
                extension_projected["revision"] = {
                    key: _copy_keys(
                        revision_map[key],
                        ("value", "unit"),
                        f"semantic_context.extension.revision.{key}",
                    )
                    for key in ("previous", "revised")
                    if key in revision_map
                }
    elif domain == "policy":
        extension_projected.update(
            _copy_keys(
                extension,
                ("policy_type", "action", "effective_at", "affected_scope"),
                "semantic_context.extension",
            )
        )
    projected["extension"] = extension_projected
    return projected


def _project_source(item: Mapping[str, Any]) -> dict[str, Any]:
    source = _copy_required(item, "source", "item")
    projected = _copy_keys(
        source,
        (
            "id",
            "name",
            "tier",
            "kind",
            "url",
            "published_at",
            "updated_at",
            "knowledge_available_at",
            "original_publisher",
            "syndication_origin",
        ),
        "item.source",
    )
    return projected


def _project_lineage(item: Mapping[str, Any]) -> tuple[dict[str, Any], ...] | None:
    if "source_lineage" not in item:
        return None
    return tuple(
        _copy_keys(
            entry,
            ("id", "provider_id", "source_id", "original_publisher", "syndication_origin"),
            "item.source_lineage[]",
        )
        for entry in _sequence(item["source_lineage"], "item.source_lineage")
    )


def _numeric(value: Any, where: str) -> dict[str, Any]:
    return _copy_keys(value, ("value", "unit", "unknown_reason"), where)


def _project_source_content(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Copy reader-relevant source content without its Feed-only provenance."""
    content = _mapping(payload["source_content"], "item.payload.source_content")
    return {
        "source_content": _copy_keys(
            content, ("text", "format", "truncated"), "item.payload.source_content"
        )
    }


def _with_source_content(result: dict[str, Any], payload: Mapping[str, Any]) -> dict[str, Any]:
    if "source_content" in payload:
        result.update(_project_source_content(payload))
    return result


def _project_semantic_payload(payload: Mapping[str, Any], domain: str) -> dict[str, Any]:
    if domain == "news":
        return _with_source_content(
            _copy_keys(payload, ("type", "title", "snippet", "occurred_at"), "item.payload"),
            payload,
        )
    if domain == "macro_release":
        result = _copy_keys(
            payload,
            ("type", "series_id", "released_at", "observation_period"),
            "item.payload",
        )
        for name in ("actual", "consensus", "previous"):
            if name in payload:
                result[name] = _numeric(payload[name], f"item.payload.{name}")
        return _with_source_content(result, payload)
    if domain == "policy":
        return _with_source_content(
            _copy_keys(payload, ("type", "title", "announced_at", "effective_at"), "item.payload"),
            payload,
        )
    raise DigestPreparationError(f"unsupported semantic payload domain: {domain!r}")


def _form4_numeric(value: Any, where: str) -> dict[str, Any]:
    return _copy_keys(value, ("value", "unit", "footnote_ids"), where)


def _form4_amount(value: Any, where: str, branches: tuple[str, ...]) -> dict[str, Any]:
    amount = _mapping(value, where)
    result = _copy_keys(amount, ("branch",), where)
    for branch in branches:
        if branch in amount:
            result[branch] = (
                None
                if amount[branch] is None
                else _form4_numeric(amount[branch], f"{where}.{branch}")
            )
    return result


def _form4_entry(value: Any, where: str) -> dict[str, Any]:
    entry = _mapping(value, where)
    result = _copy_keys(
        entry,
        (
            "entry_kind",
            "source_ordinal",
            "entry_id",
            "security_title",
            "transaction_date",
            "deemed_execution_date",
            "timeliness",
            "acquisition_disposition_code",
        ),
        where,
    )
    if "transaction_coding" in entry:
        result["transaction_coding"] = _copy_keys(
            entry["transaction_coding"],
            ("transaction_form_type", "transaction_code", "equity_swap_involved"),
            f"{where}.transaction_coding",
        )
    if "transaction_amount" in entry:
        result["transaction_amount"] = _form4_amount(
            entry["transaction_amount"], f"{where}.transaction_amount", ("shares", "total_value")
        )
    if "price_per_share" in entry:
        result["price_per_share"] = (
            None
            if entry["price_per_share"] is None
            else _form4_numeric(entry["price_per_share"], f"{where}.price_per_share")
        )
    if "post_transaction_amount" in entry:
        result["post_transaction_amount"] = _form4_amount(
            entry["post_transaction_amount"],
            f"{where}.post_transaction_amount",
            ("shares", "value"),
        )
    if "ownership_nature" in entry:
        result["ownership_nature"] = _copy_keys(
            entry["ownership_nature"],
            ("direct_or_indirect", "nature_of_ownership"),
            f"{where}.ownership_nature",
        )
    if "derivative_terms" in entry:
        terms = entry["derivative_terms"]
        if terms is None:
            result["derivative_terms"] = None
        else:
            derivative_terms = _copy_keys(
                terms,
                ("exercise_date", "expiration_date", "conversion_or_exercise_price"),
                f"{where}.derivative_terms",
            )
            result["derivative_terms"] = derivative_terms
            if isinstance(terms, Mapping) and terms.get("conversion_or_exercise_price") is not None:
                derivative_terms["conversion_or_exercise_price"] = _form4_numeric(
                    terms["conversion_or_exercise_price"],
                    f"{where}.derivative_terms.conversion_or_exercise_price",
                )
    if "underlying_security" in entry:
        underlying = entry["underlying_security"]
        result["underlying_security"] = (
            None
            if underlying is None
            else {
                "title": _copy_required(underlying, "title", f"{where}.underlying_security"),
                "amount": _form4_amount(
                    _copy_required(underlying, "amount", f"{where}.underlying_security"),
                    f"{where}.underlying_security.amount",
                    ("shares", "value"),
                ),
            }
        )
    if "field_references" in entry:
        result["field_references"] = [
            _copy_keys(ref, ("field", "footnote_ids"), f"{where}.field_references[]")
            for ref in _sequence(entry["field_references"], f"{where}.field_references")
        ]
    return result


def _project_beneficial_numeric(value: Any, where: str) -> dict[str, Any]:
    numeric = _copy_keys(
        value,
        ("status", "value", "unit", "reason", "derivation"),
        where,
    )
    if "source_field_refs" in _mapping(value, where):
        numeric["source_field_refs"] = [
            _copy_keys(ref, ("snapshot", "source_ordinal", "field"), f"{where}.source_field_refs[]")
            for ref in _sequence(
                _mapping(value, where)["source_field_refs"], f"{where}.source_field_refs"
            )
        ]
    return numeric


def _project_beneficial_position(value: Any, where: str) -> dict[str, Any]:
    position = _mapping(value, where)
    result = _copy_keys(
        position,
        ("source_ordinal", "source_name", "source_cik", "identity_basis", "person_types"),
        where,
    )
    if "group_membership" in position:
        result["group_membership"] = _copy_keys(
            position["group_membership"], ("is_member",), f"{where}.group_membership"
        )
    for name in (
        "beneficially_owned_shares",
        "ownership_percentage",
        "voting_power",
        "dispositive_power",
    ):
        if name in position:
            result[name] = _project_beneficial_numeric(position[name], f"{where}.{name}")
    if "source_field_refs" in position:
        result["source_field_refs"] = [
            _copy_keys(ref, ("snapshot", "source_ordinal", "field"), f"{where}.source_field_refs[]")
            for ref in _sequence(position["source_field_refs"], f"{where}.source_field_refs")
        ]
    if "comparison" in position:
        comparison = _mapping(position["comparison"], f"{where}.comparison")
        result["comparison"] = _copy_keys(comparison, ("status", "reason"), f"{where}.comparison")
        for name in ("shares_delta", "percentage_delta"):
            if name in comparison:
                result["comparison"][name] = _project_beneficial_numeric(
                    comparison[name], f"{where}.comparison.{name}"
                )
    return result


def _project_beneficial_snapshot(value: Any, where: str) -> dict[str, Any]:
    snapshot = _mapping(value, where)
    result = _copy_keys(
        snapshot,
        (
            "accession_number",
            "form",
            "schedule_family",
            "filed_at",
            "accepted_at",
            "document_url",
            "is_amendment",
            "amendment_number",
        ),
        where,
    )
    if "issuer" in snapshot:
        result["issuer"] = _copy_keys(snapshot["issuer"], ("cik", "name"), f"{where}.issuer")
    if "ownership_class" in snapshot:
        result["ownership_class"] = _copy_keys(
            snapshot["ownership_class"],
            ("cusip", "title", "identity_basis"),
            f"{where}.ownership_class",
        )
    if "reporting_positions" in snapshot:
        result["reporting_positions"] = [
            _project_beneficial_position(position, f"{where}.reporting_positions[]")
            for position in _sequence(
                snapshot["reporting_positions"], f"{where}.reporting_positions"
            )
        ]
    if "group_evidence" in snapshot:
        group = snapshot["group_evidence"]
        if group is None:
            result["group_evidence"] = None
        else:
            group_map = _mapping(group, f"{where}.group_evidence")
            result["group_evidence"] = _copy_keys(
                group_map, ("name", "is_explicit"), f"{where}.group_evidence"
            )
            if "aggregate_shares" in group_map:
                result["group_evidence"]["aggregate_shares"] = _project_beneficial_numeric(
                    group_map["aggregate_shares"], f"{where}.group_evidence.aggregate_shares"
                )
    return result


def _project_filing(payload: Mapping[str, Any]) -> dict[str, Any]:
    result = _copy_keys(
        payload,
        (
            "type",
            "filing_subtype",
            "form",
            "company",
            "accession_number",
            "filed_at",
            "report_period",
            "accepted_at",
            "document_url",
            "is_amendment",
            "amendment_number",
        ),
        "item.payload",
    )
    if "company_identity" in payload:
        result["company_identity"] = _copy_keys(
            payload["company_identity"], ("cik", "name", "tickers"), "item.payload.company_identity"
        )
    if "value_normalization" in payload:
        result["value_normalization"] = _copy_keys(
            payload["value_normalization"],
            ("source_unit", "formula_id"),
            "item.payload.value_normalization",
        )
    subtype = payload.get("filing_subtype")
    if subtype == "form13f":
        if "comparison" in payload:
            comparison = _copy_keys(
                payload["comparison"],
                (
                    "status",
                    "previous_accession_number",
                    "previous_report_period",
                    "previous_accepted_at",
                    "previous_filed_at",
                    "previous_source_url",
                    "previous_value_normalization",
                    "reason",
                ),
                "item.payload.comparison",
            )
            if (
                "previous_value_normalization" in comparison
                and comparison["previous_value_normalization"] is not None
            ):
                comparison["previous_value_normalization"] = _copy_keys(
                    comparison["previous_value_normalization"],
                    ("source_unit", "formula_id"),
                    "item.payload.comparison.previous_value_normalization",
                )
            result["comparison"] = comparison
        if "holdings" in payload:
            result["holdings"] = []
            for holding in _sequence(payload["holdings"], "item.payload.holdings"):
                row = _mapping(holding, "item.payload.holdings[]")
                projected = _copy_keys(row, ("change_type",), "item.payload.holdings[]")
                projected["security"] = _copy_keys(
                    _copy_required(row, "security", "item.payload.holdings[]"),
                    ("cusip", "figi", "issuer_name", "title_of_class", "put_call", "amount_type"),
                    "item.payload.holdings[].security",
                )
                for side in ("current", "previous", "delta"):
                    if side in row:
                        side_value = row[side]
                        if side_value is None:
                            projected[side] = None
                        else:
                            side_map = _mapping(side_value, f"item.payload.holdings[].{side}")
                            projected[side] = {}
                            for name in ("reported_amount", "reported_value_usd_thousands"):
                                if name in side_map:
                                    projected[side][name] = _numeric(
                                        side_map[name], f"item.payload.holdings[].{side}.{name}"
                                    )
                result["holdings"].append(projected)
    elif subtype == "form4":
        if "issuer" in payload:
            result["issuer"] = _copy_keys(
                payload["issuer"], ("cik", "name", "trading_symbol"), "item.payload.issuer"
            )
        if "reporting_owners" in payload:
            result["reporting_owners"] = []
            for owner in _sequence(payload["reporting_owners"], "item.payload.reporting_owners"):
                owner_map = _mapping(owner, "item.payload.reporting_owners[]")
                result["reporting_owners"].append(
                    {
                        **_copy_keys(owner_map, ("cik", "name"), "item.payload.reporting_owners[]"),
                        "relationship": _copy_keys(
                            _copy_required(
                                owner_map, "relationship", "item.payload.reporting_owners[]"
                            ),
                            (
                                "director",
                                "officer",
                                "ten_percent_owner",
                                "other",
                                "officer_title",
                                "other_text",
                            ),
                            "item.payload.reporting_owners[].relationship",
                        ),
                    }
                )
        for table in ("non_derivative_entries", "derivative_entries"):
            if table in payload:
                result[table] = [
                    _form4_entry(entry, f"item.payload.{table}[]")
                    for entry in _sequence(payload[table], f"item.payload.{table}")
                ]
        for key in ("footnotes", "remarks", "date_of_original_submission"):
            if key in payload:
                if key == "footnotes":
                    result[key] = [
                        _copy_keys(note, ("id", "text"), "item.payload.footnotes[]")
                        for note in _sequence(payload[key], "item.payload.footnotes")
                    ]
                else:
                    result[key] = copy.deepcopy(payload[key])
    elif subtype == "beneficial_ownership":
        if "schedule_family" in payload:
            result["schedule_family"] = copy.deepcopy(payload["schedule_family"])
        for side in ("current", "previous"):
            snapshot_key = f"{side}_snapshot"
            if snapshot_key in payload:
                result[snapshot_key] = (
                    None
                    if payload[snapshot_key] is None
                    else _project_beneficial_snapshot(
                        payload[snapshot_key], f"item.payload.{snapshot_key}"
                    )
                )
        if "comparison" in payload:
            ownership_comparison = _mapping(payload["comparison"], "item.payload.comparison")
            result["comparison"] = _copy_keys(
                ownership_comparison, ("status", "reason"), "item.payload.comparison"
            )
            if "previous" in ownership_comparison:
                previous = ownership_comparison["previous"]
                result["comparison"]["previous"] = (
                    None
                    if previous is None
                    else _copy_keys(
                        previous,
                        ("accession_number", "accepted_at", "document_url"),
                        "item.payload.comparison.previous",
                    )
                )
    elif subtype is not None:
        raise DigestPreparationError(f"unsupported filing subtype: {subtype!r}")
    return result


@dataclass(frozen=True, slots=True)
class DigestFeedBinding:
    schema_version: int
    run_id: str
    content_digest: str
    window: Mapping[str, Any]
    evidence_cutoff_at: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "window", _freeze(self.window))

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "content_digest": self.content_digest,
            "window": _thaw(self.window),
            "evidence_cutoff_at": self.evidence_cutoff_at,
        }


@dataclass(frozen=True, slots=True)
class DigestEventTime:
    kind: str
    value: str

    def __post_init__(self) -> None:
        if self.kind not in {kind for kind, _ in MEMBERSHIP_AUTHORITY.values()}:
            raise DigestPreparationError(f"unsupported event-time kind: {self.kind!r}")

    def to_mapping(self) -> dict[str, Any]:
        return {"kind": self.kind, "value": self.value}


@dataclass(frozen=True, slots=True)
class DigestUnitTrace:
    feed_item_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "feed_item_ids", tuple(self.feed_item_ids))
        if not self.feed_item_ids:
            raise DigestPreparationError("a DigestUpdateUnit requires at least one Feed item trace")

    def to_mapping(self) -> dict[str, Any]:
        return {"feed_item_ids": list(self.feed_item_ids)}


@dataclass(frozen=True, slots=True)
class DigestUpdateUnit:
    unit_id: str
    domain: str
    unit_type: str
    provider_id: str
    source: Mapping[str, Any]
    event_time: DigestEventTime
    evidence: Mapping[str, Any]
    trace: DigestUnitTrace
    source_lineage: tuple[Mapping[str, Any], ...] | None = None

    def __post_init__(self) -> None:
        if self.domain not in DOMAIN_ORDER:
            raise DigestPreparationError(f"unsupported unit domain: {self.domain!r}")
        if self.unit_type != DOMAIN_UNIT_TYPE[self.domain]:
            raise DigestPreparationError(
                f"unit type {self.unit_type!r} does not belong to domain {self.domain!r}"
            )
        if self.unit_type not in UNIT_TYPES:
            raise DigestPreparationError(f"unsupported unit type: {self.unit_type!r}")
        object.__setattr__(self, "source", _freeze(self.source))
        object.__setattr__(self, "evidence", _freeze(self.evidence))
        if self.source_lineage is not None:
            object.__setattr__(
                self, "source_lineage", tuple(_freeze(row) for row in self.source_lineage)
            )

    def to_mapping(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "unit_id": self.unit_id,
            "domain": self.domain,
            "unit_type": self.unit_type,
            "provider_id": self.provider_id,
            "source": _thaw(self.source),
            "event_time": self.event_time.to_mapping(),
            "evidence": _thaw(self.evidence),
            "trace": self.trace.to_mapping(),
        }
        if self.source_lineage is not None:
            result["source_lineage"] = _thaw(self.source_lineage)
        return result


@dataclass(frozen=True, slots=True)
class DigestDomainStatus:
    domain: str
    scope: str
    state: str
    data_as_of: str | None = None

    def __post_init__(self) -> None:
        if self.scope not in SCOPE_ORDER:
            raise DigestPreparationError(f"unsupported status scope: {self.scope!r}")
        if SCOPE_DOMAIN[self.scope] != self.domain:
            raise DigestPreparationError(
                f"status scope {self.scope!r} does not belong to domain {self.domain!r}"
            )
        if self.state not in DOMAIN_STATES:
            raise DigestPreparationError(f"unsupported domain state: {self.state!r}")

    def to_mapping(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "domain": self.domain,
            "scope": self.scope,
            "state": self.state,
        }
        if self.data_as_of is not None:
            result["data_as_of"] = self.data_as_of
        return result


@dataclass(frozen=True, slots=True)
class DigestLimitation:
    code: str
    provider_id: str | None = None
    affected_coverage_groups: tuple[str, ...] = ()
    uncovered_start: str | None = None
    uncovered_end: str | None = None

    def __post_init__(self) -> None:
        if self.code not in LIMITATION_CODES:
            raise DigestPreparationError(f"unsupported limitation code: {self.code!r}")
        object.__setattr__(
            self, "affected_coverage_groups", tuple(sorted(self.affected_coverage_groups))
        )
        if self.code == "provider_unavailable":
            if self.provider_id is None:
                raise DigestPreparationError("provider_unavailable requires a Provider ID")
            if self.uncovered_start is not None or self.uncovered_end is not None:
                raise DigestPreparationError("provider_unavailable carries no coverage bounds")
        else:
            if self.uncovered_start is None or self.uncovered_end is None:
                raise DigestPreparationError("coverage_gap requires its Feed bounds")
            if self.provider_id is not None or self.affected_coverage_groups:
                raise DigestPreparationError("coverage_gap carries no Provider identity")

    def to_mapping(self) -> dict[str, Any]:
        if self.code == "provider_unavailable":
            return {
                "code": self.code,
                "provider_id": self.provider_id,
                "affected_coverage_groups": list(self.affected_coverage_groups),
            }
        return {
            "code": self.code,
            "uncovered_start": self.uncovered_start,
            "uncovered_end": self.uncovered_end,
        }


@dataclass(frozen=True, slots=True)
class DigestContent:
    updates: tuple[DigestUpdateUnit, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "updates", tuple(self.updates))

    def to_mapping(self) -> dict[str, Any]:
        return {"updates": [unit.to_mapping() for unit in self.updates]}


@dataclass(frozen=True, slots=True)
class DigestStatus:
    domains: tuple[DigestDomainStatus, ...]
    limitations: tuple[DigestLimitation, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "domains", tuple(self.domains))
        object.__setattr__(self, "limitations", tuple(self.limitations))

    def to_mapping(self) -> dict[str, Any]:
        return {
            "domains": [domain.to_mapping() for domain in self.domains],
            "limitations": [limitation.to_mapping() for limitation in self.limitations],
        }


@dataclass(frozen=True, slots=True)
class DigestContext:
    context_version: int
    feed: DigestFeedBinding
    content: DigestContent
    status: DigestStatus

    def __post_init__(self) -> None:
        if self.context_version != CONTEXT_VERSION:
            raise DigestPreparationError(
                f"unsupported DigestContext version: {self.context_version!r}"
            )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "context_version": self.context_version,
            "feed": self.feed.to_mapping(),
            "content": self.content.to_mapping(),
            "status": self.status.to_mapping(),
        }

    def canonical_bytes(self) -> bytes:
        return canonical_bytes(self.to_mapping())

    def to_dict(self) -> dict[str, Any]:
        return self.to_mapping()


def _membership_state(
    item: Mapping[str, Any], domain: str, window_start: datetime, window_end: datetime
) -> tuple[str, str | None]:
    """Classify one item as current, explicitly old, or unproven-current."""
    _, path = MEMBERSHIP_AUTHORITY[domain]
    value = _nested(item, path)
    where = f"items[].{'.'.join(path)}"
    if not isinstance(value, str) or not value:
        return "unproven", None
    try:
        moment = _timestamp(value, where)
    except DigestPreparationError:
        return "unproven", None
    if moment < window_start:
        return "old", value
    if moment >= window_end:
        return "unproven", value
    return "current", value


def _build_unit(
    item: Mapping[str, Any], payload: Mapping[str, Any], domain: str, event_value: str
) -> DigestUpdateUnit:
    kind, _ = MEMBERSHIP_AUTHORITY[domain]
    evidence: dict[str, Any] = {"payload": _project_payload(payload, domain)}
    if domain in {"news", "macro_release", "policy"} and "semantic_context" in item:
        evidence["semantic_context"] = _project_semantic_context(item["semantic_context"], domain)
    item_id = _copy_required(item, "id", "items[]")
    return DigestUpdateUnit(
        unit_id=f"{DOMAIN_UNIT_TYPE[domain]}:{item_id}",
        domain=domain,
        unit_type=DOMAIN_UNIT_TYPE[domain],
        provider_id=_copy_required(item, "provider_id", "items[]"),
        source=_project_source(item),
        source_lineage=_project_lineage(item),
        event_time=DigestEventTime(kind=kind, value=event_value),
        evidence=evidence,
        trace=DigestUnitTrace(feed_item_ids=(item_id,)),
    )


def _project_payload(payload: Mapping[str, Any], domain: str) -> dict[str, Any]:
    if domain == "filing":
        return _project_filing(payload)
    return _project_semantic_payload(payload, domain)


def _filing_scope(payload: Mapping[str, Any]) -> str | None:
    subtype = payload.get("filing_subtype")
    if subtype is None:
        return None
    if subtype not in FILING_SUBTYPES:
        raise DigestPreparationError(f"unsupported filing subtype: {subtype!r}")
    return subtype


def _aggregate_states(states: Sequence[str]) -> str:
    if "current" in states:
        return "current_updates_available"
    if "unproven" in states:
        return "current_membership_unproven"
    if "old" in states:
        return "no_current_update"
    return "domain_empty"


def _common_data_as_of(items: Sequence[Mapping[str, Any]]) -> str | None:
    values = set()
    for item in items:
        payload = item.get("payload")
        value = payload.get("as_of") if isinstance(payload, Mapping) else None
        values.add(value)
    if len(values) != 1:
        return None
    (value,) = values
    return value if isinstance(value, str) and value else None


def _positioning_status(
    items: Sequence[Mapping[str, Any]], outcomes: Mapping[str, Mapping[str, Any]]
) -> DigestDomainStatus:
    if not items:
        return DigestDomainStatus(domain="positioning", scope="cftc", state="domain_empty")
    provider_ids = sorted({_copy_required(item, "provider_id", "items[]") for item in items})
    if len(provider_ids) != 1:
        raise DigestPreparationError("positioning slice spans multiple Providers")
    outcome = outcomes.get(provider_ids[0])
    if outcome is None:
        raise DigestPreparationError(
            f"positioning Provider {provider_ids[0]!r} has no validated outcome"
        )
    freshness = _mapping(
        _copy_required(outcome, "freshness", "provider_outcomes[]"),
        "provider_outcomes[].freshness",
    )
    if freshness.get("carried_forward_from_run_id") is not None:
        state = "carried_reference_state"
    elif freshness.get("status") == "stale":
        state = "stale_reference_state"
    else:
        state = "current_membership_unproven"
    return DigestDomainStatus(
        domain="positioning",
        scope="cftc",
        state=state,
        data_as_of=_common_data_as_of(items),
    )


def _limitations(
    outcomes: Sequence[Mapping[str, Any]], pipeline: Mapping[str, Any]
) -> list[DigestLimitation]:
    limitations: list[DigestLimitation] = []
    blocked = sorted(
        (outcome for outcome in outcomes if outcome.get("availability") == "blocked"),
        key=lambda outcome: str(outcome.get("provider_id")),
    )
    for outcome in blocked:
        limitations.append(
            DigestLimitation(
                code="provider_unavailable",
                provider_id=_copy_required(outcome, "provider_id", "provider_outcomes[]"),
                affected_coverage_groups=tuple(
                    _sequence(
                        _copy_required(outcome, "affected_coverage_groups", "provider_outcomes[]"),
                        "provider_outcomes[].affected_coverage_groups",
                    )
                ),
            )
        )
    gap = pipeline.get("coverage_gap")
    if gap is not None:
        limitations.append(
            DigestLimitation(
                code="coverage_gap",
                uncovered_start=_copy_required(
                    gap, "uncovered_start", "Feed.pipeline.coverage_gap"
                ),
                uncovered_end=_copy_required(gap, "uncovered_end", "Feed.pipeline.coverage_gap"),
            )
        )
    return limitations


def _project_validated_feed(
    feed: Mapping[str, Any], *, context_version: int = CONTEXT_VERSION
) -> DigestContext:
    """Prepare one already validated current Feed without re-validating it."""
    try:
        if context_version != CONTEXT_VERSION:
            raise DigestPreparationError(f"unsupported DigestContext version: {context_version!r}")
        feed_map = _mapping(feed, "Feed")
        window = _mapping(_copy_required(feed_map, "window", "Feed"), "Feed.window")
        window_start = _timestamp(window.get("start"), "Feed.window.start")
        window_end = _timestamp(window.get("end"), "Feed.window.end")
        pipeline = _mapping(_copy_required(feed_map, "pipeline", "Feed"), "Feed.pipeline")
        if pipeline.get("status") not in {"healthy", "degraded"}:
            raise DigestPreparationError(
                f"Feed.pipeline.status: not a consumable Feed: {pipeline.get('status')!r}"
            )
        outcomes = _sequence(
            _copy_required(feed_map, "provider_outcomes", "Feed"), "Feed.provider_outcomes"
        )
        outcome_by_provider = {
            _copy_required(outcome, "provider_id", "provider_outcomes[]"): _mapping(
                outcome, "provider_outcomes[]"
            )
            for outcome in outcomes
        }
        items = _sequence(_copy_required(feed_map, "items", "Feed"), "Feed.items")
        binding = DigestFeedBinding(
            schema_version=feed_map["schema_version"],
            run_id=feed_map["run_id"],
            content_digest=feed_map["content_digest"],
            window=window,
            evidence_cutoff_at=feed_map["evidence_cutoff_at"],
        )
        updates: list[DigestUpdateUnit] = []
        scope_states: dict[str, list[str]] = {scope: [] for scope in SCOPE_ORDER}
        positioning_items: list[Mapping[str, Any]] = []
        for item in items:
            item_map = _mapping(item, "items[]")
            payload = _mapping(_copy_required(item_map, "payload", "items[]"), "items[].payload")
            domain = payload.get("type")
            if domain not in DOMAIN_ORDER:
                raise DigestPreparationError(f"items[].payload.type: unsupported domain {domain!r}")
            if domain == "positioning":
                positioning_items.append(item_map)
                continue
            state, event_value = _membership_state(item_map, domain, window_start, window_end)
            scope = _filing_scope(payload) if domain == "filing" else domain
            if scope is not None:
                scope_states[scope].append(state)
            if state == "current":
                assert isinstance(event_value, str)
                updates.append(_build_unit(item_map, payload, domain, event_value))
        domains = tuple(
            _positioning_status(positioning_items, outcome_by_provider)
            if scope == "cftc"
            else DigestDomainStatus(
                domain=SCOPE_DOMAIN[scope],
                scope=scope,
                state=_aggregate_states(scope_states[scope]),
            )
            for scope in SCOPE_ORDER
        )
        return DigestContext(
            context_version=context_version,
            feed=binding,
            content=DigestContent(updates=tuple(updates)),
            status=DigestStatus(
                domains=domains, limitations=tuple(_limitations(outcomes, pipeline))
            ),
        )
    except DigestPreparationError:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise DigestPreparationError(f"cannot prepare validated Feed: {exc}") from exc


def prepare_digest_context(*, context_version: int = CONTEXT_VERSION) -> DigestContext:
    """Consume exactly one canonical current Feed and prepare its context."""
    if context_version != CONTEXT_VERSION:
        raise DigestPreparationError(f"unsupported DigestContext version: {context_version!r}")
    return _project_validated_feed(consume_published_feed(), context_version=context_version)


def _build_parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        prog="prepare-feed",
        description="Prepare canonical DigestContext input from the current published Feed.",
    )


def main(argv: list[str] | None = None) -> int:
    _build_parser().parse_args(argv)
    try:
        context = prepare_digest_context()
    except (FeedRemoteError, DigestPreparationError) as exc:
        print(f"prepare-feed: {exc}", file=sys.stderr)
        return 1
    sys.stdout.buffer.write(context.canonical_bytes())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "CONTEXT_VERSION",
    "DOMAIN_ORDER",
    "DOMAIN_STATES",
    "DOMAIN_UNIT_TYPE",
    "ELIGIBLE_PATHS",
    "LIMITATION_CODES",
    "MEMBERSHIP_AUTHORITY",
    "SCOPE_DOMAIN",
    "SCOPE_ORDER",
    "UNIT_TYPES",
    "DigestContent",
    "DigestContext",
    "DigestDomainStatus",
    "DigestEventTime",
    "DigestFeedBinding",
    "DigestLimitation",
    "DigestPreparationError",
    "DigestStatus",
    "DigestUnitTrace",
    "DigestUpdateUnit",
    "eligible_paths",
    "main",
    "prepare_digest_context",
]
