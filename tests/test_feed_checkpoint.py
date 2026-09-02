"""Task 2.1 — closed Feed continuity checkpoint contract."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from follow_the_money.feed.checkpoint import (
    CheckpointError,
    FeedCheckpoint,
    PreviousSuccess,
    read_checkpoint,
    write_checkpoint,
)
from follow_the_money.feed.plan import FeedPlanError, plan_window

CUTOFF = datetime(2026, 8, 31, 5, 46, 41, 368000, tzinfo=UTC)
CUTOFF_TEXT = "2026-08-31T05:46:41.368Z"
RUN_ID = f"{CUTOFF_TEXT}::" + "a" * 32


def _success() -> PreviousSuccess:
    return PreviousSuccess(evidence_cutoff_at=CUTOFF_TEXT, run_id=RUN_ID)


def test_checkpoint_reads_explicit_null_previous_success(tmp_path):
    path = tmp_path / "feed-checkpoint.json"
    path.write_text('{"previous_success":null,"version":"1"}', encoding="utf-8")

    assert read_checkpoint(path) == FeedCheckpoint(previous_success=None)


def test_checkpoint_reads_valid_previous_success(tmp_path):
    path = tmp_path / "feed-checkpoint.json"
    path.write_text(
        json.dumps(
            {
                "previous_success": {
                    "evidence_cutoff_at": CUTOFF_TEXT,
                    "run_id": RUN_ID,
                },
                "version": "1",
            }
        ),
        encoding="utf-8",
    )

    assert read_checkpoint(path) == FeedCheckpoint(previous_success=_success())


def test_missing_checkpoint_fails_closed(tmp_path):
    with pytest.raises(CheckpointError, match="missing checkpoint"):
        read_checkpoint(tmp_path / "feed-checkpoint.json")


@pytest.mark.parametrize(
    "payload",
    [
        {"previous_success": None},
        {"previous_success": None, "version": "2"},
        {"previous_success": None, "version": "1", "extra": True},
        {
            "previous_success": {
                "evidence_cutoff_at": CUTOFF_TEXT,
                "run_id": RUN_ID,
                "extra": True,
            },
            "version": "1",
        },
    ],
)
def test_checkpoint_rejects_missing_unknown_or_unsupported_fields(tmp_path, payload):
    path = tmp_path / "feed-checkpoint.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(CheckpointError):
        read_checkpoint(path)


@pytest.mark.parametrize(
    "success",
    [
        replace(_success(), evidence_cutoff_at="2026-08-31T05:46:41.368"),
        replace(_success(), evidence_cutoff_at="2026-08-31 05:46:41.368Z"),
        replace(_success(), evidence_cutoff_at="2026-08-31T05:46:41.368+08:00"),
        replace(_success(), run_id="not-a-run-id"),
        replace(_success(), run_id=f"{CUTOFF_TEXT}::" + "A" * 32),
        replace(
            _success(),
            run_id="2026-08-31T05:46:42.368Z::" + "a" * 32,
        ),
    ],
)
def test_checkpoint_rejects_invalid_utc_or_run_identity(tmp_path, success):
    path = tmp_path / "feed-checkpoint.json"
    path.write_text(
        json.dumps(
            {
                "previous_success": {
                    "evidence_cutoff_at": success.evidence_cutoff_at,
                    "run_id": success.run_id,
                },
                "version": "1",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(CheckpointError):
        read_checkpoint(path)


def test_checkpoint_rejects_partial_json(tmp_path):
    path = tmp_path / "feed-checkpoint.json"
    path.write_bytes(b'{"previous_success":null,"version":"1"')

    with pytest.raises(CheckpointError, match="invalid JSON"):
        read_checkpoint(path)


def test_checkpoint_writer_is_atomic_and_closed(tmp_path):
    path = tmp_path / "nested" / "feed-checkpoint.json"

    write_checkpoint(path, FeedCheckpoint(previous_success=_success()))

    assert json.loads(path.read_text(encoding="utf-8")) == {
        "previous_success": {
            "evidence_cutoff_at": CUTOFF_TEXT,
            "run_id": RUN_ID,
        },
        "version": "1",
    }
    assert not any(".tmp-" in child.name for child in path.parent.iterdir())


def test_checkpoint_writer_surfaces_atomic_write_failure(tmp_path, monkeypatch):
    path = tmp_path / "feed-checkpoint.json"

    def fail(*_args, **_kwargs):
        raise OSError("simulated atomic write failure")

    monkeypatch.setattr("follow_the_money.feed.checkpoint._atomic_write", fail)
    with pytest.raises(CheckpointError, match="simulated atomic write failure"):
        write_checkpoint(path, FeedCheckpoint(previous_success=None))


def test_plan_window_uses_bounded_bootstrap_for_explicit_null_checkpoint():
    plan = plan_window(cutoff=CUTOFF, previous_success=None)

    assert plan.bootstrap is True
    assert plan.window_start == "2026-08-28T05:46:41.368Z"
    assert plan.evidence_cutoff_at == CUTOFF_TEXT


def test_plan_window_advances_from_checkpoint_cutoff():
    plan = plan_window(
        cutoff=datetime(2026, 8, 31, 6, 46, 41, 368000, tzinfo=UTC),
        previous_success=_success(),
    )

    assert plan.bootstrap is False
    assert plan.window_start == CUTOFF_TEXT


@pytest.mark.parametrize(
    "cutoff",
    [CUTOFF, datetime(2026, 8, 31, 5, 46, 40, 368000, tzinfo=UTC)],
)
def test_plan_window_rejects_equal_or_earlier_cutoff(cutoff):
    with pytest.raises(FeedPlanError, match="non_advancing_cutoff"):
        plan_window(cutoff=cutoff, previous_success=_success())


def test_plan_window_rejects_naive_cutoff():
    with pytest.raises(FeedPlanError, match="timezone-aware"):
        plan_window(cutoff=CUTOFF.replace(tzinfo=None), previous_success=None)


def test_plan_window_preserves_exact_threshold_gap():
    cutoff = CUTOFF + timedelta(hours=72)

    plan = plan_window(cutoff=cutoff, previous_success=_success())

    assert plan.bootstrap is False
    assert plan.gap_warning is None
    assert plan.window_start == CUTOFF_TEXT


def test_plan_window_reports_over_threshold_gap():
    cutoff = CUTOFF + timedelta(hours=73)

    plan = plan_window(cutoff=cutoff, previous_success=_success())

    assert plan.bootstrap is True
    assert plan.window_start == "2026-08-31T06:46:41.368Z"
    assert plan.gap_warning == (CUTOFF_TEXT, plan.window_start)


def test_steady_state_planning_never_reads_latest_json(monkeypatch):
    def fail(*_args, **_kwargs):
        raise AssertionError("steady-state planning read latest.json")

    monkeypatch.setattr(Path, "read_bytes", fail)
    plan = plan_window(
        cutoff=datetime(2026, 8, 31, 6, 46, 41, 368000, tzinfo=UTC),
        previous_success=_success(),
    )

    assert plan.window_start == CUTOFF_TEXT
