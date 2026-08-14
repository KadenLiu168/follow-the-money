"""Task 2.1 — Feed envelope boundary fixtures.

Positive and negative fixtures for the Feed envelope: supported major,
strict-UTF-8/lone-surrogate rejection, window ordering, wall-clock order,
digest/run-ID recomputation, numeric guards, intelligence-field rejection,
calendar horizon, and provenance descriptors.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from follow_the_money.feed.validate import (
    assert_feed_identity,
    recompute_feed_identity,
    validate_canonical_numeric,
    validate_feed,
    validate_numeric_token,
)
from follow_the_money.schema import SchemaError

T0 = datetime(2026, 8, 11, 0, 20, 0, tzinfo=UTC)


def _ts(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _valid_feed(**overrides) -> dict:
    cutoff = T0
    started = cutoff - timedelta(seconds=30)
    completed = cutoff + timedelta(minutes=4)
    generated = cutoff + timedelta(minutes=5)
    feed = {
        "schema_version": 1,
        "run_id": f"{_ts(cutoff)}::deadbeef",
        "window": {"start": _ts(cutoff - timedelta(hours=72)), "end": _ts(cutoff)},
        "collection_started_at": _ts(started),
        "evidence_cutoff_at": _ts(cutoff),
        "collection_completed_at": _ts(completed),
        "generated_at": _ts(generated),
        "provider_outcomes": [],
        "producer": {
            "package_version": "0.1.0",
            "files": [],
            "fingerprint": "a" * 64,
        },
        "feed_config": {"snapshot": {}, "hash": "b" * 64},
        "feed_schema": {"path": "schemas/feed.schema.json", "sha256": "c" * 64},
        "provider_contracts": [],
        "git": None,
        "content_digest": "d" * 64,
        "items": [],
        "pipeline": {"status": "healthy", "warnings": []},
    }
    feed.update(overrides)
    return feed


def _news_item(published: datetime, title: str = "标题") -> dict:
    return {
        "id": "item-1",
        "provider_id": "prov_a",
        "source": {
            "id": "src-1",
            "name": "Source A",
            "tier": "Tier 1",
            "kind": "news",
            "url": "https://a.example.com/x",
            "published_at": _ts(published),
            "knowledge_available_at": _ts(published),
        },
        "payload": {
            "type": "news",
            "title": title,
            "snippet": "摘要",
            "occurred_at": _ts(published),
            "raw_metadata": {},
        },
    }


# ---------------------------------------------------------------------------
# Positive
# ---------------------------------------------------------------------------


def test_valid_empty_feed_passes():
    feed = _valid_feed()
    digest, run_id = recompute_feed_identity(feed)
    feed["content_digest"] = digest
    feed["run_id"] = run_id
    validate_feed(feed)
    assert_feed_identity(feed)


def test_valid_news_item_passes():
    feed = _valid_feed()
    feed["items"] = [_news_item(T0 - timedelta(hours=1))]
    validate_feed(feed)


def test_all_eight_payloads_pass_schema():
    feed = _valid_feed()
    base_source = _news_item(T0 - timedelta(hours=1))["source"]
    items = [
        {
            "id": "n",
            "provider_id": "p",
            "source": base_source,
            "payload": {
                "type": "news",
                "title": "t",
                "snippet": "s",
                "occurred_at": _ts(T0),
                "raw_metadata": {},
            },
        },
        {
            "id": "m",
            "provider_id": "p",
            "source": base_source,
            "payload": {
                "type": "macro_release",
                "series_id": "us_cpi_all_items_sa_mom",
                "released_at": _ts(T0),
                "observation_period": None,
                "actual": {"value": "3.2", "unit": "percent"},
                "consensus": {"value": None, "unit": "percent", "unknown_reason": "missing"},
                "previous": {"value": "3.1", "unit": "percent"},
                "raw_metadata": {},
            },
        },
        {
            "id": "po",
            "provider_id": "p",
            "source": base_source,
            "payload": {
                "type": "policy",
                "title": "policy",
                "announced_at": _ts(T0),
                "raw_metadata": {},
            },
        },
        {
            "id": "md",
            "provider_id": "p",
            "source": base_source,
            "payload": {
                "type": "market_data",
                "instrument_id": "sp500",
                "observations": [
                    {"as_of": _ts(T0 - timedelta(days=1)), "value": "5000.0", "unit": "index"}
                ],
                "raw_metadata": {},
            },
        },
        {
            "id": "f",
            "provider_id": "p",
            "source": base_source,
            "payload": {
                "type": "flow",
                "instrument_id": "spy",
                "as_of": _ts(T0),
                "net_flow": {"value": "100.5", "unit": "usd"},
                "raw_metadata": {},
            },
        },
        {
            "id": "pos",
            "provider_id": "p",
            "source": base_source,
            "payload": {
                "type": "positioning",
                "instrument_id": "gold",
                "as_of": _ts(T0),
                "position": {"value": "50", "unit": "percent"},
                "raw_metadata": {},
            },
        },
        {
            "id": "fil",
            "provider_id": "p",
            "source": base_source,
            "payload": {
                "type": "filing",
                "form": "13F",
                "company": "Acme",
                "accession_number": "0001",
                "filed_at": _ts(T0),
                "raw_metadata": {},
            },
        },
        {
            "id": "cal",
            "provider_id": "p",
            "source": base_source,
            "payload": {
                "type": "calendar",
                "calendar_id": "c1",
                "scheduled_at": _ts(T0 + timedelta(hours=12)),
                "priority": "high",
                "raw_metadata": {},
            },
        },
    ]
    feed["items"] = sorted(items, key=lambda i: (i["source"]["knowledge_available_at"], i["id"]))
    validate_feed(feed)


# ---------------------------------------------------------------------------
# Schema/version
# ---------------------------------------------------------------------------


def test_unsupported_major_rejected():
    feed = _valid_feed(schema_version=2)
    # Schema const(1) fires first; the semantic supported-major check is a
    # second independent guard.
    with pytest.raises(SchemaError, match="unsupported|was expected"):
        validate_feed(feed)


def test_unknown_property_rejected():
    feed = _valid_feed(extra_field=True)
    with pytest.raises(SchemaError):
        validate_feed(feed)


# ---------------------------------------------------------------------------
# Window ordering
# ---------------------------------------------------------------------------


def test_equal_window_rejected():
    cutoff = T0
    feed = _valid_feed()
    feed["window"] = {"start": _ts(cutoff), "end": _ts(cutoff)}
    with pytest.raises(SchemaError, match="strictly advancing"):
        validate_feed(feed)


def test_backward_window_rejected():
    feed = _valid_feed()
    feed["window"] = {"start": _ts(T0 + timedelta(hours=1)), "end": _ts(T0)}
    with pytest.raises(SchemaError, match="strictly advancing"):
        validate_feed(feed)


def test_wall_clock_order_violated():
    feed = _valid_feed()
    feed["evidence_cutoff_at"] = _ts(T0 + timedelta(minutes=10))
    with pytest.raises(SchemaError, match="wall-clock order"):
        validate_feed(feed)


def test_retrieved_at_out_of_bounds():
    feed = _valid_feed()
    feed["provider_outcomes"] = [
        {
            "provider_id": "p",
            "state": "healthy",
            "attempted": 1,
            "fetched": 1,
            "succeeded": True,
            "empty": False,
            "partial": False,
            "failed": False,
            "skipped": False,
            "accepted": 1,
            "rejected": 0,
            "retrieved_at": _ts(T0 - timedelta(minutes=1)),
        }
    ]
    with pytest.raises(SchemaError, match="retrieved_at"):
        validate_feed(feed)


# ---------------------------------------------------------------------------
# Digest / run ID identity
# ---------------------------------------------------------------------------


def test_digest_mismatch_rejected():
    feed = _valid_feed()
    _digest, run_id = recompute_feed_identity(feed)
    feed["content_digest"] = "f" * 64
    feed["run_id"] = run_id
    with pytest.raises(SchemaError, match="content_digest"):
        assert_feed_identity(feed)


def test_run_id_mismatch_rejected():
    feed = _valid_feed()
    digest, _run_id = recompute_feed_identity(feed)
    feed["content_digest"] = digest
    feed["run_id"] = "wrong-run-id"
    with pytest.raises(SchemaError, match="run_id"):
        assert_feed_identity(feed)


def test_digest_covers_producer_provenance():
    a = _valid_feed()
    b = _valid_feed()
    a["producer"]["fingerprint"] = "a" * 64
    b["producer"]["fingerprint"] = "b" * 64
    da, _ = recompute_feed_identity(a)
    db, _ = recompute_feed_identity(b)
    assert da != db


def test_digest_omits_run_id_and_digest():
    a = _valid_feed()
    b = _valid_feed()
    a["run_id"] = "x"
    b["run_id"] = "y"
    da, _ = recompute_feed_identity(a)
    db, _ = recompute_feed_identity(b)
    assert da == db  # run_id does not participate


# ---------------------------------------------------------------------------
# Numeric guards
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "token,ok",
    [
        ("0", True),
        ("-0.5", True),
        ("3.14159265358979323846264", True),  # 24 significant digits
        ("3.141592653589793238462643", False),  # 25 digits
        ("1e12", True),
        ("1e-12", True),
        ("1e13", False),  # exponent > 12
        ("0x1f", False),
        ("NaN", False),
        ("Infinity", False),
        ("1,5", False),
        ("+3.2", True),
        ("-0", True),  # raw token allows -0; canonical persistence forbids it
    ],
)
def test_raw_numeric_token_boundaries(token, ok):
    if ok:
        validate_numeric_token(token, where="test")
    else:
        with pytest.raises(SchemaError):
            validate_numeric_token(token, where="test")


@pytest.mark.parametrize(
    "value,ok",
    [
        ("0", True),
        ("123456789012345678.9", True),  # 18-digit integer part ok
        ("1234567890123456789", False),  # 19-digit integer part > 10^18 guard
        ("-0.0", False),
        ("3.2e1", False),  # exponent forbidden in canonical form
        ("abc", False),
        ("1000000000000000000", True),  # exactly 10^18 allowed
    ],
)
def test_canonical_numeric_guards(value, ok):
    if ok:
        validate_canonical_numeric(value, where="test")
    else:
        with pytest.raises(SchemaError):
            validate_canonical_numeric(value, where="test")


def test_canonical_numeric_negative_zero_rejected():
    with pytest.raises(SchemaError, match="negative zero"):
        validate_canonical_numeric("-0.00", where="test")


# ---------------------------------------------------------------------------
# Intelligence-field rejection
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "field", ["importance", "direction", "price_in", "regime", "impact", "ranking"]
)
def test_intelligence_field_rejected(field):
    feed = _valid_feed()
    item = _news_item(T0 - timedelta(hours=1))
    item["payload"][field] = "anything"
    feed["items"] = [item]
    # Schema-level additionalProperties rejection fires first; the semantic
    # intelligence check is a second, independent guard.
    with pytest.raises(SchemaError, match="intelligence|not valid under any of the given schemas"):
        validate_feed(feed)


# ---------------------------------------------------------------------------
# Lone surrogate / strict UTF-8
# ---------------------------------------------------------------------------


def test_lone_surrogate_in_title_rejected():
    feed = _valid_feed()
    item = _news_item(T0 - timedelta(hours=1))
    item["payload"]["title"] = "bad\ud800title"
    feed["items"] = [item]
    with pytest.raises(SchemaError, match="surrogate"):
        validate_feed(feed)


def test_escaped_lone_surrogate_rejected():
    feed = _valid_feed()
    item = _news_item(T0 - timedelta(hours=1))
    item["payload"]["title"] = "bad\udfff"
    feed["items"] = [item]
    with pytest.raises(SchemaError, match="surrogate"):
        validate_feed(feed)


# ---------------------------------------------------------------------------
# Calendar horizon
# ---------------------------------------------------------------------------


def test_calendar_horizon_before_cutoff_rejected():
    feed = _valid_feed(calendar_horizon_end=_ts(T0 - timedelta(hours=1)))
    with pytest.raises(SchemaError, match="calendar_horizon_end"):
        validate_feed(feed)


def test_calendar_horizon_26h_after_cutoff_ok():
    feed = _valid_feed(calendar_horizon_end=_ts(T0 + timedelta(hours=26)))
    validate_feed(feed)
