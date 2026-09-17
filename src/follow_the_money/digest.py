"""Deterministic, non-persisted preparation for Host-Agent digest input."""

from __future__ import annotations

import argparse
import copy
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from .canonical import canonical_bytes
from .config.model import SUPPORTED_FEED_PAYLOAD_TYPES
from .feed.remote import FeedRemoteError, consume_published_feed

CONTEXT_VERSION = 1
DOMAIN_ORDER = SUPPORTED_FEED_PAYLOAD_TYPES


class DigestPreparationError(ValueError):
    """A validated Feed could not be projected into the v1 DigestContext."""


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


def _unique_paths(paths: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(paths))


FRESHNESS_FIELDS = (
    "cadence",
    "status",
    "origin_contract_hash",
    "carried_forward_from_run_id",
)


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
POSITIONING_PATHS = (
    "payload.type",
    "payload.instrument_id",
    "payload.as_of",
    "payload.position.value",
    "payload.position.unit",
    "payload.position.unknown_reason",
    "payload.market_identity.cftc_contract_market_code",
    "payload.market_identity.contract_market_name",
    *(
        f"payload.current_metrics.{name}.{field}"
        for name in (
            "net_noncommercial",
            "noncommercial_long",
            "noncommercial_short",
            "noncommercial_spreading",
            "open_interest",
        )
        for field in ("value", "unit", "unknown_reason")
    ),
    *(
        f"payload.previous_metrics.{name}.{field}"
        for name in (
            "net_noncommercial",
            "noncommercial_long",
            "noncommercial_short",
            "noncommercial_spreading",
            "open_interest",
        )
        for field in ("value", "unit", "unknown_reason")
    ),
    *(
        f"payload.delta_metrics.{name}.{field}"
        for name in (
            "net_noncommercial",
            "noncommercial_long",
            "noncommercial_short",
            "noncommercial_spreading",
            "open_interest",
        )
        for field in ("value", "unit", "unknown_reason")
    ),
    "payload.comparison.status",
    "payload.comparison.previous_as_of",
    "payload.comparison.reason",
    "payload.derivations.net_noncommercial.formula_id",
)
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

ELIGIBLE_PATHS: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "news": _unique_paths(
            COMMON_PATHS
            + (
                "payload.type",
                "payload.title",
                "payload.snippet",
                "payload.occurred_at",
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
            )
            + SEMANTIC_PATHS
            + SEMANTIC_POLICY_PATHS
        ),
        "positioning": _unique_paths(COMMON_PATHS + POSITIONING_PATHS),
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


def _project_lineage(item: Mapping[str, Any]) -> list[dict[str, Any]] | None:
    if "source_lineage" not in item:
        return None
    return [
        _copy_keys(
            entry,
            ("id", "provider_id", "source_id", "original_publisher", "syndication_origin"),
            "item.source_lineage[]",
        )
        for entry in _sequence(item["source_lineage"], "item.source_lineage")
    ]


def _project_freshness(value: Any) -> dict[str, Any]:
    freshness = _mapping(value, "provider_outcomes[].freshness")
    return {
        field: _copy_required(freshness, field, "provider_outcomes[].freshness")
        for field in FRESHNESS_FIELDS
    }


def _numeric(value: Any, where: str) -> dict[str, Any]:
    return _copy_keys(value, ("value", "unit", "unknown_reason"), where)


def _metrics(value: Any, where: str) -> dict[str, Any] | None:
    if value is None:
        return None
    metrics = _mapping(value, where)
    return {
        name: _numeric(metrics[name], f"{where}.{name}")
        for name in (
            "net_noncommercial",
            "noncommercial_long",
            "noncommercial_short",
            "noncommercial_spreading",
            "open_interest",
        )
        if name in metrics
    }


