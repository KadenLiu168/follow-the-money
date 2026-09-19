"""Deterministic v2 current-membership and reader-unit regressions."""

from __future__ import annotations

from copy import deepcopy
from datetime import timedelta

from follow_the_money.canonical import canonical_bytes
from follow_the_money.digest import _project_validated_feed
from tests.test_digest_prepare import (
    CURRENT,
    _current_macro,
    _current_news,
    _current_policy,
    _form13f_item,
    _status_by_scope,
    _ts,
)
from tests.test_feed_boundary import _cftc_v2_item, _sec_v2_item
from tests.test_feed_bundle import T0, _feed

WINDOW_START = T0 - timedelta(hours=72)
OLD = T0 - timedelta(days=30)
AFTER_WINDOW = T0 + timedelta(hours=1)


def _updates(feed: dict) -> list[dict]:
    return _project_validated_feed(feed).to_mapping()["content"]["updates"]


def _form4_item(accepted_at: str | None = None) -> dict:
    item = deepcopy(_sec_v2_item())
    item["id"] = "form4-item"
    item["source"]["id"] = "form4-item"
    item["payload"] = {
        "type": "filing",
        "filing_subtype": "form4",
        "form": "4",
        "company": "0000000001",
        "accession_number": "0000000001-23-000002",
        "filed_at": accepted_at or _ts(CURRENT),
        "accepted_at": accepted_at or _ts(CURRENT),
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
        "non_derivative_entries": [_form4_entry(ordinal) for ordinal in range(2)],
        "derivative_entries": [],
        "footnotes": [],
        "remarks": None,
        "date_of_original_submission": None,
        "is_amendment": False,
        "amendment_number": None,
    }
    return item


