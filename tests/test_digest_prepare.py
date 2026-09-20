"""Deterministic Feed-to-DigestContext v2 preparation regressions."""

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from dataclasses import FrozenInstanceError, fields, is_dataclass
from datetime import timedelta
from pathlib import Path

import pytest

from follow_the_money.canonical import canonical_bytes
from follow_the_money.digest import (
    DOMAIN_STATES,
    ELIGIBLE_PATHS,
    LIMITATION_CODES,
    SCOPE_ORDER,
    DigestContext,
    DigestPreparationError,
    _project_validated_feed,
    eligible_paths,
    prepare_digest_context,
)
from tests.test_feed_boundary import _macro_item, _policy_item, _sec_v2_item
from tests.test_feed_bundle import T0, _feed, _news

CURRENT = T0 - timedelta(hours=1)
EXPECTED_SCOPES = (
    ("news", "news"),
    ("macro_release", "macro_release"),
    ("policy", "policy"),
    ("positioning", "cftc"),
    ("filing", "form13f"),
    ("filing", "form4"),
    ("filing", "beneficial_ownership"),
)


def _current_news(item_id: str = "news-current") -> dict:
    return _news(item_id, at=CURRENT)


def _current_macro() -> dict:
    item = _macro_item()
    item["payload"]["released_at"] = _ts(CURRENT)
    item["source"]["published_at"] = _ts(CURRENT)
    item["source"]["knowledge_available_at"] = _ts(CURRENT)
    item["semantic_context"]["event"]["occurred_at"] = _ts(CURRENT)
    return item


def _current_policy() -> dict:
    item = _policy_item()
    item["payload"]["announced_at"] = _ts(CURRENT)
    item["source"]["published_at"] = _ts(CURRENT)
    item["source"]["knowledge_available_at"] = _ts(CURRENT)
    return item


def _form13f_item(item_id: str = "sec-v2-item", accepted_at: str | None = None) -> dict:
    item = _sec_v2_item()
    item["id"] = item_id
    item["source"]["id"] = item_id
    item["payload"]["filing_subtype"] = "form13f"
    if accepted_at is not None:
        item["payload"]["accepted_at"] = accepted_at
        item["payload"]["filed_at"] = accepted_at
    return item


def _ts(value) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _status_by_scope(context: DigestContext) -> dict[str, dict]:
    return {row["scope"]: row for row in context.to_mapping()["status"]["domains"]}


def test_digest_context_v2_is_frozen_slotted_and_explicitly_versioned():
    context = _project_validated_feed(_feed([_current_news()]))

    assert is_dataclass(context)
    assert context.context_version == 2
    assert hasattr(context, "__slots__")
    assert all(field.name != "__dict__" for field in fields(context))
    with pytest.raises(FrozenInstanceError):
        context.context_version = 1  # type: ignore[misc]
    with pytest.raises(TypeError):
        context.feed.window["start"] = "changed"  # type: ignore[index]
    unit = context.content.updates[0]
    with pytest.raises(TypeError):
        unit.evidence["payload"]["title"] = "changed"  # type: ignore[index]


def test_digest_context_v2_exposes_only_feed_content_and_status():
    feed = _feed([_current_news()])
    context = _project_validated_feed(feed)
    value = context.to_mapping()

    assert set(value) == {"context_version", "feed", "content", "status"}
    assert set(value["content"]) == {"updates"}
    assert set(value["status"]) == {"domains", "limitations"}
    assert value["feed"] == {
        "schema_version": feed["schema_version"],
        "run_id": feed["run_id"],
        "content_digest": feed["content_digest"],
        "window": feed["window"],
        "evidence_cutoff_at": feed["evidence_cutoff_at"],
    }
    for row in value["status"]["domains"]:
        assert set(row) <= {"domain", "scope", "state", "data_as_of"}
        assert "items" not in row
        assert "total" not in row
    for unit in value["content"]["updates"]:
        assert set(unit) <= {
            "unit_id",
            "domain",
            "unit_type",
            "provider_id",
            "source",
            "source_lineage",
            "event_time",
            "evidence",
            "trace",
        }
        assert "payload" not in unit

    serialized = canonical_bytes(value).decode("utf-8")
    for removed in (
        "reference_state",
        "unresolved_items",
        "providers",
        "warnings",
        "freshness",
        "attempted",
        "rejected",
        "availability",
        "upstream_http_status",
    ):
        assert removed not in serialized


def test_unsupported_context_version_fails_closed():
    feed = _feed([_current_news()])

    with pytest.raises(DigestPreparationError, match="unsupported DigestContext version"):
        _project_validated_feed(feed, context_version=1)
    with pytest.raises(DigestPreparationError, match="unsupported DigestContext version"):
        _project_validated_feed(feed, context_version=3)
    with pytest.raises(DigestPreparationError, match="unsupported DigestContext version"):
        prepare_digest_context(context_version=1)