def _project_semantic_payload(payload: Mapping[str, Any], domain: str) -> dict[str, Any]:
    if domain == "news":
        return _copy_keys(payload, ("type", "title", "snippet", "occurred_at"), "item.payload")
    if domain == "macro_release":
        result = _copy_keys(
            payload,
            ("type", "series_id", "released_at", "observation_period"),
            "item.payload",
        )
        for name in ("actual", "consensus", "previous"):
            if name in payload:
                result[name] = _numeric(payload[name], f"item.payload.{name}")
        return result
    if domain == "policy":
        return _copy_keys(
            payload, ("type", "title", "announced_at", "effective_at"), "item.payload"
        )
    raise DigestPreparationError(f"unsupported semantic payload domain: {domain!r}")


def _project_positioning(payload: Mapping[str, Any]) -> dict[str, Any]:
    result = _copy_keys(payload, ("type", "instrument_id", "as_of"), "item.payload")
    if "position" in payload:
        result["position"] = _numeric(payload["position"], "item.payload.position")
    if "market_identity" in payload:
        result["market_identity"] = _copy_keys(
            payload["market_identity"],
            ("cftc_contract_market_code", "contract_market_name"),
            "item.payload.market_identity",
        )
    for name in ("current_metrics", "previous_metrics", "delta_metrics"):
        if name in payload:
            result[name] = _metrics(payload[name], f"item.payload.{name}")
    if "comparison" in payload:
        result["comparison"] = _copy_keys(
            payload["comparison"],
            ("status", "previous_as_of", "reason"),
            "item.payload.comparison",
        )
    if "derivations" in payload:
        derivations = _mapping(payload["derivations"], "item.payload.derivations")
        if "net_noncommercial" in derivations:
            result["derivations"] = {
                "net_noncommercial": _copy_keys(
                    derivations["net_noncommercial"],
                    ("formula_id",),
                    "item.payload.derivations.net_noncommercial",
                )
            }
    return result


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
        result["derivative_terms"] = (
            None
            if terms is None
            else _copy_keys(
                terms,
                ("exercise_date", "expiration_date", "conversion_or_exercise_price"),
                f"{where}.derivative_terms",
            )
        )
        if isinstance(terms, Mapping) and terms.get("conversion_or_exercise_price") is not None:
            result["derivative_terms"]["conversion_or_exercise_price"] = _form4_numeric(
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


def _project_item(item: Any) -> DigestItem:
    item_map = _mapping(item, "items[]")
    payload = _mapping(_copy_required(item_map, "payload", "items[]"), "items[].payload")
    domain = payload.get("type")
    if domain not in DOMAIN_ORDER:
        raise DigestPreparationError(f"items[].payload.type: unsupported domain {domain!r}")
    projected = {
        "id": _copy_required(item_map, "id", "items[]"),
        "provider_id": _copy_required(item_map, "provider_id", "items[]"),
        "source": _project_source(item_map),
        "payload": (
            _project_filing(payload)
            if domain == "filing"
            else _project_positioning(payload)
            if domain == "positioning"
            else _project_semantic_payload(payload, domain)
        ),
    }
    lineage = _project_lineage(item_map)
    if lineage is not None:
        projected["source_lineage"] = lineage
    if domain in {"news", "macro_release", "policy"} and "semantic_context" in item_map:
        projected["semantic_context"] = _project_semantic_context(
            item_map["semantic_context"], domain
        )
    return DigestItem(
        id=projected["id"],
        provider_id=projected["provider_id"],
        source=projected["source"],
        payload=projected["payload"],
        source_lineage=projected.get("source_lineage"),
        semantic_context=projected.get("semantic_context"),
    )


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
class DigestStatus:
    status: str
    warnings: tuple[str, ...]
    coverage_gap: Mapping[str, Any] | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "warnings", tuple(self.warnings))
        object.__setattr__(
            self, "coverage_gap", None if self.coverage_gap is None else _freeze(self.coverage_gap)
        )

    @property
    def pipeline_status(self) -> str:
        return self.status

    def to_mapping(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "warnings": list(self.warnings),
            "coverage_gap": _thaw(self.coverage_gap),
        }


