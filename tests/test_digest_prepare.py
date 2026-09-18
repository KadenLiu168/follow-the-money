"""Deterministic Feed-to-DigestContext preparation regressions."""

from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path

import pytest

from follow_the_money.canonical import canonical_bytes
from follow_the_money.digest import (
    ELIGIBLE_PATHS,
    DigestPreparationError,
    _project_validated_feed,
    eligible_paths,
    prepare_digest_context,
)
from tests.test_feed_boundary import _cftc_v2_item, _macro_item, _policy_item, _sec_v2_item
from tests.test_feed_bundle import _feed, _news


def test_digest_context_is_frozen_and_slotted_with_explicit_version():
    context = _project_validated_feed(_feed([_news()]))

    assert is_dataclass(context)
    assert context.context_version == 1
    assert hasattr(context, "__slots__")
    assert all(field.name != "__dict__" for field in fields(context))
    with pytest.raises(FrozenInstanceError):
        context.context_version = 2  # type: ignore[misc]
    with pytest.raises(TypeError):
        context.feed.window["start"] = "changed"  # type: ignore[index]


def test_digest_context_retains_exact_feed_binding_and_fixed_domain_order():
    feed = _feed([_news()])
    context = _project_validated_feed(feed)
    value = context.to_mapping()

    assert value["feed"] == {
        "schema_version": feed["schema_version"],
        "run_id": feed["run_id"],
        "content_digest": feed["content_digest"],
        "window": feed["window"],
        "evidence_cutoff_at": feed["evidence_cutoff_at"],
    }
    assert [domain["domain"] for domain in value["domains"]] == [
        "news",
        "macro_release",
        "policy",
        "positioning",
        "filing",
    ]
    assert [domain["total"] for domain in value["domains"]] == [1, 0, 0, 0, 0]


def test_repeated_preparation_has_byte_identical_canonical_json():
    feed = _feed([_news()])

    first = _project_validated_feed(feed)
    second = _project_validated_feed(deepcopy(feed))

    assert canonical_bytes(first.to_mapping()) == canonical_bytes(second.to_mapping())


def test_supported_entry_consumes_once(monkeypatch):
    from follow_the_money import digest

    feed = _feed([_news()])
    calls = 0

    def consume():
        nonlocal calls
        calls += 1
        return feed

    monkeypatch.setattr(digest, "consume_published_feed", consume)
    assert prepare_digest_context().feed.run_id == feed["run_id"]
    assert calls == 1


def test_projection_failure_has_preparation_specific_error_without_partial_context():
    feed = _feed([_news()])
    del feed["items"][0]["payload"]

    with pytest.raises(DigestPreparationError):
        _project_validated_feed(feed)


def _form4_item() -> dict:
    item = deepcopy(_sec_v2_item())
    item["payload"] = {
        "type": "filing",
        "filing_subtype": "form4",
        "form": "4",
        "company": "0000000001",
        "accession_number": "0000000001-23-000002",
        "filed_at": "2023-01-04T00:00:00.000Z",
        "accepted_at": "2023-01-04T12:00:00.000Z",
        "document_url": "https://www.sec.gov/Archives/edgar/data/1/form4.xml",
        "issuer": {"cik": "0000000001", "name": "Issuer", "trading_symbol": "EXM"},
        "reporting_owners": [
            {
                "cik": "0000000002",
                "name": "Owner",
                "relationship": {
                    "director": True,
                    "officer": False,
                    "ten_percent_owner": False,
                    "other": False,
                    "officer_title": None,
                    "other_text": None,
                },
            }
        ],
        "non_derivative_entries": [
            {
                "entry_kind": "transaction",
                "source_ordinal": 0,
                "entry_id": "transaction-0",
                "security_title": "Common Stock",
                "transaction_date": "2023-01-03",
                "deemed_execution_date": None,
                "transaction_coding": {
                    "transaction_form_type": "4",
                    "transaction_code": "A",
                    "equity_swap_involved": False,
                },
                "timeliness": None,
                "transaction_amount": {
                    "branch": "shares",
                    "shares": {"value": "10", "unit": "shares", "footnote_ids": []},
                    "total_value": None,
                },
                "price_per_share": None,
                "acquisition_disposition_code": "A",
                "post_transaction_amount": {
                    "branch": "shares",
                    "shares": {"value": "10", "unit": "shares", "footnote_ids": []},
                    "value": None,
                },
                "ownership_nature": {"direct_or_indirect": "direct", "nature_of_ownership": None},
                "derivative_terms": {
                    "exercise_date": None,
                    "expiration_date": None,
                    "conversion_or_exercise_price": None,
                },
                "underlying_security": None,
                "field_references": [],
            }
        ],
        "derivative_entries": [],
        "footnotes": [],
        "remarks": None,
        "date_of_original_submission": None,
        "is_amendment": False,
        "amendment_number": None,
    }
    return item


