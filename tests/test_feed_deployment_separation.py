"""Focused deployment regressions for separate product and runtime roots."""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from follow_the_money.canonical import canonical_bytes
from follow_the_money.config.model import RatePolicy
from follow_the_money.feed import deployment
from follow_the_money.feed.bundle import build_bundle
from follow_the_money.feed.checkpoint import (
    FeedCheckpoint,
    PreviousSuccess,
    read_checkpoint,
    write_checkpoint,
)
from follow_the_money.feed.deployment import (
    DeploymentError,
    DeploymentLease,
    _migration_allowlisted_paths,
    allowlisted_paths,
    finalize_deployment,
    prepare_deployment,
    publish_generated_state,
    read_lease,
    write_lease,
)
from follow_the_money.feed.publish import publish_bundle
from follow_the_money.feed.validate import recompute_feed_identity
from follow_the_money.providers.rate import RateRegistry

NOW = datetime(2026, 8, 29, 0, 0, tzinfo=UTC)


def _policy(scope_id: str = "scope-a") -> RatePolicy:
    return RatePolicy(
        scope_id=scope_id,
        capacity=10,
        refill_period_seconds=60,
        minimum_interval_seconds=5,
    )


def _cfg(*policies: RatePolicy, cooldown_hours: int = 24):
    return SimpleNamespace(
        feed=SimpleNamespace(pre_commit_deadline_seconds=300),
        rate_registry=SimpleNamespace(
            version="1", schema_file="rate-registry.json", crash_cooldown_hours=cooldown_hours
        ),
        providers=tuple(SimpleNamespace(enabled=True, rate_policy=policy) for policy in policies),
    )


def _lease(
    state: str = "bootstrap",
    *,
    run_id: str = "old-run",
    armed_at: datetime = NOW,
    feed_start: datetime | None = None,
    recovery: datetime | None = None,
) -> DeploymentLease:
    return DeploymentLease(
        version="1",
        deployment_run_id=run_id,
        state=state,
        armed_at=armed_at,
        finished_at=None,
        feed_start_not_after=feed_start,
        recovery_not_before=recovery or armed_at + timedelta(hours=24),
    )


def _legacy_state(product_root: Path, cfg, lease: DeploymentLease | None = None) -> RateRegistry:
    registry = RateRegistry(product_root)
    registry.ensure_registry(now=lambda: NOW)
    policy = cfg.providers[0].rate_policy
    registry.initialize_scope(
        policy.scope_id,
        policy.capacity,
        policy.refill_period_seconds,
        policy.minimum_interval_seconds,
        now=lambda: NOW,
    )
    write_lease(product_root / "feed-run-lease.json", lease or _lease())
    return registry


def _healthy_feed(cutoff: str = "2026-08-28T00:00:00.000Z") -> dict:
    feed = {
        "schema_version": 1,
        "run_id": "",
        "window": {"start": "2026-08-25T00:00:00.000Z", "end": cutoff},
        "collection_started_at": "2026-08-27T23:59:00.000Z",
        "evidence_cutoff_at": cutoff,
        "collection_completed_at": "2026-08-28T00:01:00.000Z",
        "generated_at": "2026-08-28T00:02:00.000Z",
        "provider_outcomes": [],
        "producer": {"package_version": "0.1.0", "files": [], "fingerprint": "a" * 64},
        "feed_config": {"snapshot": {}, "hash": "b" * 64},
        "feed_schema": {"path": "schemas/feed.schema.json", "sha256": "c" * 64},
        "provider_contracts": [],
        "git": None,
        "content_digest": "",
        "items": [],
        "pipeline": {"status": "healthy", "warnings": []},
    }
    digest, run_id = recompute_feed_identity(feed)
    feed["content_digest"] = digest
    feed["run_id"] = run_id
    return feed


def test_clean_bootstrap_uses_explicit_runtime_root(tmp_path: Path):
    product_root = tmp_path / "feeds"
    state_root = tmp_path / ".feed-state"
    result = prepare_deployment(
        product_root,
        state_root,
        _cfg(_policy()),
        deployment_run_id="new-run",
        now=lambda: NOW,
    )

    assert result.mode == "bootstrap"
    assert (state_root / ".follow-the-money-persistent").exists()
    assert (state_root / "rate-registry.json").exists()
    assert (state_root / "feed-checkpoint.json").exists()
    assert read_lease(state_root / "feed-run-lease.json").state == "bootstrap"
    assert not (product_root / "rate-registry.json").exists()