@dataclass(frozen=True, slots=True)
class DigestProvider:
    provider_id: str
    state: str
    attempted: int
    fetched: int
    succeeded: bool
    empty: bool
    partial: bool
    failed: bool
    skipped: bool
    accepted: int
    rejected: int
    availability: str
    availability_reason: str | None
    upstream_http_status: int | None
    affected_coverage_groups: tuple[str, ...]
    freshness: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "affected_coverage_groups", tuple(self.affected_coverage_groups))
        object.__setattr__(self, "freshness", _freeze(self.freshness))

    def to_mapping(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "state": self.state,
            "attempted": self.attempted,
            "fetched": self.fetched,
            "succeeded": self.succeeded,
            "empty": self.empty,
            "partial": self.partial,
            "failed": self.failed,
            "skipped": self.skipped,
            "accepted": self.accepted,
            "rejected": self.rejected,
            "availability": self.availability,
            "availability_reason": self.availability_reason,
            "upstream_http_status": self.upstream_http_status,
            "affected_coverage_groups": list(self.affected_coverage_groups),
            "freshness": _thaw(self.freshness),
        }


@dataclass(frozen=True, slots=True)
class DigestItem:
    id: str
    provider_id: str
    source: Mapping[str, Any]
    payload: Mapping[str, Any]
    source_lineage: tuple[Mapping[str, Any], ...] | None = None
    semantic_context: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "source", _freeze(self.source))
        object.__setattr__(self, "payload", _freeze(self.payload))
        if self.source_lineage is not None:
            object.__setattr__(
                self, "source_lineage", tuple(_freeze(row) for row in self.source_lineage)
            )
        if self.semantic_context is not None:
            object.__setattr__(self, "semantic_context", _freeze(self.semantic_context))

    def to_mapping(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "id": self.id,
            "provider_id": self.provider_id,
            "source": _thaw(self.source),
            "payload": _thaw(self.payload),
        }
        if self.source_lineage is not None:
            result["source_lineage"] = _thaw(self.source_lineage)
        if self.semantic_context is not None:
            result["semantic_context"] = _thaw(self.semantic_context)
        return result


@dataclass(frozen=True, slots=True)
class DigestDomain:
    domain: str
    items: tuple[DigestItem, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "items", tuple(self.items))

    @property
    def total(self) -> int:
        return len(self.items)

    def to_mapping(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "total": self.total,
            "items": [item.to_mapping() for item in self.items],
        }


@dataclass(frozen=True, slots=True)
class DigestContext:
    context_version: int
    feed: DigestFeedBinding
    status: DigestStatus
    providers: tuple[DigestProvider, ...]
    domains: tuple[DigestDomain, ...]

    def __post_init__(self) -> None:
        if self.context_version != CONTEXT_VERSION:
            raise DigestPreparationError(
                f"unsupported DigestContext version: {self.context_version!r}"
            )
        object.__setattr__(self, "providers", tuple(self.providers))
        object.__setattr__(self, "domains", tuple(self.domains))

    def to_mapping(self) -> dict[str, Any]:
        return {
            "context_version": self.context_version,
            "feed": self.feed.to_mapping(),
            "status": self.status.to_mapping(),
            "providers": [provider.to_mapping() for provider in self.providers],
            "domains": [domain.to_mapping() for domain in self.domains],
        }

    def canonical_bytes(self) -> bytes:
        return canonical_bytes(self.to_mapping())

    def to_dict(self) -> dict[str, Any]:
        return self.to_mapping()