def _beneficial_ownership_item() -> dict:
    item = deepcopy(_sec_v2_item())
    numeric = {
        "status": "unavailable",
        "value": None,
        "unit": "shares",
        "reason": "missing_operand",
        "source_field_refs": [
            {
                "snapshot": "current",
                "source_ordinal": 0,
                "field": "reporting_person[0].beneficially_owned_shares",
                "ignored": "not eligible",
            }
        ],
    }
    position = {
        "source_ordinal": 0,
        "source_name": "Owner",
        "source_cik": None,
        "identity_basis": "source_name",
        "person_types": ["individual"],
        "group_membership": {"is_member": False},
        "beneficially_owned_shares": numeric,
        "ownership_percentage": {**numeric, "unit": "percent"},
        "source_field_refs": [],
        "comparison": {
            "status": "unavailable",
            "reason": "missing_operand",
            "shares_delta": numeric,
            "percentage_delta": {**numeric, "unit": "percentage_points"},
        },
    }
    snapshot = {
        "accession_number": "0000000001-23-000003",
        "form": "SCHEDULE 13D",
        "schedule_family": "13D",
        "filed_at": "2023-01-05T00:00:00.000Z",
        "accepted_at": "2023-01-05T12:00:00.000Z",
        "document_url": "https://www.sec.gov/Archives/edgar/data/1/schedule.xml",
        "issuer": {"cik": "0000000001", "name": "Issuer"},
        "ownership_class": {"cusip": None, "title": "Common", "identity_basis": "class_title"},
        "reporting_positions": [position],
        "group_evidence": None,
        "is_amendment": False,
        "amendment_number": None,
    }
    item["payload"] = {
        "type": "filing",
        "filing_subtype": "beneficial_ownership",
        "form": "SCHEDULE 13D",
        "company": "0000000001",
        "accession_number": snapshot["accession_number"],
        "filed_at": snapshot["filed_at"],
        "accepted_at": snapshot["accepted_at"],
        "document_url": snapshot["document_url"],
        "schedule_family": "13D",
        "current_snapshot": snapshot,
        "previous_snapshot": None,
        "comparison": {"status": "initial_filing", "reason": None, "previous": None},
        "is_amendment": False,
        "amendment_number": None,
    }
    return item


def test_domain_projection_preserves_order_qualifiers_and_excludes_unlisted_fields():
    news = _news("news-1")
    news["source_lineage"] = [
        {
            "id": "duplicate-1",
            "provider_id": "sse",
            "source_id": "source-1",
            "original_publisher": None,
            "syndication_origin": None,
            "ignored": "not eligible",
        }
    ]
    macro = _macro_item()
    macro["payload"]["actual"]["unknown_reason"] = "missing"
    positioning = _cftc_v2_item()
    filing13f = _sec_v2_item()
    filing13f["payload"]["filing_subtype"] = "form13f"
    items = [
        news,
        macro,
        _policy_item(),
        positioning,
        filing13f,
        _form4_item(),
        _beneficial_ownership_item(),
    ]

    context = _project_validated_feed(_feed(items))
    mapping = context.to_mapping()
    domains = {domain["domain"]: domain for domain in mapping["domains"]}

    assert [item["id"] for item in domains["news"]["items"]] == ["news-1"]
    assert domains["news"]["items"][0]["source_lineage"] == [
        {
            "id": "duplicate-1",
            "provider_id": "sse",
            "source_id": "source-1",
            "original_publisher": None,
            "syndication_origin": None,
        }
    ]
    assert "raw_metadata" not in str(mapping)
    assert "ignored" not in str(mapping)
    assert domains["macro_release"]["items"][0]["payload"]["actual"] == {
        "value": None,
        "unit": "percent",
        "unknown_reason": "missing",
    }
    assert domains["positioning"]["items"][0]["payload"]["delta_metrics"] is None
    assert domains["filing"]["total"] == 3
    assert domains["filing"]["items"][1]["payload"]["filing_subtype"] == "form4"
    assert domains["filing"]["items"][2]["payload"]["filing_subtype"] == "beneficial_ownership"
    assert (
        domains["filing"]["items"][2]["payload"]["current_snapshot"]["reporting_positions"][0][
            "ownership_percentage"
        ]["reason"]
        == "missing_operand"
    )
    assert domains["filing"]["items"][2]["payload"]["current_snapshot"]["reporting_positions"][0][
        "beneficially_owned_shares"
    ]["source_field_refs"] == [
        {
            "snapshot": "current",
            "source_ordinal": 0,
            "field": "reporting_person[0].beneficially_owned_shares",
        }
    ]