def test_deployment_rejects_one_path_used_as_both_product_and_runtime_root(tmp_path: Path):
    shared_root = tmp_path / "feeds"

    with pytest.raises(DeploymentError, match="must be distinct"):
        prepare_deployment(
            shared_root,
            shared_root,
            _cfg(_policy()),
            deployment_run_id="new-run",
            now=lambda: NOW,
        )

    assert not shared_root.exists()


def test_established_state_missing_checkpoint_fails_without_bootstrap(tmp_path: Path):
    product_root = tmp_path / "feeds"
    state_root = tmp_path / ".feed-state"
    prepare_deployment(
        product_root, state_root, _cfg(_policy()), deployment_run_id="first", now=lambda: NOW
    )
    checkpoint = state_root / "feed-checkpoint.json"
    checkpoint.unlink()
    marker = (state_root / ".follow-the-money-persistent").read_bytes()

    with pytest.raises(DeploymentError, match="checkpoint"):
        prepare_deployment(
            product_root,
            state_root,
            _cfg(_policy()),
            deployment_run_id="second",
            now=lambda: NOW + timedelta(days=2),
        )

    assert not checkpoint.exists()
    assert (state_root / ".follow-the-money-persistent").read_bytes() == marker


def test_corrupt_established_registry_is_a_typed_preflight_failure(tmp_path: Path):
    product_root = tmp_path / "feeds"
    state_root = tmp_path / ".feed-state"
    prepare_deployment(
        product_root, state_root, _cfg(_policy()), deployment_run_id="first", now=lambda: NOW
    )
    (state_root / "rate-registry.json").write_bytes(b"{corrupt")

    with pytest.raises(DeploymentError, match="rate registry"):
        prepare_deployment(
            product_root,
            state_root,
            _cfg(_policy()),
            deployment_run_id="second",
            now=lambda: NOW + timedelta(days=2),
        )


def test_new_runtime_legacy_product_uses_migration_only(tmp_path: Path):
    product_root = tmp_path / "feeds"
    state_root = tmp_path / ".feed-state"
    cfg = _cfg(_policy())
    prepare_deployment(
        product_root, state_root, cfg, deployment_run_id="bootstrap", now=lambda: NOW
    )
    feed = _healthy_feed()
    latest = product_root / "latest.json"
    latest.parent.mkdir(parents=True, exist_ok=True)
    latest.write_bytes(canonical_bytes(feed))
    write_checkpoint(
        state_root / "feed-checkpoint.json",
        FeedCheckpoint(
            previous_success=PreviousSuccess(
                evidence_cutoff_at=feed["evidence_cutoff_at"], run_id=feed["run_id"]
            )
        ),
    )
    checkpoint_bytes = (state_root / "feed-checkpoint.json").read_bytes()

    result = prepare_deployment(
        product_root,
        state_root,
        cfg,
        deployment_run_id="migration-run",
        now=lambda: NOW + timedelta(days=2),
    )

    assert result.mode == "migration"
    assert (product_root / "feed-manifest.json").is_file()
    assert latest.read_bytes() == canonical_bytes(feed)
    assert (state_root / "feed-checkpoint.json").read_bytes() == checkpoint_bytes