def test_non_consumable_pipeline_status_fails_closed():
    feed = _feed([_current_news()])
    feed["pipeline"] = {"status": "failure", "warnings": ["deficient coverage groups: x"]}

    with pytest.raises(DigestPreparationError, match="not a consumable Feed"):
        _project_validated_feed(feed)


def test_repeated_preparation_has_byte_identical_canonical_json():
    feed = _feed([_current_news(), _current_macro(), _current_policy()])

    first = _project_validated_feed(feed)
    second = _project_validated_feed(deepcopy(feed))

    assert canonical_bytes(first.to_mapping()) == canonical_bytes(second.to_mapping())


def test_preparation_is_invariant_to_pre_normalization_input_perturbation():
    feed = _feed([_current_news("news-1"), _current_macro(), _current_policy()])
    perturbed = json.loads(json.dumps(feed, sort_keys=True))
    assert list(perturbed) != list(feed)

    baseline = _project_validated_feed(feed)
    other = _project_validated_feed(perturbed)

    assert baseline.to_mapping() == other.to_mapping()
    assert [unit.unit_id for unit in baseline.content.updates] == [
        "news_publication:news-1",
        "macro_release:macro-item",
        "policy_document:policy-item",
    ]
    assert baseline.status.to_mapping() == other.status.to_mapping()
    assert baseline.canonical_bytes() == other.canonical_bytes()


def test_supported_entry_consumes_once(monkeypatch):
    from follow_the_money import digest

    feed = _feed([_current_news()])
    calls = 0

    def consume():
        nonlocal calls
        calls += 1
        return feed

    monkeypatch.setattr(digest, "consume_published_feed", consume)
    assert prepare_digest_context().feed.run_id == feed["run_id"]
    assert calls == 1


def test_preparation_failure_has_preparation_specific_error_without_partial_context():
    feed = _feed([_current_news()])
    del feed["items"][0]["payload"]

    with pytest.raises(DigestPreparationError):
        _project_validated_feed(feed)


def test_units_carry_closed_provenance_evidence_and_trace():
    news = _current_news("news-1")
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
    macro = _current_macro()
    macro["payload"]["actual"]["unknown_reason"] = "missing"
    policy = _current_policy()
    policy["payload"]["unlisted_field"] = "must stay out"

    context = _project_validated_feed(_feed([news, macro, policy]))
    updates = context.to_mapping()["content"]["updates"]

    assert [unit["unit_id"] for unit in updates] == [
        "news_publication:news-1",
        "macro_release:macro-item",
        "policy_document:policy-item",
    ]
    assert [unit["domain"] for unit in updates] == ["news", "macro_release", "policy"]
    assert [unit["unit_type"] for unit in updates] == [
        "news_publication",
        "macro_release",
        "policy_document",
    ]
    assert [unit["event_time"] for unit in updates] == [
        {"kind": "published_at", "value": _ts(CURRENT)},
        {"kind": "released_at", "value": _ts(CURRENT)},
        {"kind": "announced_at", "value": _ts(CURRENT)},
    ]
    assert [unit["trace"] for unit in updates] == [
        {"feed_item_ids": ["news-1"]},
        {"feed_item_ids": ["macro-item"]},
        {"feed_item_ids": ["policy-item"]},
    ]
    assert updates[0]["source_lineage"] == [
        {
            "id": "duplicate-1",
            "provider_id": "sse",
            "source_id": "source-1",
            "original_publisher": None,
            "syndication_origin": None,
        }
    ]
    assert updates[1]["evidence"]["payload"]["actual"] == {
        "value": None,
        "unit": "percent",
        "unknown_reason": "missing",
    }
    assert "semantic_context" in updates[0]["evidence"]
    serialized = canonical_bytes(context.to_mapping()).decode("utf-8")
    assert "raw_metadata" not in serialized
    assert "ignored" not in serialized
    assert "unlisted_field" not in serialized


def test_eligible_path_inventory_is_explicit_and_domain_specific():
    assert set(ELIGIBLE_PATHS) == {"news", "macro_release", "policy", "positioning", "filing"}
    assert "payload.raw_metadata" not in ELIGIBLE_PATHS["news"]
    assert eligible_paths("positioning") == ("payload.as_of",)
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
    assert "payload.as_of" in set(eligible_paths("positioning"))
    assert "payload.derivative_entries[].transaction_coding.transaction_code" in set(
        eligible_paths("filing")
    )