def _form4_entry(ordinal: int) -> dict:
    amount = {
        "branch": "shares",
        "shares": {"value": "10", "unit": "shares", "footnote_ids": []},
        "total_value": None,
    }
    return {
        "entry_kind": "transaction",
        "source_ordinal": ordinal,
        "entry_id": f"transaction-{ordinal}",
        "security_title": "Common Stock",
        "transaction_date": "2023-01-03",
        "deemed_execution_date": None,
        "transaction_coding": {
            "transaction_form_type": "4",
            "transaction_code": "A",
            "equity_swap_involved": False,
        },
        "timeliness": None,
        "transaction_amount": deepcopy(amount),
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


def _ownership_snapshot(accession_number: str, accepted_at: str) -> dict:
    numeric = {
        "status": "unavailable",
        "value": None,
        "unit": "shares",
        "reason": "missing_operand",
        "source_field_refs": [],
    }
    return {
        "accession_number": accession_number,
        "form": "SCHEDULE 13D",
        "schedule_family": "13D",
        "filed_at": accepted_at,
        "accepted_at": accepted_at,
        "document_url": "https://www.sec.gov/Archives/edgar/data/1/schedule.xml",
        "issuer": {"cik": "0000000001", "name": "Issuer"},
        "ownership_class": {"cusip": None, "title": "Common", "identity_basis": "class_title"},
        "reporting_positions": [
            {
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
        ],
        "group_evidence": None,
        "is_amendment": False,
        "amendment_number": None,
    }


def _beneficial_ownership_item(*, accepted_at: str = _ts(CURRENT), previous: bool = True) -> dict:
    item = deepcopy(_sec_v2_item())
    item["id"] = "beneficial-item"
    item["source"]["id"] = "beneficial-item"
    current = _ownership_snapshot("0000000001-23-000003", accepted_at)
    item["payload"] = {
        "type": "filing",
        "filing_subtype": "beneficial_ownership",
        "form": "SCHEDULE 13D",
        "company": "0000000001",
        "accession_number": current["accession_number"],
        "filed_at": accepted_at,
        "accepted_at": accepted_at,
        "document_url": current["document_url"],
        "schedule_family": "13D",
        "current_snapshot": current,
        "previous_snapshot": (
            _ownership_snapshot("0000000001-22-000002", _ts(OLD)) if previous else None
        ),
        "comparison": {
            "status": "comparable" if previous else "initial_filing",
            "reason": None,
            "previous": (
                {
                    "accession_number": "0000000001-22-000002",
                    "accepted_at": _ts(OLD),
                    "document_url": "https://www.sec.gov/Archives/edgar/data/1/schedule-previous.xml",
                }
                if previous
                else None
            ),
        },
        "is_amendment": False,
        "amendment_number": None,
    }
    return item


def _positioning_item(item_id: str = "cftc-v2-item", as_of: str | None = None) -> dict:
    item = _cftc_v2_item()
    item["id"] = item_id
    item["source"]["id"] = item_id
    if as_of is not None:
        item["payload"]["as_of"] = as_of
    return item


def _with_positioning_freshness(feed: dict, **freshness: object) -> dict:
    outcome = next(row for row in feed["provider_outcomes"] if row["provider_id"] == "cftc")
    outcome["freshness"] = {
        "cadence": "weekly",
        "status": "fresh",
        "origin_contract_hash": None,
        "carried_forward_from_run_id": None,
        **freshness,
    }
    return feed


def test_news_membership_uses_only_source_published_at():
    item = _current_news("news-1")

    updates = _updates(_feed([item]))

    assert len(updates) == 1
    assert updates[0]["unit_type"] == "news_publication"
    assert updates[0]["event_time"] == {"kind": "published_at", "value": _ts(CURRENT)}
    assert updates[0]["trace"]["feed_item_ids"] == ["news-1"]
    assert updates[0]["evidence"]["payload"]["title"] == "title"

    # An in-window occurrence or knowledge time never substitutes for publication.
    substituted = _current_news("news-2")
    substituted["source"]["published_at"] = _ts(OLD)
    assert _updates(_feed([substituted])) == []
    assert _status_by_scope(_project_validated_feed(_feed([substituted])))["news"]["state"] == (
        "no_current_update"
    )

    # A missing authority is unproven rather than old, and is never inferred.
    missing = _current_news("news-3")
    del missing["source"]["published_at"]
    feed = _feed([missing])
    assert _updates(feed) == []
    assert _status_by_scope(_project_validated_feed(feed))["news"]["state"] == (
        "current_membership_unproven"
    )


def test_window_is_half_open_for_every_closed_authority():
    at_start = _current_news("news-start")
    at_start["source"]["published_at"] = _ts(WINDOW_START)
    at_end = _current_news("news-end")
    at_end["source"]["published_at"] = _ts(T0)

    assert [unit["trace"]["feed_item_ids"] for unit in _updates(_feed([at_start]))] == [
        ["news-start"]
    ]
    assert _updates(_feed([at_end])) == []
    assert _status_by_scope(_project_validated_feed(_feed([at_end])))["news"]["state"] == (
        "current_membership_unproven"
    )


def test_macro_membership_uses_only_payload_released_at():
    item = _current_macro()
    item["payload"]["actual"] = {"value": "1.5", "unit": "percent", "unknown_reason": None}
    item["semantic_context"]["numeric_facts"][0] = {
        "metric": "observation",
        "role": "actual",
        "value": "1.5",
        "unit": "percent",
        "unknown_reason": None,
    }

    updates = _updates(_feed([item]))

    assert len(updates) == 1
    assert updates[0]["unit_type"] == "macro_release"
    assert updates[0]["event_time"] == {"kind": "released_at", "value": _ts(CURRENT)}
    assert updates[0]["evidence"]["payload"]["actual"]["value"] == "1.5"
    assert updates[0]["evidence"]["payload"]["observation_period"] is None
    assert updates[0]["evidence"]["semantic_context"]["extension"]["indicator"]["id"] == (
        "cn_industrial_production_yoy"
    )

    stale = _current_macro()
    stale["payload"]["released_at"] = _ts(OLD)
    feed = _feed([stale])
    assert _updates(feed) == []
    assert _status_by_scope(_project_validated_feed(feed))["macro_release"]["state"] == (
        "no_current_update"
    )


def test_policy_membership_uses_announced_at_and_keeps_effective_at_as_evidence():
    item = _current_policy()
    item["payload"]["effective_at"] = _ts(AFTER_WINDOW)
    item["payload"]["title"] = "Federal Reserve issues FOMC statement"

    updates = _updates(_feed([item]))

    assert len(updates) == 1
    assert updates[0]["unit_type"] == "policy_document"
    assert updates[0]["event_time"] == {"kind": "announced_at", "value": _ts(CURRENT)}
    assert updates[0]["evidence"]["payload"]["effective_at"] == _ts(AFTER_WINDOW)

    # A later effective time is never the membership authority.
    future_only = _current_policy()
    future_only["payload"]["announced_at"] = None
    future_only["payload"]["effective_at"] = _ts(CURRENT)
    feed = _feed([future_only])
    assert _updates(feed) == []
    assert _status_by_scope(_project_validated_feed(feed))["policy"]["state"] == (
        "current_membership_unproven"
    )


def test_sec_membership_uses_accepted_at_and_never_falls_back_to_filed_at():
    legacy_insufficient = _form13f_item("sec-legacy")
    del legacy_insufficient["payload"]["accepted_at"]
    legacy_insufficient["payload"]["filed_at"] = _ts(CURRENT)
    feed = _feed([legacy_insufficient])

    assert _updates(feed) == []
    assert _status_by_scope(_project_validated_feed(feed))["form13f"]["state"] == (
        "current_membership_unproven"
    )


def test_old_form13f_yields_status_only_without_holdings():
    feed = _feed([_form13f_item("sec-old")])

    context = _project_validated_feed(feed)
    value = context.to_mapping()

    assert value["content"] == {"updates": []}
    assert _status_by_scope(context)["form13f"] == {
        "domain": "filing",
        "scope": "form13f",
        "state": "no_current_update",
    }
    assert _status_by_scope(context)["form4"]["state"] == "domain_empty"
    serialized = canonical_bytes(value).decode("utf-8")
    assert "holdings" not in serialized
    assert "Apple" not in serialized


def test_current_form13f_is_one_unit_with_holdings_as_evidence():
    item = _form13f_item("sec-current", accepted_at=_ts(CURRENT))
    item["payload"]["holdings"].append(
        {
            "security": {
                "cusip": "594918104",
                "figi": None,
                "issuer_name": "Microsoft",
                "title_of_class": "Common",
                "put_call": None,
                "amount_type": "SH",
            },
            "current": {
                "reported_amount": {"value": "20", "unit": "shares"},
                "reported_value_usd_thousands": {"value": "42", "unit": "usd_thousands"},
            },
            "previous": None,
            "delta": None,
            "change_type": None,
        }
    )

    updates = _updates(_feed([item]))

    assert len(updates) == 1
    assert updates[0]["unit_id"] == "sec_filing:sec-current"
    assert updates[0]["domain"] == "filing"
    assert updates[0]["unit_type"] == "sec_filing"
    assert updates[0]["event_time"] == {"kind": "accepted_at", "value": _ts(CURRENT)}
    assert [row["security"]["cusip"] for row in updates[0]["evidence"]["payload"]["holdings"]] == [
        "037833100",
        "594918104",
    ]
    assert _status_by_scope(_project_validated_feed(_feed([item])))["form13f"]["state"] == (
        "current_updates_available"
    )


def test_current_form4_accession_is_exactly_one_unit():
    item = _form4_item()
    assert len(item["payload"]["non_derivative_entries"]) > 1

    updates = _updates(_feed([item]))

    assert len(updates) == 1
    assert updates[0]["unit_id"] == "sec_filing:form4-item"
    assert updates[0]["unit_type"] == "sec_filing"
    assert updates[0]["evidence"]["payload"]["filing_subtype"] == "form4"
    assert [
        entry["entry_id"] for entry in updates[0]["evidence"]["payload"]["non_derivative_entries"]
    ] == [
        "transaction-0",
        "transaction-1",
    ]
    assert _status_by_scope(_project_validated_feed(_feed([item])))["form4"]["state"] == (
        "current_updates_available"
    )


def test_current_beneficial_ownership_keeps_previous_evidence_nested():
    item = _beneficial_ownership_item()

    updates = _updates(_feed([item]))

    assert len(updates) == 1
    assert updates[0]["unit_id"] == "sec_filing:beneficial-item"
    payload = updates[0]["evidence"]["payload"]
    assert payload["current_snapshot"]["accession_number"] == "0000000001-23-000003"
    assert payload["previous_snapshot"]["accession_number"] == "0000000001-22-000002"
    assert payload["comparison"]["previous"]["accession_number"] == "0000000001-22-000002"
    assert all("0000000001-22-000002" not in unit["unit_id"] for unit in updates)
    assert (
        _status_by_scope(_project_validated_feed(_feed([item])))["beneficial_ownership"]["state"]
        == "current_updates_available"
    )


def test_old_form4_and_beneficial_ownership_never_reach_status_as_units():
    feed = _feed(
        [
            _form4_item(accepted_at=_ts(OLD)),
            _beneficial_ownership_item(accepted_at=_ts(OLD)),
        ]
    )

    context = _project_validated_feed(feed)
    states = _status_by_scope(context)

    assert context.to_mapping()["content"] == {"updates": []}
    assert states["form4"]["state"] == "no_current_update"
    assert states["beneficial_ownership"]["state"] == "no_current_update"
    assert states["form13f"]["state"] == "domain_empty"
    serialized = canonical_bytes(context.to_mapping()).decode("utf-8")
    assert "reporting_positions" not in serialized
    assert "non_derivative_entries" not in serialized


def test_carried_positioning_slice_is_status_only_with_supported_data_as_of():
    feed = _with_positioning_freshness(
        _feed([_positioning_item()]),
        carried_forward_from_run_id="run-previous",
        status="valid_unchanged",
    )

    context = _project_validated_feed(feed)
    value = context.to_mapping()

    assert value["content"] == {"updates": []}
    assert _status_by_scope(context)["cftc"] == {
        "domain": "positioning",
        "scope": "cftc",
        "state": "carried_reference_state",
        "data_as_of": "2026-08-04T00:00:00.000Z",
    }


def test_stale_positioning_slice_is_status_only():
    feed = _with_positioning_freshness(_feed([_positioning_item()]), status="stale")

    context = _project_validated_feed(feed)

    assert context.to_mapping()["content"] == {"updates": []}
    assert _status_by_scope(context)["cftc"] == {
        "domain": "positioning",
        "scope": "cftc",
        "state": "stale_reference_state",
        "data_as_of": "2026-08-04T00:00:00.000Z",
    }


def test_fresh_positioning_slice_stays_unproven_without_report_identity():
    rows = [_positioning_item(f"cftc-{index}") for index in range(3)]
    feed = _with_positioning_freshness(_feed(rows), status="fresh")

    context = _project_validated_feed(feed)
    value = context.to_mapping()

    assert value["content"] == {"updates": []}
    assert _status_by_scope(context)["cftc"] == {
        "domain": "positioning",
        "scope": "cftc",
        "state": "current_membership_unproven",
        "data_as_of": "2026-08-04T00:00:00.000Z",
    }
    serialized = canonical_bytes(value).decode("utf-8")
    for excluded in ("market_identity", "current_metrics", "noncommercial_long", "245678", "GOLD"):
        assert excluded not in serialized


def test_same_provider_and_date_never_group_into_one_positioning_unit():
    rows = [
        _positioning_item("cftc-1", "2026-08-04T00:00:00.000Z"),
        _positioning_item("cftc-2", "2026-08-04T00:00:00.000Z"),
    ]

    context = _project_validated_feed(_with_positioning_freshness(_feed(rows), status="fresh"))

    assert context.to_mapping()["content"] == {"updates": []}
    assert [row["scope"] for row in context.to_mapping()["status"]["domains"]] == [
        "news",
        "macro_release",
        "policy",
        "cftc",
        "form13f",
        "form4",
        "beneficial_ownership",
    ]


def test_positioning_data_as_of_is_omitted_when_the_slice_disagrees():
    rows = [
        _positioning_item("cftc-1", "2026-08-04T00:00:00.000Z"),
        _positioning_item("cftc-2", "2026-07-28T00:00:00.000Z"),
    ]

    context = _project_validated_feed(_with_positioning_freshness(_feed(rows), status="stale"))

    assert _status_by_scope(context)["cftc"] == {
        "domain": "positioning",
        "scope": "cftc",
        "state": "stale_reference_state",
    }


def test_production_shaped_feed_serializes_only_current_units_and_compact_status():
    rows = [_positioning_item(f"cftc-{index:03d}") for index in range(300)]
    old_filings = [_form13f_item(f"sec-old-{index}") for index in range(3)]
    feed = _feed(
        [*rows, *old_filings, _current_news("news-1"), _current_news("news-2"), _current_policy()]
    )
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
        }
    )
    _with_positioning_freshness(feed, status="stale")

    context = _project_validated_feed(feed)
    value = context.to_mapping()
    serialized = canonical_bytes(value)

    assert [unit["unit_id"] for unit in value["content"]["updates"]] == [
        "news_publication:news-1",
        "news_publication:news-2",
        "policy_document:policy-item",
    ]
    assert value["status"]["limitations"] == [
        {
            "code": "provider_unavailable",
            "provider_id": "bls",
            "affected_coverage_groups": ["us_official_macro_policy"],
        }
    ]
    states = _status_by_scope(context)
    assert states["cftc"]["state"] == "stale_reference_state"
    assert states["form13f"]["state"] == "no_current_update"
    assert states["news"]["state"] == "current_updates_available"
    assert len(serialized) * 20 < len(canonical_bytes(feed))
    assert canonical_bytes(_project_validated_feed(deepcopy(feed)).to_mapping()) == serialized
