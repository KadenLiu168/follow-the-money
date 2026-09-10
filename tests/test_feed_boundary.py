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