def test_complete_legacy_migration_preserves_state_and_seeds_checkpoint(tmp_path: Path):
    product_root = tmp_path / "feeds"
    state_root = tmp_path / ".feed-state"
    cfg = _cfg(_policy())
    registry = _legacy_state(product_root, cfg)
    old_scope = registry.scope_path("scope-a").read_bytes()
    old_lease = (product_root / "feed-run-lease.json").read_bytes()
    old_registry = json.loads(registry.registry_path.read_bytes())
    feed = _healthy_feed()
    latest = product_root / "latest.json"
    latest.parent.mkdir(parents=True, exist_ok=True)
    latest.write_bytes(canonical_bytes(feed))
    daily = product_root / "daily/2026-08-28/old.json"
    daily.parent.mkdir(parents=True)
    daily.write_bytes(b"product")

    result = prepare_deployment(
        product_root,
        state_root,
        cfg,
        deployment_run_id="migration-run",
        now=lambda: NOW + timedelta(days=2),
    )

    assert result.mode == "migration"
    assert (state_root / "feed-run-lease.json").read_bytes() == old_lease
    assert (state_root / registry.scope_path("scope-a").name).read_bytes() == old_scope
    new_registry = json.loads((state_root / "rate-registry.json").read_bytes())
    assert {key: value for key, value in new_registry.items() if key != "root_identity"} == {
        key: value for key, value in old_registry.items() if key != "root_identity"
    }
    assert new_registry["root_identity"] == str(state_root.resolve())
    checkpoint = read_checkpoint(state_root / "feed-checkpoint.json")
    assert checkpoint.previous_success is not None
    assert checkpoint.previous_success.run_id == feed["run_id"]
    assert latest.exists() and daily.read_bytes() == b"product"
    for name in (
        ".follow-the-money-persistent",
        "rate-registry.json",
        "feed-run-lease.json",
    ):
        assert not (product_root / name).exists()
    assert not registry.scope_path("scope-a").exists()


def test_legacy_without_latest_seeds_null_without_scanning_daily(tmp_path: Path):
    product_root = tmp_path / "feeds"
    state_root = tmp_path / ".feed-state"
    cfg = _cfg(_policy())
    _legacy_state(product_root, cfg)
    dated = product_root / "daily/2026-08-28/old.json"
    dated.parent.mkdir(parents=True)
    dated.write_bytes(canonical_bytes(_healthy_feed()))

    prepare_deployment(
        product_root,
        state_root,
        cfg,
        deployment_run_id="migration-run",
        now=lambda: NOW + timedelta(days=2),
    )

    assert read_checkpoint(state_root / "feed-checkpoint.json").previous_success is None


def test_mixed_layout_fails_before_mutating_either_root(tmp_path: Path):
    product_root = tmp_path / "feeds"
    state_root = tmp_path / ".feed-state"
    cfg = _cfg(_policy())
    _legacy_state(product_root, cfg)
    state_root.mkdir()
    (state_root / "feed-checkpoint.json").write_text("{}", encoding="utf-8")

    with pytest.raises(DeploymentError, match="mixed"):
        prepare_deployment(
            product_root,
            state_root,
            cfg,
            deployment_run_id="migration-run",
            now=lambda: NOW + timedelta(days=2),
        )

    assert (product_root / "rate-registry.json").exists()
    assert not (state_root / "rate-registry.json").exists()


def test_invalid_legacy_latest_blocks_migration_without_new_state(tmp_path: Path):
    product_root = tmp_path / "feeds"
    state_root = tmp_path / ".feed-state"
    cfg = _cfg(_policy())
    _legacy_state(product_root, cfg)
    (product_root / "latest.json").write_bytes(b"{invalid")

    with pytest.raises(DeploymentError, match="latest"):
        prepare_deployment(
            product_root,
            state_root,
            cfg,
            deployment_run_id="migration-run",
            now=lambda: NOW + timedelta(days=2),
        )

    assert not state_root.exists()
    assert (product_root / "rate-registry.json").exists()


def test_migration_preserves_in_progress_recovery_bounds(tmp_path: Path):
    product_root = tmp_path / "feeds"
    state_root = tmp_path / ".feed-state"
    feed_start = NOW + timedelta(minutes=5)
    recovery = NOW + timedelta(days=3)
    old = _lease(
        "in_progress",
        run_id="incomplete-run",
        feed_start=feed_start,
        recovery=recovery,
    )
    _legacy_state(product_root, _cfg(_policy()), old)

    result = prepare_deployment(
        product_root,
        state_root,
        _cfg(_policy()),
        deployment_run_id="migration-run",
        now=lambda: NOW + timedelta(days=1),
    )

    assert result.mode == "migration"
    relocated = read_lease(state_root / "feed-run-lease.json")
    assert relocated.deployment_run_id == old.deployment_run_id
    assert relocated.feed_start_not_after == old.feed_start_not_after
    assert relocated.recovery_not_before == old.recovery_not_before
    with pytest.raises(DeploymentError, match="recovery_not_before"):
        prepare_deployment(
            product_root,
            state_root,
            _cfg(_policy()),
            deployment_run_id="next-run",
            now=lambda: NOW + timedelta(days=2),
        )


