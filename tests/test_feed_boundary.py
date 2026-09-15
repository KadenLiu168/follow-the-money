"""Feed-only envelope and trust-boundary regressions."""

from __future__ import annotations

from copy import deepcopy
from datetime import timedelta

import pytest

from follow_the_money.canonical import canonical_digest
from follow_the_money.feed.bundle import build_bundle
from follow_the_money.feed.validate import (
    assert_feed_identity,
    recompute_feed_identity,
    validate_canonical_numeric,
    validate_feed,
    validate_numeric_token,
)
from follow_the_money.schema import SchemaError
from tests.test_feed_bundle import T0, _feed, _news, _ts


def test_valid_empty_and_populated_five_domain_feeds_pass():
    empty = _feed()
    empty["content_digest"], empty["run_id"] = recompute_feed_identity(empty)
    validate_feed(empty)
    assert_feed_identity(empty)

    populated = _feed([_news()])
    validate_feed(populated)
    assert build_bundle(populated).artifacts["news"]["items"] == populated["items"]


def test_v4_rejects_removed_payload_types_and_fields():
    feed = _feed([_news()])
    item = deepcopy(feed["items"][0])
    item["payload"] = {
        "type": "market_data",
        "instrument_id": "sp500",
        "observations": [{"as_of": _ts(T0 - timedelta(hours=1)), "value": "1", "unit": "index"}],
        "raw_metadata": {},
    }
    feed["items"] = [item]
    with pytest.raises(SchemaError):
        validate_feed(feed)

    with pytest.raises(SchemaError):
        validate_feed({**_feed(), "calendar_horizon_end": _ts(T0 + timedelta(hours=26))})


def test_unsupported_major_unknown_properties_and_bad_windows_fail_closed():
    previous = _feed()
    previous["schema_version"] = 3
    with pytest.raises(SchemaError):
        validate_feed(previous)
    with pytest.raises(SchemaError):
        validate_feed({**_feed(), "unexpected": True})
    with pytest.raises(SchemaError, match="strictly advancing"):
        validate_feed(
            {
                **_feed(),
                "window": {"start": _ts(T0), "end": _ts(T0)},
            }
        )


def test_lifecycle_order_and_item_order_are_enforced():
    bad_lifecycle = _feed()
    bad_lifecycle["generated_at"] = _ts(T0 - timedelta(minutes=1))
    with pytest.raises(SchemaError, match="wall-clock order"):
        validate_feed(bad_lifecycle)

    first = _news("first", T0 - timedelta(hours=1))
    second = _news("second", T0 - timedelta(hours=2))
    bad_order = _feed([first, second])
    with pytest.raises(SchemaError, match="total order"):
        validate_feed(bad_order)


def test_identity_rejects_forged_digest_or_run_id_and_covers_semantics():
    feed = _feed([_news()])
    digest, run_id = recompute_feed_identity(feed)
    feed["content_digest"], feed["run_id"] = digest, run_id
    assert_feed_identity(feed)

    forged = dict(feed)
    forged["content_digest"] = "0" * 64
    with pytest.raises(SchemaError, match="content_digest"):
        assert_feed_identity(forged)

    changed = deepcopy(feed)
    changed["pipeline"] = {"status": "degraded", "warnings": ["changed"]}
    assert recompute_feed_identity(changed)[0] != digest


def test_numeric_guards_remain_closed_for_retained_numeric_evidence():
    validate_numeric_token("-12.5e+2", where="value")
    validate_canonical_numeric("100.25", where="value")
    for token in ("01", "1.", "1e99"):
        with pytest.raises(SchemaError):
            validate_numeric_token(token, where="value")
    with pytest.raises(SchemaError):
        validate_canonical_numeric("-0", where="value")


def test_producer_and_contract_descriptors_are_part_of_identity():
    feed = _feed()
    first = recompute_feed_identity(feed)[0]
    changed = deepcopy(feed)
    changed["provider_contracts"][0]["snapshot"]["payload_types"] = ["filing"]
    changed["provider_contracts"][0]["hash"] = canonical_digest(
        changed["provider_contracts"][0]["snapshot"]
    )
    assert recompute_feed_identity(changed)[0] != first


