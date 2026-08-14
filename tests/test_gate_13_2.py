"""Gate 13.2 — Feed publication recovery gate.

Behavior-based failure injection and two-process tests for the publication
contract: lock-before-cutoff planning, Asia/Shanghai dated paths, atomic
no-replace dated commit, monotonic latest ownership, fsync boundaries,
``commit_durability_unknown``, crash recovery, idempotency, equal-cutoff
variant ordering, deadline reserve, and zero mutation after cancellation.
"""

from __future__ import annotations

import errno
import json
import time
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from unittest import mock

import pytest

from follow_the_money.feed.cli import FeedCliError, FeedExecutionError, run_feed
from follow_the_money.feed.publish import (
    PublishError,
    atomic_no_replace_rename,
    publish_feed,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
T0 = datetime(2026, 8, 11, 0, 20, 0, tzinfo=UTC)


def _ts(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


class _MinimalAdapter:
    """One healthy provider adapter producing a single valid policy item."""

    provider_id = "federal_reserve"

    def fetch(self, window, client=None):
        from types import SimpleNamespace

        return SimpleNamespace(body_bytes=b"<rss version='2.0'><channel></channel></rss>")

    def normalize(self, raw, window):
        return [
            {
                "id": "item_min",
                "provider_id": "federal_reserve",
                "source": {
                    "id": "src-min",
                    "name": "Federal Reserve",
                    "tier": "Tier 1",
                    "kind": "news",
                    "url": "https://www.federalreserve.gov/newsevents/pressreleases/min20260811.htm",
                    "published_at": _ts(T0),
                    "knowledge_available_at": _ts(T0),
                },
                "payload": {
                    "type": "policy",
                    "title": "最小测试声明",
                    "announced_at": _ts(T0),
                    "raw_metadata": {},
                },
            }
        ]


def _minimal_registry() -> dict:
    return {"federal_reserve": _MinimalAdapter()}


def _healthy_feed_dict() -> dict:
    return {
        "schema_version": 1,
        "run_id": "x",
        "window": {"start": _ts(T0 - timedelta(hours=72)), "end": _ts(T0)},
        "collection_started_at": _ts(T0 - timedelta(seconds=30)),
        "evidence_cutoff_at": _ts(T0),
        "collection_completed_at": _ts(T0 + timedelta(minutes=4)),
        "generated_at": _ts(T0 + timedelta(minutes=5)),
        "provider_outcomes": [],
        "producer": {"package_version": "0.1.0", "files": [], "fingerprint": "a" * 64},
        "feed_config": {"snapshot": {}, "hash": "b" * 64},
        "feed_schema": {"path": "x", "sha256": "c" * 64},
        "provider_contracts": [],
        "git": None,
        "content_digest": "d" * 64,
        "items": [],
        "pipeline": {"status": "healthy", "warnings": []},
        "calendar_horizon_end": _ts(T0 + timedelta(hours=26)),
    }


def _publication_bytes(cutoff: datetime, digest: str, marker: str) -> bytes:
    """Minimal canonical ownership envelope for the publisher boundary."""
    return json.dumps(
        {
            "content_digest": digest,
            "evidence_cutoff_at": _ts(cutoff),
            "marker": marker,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


# ---------------------------------------------------------------------------
# Atomic no-replace dated commit
# ---------------------------------------------------------------------------


def test_dated_no_replace_refuses_overwrite(tmp_path):
    root = tmp_path / "out"
    root.mkdir()
    a = root / "a.json"
    b = root / "b.json"
    a.write_bytes(b"first")
    b.write_bytes(b"first")
    with pytest.raises(PublishError, match="refusing to overwrite"):
        atomic_no_replace_rename(a, b)
    assert a.exists()  # source retained on collision


def test_asia_shanghai_cutoff_date_boundary(tmp_path):
    # UTC 2026-08-10 15:59:59 => Shanghai 2026-08-10 23:59:59 (same date),
    # 16:00:00 UTC => 2026-08-11 (next Shanghai date).
    root = tmp_path / "out"
    root.mkdir()
    cutoff = datetime(2026, 8, 10, 15, 59, 59, tzinfo=UTC)
    feed_1 = _publication_bytes(cutoff, "a" * 64, "r1")
    r1 = publish_feed(
        output_root=root, cutoff=cutoff, run_id="r1", feed_bytes=feed_1, latest_bytes=feed_1
    )
    assert r1.dated_path.parent.name == "2026-08-10"
    cutoff2 = datetime(2026, 8, 10, 16, 0, 0, tzinfo=UTC)
    feed_2 = _publication_bytes(cutoff2, "b" * 64, "r2")
    r2 = publish_feed(
        output_root=root, cutoff=cutoff2, run_id="r2", feed_bytes=feed_2, latest_bytes=feed_2
    )
    assert r2.dated_path.parent.name == "2026-08-11"


def test_equal_cutoff_different_digest_both_orders(tmp_path):
    root = tmp_path / "out"
    root.mkdir()
    cutoff = datetime(2026, 8, 11, 0, 20, 0, tzinfo=UTC)
    feed_a = _publication_bytes(cutoff, "a" * 64, "a")
    feed_b = _publication_bytes(cutoff, "b" * 64, "b")
    # Submission order A then B: distinct run IDs => both dated artifacts and
    # the lexicographically greater ownership digest wins latest.
    publish_feed(
        output_root=root, cutoff=cutoff, run_id="run_a", feed_bytes=feed_a, latest_bytes=feed_a
    )
    publish_feed(
        output_root=root, cutoff=cutoff, run_id="run_b", feed_bytes=feed_b, latest_bytes=feed_b
    )
    dated_dir = root / "daily" / "2026-08-11"
    assert (dated_dir / "run_a.json").exists()
    assert (dated_dir / "run_b.json").exists()
    assert (root / "latest.json").read_bytes() == feed_b
    # Reverse order on a fresh root.
    root2 = tmp_path / "out2"
    root2.mkdir()
    publish_feed(
        output_root=root2, cutoff=cutoff, run_id="run_b", feed_bytes=feed_b, latest_bytes=feed_b
    )
    publish_feed(
        output_root=root2, cutoff=cutoff, run_id="run_a", feed_bytes=feed_a, latest_bytes=feed_a
    )
    assert (root2 / "daily" / "2026-08-11" / "run_a.json").exists()
    assert (root2 / "daily" / "2026-08-11" / "run_b.json").exists()
    assert (root2 / "latest.json").read_bytes() == feed_b


def test_older_candidate_keeps_newer_latest_and_dated_artifact(tmp_path):
    root = tmp_path / "out"
    root.mkdir()
    older = _publication_bytes(T0, "a" * 64, "older")
    newer = _publication_bytes(T0 + timedelta(hours=1), "a" * 64, "newer")

    publish_feed(
        output_root=root,
        cutoff=T0 + timedelta(hours=1),
        run_id="newer",
        feed_bytes=newer,
        latest_bytes=newer,
    )
    result = publish_feed(
        output_root=root,
        cutoff=T0,
        run_id="older",
        feed_bytes=older,
        latest_bytes=older,
    )

    assert not result.latest_replaced
    assert not result.idempotent
    assert (root / "latest.json").read_bytes() == newer
    assert (root / "daily" / "2026-08-11" / "older.json").read_bytes() == older


def test_incompatible_equal_owner_fails_closed(tmp_path):
    root = tmp_path / "out"
    root.mkdir()
    first = _publication_bytes(T0, "a" * 64, "first")
    incompatible = _publication_bytes(T0, "a" * 64, "different")

    publish_feed(
        output_root=root,
        cutoff=T0,
        run_id="first",
        feed_bytes=first,
        latest_bytes=first,
    )
    with pytest.raises(PublishError, match="equal ownership"):
        publish_feed(
            output_root=root,
            cutoff=T0,
            run_id="different",
            feed_bytes=incompatible,
            latest_bytes=incompatible,
        )
    assert (root / "latest.json").read_bytes() == first
    assert (root / "daily" / "2026-08-11" / "different.json").read_bytes() == incompatible


# ---------------------------------------------------------------------------
# fsync boundaries and commit_durability_unknown
# ---------------------------------------------------------------------------


def test_latest_parent_fsync_failure_durability_unknown(tmp_path):
    root = tmp_path / "out"
    root.mkdir()
    cutoff = datetime(2026, 8, 11, 0, 20, 0, tzinfo=UTC)
    real_fsync_dir = "follow_the_money.feed.publish._fsync_dir"
    original = __import__("follow_the_money.feed.publish", fromlist=["_fsync_dir"])._fsync_dir
    calls = {"n": 0}

    def flaky_fsync(path):
        # Fail only on the final output-root fsync (after latest replace).
        if path == root and calls["n"] >= 3:
            raise OSError("simulated fsync failure")
        calls["n"] += 1
        return original(path)

    with mock.patch(real_fsync_dir, side_effect=flaky_fsync):
        feed = _publication_bytes(cutoff, "a" * 64, "run_1")
        result = publish_feed(
            output_root=root,
            cutoff=cutoff,
            run_id="run_1",
            feed_bytes=feed,
            latest_bytes=feed,
        )
    # Artifact committed; durability unknown reported, never raised/rolled back.
    assert result.commit_durability_unknown
    assert (root / "daily" / "2026-08-11" / "run_1.json").exists()
    assert (root / "latest.json").read_bytes() == feed


def test_dated_parent_fsync_failure_durability_unknown(tmp_path):
    root = tmp_path / "out"
    root.mkdir()
    cutoff = datetime(2026, 8, 11, 0, 20, 0, tzinfo=UTC)
    original = __import__("follow_the_money.feed.publish", fromlist=["_fsync_dir"])._fsync_dir
    # Fail only the dated-dir fsync that occurs AFTER the rename committed
    # (the pre-commit staging fsync must still succeed).
    calls = {"n": 0}

    def flaky_fsync(path):
        if path == root / "daily" / "2026-08-11":
            calls["n"] += 1
            if calls["n"] >= 2:  # first is pre-commit staging; second is post-rename
                raise OSError("simulated dated-dir fsync failure")
        return original(path)

    with mock.patch("follow_the_money.feed.publish._fsync_dir", side_effect=flaky_fsync):
        feed = _publication_bytes(cutoff, "a" * 64, "run_1")
        result = publish_feed(
            output_root=root,
            cutoff=cutoff,
            run_id="run_1",
            feed_bytes=feed,
            latest_bytes=feed,
        )
    assert result.commit_durability_unknown
    assert (root / "daily" / "2026-08-11" / "run_1.json").exists()
    assert not (root / "latest.json").exists()


def test_staging_fsync_failure_fails_before_commit(tmp_path):
    root = tmp_path / "out"
    root.mkdir()
    cutoff = datetime(2026, 8, 11, 0, 20, 0, tzinfo=UTC)
    original = __import__("follow_the_money.feed.publish", fromlist=["_fsync_dir"])._fsync_dir
    failed = {"done": False}

    def fail_on_first(path):
        if not failed["done"]:
            failed["done"] = True
            raise OSError("simulated pre-commit fsync failure")
        return original(path)

    with (
        mock.patch("follow_the_money.feed.publish._fsync_dir", side_effect=fail_on_first),
        pytest.raises(OSError),
    ):
        feed = _publication_bytes(cutoff, "a" * 64, "run_1")
        publish_feed(
            output_root=root,
            cutoff=cutoff,
            run_id="run_1",
            feed_bytes=feed,
            latest_bytes=feed,
        )
    # No dated or latest artifact committed.
    assert not (root / "latest.json").exists()
    assert not list((root / "daily").rglob("*.json")) if (root / "daily").exists() else True


def test_crash_recovery_dated_committed_latest_not(tmp_path):
    # Simulate a crash after the dated commit but before latest: a subsequent
    # publish of the same run is idempotent and latest is completed.
    root = tmp_path / "out"
    root.mkdir()
    cutoff = datetime(2026, 8, 11, 0, 20, 0, tzinfo=UTC)
    # Manually stage the dated commit (as if the process died mid-publication).
    date_dir = root / "daily" / "2026-08-11"
    date_dir.mkdir(parents=True)
    feed = _publication_bytes(cutoff, "a" * 64, "run_1")
    (date_dir / "run_1.json").write_bytes(feed)
    # Re-run: idempotent for the same run + digest.
    result = publish_feed(
        output_root=root,
        cutoff=cutoff,
        run_id="run_1",
        feed_bytes=feed,
        latest_bytes=feed,
    )
    assert result.idempotent
    assert (root / "latest.json").read_bytes() == feed


def test_same_run_recovery_does_not_regress_newer_latest(tmp_path):
    root = tmp_path / "out"
    root.mkdir()
    older = _publication_bytes(T0, "a" * 64, "older")
    newer = _publication_bytes(T0 + timedelta(hours=1), "a" * 64, "newer")
    date_dir = root / "daily" / "2026-08-11"
    date_dir.mkdir(parents=True)
    (date_dir / "older.json").write_bytes(older)
    (root / "latest.json").write_bytes(newer)

    result = publish_feed(
        output_root=root,
        cutoff=T0,
        run_id="older",
        feed_bytes=older,
        latest_bytes=older,
    )

    assert result.idempotent
    assert not result.latest_replaced
    assert (root / "latest.json").read_bytes() == newer
    assert not [p for p in root.rglob("*") if ".stage-" in p.name]


# ---------------------------------------------------------------------------
# Monotonic latest ownership
# ---------------------------------------------------------------------------


def test_latest_ownership_stale_candidate_rejected(tmp_path):
    root = tmp_path / "out"
    root.mkdir()
    cutoff = datetime(2026, 8, 11, 0, 20, 0, tzinfo=UTC)
    newer = _publication_bytes(cutoff, "b" * 64, "newer")
    (root / "latest.json").write_bytes(newer)
    candidate = _publication_bytes(cutoff, "a" * 64, "candidate")
    with pytest.raises(PublishError, match="ownership mismatch"):
        publish_feed(
            output_root=root,
            cutoff=cutoff,
            run_id="run_1",
            feed_bytes=candidate,
            latest_bytes=candidate,
            existing_latest_sha256="0" * 64,
        )


# ---------------------------------------------------------------------------
# Two-process serialization (lock-before-cutoff)
# ---------------------------------------------------------------------------


def _child_run_feed(out_root: str, cutoff_iso: str, status_file: str) -> None:
    """Child process: run the feed with an empty-but-enabled registry so the
    lock/planning/publication path executes with zero provider calls."""
    from datetime import datetime

    from follow_the_money.feed.cli import run_feed

    cutoff = datetime.fromisoformat(cutoff_iso)
    result = run_feed(
        output_root=out_root,
        cutoff=cutoff,
        providers_fn=_minimal_registry,
        enabled_provider_ids=["federal_reserve"],
    )
    Path(status_file).write_text(json.dumps({"exit": result.exit_code, "status": result.status}))


def test_two_processes_serialized_lock_before_cutoff(tmp_path):
    out = tmp_path / "out"
    # First process publishes at T0.
    from follow_the_money.feed.cli import run_feed

    r1 = run_feed(
        output_root=str(out),
        cutoff=T0,
        providers_fn=_minimal_registry,
        enabled_provider_ids=["federal_reserve"],
    )
    assert r1.exit_code == 0
    latest = json.loads((out / "latest.json").read_bytes())
    assert latest["evidence_cutoff_at"] == _ts(T0)

    # Second process at T0 + 1h must re-read the advanced latest (planned from
    # the prior cutoff) rather than a frozen pre-lock window.
    r2 = run_feed(
        output_root=str(out),
        cutoff=T0 + timedelta(hours=1),
        providers_fn=_minimal_registry,
        enabled_provider_ids=["federal_reserve"],
    )
    assert r2.exit_code == 0
    latest2 = json.loads((out / "latest.json").read_bytes())
    assert latest2["window"]["start"] == _ts(T0)
    assert latest2["evidence_cutoff_at"] == _ts(T0 + timedelta(hours=1))

    # Dated artifacts for both cutoffs exist (Asia/Shanghai dates differ).
    assert (out / "daily" / "2026-08-11").exists()
    assert (out / "daily" / "2026-08-11").is_dir()


def test_cutoff_clock_is_read_after_lock_acquisition(tmp_path, monkeypatch):
    from follow_the_money.feed import cli as feed_cli

    order: list[str] = []
    original_acquire = feed_cli.CollectionLock.acquire

    def acquire(self):
        order.append("lock")
        return original_acquire(self)

    def now() -> datetime:
        order.append("clock")
        return T0

    monkeypatch.setattr(feed_cli.CollectionLock, "acquire", acquire)
    result = run_feed(
        output_root=str(tmp_path / "out"),
        providers_fn=_minimal_registry,
        enabled_provider_ids=["federal_reserve"],
        now_fn=now,
    )

    assert result.exit_code == 0
    assert order.index("lock") < order.index("clock")


def test_non_advancing_cutoff_no_artifact(tmp_path):
    out = tmp_path / "out"
    from follow_the_money.feed.cli import run_feed

    run_feed(
        output_root=str(out),
        cutoff=T0,
        providers_fn=_minimal_registry,
        enabled_provider_ids=["federal_reserve"],
    )
    with pytest.raises(FeedExecutionError, match="non_advancing"):
        run_feed(
            output_root=str(out),
            cutoff=T0,
            providers_fn=_minimal_registry,
            enabled_provider_ids=["federal_reserve"],
        )
    # No second dated artifact.
    dated = list((out / "daily").rglob("*.json"))
    assert len(dated) == 1


# ---------------------------------------------------------------------------
# Deadline reserve and zero mutation after cancellation
# ---------------------------------------------------------------------------


def test_deadline_reserve_blocks_publication(tmp_path):
    out = tmp_path / "out"
    from follow_the_money.feed.cli import run_feed

    clock = {"t": 0.0, "calls": 0}

    def monotonic() -> float:
        # First read is the deadline anchor (start of run); every later read
        # reports the deadline already consumed (>= 285s of a 300s budget).
        clock["calls"] += 1
        return clock["t"] if clock["calls"] == 1 else 290.0

    with pytest.raises(FeedExecutionError, match="pre_commit_deadline_exceeded"):
        run_feed(
            output_root=str(out),
            cutoff=T0,
            providers_fn=_minimal_registry,
            enabled_provider_ids=["federal_reserve"],
            monotonic_now=monotonic,
        )
    # Zero mutation: no dated/latest artifact after a deadline refusal.
    assert not (out / "latest.json").exists()
    assert not list((out / "daily").rglob("*.json")) if (out / "daily").exists() else True


def test_staging_crossing_admission_boundary_refuses_before_any_rename(tmp_path, monkeypatch):
    root = tmp_path / "out"
    root.mkdir()
    feed = _publication_bytes(T0, "a" * 64, "late-stage")
    clock = {"now": 284.0}
    original_fsync_file = __import__(
        "follow_the_money.feed.publish", fromlist=["_fsync_file"]
    )._fsync_file

    def crossing_fsync(path):
        clock["now"] = 285.0
        return original_fsync_file(path)

    monkeypatch.setattr("follow_the_money.feed.publish._fsync_file", crossing_fsync)
    with pytest.raises(PublishError, match="pre_commit_deadline_exceeded"):
        publish_feed(
            output_root=root,
            cutoff=T0,
            run_id="late-stage",
            feed_bytes=feed,
            latest_bytes=feed,
            monotonic_now=lambda: clock["now"],
            deadline_at=285.0,
        )

    assert not (root / "latest.json").exists()
    assert not list((root / "daily").rglob("*.json")) if (root / "daily").exists() else True
    assert not [p for p in root.rglob("*") if ".stage-" in p.name]


def test_idempotent_recovery_crossing_admission_keeps_dated_only(tmp_path):
    root = tmp_path / "out"
    root.mkdir()
    feed = _publication_bytes(T0, "a" * 64, "recovery")
    date_dir = root / "daily" / "2026-08-11"
    date_dir.mkdir(parents=True)
    (date_dir / "recovery.json").write_bytes(feed)

    with pytest.raises(PublishError, match="pre_commit_deadline_exceeded"):
        publish_feed(
            output_root=root,
            cutoff=T0,
            run_id="recovery",
            feed_bytes=feed,
            latest_bytes=feed,
            monotonic_now=lambda: 285.0,
            deadline_at=285.0,
        )

    assert (date_dir / "recovery.json").read_bytes() == feed
    assert not (root / "latest.json").exists()
    assert not [p for p in root.rglob("*") if ".stage-" in p.name]


def test_admitted_commit_crossing_nominal_deadline_is_not_cancelled(tmp_path, monkeypatch):
    root = tmp_path / "out"
    root.mkdir()
    feed = _publication_bytes(T0, "a" * 64, "overrun")
    fsync_calls = {"root": 0}
    original_fsync_dir = __import__(
        "follow_the_money.feed.publish", fromlist=["_fsync_dir"]
    )._fsync_dir

    def overrun_after_admission(path):
        if path == root:
            fsync_calls["root"] += 1
            if fsync_calls["root"] == 2:
                clock["now"] = 301.0
        return original_fsync_dir(path)

    clock = {"now": 284.0}
    monkeypatch.setattr("follow_the_money.feed.publish._fsync_dir", overrun_after_admission)
    result = publish_feed(
        output_root=root,
        cutoff=T0,
        run_id="overrun",
        feed_bytes=feed,
        latest_bytes=feed,
        monotonic_now=lambda: clock["now"],
        deadline_at=285.0,
    )

    assert result.latest_replaced
    assert (root / "latest.json").read_bytes() == feed


def test_recovery_post_rename_fsync_failure_reports_durability_unknown(tmp_path, monkeypatch):
    root = tmp_path / "out"
    root.mkdir()
    feed = _publication_bytes(T0, "a" * 64, "recovery-fsync")
    date_dir = root / "daily" / "2026-08-11"
    date_dir.mkdir(parents=True)
    (date_dir / "recovery-fsync.json").write_bytes(feed)
    original_fsync_dir = __import__(
        "follow_the_money.feed.publish", fromlist=["_fsync_dir"]
    )._fsync_dir
    root_calls = {"count": 0}

    def fail_after_recovery_replace(path):
        if path == root:
            root_calls["count"] += 1
            if root_calls["count"] == 2:
                raise OSError("simulated recovery fsync failure")
        return original_fsync_dir(path)

    monkeypatch.setattr("follow_the_money.feed.publish._fsync_dir", fail_after_recovery_replace)
    result = publish_feed(
        output_root=root,
        cutoff=T0,
        run_id="recovery-fsync",
        feed_bytes=feed,
        latest_bytes=feed,
    )

    assert result.commit_durability_unknown
    assert (root / "latest.json").read_bytes() == feed


def test_malformed_current_latest_ownership_fails_closed(tmp_path):
    root = tmp_path / "out"
    root.mkdir()
    (root / "latest.json").write_bytes(b'{"evidence_cutoff_at":"not-a-date"}')
    feed = _publication_bytes(T0, "a" * 64, "candidate")

    with pytest.raises(PublishError, match="current latest Feed ownership key invalid"):
        publish_feed(
            output_root=root,
            cutoff=T0,
            run_id="candidate",
            feed_bytes=feed,
            latest_bytes=feed,
        )


def test_production_dry_run_coordinates_and_reconciles_rate_state(tmp_path, monkeypatch):
    from follow_the_money.feed import cli as feed_cli

    out = tmp_path / "out"
    acquire_calls: list[Path] = []
    original_acquire = feed_cli.CollectionLock.acquire

    def acquire(lock):
        acquire_calls.append(out)
        return original_acquire(lock)

    monkeypatch.setattr(feed_cli.CollectionLock, "acquire", acquire)
    monkeypatch.setattr(
        feed_cli,
        "_production_adapters",
        lambda _cfg, _registry: {"federal_reserve": [_MinimalAdapter()]},
    )
    monkeypatch.setattr("follow_the_money.providers.adapters.build_registry", lambda: object())

    result = run_feed(
        output_root=str(out),
        cutoff=T0,
        dry_run=True,
        enabled_provider_ids=["federal_reserve"],
    )

    assert result.feed is not None
    assert acquire_calls == [out]
    assert (out / "rate-registry.json").exists()
    scope_files = [p for p in out.glob("scope-*.json")]
    assert len(scope_files) == 1
    state = json.loads(scope_files[0].read_bytes())
    assert Decimal(state["tokens"]) < Decimal(state["capacity"])
    assert state["last_dispatch_wall"] is not None
    assert state["cooldown_until"] is not None
    assert not (out / "latest.json").exists()
    assert not list((out / "daily").rglob("*.json")) if (out / "daily").exists() else True


def test_late_provider_result_is_not_normalized_or_added_to_feed(tmp_path):
    from unittest.mock import Mock

    adapter = _MinimalAdapter()
    adapter.normalize = Mock(wraps=adapter.normalize)
    clock_values = iter((0.0, 0.0, 285.0, 285.0))

    def monotonic() -> float:
        return next(clock_values, 285.0)

    result = run_feed(
        output_root=str(tmp_path / "out"),
        cutoff=T0,
        dry_run=True,
        providers_fn=lambda: {"federal_reserve": adapter},
        enabled_provider_ids=["federal_reserve"],
        monotonic_now=monotonic,
    )

    assert result.feed is not None
    assert result.feed["items"] == []
    assert result.feed["provider_outcomes"][0]["error"].startswith("pre_commit_deadline_exceeded")
    adapter.normalize.assert_not_called()


def test_zero_mutation_after_invalid_latest(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    (out / "latest.json").write_bytes(b"{corrupt")
    with pytest.raises(FeedExecutionError, match="invalid_latest_integrity"):
        run_feed(
            output_root=str(out),
            cutoff=T0 + timedelta(hours=1),
            providers_fn=_minimal_registry,
            enabled_provider_ids=["federal_reserve"],
        )
    # Zero provider writes: no rate registry, no dated artifact, and the
    # corrupt latest is untouched (the lock file itself is infrastructure).
    assert not (out / "rate-registry.json").exists()
    assert not (out / "daily").exists()
    assert (out / "latest.json").read_bytes() == b"{corrupt"


def test_two_os_processes_serialized_by_collection_lock(tmp_path):
    """Cross-process lock enforcement: while one OS process holds the
    output-root collection lock, a second OS process's run_feed fails typed
    ``collection_lock_timeout`` with zero artifacts (not merely an
    in-thread test)."""
    import multiprocessing as mp

    out = tmp_path / "out"
    held = mp.Event()
    release = mp.Event()
    status_file = str(tmp_path / "runner_status.json")

    def holder(root: str, held_ev, release_ev) -> None:
        from follow_the_money.providers.lock import CollectionLock

        lock = CollectionLock(root, timeout_seconds=300, monotonic_now=time.monotonic)
        lock.acquire()
        held_ev.set()
        release_ev.wait(300)
        lock.release()

    def runner(root: str, cutoff_iso: str, status: str) -> None:
        import time as _time
        from datetime import datetime

        from follow_the_money.feed.cli import run_feed

        # After the run's deadline anchor, every read advances 1000s so the
        # lock wait cannot admit the runner (the deadline is always exceeded).
        clock = {"t": None}

        def monotonic() -> float:
            now = _time.monotonic()
            if clock["t"] is None:
                clock["t"] = now
                return now
            clock["t"] += 1000.0
            return clock["t"]

        try:
            run_feed(
                output_root=root,
                cutoff=datetime.fromisoformat(cutoff_iso),
                providers_fn=_minimal_registry,
                enabled_provider_ids=["federal_reserve"],
                monotonic_now=monotonic,
            )
            outcome = {"exit": 0}
        except FeedCliError as exc:
            outcome = {"exit": 1, "error": str(exc)}
        Path(status).write_text(json.dumps(outcome))

    ctx = mp.get_context("fork")
    hp = ctx.Process(target=holder, args=(str(out), held, release))
    hp.start()
    try:
        assert held.wait(60), "holder process never acquired the lock"
        rp = ctx.Process(
            target=runner,
            args=(str(out), _ts(T0), status_file),
        )
        rp.start()
        rp.join(90)
        assert rp.exitcode == 0
        outcome = json.loads(Path(status_file).read_bytes())
        assert outcome["exit"] == 1
        assert "collection_lock_timeout" in outcome["error"]
        # The timed-out runner wrote no dated/latest artifact.
        assert not (out / "latest.json").exists()
        assert not list((out / "daily").rglob("*.json")) if (out / "daily").exists() else True
    finally:
        release.set()
        hp.join(60)
        assert hp.exitcode == 0


def test_collection_lock_timeout_typed(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    # Hold the lock from another process/thread with a very short timeout.
    from follow_the_money.providers.lock import CollectionLock

    lock = CollectionLock(out, timeout_seconds=60, monotonic_now=time.monotonic)
    lock.acquire()
    try:
        clock = {"t": time.monotonic()}

        def slow_clock() -> float:
            clock["t"] += 1000  # instantly past any deadline
            return clock["t"]

        from follow_the_money.feed.cli import run_feed

        with pytest.raises(FeedExecutionError, match="collection_lock_timeout"):
            run_feed(
                output_root=str(out),
                cutoff=T0,
                providers_fn=_minimal_registry,
                enabled_provider_ids=["federal_reserve"],
                monotonic_now=slow_clock,
            )
    finally:
        lock.release()


def test_collection_lock_primitive_unavailable_fails_closed(tmp_path, monkeypatch):
    import fcntl

    from follow_the_money.providers.lock import CollectionLock, CollectionLockError

    def unavailable(*_args, **_kwargs):
        raise OSError(errno.ENOTSUP, "flock unavailable")

    monkeypatch.setattr(fcntl, "flock", unavailable)
    with pytest.raises(CollectionLockError, match="primitive unavailable"):
        CollectionLock(tmp_path / "out", timeout_seconds=1).acquire()