def test_status_domains_use_fixed_closed_scope_and_state_order():
    context = _project_validated_feed(_feed([_current_news()]))
    domains = context.to_mapping()["status"]["domains"]

    assert [(row["domain"], row["scope"]) for row in domains] == list(EXPECTED_SCOPES)
    assert [row["scope"] for row in domains] == list(SCOPE_ORDER)
    assert {row["state"] for row in domains} <= DOMAIN_STATES
    assert {row["state"] for row in domains} == {"current_updates_available", "domain_empty"}
    assert domains[0] == {
        "domain": "news",
        "scope": "news",
        "state": "current_updates_available",
    }
    assert "data_as_of" not in domains[3]


def test_domain_empty_no_current_and_unproven_current_stay_distinct():
    old_news = _current_news("news-old")
    old_news["source"]["published_at"] = _ts(T0 - timedelta(days=30))
    unproven_news = _current_news("news-unproven")
    del unproven_news["source"]["published_at"]
    after_window = _current_news("news-after")
    after_window["source"]["published_at"] = _ts(T0 + timedelta(hours=1))
    old_macro = _current_macro()
    old_macro["payload"]["released_at"] = _ts(T0 - timedelta(days=30))

    contexts = {
        "empty": _feed([]),
        "old_only": _feed([old_news]),
        "unproven_only": _feed([unproven_news]),
        "after_window_only": _feed([after_window]),
        "mixed": _feed([old_news, unproven_news]),
    }
    states = {
        name: _status_by_scope(_project_validated_feed(feed)) for name, feed in contexts.items()
    }

    assert states["empty"]["news"]["state"] == "domain_empty"
    assert states["old_only"]["news"]["state"] == "no_current_update"
    assert states["unproven_only"]["news"]["state"] == "current_membership_unproven"
    assert states["after_window_only"]["news"]["state"] == "current_membership_unproven"
    assert states["mixed"]["news"]["state"] == "current_membership_unproven"
    assert states["mixed"]["macro_release"]["state"] == "domain_empty"

    # An old item still leaves every other scope empty, and no old evidence leaks.
    old_only = _project_validated_feed(contexts["old_only"])
    assert old_only.to_mapping()["content"] == {"updates": []}
    assert old_only.to_mapping()["status"]["limitations"] == []
    assert _status_by_scope(_project_validated_feed(_feed([old_macro])))["macro_release"] == {
        "domain": "macro_release",
        "scope": "macro_release",
        "state": "no_current_update",
    }


def test_provider_unavailable_is_a_closed_limitation_not_a_provider_audit_row():
    feed = _feed([_current_news("news-1")])
    feed["pipeline"] = {
        "status": "degraded",
        "warnings": ["blocked Provider bls"],
        "coverage_gap": None,
    }
    blocked = next(row for row in feed["provider_outcomes"] if row["provider_id"] == "bls")
    blocked.update(
        {
            "state": "failed",
            "succeeded": False,
            "failed": True,
            "accepted": 0,
            "availability": "blocked",
            "availability_reason": "HTTP 403",
            "upstream_http_status": 403,
            "freshness": {
                "cadence": "event_driven",
                "status": "not_evaluated",
                "origin_contract_hash": None,
                "carried_forward_from_run_id": None,
            },
        }
    )
    blocked["freshness"]["future_schema_field"] = "must stay out"

    context = _project_validated_feed(feed)
    value = context.to_mapping()

    assert value["status"]["limitations"] == [
        {
            "code": "provider_unavailable",
            "provider_id": "bls",
            "affected_coverage_groups": ["us_official_macro_policy"],
        }
    ]
    assert value["status"]["domains"][0]["state"] == "current_updates_available"
    serialized = canonical_bytes(value).decode("utf-8")
    for excluded in (
        "warnings",
        "blocked Provider bls",
        "HTTP 403",
        "upstream_http_status",
        "availability_reason",
        "not_evaluated",
        "future_schema_field",
        "total",
    ):
        assert excluded not in serialized


def test_structured_coverage_gap_keeps_exact_feed_bounds():
    feed = _feed([_current_news("news-1")])
    feed["pipeline"] = {
        "status": "healthy",
        "warnings": ["checkpoint gap exceeded maximum lookback"],
        "coverage_gap": {
            "uncovered_start": "2026-08-10T00:00:00.000Z",
            "uncovered_end": "2026-08-10T01:00:00.000Z",
        },
    }

    value = _project_validated_feed(feed).to_mapping()

    assert value["status"]["limitations"] == [
        {
            "code": "coverage_gap",
            "uncovered_start": "2026-08-10T00:00:00.000Z",
            "uncovered_end": "2026-08-10T01:00:00.000Z",
        }
    ]
    assert LIMITATION_CODES == ("provider_unavailable", "coverage_gap")