def test_migration_publication_stages_legacy_deletion_with_the_bundle(tmp_path: Path, monkeypatch):
    product_root = tmp_path / "feeds"
    state_root = tmp_path / ".feed-state"
    cfg = _cfg(_policy())
    _legacy_state(product_root, cfg, _lease(run_id="legacy-run"))
    feed = _healthy_feed()
    latest = product_root / "latest.json"
    latest.write_bytes(canonical_bytes(feed))
    result = prepare_deployment(
        product_root,
        state_root,
        cfg,
        deployment_run_id="current-run",
        now=lambda: NOW + timedelta(days=2),
    )
    published: list[Path] = []
    monkeypatch.setattr(
        deployment,
        "publish_generated_state",
        lambda _repo, paths, **_kwargs: published.extend(paths),
    )

    assert (
        deployment._command_publish(
            SimpleNamespace(
                product_root=str(product_root),
                runtime_state_root=str(state_root),
                mode=result.mode,
                run_id="current-run",
                repo=str(tmp_path),
            )
        )
        == 0
    )
    assert latest in published
    assert not latest.exists()
    assert product_root / "feed-manifest.json" in published


def test_failure_finalization_excludes_checkpoint_and_products(tmp_path: Path):
    product_root = tmp_path / "feeds"
    state_root = tmp_path / ".feed-state"
    cfg = _cfg(_policy())
    prepare_deployment(
        product_root,
        state_root,
        cfg,
        deployment_run_id="first",
        now=lambda: NOW,
    )
    prepare_deployment(
        product_root,
        state_root,
        cfg,
        deployment_run_id="second",
        now=lambda: NOW + timedelta(days=2),
    )
    checkpoint = state_root / "feed-checkpoint.json"
    checkpoint.write_bytes(checkpoint.read_bytes() + b"\n")

    paths = finalize_deployment(
        product_root,
        state_root,
        deployment_run_id="second",
        feed_succeeded=False,
        status_path=tmp_path / "feed-status.json",
        now=lambda: NOW + timedelta(days=2, seconds=1),
    )

    assert checkpoint not in paths
    assert all(path.parent != product_root for path in paths)
    assert read_lease(state_root / "feed-run-lease.json").state == "failure"
    assert not (product_root / "latest.json").exists()
    assert checkpoint.exists()


def test_success_finalization_requires_and_publishes_matching_checkpoint(tmp_path: Path):
    product_root = tmp_path / "feeds"
    state_root = tmp_path / ".feed-state"
    cfg = _cfg(_policy())
    prepare_deployment(product_root, state_root, cfg, deployment_run_id="first", now=lambda: NOW)
    armed_at = NOW + timedelta(days=2)
    prepare_deployment(
        product_root, state_root, cfg, deployment_run_id="second", now=lambda: armed_at
    )
    feed = _healthy_feed()
    product_root.mkdir(parents=True)
    bundle = build_bundle(feed)
    publish_bundle(
        output_root=product_root,
        bundle=bundle,
        cutoff=datetime.fromisoformat(feed["evidence_cutoff_at"]),
        run_id=feed["run_id"],
    )
    manifest = product_root / "feed-manifest.json"
    status = tmp_path / "feed-status.json"
    status.write_text(
        json.dumps(
            {
                "status": "healthy",
                "run_id": feed["run_id"],
                "evidence_cutoff_at": feed["evidence_cutoff_at"],
                "manifest_relative_path": "feed-manifest.json",
            }
        ),
        encoding="utf-8",
    )
    checkpoint = state_root / "feed-checkpoint.json"
    write_checkpoint(
        checkpoint,
        FeedCheckpoint(
            previous_success=PreviousSuccess(
                evidence_cutoff_at=feed["evidence_cutoff_at"],
                run_id=feed["run_id"],
            )
        ),
    )

    paths = finalize_deployment(
        product_root,
        state_root,
        deployment_run_id="second",
        feed_succeeded=True,
        status_path=status,
        now=lambda: armed_at + timedelta(seconds=1),
    )

    assert checkpoint in paths
    assert paths.count(manifest) == 1
    assert all(path.parent != product_root / "daily" for path in paths)
    assert read_lease(state_root / "feed-run-lease.json").state == "success"