def _project_provider(value: Any) -> DigestProvider:
    outcome = _mapping(value, "provider_outcomes[]")
    required = (
        "provider_id",
        "state",
        "attempted",
        "fetched",
        "succeeded",
        "empty",
        "partial",
        "failed",
        "skipped",
        "accepted",
        "rejected",
        "availability",
        "availability_reason",
        "upstream_http_status",
        "affected_coverage_groups",
        "freshness",
    )
    missing = [key for key in required if key not in outcome]
    if missing:
        raise DigestPreparationError(f"provider_outcomes[]: missing validated fields {missing!r}")
    return DigestProvider(
        provider_id=outcome["provider_id"],
        state=outcome["state"],
        attempted=outcome["attempted"],
        fetched=outcome["fetched"],
        succeeded=outcome["succeeded"],
        empty=outcome["empty"],
        partial=outcome["partial"],
        failed=outcome["failed"],
        skipped=outcome["skipped"],
        accepted=outcome["accepted"],
        rejected=outcome["rejected"],
        availability=outcome["availability"],
        availability_reason=outcome["availability_reason"],
        upstream_http_status=outcome["upstream_http_status"],
        affected_coverage_groups=tuple(outcome["affected_coverage_groups"]),
        freshness=_project_freshness(outcome["freshness"]),
    )


def _project_validated_feed(
    feed: Mapping[str, Any], *, context_version: int = CONTEXT_VERSION
) -> DigestContext:
    """Project one already validated current Feed without re-validating it."""
    try:
        if context_version != CONTEXT_VERSION:
            raise DigestPreparationError(f"unsupported DigestContext version: {context_version!r}")
        feed_map = _mapping(feed, "Feed")
        window = _mapping(_copy_required(feed_map, "window", "Feed"), "Feed.window")
        pipeline = _mapping(_copy_required(feed_map, "pipeline", "Feed"), "Feed.pipeline")
        warnings = _sequence(
            _copy_required(pipeline, "warnings", "Feed.pipeline"), "Feed.pipeline.warnings"
        )
        outcomes = _sequence(
            _copy_required(feed_map, "provider_outcomes", "Feed"), "Feed.provider_outcomes"
        )
        items = _sequence(_copy_required(feed_map, "items", "Feed"), "Feed.items")
        binding = DigestFeedBinding(
            schema_version=feed_map["schema_version"],
            run_id=feed_map["run_id"],
            content_digest=feed_map["content_digest"],
            window=window,
            evidence_cutoff_at=feed_map["evidence_cutoff_at"],
        )
        coverage_gap = pipeline.get("coverage_gap")
        status = DigestStatus(
            status=pipeline["status"],
            warnings=tuple(warnings),
            coverage_gap=coverage_gap,
        )
        providers = tuple(_project_provider(outcome) for outcome in outcomes)
        projected_by_domain: dict[str, list[DigestItem]] = {domain: [] for domain in DOMAIN_ORDER}
        for item in items:
            projected = _project_item(item)
            projected_by_domain[projected.payload["type"]].append(projected)
        domains = tuple(
            DigestDomain(domain=domain, items=tuple(projected_by_domain[domain]))
            for domain in DOMAIN_ORDER
        )
        if sum(domain.total for domain in domains) != len(items):
            raise DigestPreparationError(
                "projected domain totals do not account for every Feed item"
            )
        return DigestContext(
            context_version=context_version,
            feed=binding,
            status=status,
            providers=providers,
            domains=domains,
        )
    except DigestPreparationError:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise DigestPreparationError(f"cannot project validated Feed: {exc}") from exc


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
    for warning in context.status.warnings:
        print(f"warning: {warning}", file=sys.stderr)
    sys.stdout.buffer.write(context.canonical_bytes())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "CONTEXT_VERSION",
    "DOMAIN_ORDER",
    "ELIGIBLE_PATHS",
    "DigestContext",
    "DigestDomain",
    "DigestFeedBinding",
    "DigestItem",
    "DigestPreparationError",
    "DigestProvider",
    "DigestStatus",
    "eligible_paths",
    "main",
    "prepare_digest_context",
]