def test_eligible_path_inventory_is_explicit_and_domain_specific():
    assert set(ELIGIBLE_PATHS) == {"news", "macro_release", "policy", "positioning", "filing"}
    assert "payload.raw_metadata" not in ELIGIBLE_PATHS["news"]
    assert "payload.comparison.previous_as_of" in eligible_paths("positioning")
    assert "payload.holdings[].change_type" in eligible_paths("filing", "form13f")
    assert "payload.current_snapshot.reporting_positions[].ownership_percentage.derivation" in (
        eligible_paths("filing", "beneficial_ownership")
    )


def test_eligible_path_inventories_are_unique():
    inventories = [
        *ELIGIBLE_PATHS.values(),
        *(
            eligible_paths("filing", subtype)
            for subtype in ("form13f", "form4", "beneficial_ownership")
        ),
    ]

    for paths in inventories:
        assert len(paths) == len(set(paths))


def test_implementation_inventory_covers_the_reference_contract_paths():
    domains_root = Path(__file__).parents[1] / "references" / "digest" / "domains"
    for domain in ("news", "macro_release", "policy", "positioning", "filing"):
        reference = (domains_root / f"{domain}.md").read_text(encoding="utf-8")
        documented = {
            match.group(1).removesuffix(" (when present)")
            for match in re.finditer(r"^- `([^`]+)`", reference, flags=re.MULTILINE)
        }
        declared = set(eligible_paths(domain))
        assert documented == declared

    assert "payload.raw_metadata" not in set(eligible_paths("filing"))
    assert "payload.comparison.previous_as_of" in set(eligible_paths("positioning"))
    assert "payload.derivative_entries[].transaction_coding.transaction_code" in set(
        eligible_paths("filing")
    )


def test_status_provider_limitations_and_zero_inclusive_domains_are_preserved():
    feed = _feed([_news()])
    feed["pipeline"] = {
        "status": "degraded",
        "warnings": ["blocked Provider cftc"],
        "coverage_gap": {
            "uncovered_start": "2026-08-10T00:00:00.000Z",
            "uncovered_end": "2026-08-10T01:00:00.000Z",
        },
    }
    blocked = next(row for row in feed["provider_outcomes"] if row["provider_id"] == "cftc")
    blocked.update(
        {
            "state": "failed",
            "succeeded": False,
            "failed": True,
            "availability": "blocked",
            "availability_reason": "HTTP 403",
            "upstream_http_status": 403,
            "freshness": {
                "cadence": "weekly",
                "status": "not_evaluated",
                "origin_contract_hash": None,
                "carried_forward_from_run_id": None,
            },
        }
    )
    blocked["freshness"]["future_schema_field"] = "must stay out"
    context = _project_validated_feed(feed).to_mapping()

    assert context["status"] == {
        "status": "degraded",
        "warnings": ["blocked Provider cftc"],
        "coverage_gap": feed["pipeline"]["coverage_gap"],
    }
    cftc = next(row for row in context["providers"] if row["provider_id"] == "cftc")
    assert cftc["availability"] == "blocked"
    assert cftc["freshness"]["status"] == "not_evaluated"
    assert "future_schema_field" not in cftc["freshness"]
    assert [row["total"] for row in context["domains"]] == [1, 0, 0, 0, 0]