def test_multiple_provider_limitations_use_fixed_code_then_provider_order():
    feed = _feed([_current_news("news-1")])
    feed["pipeline"] = {
        "status": "degraded",
        "warnings": [],
        "coverage_gap": {
            "uncovered_start": "2026-08-10T00:00:00.000Z",
            "uncovered_end": "2026-08-10T01:00:00.000Z",
        },
    }
    for provider_id in ("szse", "bls"):
        outcome = next(
            row for row in feed["provider_outcomes"] if row["provider_id"] == provider_id
        )
        outcome.update(
            {
                "state": "failed",
                "succeeded": False,
                "failed": True,
                "accepted": 0,
                "availability": "blocked",
                "availability_reason": "HTTP 401",
                "upstream_http_status": 401,
            }
        )

    limitations = _project_validated_feed(feed).to_mapping()["status"]["limitations"]

    assert limitations == [
        {
            "code": "provider_unavailable",
            "provider_id": "bls",
            "affected_coverage_groups": ["us_official_macro_policy"],
        },
        {
            "code": "provider_unavailable",
            "provider_id": "szse",
            "affected_coverage_groups": ["china_exchange_evidence"],
        },
        {
            "code": "coverage_gap",
            "uncovered_start": "2026-08-10T00:00:00.000Z",
            "uncovered_end": "2026-08-10T01:00:00.000Z",
        },
    ]


def test_form13f_status_never_exposes_holdings():
    feed = _feed([_form13f_item()])

    value = _project_validated_feed(feed).to_mapping()

    assert value["content"] == {"updates": []}
    assert _status_by_scope(_project_validated_feed(feed))["form13f"] == {
        "domain": "filing",
        "scope": "form13f",
        "state": "no_current_update",
    }
    serialized = canonical_bytes(value).decode("utf-8")
    assert "holdings" not in serialized
    assert "037833100" not in serialized


def _with_source_content(item: dict, *, text: str = "Official statement.", truncated: bool = False):
    item = deepcopy(item)
    item["payload"]["source_content"] = {
        "text": text,
        "format": "plain_text",
        "extraction_method": "official_html_text_v1",
        "truncated": truncated,
        "document_sha256": hashlib.sha256(item["id"].encode()).hexdigest(),
    }
    return item


def test_current_units_expose_only_reader_relevant_source_content():
    news = _with_source_content(_current_news("news-enriched"), text="Bounded official text.")
    feed = _feed([news], target_v2=True)
    context = _project_validated_feed(feed)

    unit = next(
        unit for unit in context.content.updates if unit.unit_id.startswith("news_publication")
    )
    evidence = unit.evidence["payload"]["source_content"]
    assert evidence == {
        "text": "Bounded official text.",
        "format": "plain_text",
        "truncated": False,
    }
    assert "extraction_method" not in evidence
    assert "document_sha256" not in evidence
    assert "extraction_method" not in canonical_bytes(context.to_mapping()).decode()
    assert "document_sha256" not in canonical_bytes(context.to_mapping()).decode()


def test_current_macro_and_policy_units_expose_truncation_state():
    macro = _with_source_content(_current_macro(), text="Release text.", truncated=True)
    policy = _with_source_content(_current_policy(), text="Statement text.")
    macro["provider_id"] = "nbs"
    feed = _feed([macro, policy], target_v2=True)
    context = _project_validated_feed(feed)

    units = {unit.unit_type: unit for unit in context.content.updates}
    assert units["macro_release"].evidence["payload"]["source_content"] == {
        "text": "Release text.",
        "format": "plain_text",
        "truncated": True,
    }
    assert units["policy_document"].evidence["payload"]["source_content"] == {
        "text": "Statement text.",
        "format": "plain_text",
        "truncated": False,
    }


def test_items_without_source_content_keep_the_omission():
    context = _project_validated_feed(_feed([_current_news()]))
    unit = context.content.updates[0]
    assert "source_content" not in unit.evidence["payload"]


def test_preparation_is_repeatable_and_performs_no_document_access(monkeypatch):
    feed = _feed([_with_source_content(_current_news("news-enriched"))], target_v2=True)
    first = _project_validated_feed(deepcopy(feed))
    second = _project_validated_feed(deepcopy(feed))
    assert canonical_bytes(first.to_mapping()) == canonical_bytes(second.to_mapping())

    # Preparation may not open a URL or read a document.
    import urllib.request

    def _forbidden(*_args, **_kwargs):  # pragma: no cover - must never run
        raise AssertionError("Digest preparation must not perform network access")

    monkeypatch.setattr(urllib.request, "urlopen", _forbidden)
    assert canonical_bytes(_project_validated_feed(feed).to_mapping()) == canonical_bytes(
        first.to_mapping()
    )