def _sec_v2_item():
    return {
        "id": "sec-v2-item",
        "provider_id": "sec_edgar",
        "source": {
            "id": "sec-v2-source",
            "name": "SEC EDGAR",
            "tier": "Tier 1",
            "kind": "filing",
            "url": "https://www.sec.gov/Archives/edgar/data/0000000001/a/a.txt",
            "published_at": _ts(T0 - timedelta(hours=1)),
            "knowledge_available_at": _ts(T0 - timedelta(hours=1)),
        },
        "payload": {
            "type": "filing",
            "form": "13F-HR",
            "company": "0000000001",
            "accession_number": "0000000001-23-000001",
            "filed_at": "2023-01-03T00:00:00.000Z",
            "raw_metadata": {},
            "company_identity": {"cik": "0000000001", "name": "Official Manager", "tickers": []},
            "report_period": "2022-12-31",
            "accepted_at": "2023-01-03T12:00:00.000Z",
            "value_normalization": {"source_unit": "usd", "formula_id": "usd_divided_by_1000"},
            "comparison": {
                "status": "unavailable",
                "previous_accession_number": None,
                "previous_report_period": None,
                "previous_accepted_at": None,
                "previous_filed_at": None,
                "previous_source_url": None,
                "previous_value_normalization": None,
                "reason": "no_previous_comparable_filing",
            },
            "holdings": [
                {
                    "security": {
                        "cusip": "037833100",
                        "figi": None,
                        "issuer_name": "Apple",
                        "title_of_class": "Common",
                        "put_call": None,
                        "amount_type": "SH",
                    },
                    "current": {
                        "reported_amount": {"value": "10", "unit": "shares"},
                        "reported_value_usd_thousands": {
                            "value": "1234.567",
                            "unit": "usd_thousands",
                        },
                    },
                    "previous": None,
                    "delta": None,
                    "change_type": None,
                }
            ],
        },
    }


def _enable_v2(feed, provider_id):
    contract = next(c for c in feed["provider_contracts"] if c["provider_id"] == provider_id)
    contract["snapshot"]["contract_version"] = 2
    contract["snapshot"]["units"] = (
        {
            "13f_value_before_2023_01_03": "usd_thousands",
            "13f_value_from_2023_01_03": "usd",
            "reported_value_usd_thousands": "usd_thousands",
        }
        if provider_id == "sec_edgar"
        else {"contracts": "contracts"}
    )
    contract["hash"] = canonical_digest(contract["snapshot"])


def test_v4_sec_v2_requires_complete_semantic_item_and_watched_snapshot():
    feed = _feed([_sec_v2_item()])
    _enable_v2(feed, "sec_edgar")
    feed["feed_config"]["snapshot"]["watched_companies"] = [
        {"cik": "0000000001", "name": "Configured", "tickers": []}
    ]
    outcome = next(o for o in feed["provider_outcomes"] if o["provider_id"] == "sec_edgar")
    outcome["accepted"] = 1
    outcome["freshness"]["status"] = "fresh"
    outcome["freshness"]["origin_contract_hash"] = next(
        c["hash"] for c in feed["provider_contracts"] if c["provider_id"] == "sec_edgar"
    )
    validate_feed(feed)
    missing = deepcopy(feed)
    del missing["items"][0]["payload"]["holdings"]
    with pytest.raises(SchemaError):
        validate_feed(missing)


def test_v4_sec_v2_contract_requires_watched_snapshot_without_sec_items():
    # The watched-company snapshot is required by the embedded contract, not
    # by the presence of items, so a blocked-exempt or empty SEC outcome
    # cannot skip it.
    feed = _feed()
    _enable_v2(feed, "sec_edgar")
    del feed["feed_config"]["snapshot"]["watched_companies"]
    with pytest.raises(SchemaError, match="watched_companies"):
        validate_feed(feed)


