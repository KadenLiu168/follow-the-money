"""Task 4.3/4.4/4.5/4.6 — pipeline and publication fixtures."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from follow_the_money.config import load_config
from follow_the_money.feed.plan import (
    FeedPlanError,
    ProviderOutcome,
    assess_pipeline,
    plan_window,
)
from follow_the_money.feed.publish import PublishError, publish_feed

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "config" / "config.yaml"
DEFAULT_PROVIDERS = REPO_ROOT / "config" / "providers.yaml"


def _cfg():
    return load_config(DEFAULT_CONFIG, DEFAULT_PROVIDERS, require_verified_enabled=False)


def _latest(cutoff: datetime) -> dict:
    return {"evidence_cutoff_at": cutoff.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"}


def _publication_bytes(cutoff: datetime, digest: str = "a" * 64) -> bytes:
    return json.dumps(
        {"content_digest": digest, "evidence_cutoff_at": cutoff.isoformat().replace("+00:00", "Z")},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


# ---------------------------------------------------------------------------
# Window planning
# ---------------------------------------------------------------------------


def test_first_run_bootstrap(tmp_path):
    cutoff = datetime(2026, 8, 11, 0, 20, 0, tzinfo=UTC)
    plan = plan_window(cutoff=cutoff, latest_path=tmp_path / "missing.json")
    assert plan.bootstrap is True
    start = datetime.fromisoformat(plan.window_start)
    assert (cutoff - start).total_seconds() == 72 * 3600


def test_invalid_latest_integrity(tmp_path):
    cutoff = datetime(2026, 8, 11, 0, 20, 0, tzinfo=UTC)
    path = tmp_path / "latest.json"
    path.write_bytes(b"{partial")
    with pytest.raises(FeedPlanError, match="invalid_latest_integrity"):
        plan_window(cutoff=cutoff, latest_path=path)


def test_unreadable_latest_integrity(tmp_path):
    cutoff = datetime(2026, 8, 11, 0, 20, 0, tzinfo=UTC)
    path = tmp_path / "latest.json"
    path.write_bytes(b"{}")  # valid JSON but not a valid latest (no cutoff)
    with pytest.raises(FeedPlanError, match="invalid_latest_integrity"):
        plan_window(cutoff=cutoff, latest_path=path)


def test_non_advancing_cutoff(tmp_path):
    latest_cutoff = datetime(2026, 8, 11, 0, 20, 0, tzinfo=UTC)
    path = tmp_path / "latest.json"
    path.write_bytes(b"x")
    with pytest.raises(FeedPlanError, match="non_advancing_cutoff"):
        plan_window(
            cutoff=latest_cutoff,
            latest_path=path,
            validate_latest=lambda p: _latest(latest_cutoff),
        )
    # equal cutoff also fails
    with pytest.raises(FeedPlanError, match="non_advancing_cutoff"):
        plan_window(
            cutoff=latest_cutoff + timedelta(seconds=0),
            latest_path=path,
            validate_latest=lambda p: _latest(latest_cutoff),
        )


def test_advancing_cutoff_starts_at_previous(tmp_path):
    latest_cutoff = datetime(2026, 8, 11, 0, 20, 0, tzinfo=UTC)
    new_cutoff = latest_cutoff + timedelta(hours=24)
    path = tmp_path / "latest.json"
    path.write_bytes(b"x")
    plan = plan_window(
        cutoff=new_cutoff,
        latest_path=path,
        validate_latest=lambda p: _latest(latest_cutoff),
    )
    assert plan.window_start == latest_cutoff.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    assert plan.bootstrap is False
    assert plan.gap_warning is None


def test_gap_exactly_72h_no_warning(tmp_path):
    latest_cutoff = datetime(2026, 8, 11, 0, 20, 0, tzinfo=UTC)
    new_cutoff = latest_cutoff + timedelta(hours=72)
    path = tmp_path / "latest.json"
    path.write_bytes(b"x")
    plan = plan_window(
        cutoff=new_cutoff,
        latest_path=path,
        validate_latest=lambda p: _latest(latest_cutoff),
    )
    assert plan.window_start == latest_cutoff.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    assert plan.gap_warning is None


def test_gap_over_72h_records_warning(tmp_path):
    latest_cutoff = datetime(2026, 8, 11, 0, 20, 0, tzinfo=UTC)
    new_cutoff = latest_cutoff + timedelta(hours=73)
    path = tmp_path / "latest.json"
    path.write_bytes(b"x")
    plan = plan_window(
        cutoff=new_cutoff,
        latest_path=path,
        validate_latest=lambda p: _latest(latest_cutoff),
    )
    assert plan.gap_warning is not None
    uncovered_start, uncovered_end = plan.gap_warning
    assert uncovered_start < uncovered_end
    # bounded start = cutoff - 72h
    expected_start = new_cutoff - timedelta(hours=72)
    assert plan.window_start == expected_start.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


# ---------------------------------------------------------------------------
# Pipeline health accounting
# ---------------------------------------------------------------------------


def test_healthy_six_row_coverage():
    cfg = _cfg()
    # Only a subset of the shipped (unverified) providers exist; simulate a
    # fully healthy matrix via synthetic providers matching row members.
    outcomes = {}
    for row in cfg.coverage.rows:
        for member in row.members:
            outcomes[member] = ProviderOutcome(member, state="healthy", accepted=1)
    status, warnings = assess_pipeline(config=cfg, outcomes=outcomes, total_accepted=10)
    assert status == "healthy"
    assert warnings == []


def test_one_below_minimum_degrades():
    cfg = _cfg()
    outcomes = {}
    for row in cfg.coverage.rows:
        for i, member in enumerate(row.members):
            # First member of every row fails => below minimum everywhere.
            outcomes[member] = ProviderOutcome(member, state="failed")
    outcomes["federal_reserve"] = ProviderOutcome("federal_reserve", state="healthy", accepted=1)
    status, warnings = assess_pipeline(config=cfg, outcomes=outcomes, total_accepted=1)
    assert status == "degraded"
    assert any("deficient" in w for w in warnings)


def test_permitted_empty_counts_healthy_not_accepted_item():
    cfg = _cfg()
    outcomes = {}
    for row in cfg.coverage.rows:
        for member in row.members:
            outcomes[member] = ProviderOutcome(member, state="empty", accepted=0)
    # Empty results are healthy for counting but no accepted item => failure.
    status, _warnings = assess_pipeline(config=cfg, outcomes=outcomes, total_accepted=0)
    assert status == "failure"


def test_mixed_validity_with_accepted_item():
    cfg = _cfg()
    outcomes = {}
    for row in cfg.coverage.rows:
        for member in row.members:
            outcomes[member] = ProviderOutcome(member, state="healthy", accepted=1)
    outcomes["sec_edgar"] = ProviderOutcome("sec_edgar", state="failed")
    status, warnings = assess_pipeline(config=cfg, outcomes=outcomes, total_accepted=5)
    assert status == "degraded"
    # The failed member makes us_company_filings deficient (1/1 minimum).
    assert any("deficient" in w for w in warnings)


def test_all_enabled_empty_is_failure():
    cfg = _cfg()
    outcomes = {
        member: ProviderOutcome(member, state="empty")
        for row in cfg.coverage.rows
        for member in row.members
    }
    status, _ = assess_pipeline(config=cfg, outcomes=outcomes, total_accepted=0)
    assert status == "failure"


# ---------------------------------------------------------------------------
# Publication
# ---------------------------------------------------------------------------


def test_publish_dated_then_latest(tmp_path):
    root = tmp_path / "out"
    root.mkdir()
    cutoff = datetime(2026, 8, 11, 0, 20, 0, tzinfo=UTC)
    feed = _publication_bytes(cutoff)
    result = publish_feed(
        output_root=root,
        cutoff=cutoff,
        run_id="run_1",
        feed_bytes=feed,
        latest_bytes=feed,
    )
    dated = root / "daily" / "2026-08-11" / "run_1.json"
    assert dated.exists()
    assert dated.read_bytes() == feed
    assert (root / "latest.json").read_bytes() == feed
    assert result.latest_replaced


def test_publish_idempotent_same_run(tmp_path):
    root = tmp_path / "out"
    root.mkdir()
    cutoff = datetime(2026, 8, 11, 0, 20, 0, tzinfo=UTC)
    feed = _publication_bytes(cutoff)
    publish_feed(
        output_root=root, cutoff=cutoff, run_id="run_1", feed_bytes=feed, latest_bytes=feed
    )
    result = publish_feed(
        output_root=root, cutoff=cutoff, run_id="run_1", feed_bytes=feed, latest_bytes=feed
    )
    assert result.idempotent


def test_publish_same_path_incompatible_fails(tmp_path):
    root = tmp_path / "out"
    root.mkdir()
    cutoff = datetime(2026, 8, 11, 0, 20, 0, tzinfo=UTC)
    feed = _publication_bytes(cutoff)
    publish_feed(
        output_root=root, cutoff=cutoff, run_id="run_1", feed_bytes=feed, latest_bytes=feed
    )
    incompatible = _publication_bytes(cutoff, "b" * 64)
    with pytest.raises(PublishError, match="incompatible content"):
        publish_feed(
            output_root=root,
            cutoff=cutoff,
            run_id="run_1",
            feed_bytes=incompatible,
            latest_bytes=incompatible,
        )


def test_publish_no_staging_leftovers(tmp_path):
    root = tmp_path / "out"
    root.mkdir()
    cutoff = datetime(2026, 8, 11, 0, 20, 0, tzinfo=UTC)
    feed = _publication_bytes(cutoff)
    publish_feed(
        output_root=root, cutoff=cutoff, run_id="run_1", feed_bytes=feed, latest_bytes=feed
    )
    leftovers = [p.name for p in root.rglob("*") if ".stage-" in p.name]
    assert leftovers == []


def test_publish_latest_ownership_mismatch_rejected(tmp_path):
    root = tmp_path / "out"
    root.mkdir()
    cutoff = datetime(2026, 8, 11, 0, 20, 0, tzinfo=UTC)
    feed = _publication_bytes(cutoff)
    # existing_latest_sha256 says the current latest has a different hash.
    with pytest.raises(PublishError, match="ownership mismatch"):
        publish_feed(
            output_root=root,
            cutoff=cutoff,
            run_id="run_1",
            feed_bytes=feed,
            latest_bytes=feed,
            existing_latest_sha256="0" * 64,
        )


def test_dated_path_uses_asia_shanghai_cutoff_date(tmp_path):
    root = tmp_path / "out"
    root.mkdir()
    cutoff = datetime(2026, 8, 10, 20, 30, 0, tzinfo=UTC)
    feed = _publication_bytes(cutoff)

    result = publish_feed(
        output_root=root,
        cutoff=cutoff,
        run_id="run_1",
        feed_bytes=feed,
        latest_bytes=feed,
    )

    expected = root / "daily" / "2026-08-11" / "run_1.json"
    assert result.dated_path == expected
    assert expected.read_bytes() == feed
    assert not (root / "daily" / "2026-08-10").exists()