def test_success_finalization_rejects_invalid_latest_product(tmp_path: Path):
    product_root = tmp_path / "feeds"
    state_root = tmp_path / ".feed-state"
    cfg = _cfg(_policy())
    prepare_deployment(product_root, state_root, cfg, deployment_run_id="first", now=lambda: NOW)
    armed_at = NOW + timedelta(days=2)
    prepare_deployment(
        product_root, state_root, cfg, deployment_run_id="second", now=lambda: armed_at
    )
    feed = _healthy_feed()
    product_root.mkdir(parents=True)
    (product_root / "latest.json").write_bytes(b"not a Feed")
    status = tmp_path / "feed-status.json"
    status.write_text(
        json.dumps(
            {
                "status": "healthy",
                "run_id": feed["run_id"],
                "evidence_cutoff_at": feed["evidence_cutoff_at"],
                "manifest_relative_path": "feed-manifest.json",
            }
        ),
        encoding="utf-8",
    )
    write_checkpoint(
        state_root / "feed-checkpoint.json",
        FeedCheckpoint(
            previous_success=PreviousSuccess(
                evidence_cutoff_at=feed["evidence_cutoff_at"], run_id=feed["run_id"]
            )
        ),
    )

    with pytest.raises(DeploymentError, match="manifest_relative_path"):
        finalize_deployment(
            product_root,
            state_root,
            deployment_run_id="second",
            feed_succeeded=True,
            status_path=status,
            now=lambda: armed_at + timedelta(seconds=1),
        )


def test_generic_allowlist_excludes_checkpoint(tmp_path: Path):
    state_root = tmp_path / ".feed-state"
    prepare_deployment(
        tmp_path / "feeds",
        state_root,
        _cfg(_policy()),
        deployment_run_id="first",
        now=lambda: NOW,
    )
    assert state_root / "feed-checkpoint.json" not in allowlisted_paths(state_root)


def test_migration_git_allowlist_contains_only_new_state_and_old_deletions(tmp_path: Path):
    product_root = tmp_path / "feeds"
    state_root = tmp_path / ".feed-state"
    cfg = _cfg(_policy())
    _legacy_state(product_root, cfg)
    latest = product_root / "latest.json"
    latest.parent.mkdir(parents=True, exist_ok=True)
    latest.write_bytes(canonical_bytes(_healthy_feed()))
    dated = product_root / "daily/2026-08-28/old.json"
    dated.parent.mkdir(parents=True)
    dated.write_bytes(b"product")
    unrelated = tmp_path / "unrelated.txt"
    unrelated.write_text("keep", encoding="utf-8")

    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "--all"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=tmp_path, check=True)
    transient = tmp_path / "feed-status.json"
    transient.write_text("transient", encoding="utf-8")

    prepare_deployment(
        product_root,
        state_root,
        cfg,
        deployment_run_id="migration-run",
        now=lambda: NOW + timedelta(days=2),
    )
    reconstructed = _migration_allowlisted_paths(product_root, state_root)
    scope_name = RateRegistry(state_root).scope_path("scope-a").name
    assert product_root / scope_name in reconstructed
    calls: list[list[str]] = []

    def git(args: list[str]) -> str:
        calls.append(args)
        if args[:2] == ["push", "origin"]:
            return ""
        completed = subprocess.run(
            ["git", *args], cwd=tmp_path, check=True, text=True, capture_output=True
        )
        return completed.stdout

    publish_generated_state(tmp_path, reconstructed, message="feeds: migration", git=git)
    expected = sorted(str(path.resolve().relative_to(tmp_path.resolve())) for path in reconstructed)
    add_call = next(args for args in calls if args[:2] == ["add", "--"])
    assert add_call[2:] == expected
    assert unrelated.read_text(encoding="utf-8") == "keep"
    assert transient.read_text(encoding="utf-8") == "transient"
    assert latest.exists() and dated.read_bytes() == b"product"
    assert all("--force" not in args for args in calls)