def test_v4_rejects_unknown_semantic_fields_and_unsupported_provider_version():
    feed = _feed([_sec_v2_item()])
    _enable_v2(feed, "sec_edgar")
    feed["feed_config"]["snapshot"]["watched_companies"] = [
        {"cik": "0000000001", "name": "Configured", "tickers": []}
    ]
    outcome = next(o for o in feed["provider_outcomes"] if o["provider_id"] == "sec_edgar")
    outcome["accepted"] = 1
    outcome["freshness"]["status"] = "fresh"
    contract = next(c for c in feed["provider_contracts"] if c["provider_id"] == "sec_edgar")
    outcome["freshness"]["origin_contract_hash"] = contract["hash"]
    unknown = deepcopy(feed)
    unknown["items"][0]["payload"]["holdings"][0]["unexpected"] = True
    with pytest.raises(SchemaError):
        validate_feed(unknown)
    unsupported = deepcopy(feed)
    other = next(c for c in unsupported["provider_contracts"] if c["provider_id"] == "bls")
    other["snapshot"]["contract_version"] = 2
    other["hash"] = canonical_digest(other["snapshot"])
    with pytest.raises(SchemaError, match="unsupported contract"):
        validate_feed(unsupported)


def _cftc_v2_item():
    return {
        "id": "cftc-v2-item",
        "provider_id": "cftc",
        "source": {
            "id": "cftc-v2-source",
            "name": "CFTC",
            "tier": "Tier 1",
            "kind": "positioning",
            "url": "https://publicreporting.cftc.gov/resource/6dca-aqww/cftc-v2-row.json",
            "published_at": "2026-08-07T19:30:00.000Z",
            "knowledge_available_at": "2026-08-07T19:30:00.000Z",
        },
        "payload": {
            "type": "positioning",
            "instrument_id": "GOLD",
            "as_of": "2026-08-04T00:00:00.000Z",
            "position": {"value": "245678", "unit": "contracts"},
            "raw_metadata": {},
            "market_identity": {
                "cftc_contract_market_code": "088691",
                "contract_market_name": "GOLD",
            },
            "current_metrics": {
                field: {"value": value, "unit": "contracts"}
                for field, value in {
                    "noncommercial_long": "245678",
                    "noncommercial_short": "198765",
                    "noncommercial_spreading": "1234",
                    "open_interest": "455123",
                    "net_noncommercial": "46913",
                }.items()
            },
            "previous_metrics": None,
            "delta_metrics": None,
            "comparison": {
                "status": "unavailable",
                "previous_as_of": None,
                "reason": "no_previous_comparable_report",
            },
            "derivations": {"net_noncommercial": {"formula_id": "noncommercial_long_minus_short"}},
        },
    }


def test_complete_cftc_v2_item_validates_with_typed_semantics():
    feed = _feed([_cftc_v2_item()])
    _enable_v2(feed, "cftc")
    outcome = next(o for o in feed["provider_outcomes"] if o["provider_id"] == "cftc")
    outcome["accepted"] = 1
    outcome["freshness"]["status"] = "stale"
    outcome["freshness"]["origin_contract_hash"] = next(
        c["hash"] for c in feed["provider_contracts"] if c["provider_id"] == "cftc"
    )
    validate_feed(feed)


def test_semantic_projection_changes_identity_for_sec_and_cftc_facts():
    sec = _feed([_sec_v2_item()])
    _enable_v2(sec, "sec_edgar")
    sec_digest, _ = recompute_feed_identity(sec)
    sec["items"][0]["payload"]["report_period"] = "2022-11-30"
    changed_sec_digest, _ = recompute_feed_identity(sec)
    assert changed_sec_digest != sec_digest

    cftc = _feed([_cftc_v2_item()])
    _enable_v2(cftc, "cftc")
    cftc_digest, _ = recompute_feed_identity(cftc)
    cftc["items"][0]["payload"]["current_metrics"]["open_interest"]["value"] = "455124"
    changed_cftc_digest, _ = recompute_feed_identity(cftc)
    assert changed_cftc_digest != cftc_digest
