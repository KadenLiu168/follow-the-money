"""No-network tests for the repository-native Feed deployment boundary."""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from follow_the_money.config.model import RatePolicy
from follow_the_money.feed import deployment
from follow_the_money.feed.deployment import (
    DeploymentError,
    allowlisted_paths,
    assert_feed_admitted,
    finalize_deployment,
    prepare_deployment,
    publish_generated_state,
    read_lease,
)
from follow_the_money.providers.rate import RateRegistry

NOW = datetime(2026, 8, 29, 0, 0, tzinfo=UTC)


def _cfg(*policies: RatePolicy, cooldown_hours: int = 24):
    return SimpleNamespace(
        feed=SimpleNamespace(pre_commit_deadline_seconds=300),
        rate_registry=SimpleNamespace(
            version="1", schema_file="rate-registry.json", crash_cooldown_hours=cooldown_hours
        ),
        providers=tuple(SimpleNamespace(enabled=True, rate_policy=policy) for policy in policies),
    )


def _policy(scope_id: str = "scope-a", **changes: int) -> RatePolicy:
    values = {
        "scope_id": scope_id,
        "capacity": 10,
        "refill_period_seconds": 60,
        "minimum_interval_seconds": 5,
    }
    values.update(changes)
    return RatePolicy(**values)


def _clock(value: datetime):
    return lambda: value


def test_lease_parser_is_closed_and_versioned(tmp_path: Path):
    path = tmp_path / "feed-run-lease.json"
    path.write_text(
        json.dumps(
            {
                "version": "1",
                "deployment_run_id": "42-1",
                "state": "bootstrap",
                "armed_at": "2026-08-29T00:00:00Z",
                "finished_at": None,
                "feed_start_not_after": None,
                "recovery_not_before": "2026-08-30T00:00:00Z",
                "unexpected": True,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(DeploymentError, match="unknown lease fields"):
        read_lease(path)


def test_clean_bootstrap_establishes_zero_network_state(tmp_path: Path):
    result = prepare_deployment(
        tmp_path,
        _cfg(_policy()),
        deployment_run_id="42-1",
        now=_clock(NOW),
    )
    assert result.mode == "bootstrap"
    assert read_lease(tmp_path / "feed-run-lease.json").state == "bootstrap"
    registry = RateRegistry(tmp_path)
    assert registry.registry_path.exists()
    assert registry.recover_or_load("scope-a").tokens == "10"


def test_orphaned_scope_state_blocks_bootstrap_without_mutation(tmp_path: Path):
    orphan = tmp_path / "scope-0123456789abcdef.json"
    orphan.write_text("{}", encoding="utf-8")

    with pytest.raises(DeploymentError, match="partial deployment state"):
        prepare_deployment(
            tmp_path,
            _cfg(_policy()),
            deployment_run_id="42-1",
            now=_clock(NOW),
        )

    assert not (tmp_path / ".follow-the-money-persistent").exists()
    assert not (tmp_path / "rate-registry.json").exists()


def test_prepare_refreshes_repository_before_loading_authoritative_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    events: list[str] = []
    monkeypatch.setattr(deployment, "refresh_repository", lambda _repo: events.append("refresh"))

    from follow_the_money.feed import cli

    monkeypatch.setattr(cli, "_load_app_config", lambda _path: events.append("load") or _cfg())
    monkeypatch.setattr(
        deployment,
        "prepare_deployment",
        lambda *_args, **_kwargs: SimpleNamespace(mode="bootstrap"),
    )

    assert (
        deployment._command_prepare(
            SimpleNamespace(
                config=None,
                repo=str(tmp_path),
                root=str(tmp_path / "feeds"),
                run_id="42-1",
                output=None,
            )
        )
        == 0
    )
    assert events == ["refresh", "load"]


def test_bootstrap_before_quiet_boundary_blocks(tmp_path: Path):
    prepare_deployment(tmp_path, _cfg(_policy()), deployment_run_id="42-1", now=_clock(NOW))
    with pytest.raises(DeploymentError, match="recovery_not_before"):
        prepare_deployment(
            tmp_path,
            _cfg(_policy()),
            deployment_run_id="43-1",
            now=_clock(NOW + timedelta(hours=1)),
        )


def test_established_state_arms_after_boundary_with_conservative_bounds(tmp_path: Path):
    prepare_deployment(tmp_path, _cfg(_policy()), deployment_run_id="42-1", now=_clock(NOW))
    armed_at = NOW + timedelta(hours=24)
    result = prepare_deployment(
        tmp_path,
        _cfg(_policy()),
        deployment_run_id="43-1",
        now=_clock(armed_at),
    )
    lease = read_lease(tmp_path / "feed-run-lease.json")
    assert result.mode == "armed"
    assert lease.state == "in_progress"
    assert lease.feed_start_not_after == armed_at + timedelta(seconds=300)
    assert lease.recovery_not_before == armed_at + timedelta(seconds=300 + 300 + 24 * 3600)


def test_missing_or_corrupt_established_state_fails_closed(tmp_path: Path):
    prepare_deployment(tmp_path, _cfg(_policy()), deployment_run_id="42-1", now=_clock(NOW))
    (tmp_path / "rate-registry.json").unlink()
    with pytest.raises(DeploymentError):
        prepare_deployment(
            tmp_path, _cfg(_policy()), deployment_run_id="43-1", now=_clock(NOW + timedelta(days=2))
        )


@pytest.mark.parametrize(
    ("scope_payload", "replacement"),
    [
        (None, []),
        ("tokens", "not-a-number"),
        ("refill_wall_anchor", "not-a-timestamp"),
    ],
)
def test_corrupt_scope_state_fails_as_typed_deployment_error(
    tmp_path: Path, scope_payload: str | None, replacement: object
):
    result = prepare_deployment(
        tmp_path, _cfg(_policy()), deployment_run_id="42-1", now=_clock(NOW)
    )
    scope_path = next(path for path in result.paths if path.name.startswith("scope-"))
    payload = json.loads(scope_path.read_text(encoding="utf-8"))
    if scope_payload is None:
        payload = replacement
    else:
        payload[scope_payload] = replacement
    scope_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(DeploymentError):
        prepare_deployment(
            tmp_path,
            _cfg(_policy()),
            deployment_run_id="43-1",
            now=_clock(NOW + timedelta(days=2)),
        )


def test_new_scope_uses_rate_registry_first_use_before_arming(tmp_path: Path):
    cfg = _cfg(_policy())
    prepare_deployment(tmp_path, cfg, deployment_run_id="42-1", now=_clock(NOW))
    next_run = NOW + timedelta(days=1)
    result = prepare_deployment(
        tmp_path,
        _cfg(_policy(), _policy("scope-b")),
        deployment_run_id="43-1",
        now=_clock(next_run),
    )
    assert result.mode == "armed"
    assert RateRegistry(tmp_path).recover_or_load("scope-b").tokens == "10"


def test_recovery_rejects_resolved_policy_outside_envelope_without_provider_ids(tmp_path: Path):
    prepare_deployment(tmp_path, _cfg(_policy()), deployment_run_id="42-1", now=_clock(NOW))
    with pytest.raises(DeploymentError, match="recovery envelope"):
        prepare_deployment(
            tmp_path,
            _cfg(_policy(refill_period_seconds=24 * 3600 + 1)),
            deployment_run_id="43-1",
            now=_clock(NOW + timedelta(days=1)),
        )


def test_missed_feed_start_bound_blocks_admission(tmp_path: Path):
    prepare_deployment(tmp_path, _cfg(_policy()), deployment_run_id="42-1", now=_clock(NOW))
    armed_at = NOW + timedelta(days=1)
    prepare_deployment(tmp_path, _cfg(_policy()), deployment_run_id="43-1", now=_clock(armed_at))
    with pytest.raises(DeploymentError, match="feed_start_not_after"):
        assert_feed_admitted(
            tmp_path,
            deployment_run_id="43-1",
            now=armed_at + timedelta(seconds=301),
        )


def test_in_progress_recovery_blocks_before_and_allows_after_boundary(tmp_path: Path):
    prepare_deployment(tmp_path, _cfg(_policy()), deployment_run_id="42-1", now=_clock(NOW))
    armed_at = NOW + timedelta(days=1)
    prepare_deployment(tmp_path, _cfg(_policy()), deployment_run_id="43-1", now=_clock(armed_at))
    recovery = armed_at + timedelta(seconds=300 + 300 + 24 * 3600)
    with pytest.raises(DeploymentError, match="recovery_not_before"):
        prepare_deployment(
            tmp_path,
            _cfg(_policy()),
            deployment_run_id="44-1",
            now=_clock(recovery - timedelta(seconds=1)),
        )
    assert (
        prepare_deployment(
            tmp_path,
            _cfg(_policy()),
            deployment_run_id="44-1",
            now=_clock(recovery),
        ).mode
        == "armed"
    )


def test_terminal_lease_does_not_delay_next_daily_run(tmp_path: Path):
    prepare_deployment(tmp_path, _cfg(_policy()), deployment_run_id="42-1", now=_clock(NOW))
    first_run = NOW + timedelta(days=1)
    prepare_deployment(tmp_path, _cfg(_policy()), deployment_run_id="43-1", now=_clock(first_run))
    finalize_deployment(
        tmp_path,
        deployment_run_id="43-1",
        feed_succeeded=False,
        status_path=tmp_path / "unused-status.json",
        now=_clock(first_run + timedelta(seconds=1)),
    )

    assert (
        prepare_deployment(
            tmp_path,
            _cfg(_policy()),
            deployment_run_id="44-1",
            now=_clock(first_run + timedelta(days=1)),
        ).mode
        == "armed"
    )


def test_success_and_failure_finalization_keep_exact_paths(tmp_path: Path):
    prepare_deployment(tmp_path, _cfg(_policy()), deployment_run_id="42-1", now=_clock(NOW))
    armed_at = NOW + timedelta(days=1)
    prepare_deployment(tmp_path, _cfg(_policy()), deployment_run_id="43-1", now=_clock(armed_at))
    (tmp_path / "daily/2026-08-30").mkdir(parents=True)
    (tmp_path / "daily/2026-08-30/feed-1.json").write_bytes(b"dated")
    (tmp_path / "latest.json").write_bytes(b"latest")
    status = tmp_path / "feed-status.json"
    status.write_text(
        json.dumps(
            {
                "status": "healthy",
                "run_id": "feed-1",
                "evidence_cutoff_at": "2026-08-30T00:20:00Z",
                "dated_relative_path": "daily/2026-08-30/feed-1.json",
                "latest_relative_path": "latest.json",
            }
        ),
        encoding="utf-8",
    )
    paths = finalize_deployment(
        tmp_path,
        deployment_run_id="43-1",
        feed_succeeded=True,
        status_path=status,
        now=_clock(armed_at + timedelta(seconds=1)),
    )
    assert {path.name for path in paths} >= {"feed-run-lease.json", "latest.json"}
    assert read_lease(tmp_path / "feed-run-lease.json").state == "success"

    prepare_deployment(
        tmp_path,
        _cfg(_policy()),
        deployment_run_id="44-1",
        now=_clock(armed_at + timedelta(days=2)),
    )
    failure_paths = finalize_deployment(
        tmp_path,
        deployment_run_id="44-1",
        feed_succeeded=False,
        status_path=status,
        now=_clock(armed_at + timedelta(days=2, seconds=1)),
    )
    assert all(path.name not in {"latest.json", "feed-1.json"} for path in failure_paths)
    assert read_lease(tmp_path / "feed-run-lease.json").state == "failure"


def test_source_completeness_failure_finalization_preserves_status_and_allowlist(
    tmp_path: Path,
):
    prepare_deployment(tmp_path, _cfg(_policy()), deployment_run_id="42-1", now=_clock(NOW))
    armed_at = NOW + timedelta(days=1)
    prepare_deployment(tmp_path, _cfg(_policy()), deployment_run_id="43-1", now=_clock(armed_at))
    status = tmp_path / "feed-status.json"
    payload = {
        "status": "failure",
        "warnings": [
            "source incomplete: provider_id=bls state=failed error=provider unavailable",
        ],
    }
    status.write_text(json.dumps(payload), encoding="utf-8")

    paths = finalize_deployment(
        tmp_path,
        deployment_run_id="43-1",
        feed_succeeded=False,
        status_path=status,
        now=_clock(armed_at + timedelta(seconds=1)),
    )

    assert json.loads(status.read_text(encoding="utf-8")) == payload
    assert set(paths) == set(allowlisted_paths(tmp_path))
    assert read_lease(tmp_path / "feed-run-lease.json").state == "failure"
    assert not (tmp_path / "latest.json").exists()
    assert not (tmp_path / "daily").exists()


def test_success_finalization_rejects_non_feed_status_paths(tmp_path: Path):
    result = prepare_deployment(
        tmp_path, _cfg(_policy()), deployment_run_id="42-1", now=_clock(NOW)
    )
    scope_path = next(path for path in result.paths if path.name.startswith("scope-"))
    armed_at = NOW + timedelta(days=1)
    prepare_deployment(tmp_path, _cfg(_policy()), deployment_run_id="43-1", now=_clock(armed_at))
    (tmp_path / "daily/2026-08-30").mkdir(parents=True)
    (tmp_path / "daily/2026-08-30/feed-1.json").write_bytes(b"dated")
    status = tmp_path / "feed-status.json"
    status.write_text(
        json.dumps(
            {
                "status": "healthy",
                "run_id": "feed-1",
                "evidence_cutoff_at": "2026-08-30T00:20:00Z",
                "dated_relative_path": "daily/2026-08-30/feed-1.json",
                "latest_relative_path": scope_path.name,
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(DeploymentError, match="latest_relative_path"):
        finalize_deployment(
            tmp_path,
            deployment_run_id="43-1",
            feed_succeeded=True,
            status_path=status,
            now=_clock(armed_at + timedelta(seconds=1)),
        )


def test_finalization_keeps_in_progress_when_exact_rate_state_is_missing(tmp_path: Path):
    result = prepare_deployment(
        tmp_path, _cfg(_policy()), deployment_run_id="42-1", now=_clock(NOW)
    )
    armed_at = NOW + timedelta(days=1)
    prepare_deployment(tmp_path, _cfg(_policy()), deployment_run_id="43-1", now=_clock(armed_at))
    next(path for path in result.paths if path.name.startswith("scope-")).unlink()

    with pytest.raises(DeploymentError, match="missing/partial"):
        finalize_deployment(
            tmp_path,
            deployment_run_id="43-1",
            feed_succeeded=False,
            status_path=tmp_path / "unused-status.json",
            now=_clock(armed_at + timedelta(seconds=1)),
        )

    assert read_lease(tmp_path / "feed-run-lease.json").state == "in_progress"


def test_git_publication_is_non_force_and_stages_only_allowlist(tmp_path: Path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    (tmp_path / "feeds").mkdir()
    (tmp_path / "feeds/feed-run-lease.json").write_text("{}", encoding="utf-8")
    (tmp_path / "unrelated.txt").write_text("do not stage", encoding="utf-8")
    subprocess.run(["git", "add", "feeds/feed-run-lease.json"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=tmp_path, check=True)
    (tmp_path / "feeds/feed-run-lease.json").write_text('{"state":"success"}', encoding="utf-8")
    calls: list[list[str]] = []

    def git(args: list[str]) -> str:
        calls.append(args)
        if args[:2] == ["push", "origin"]:
            raise DeploymentError("push conflict")
        completed = subprocess.run(
            ["git", *args], cwd=tmp_path, check=True, text=True, capture_output=True
        )
        return completed.stdout

    with pytest.raises(DeploymentError, match="push conflict"):
        publish_generated_state(
            tmp_path,
            [tmp_path / "feeds/feed-run-lease.json"],
            message="feeds: arm",
            git=git,
        )
    committed = subprocess.run(
        ["git", "show", "--format=", "--name-only", "HEAD"],
        cwd=tmp_path,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.splitlines()
    assert committed == ["feeds/feed-run-lease.json"]
    assert (
        not (tmp_path / "unrelated.txt").exists()
        or (tmp_path / "unrelated.txt").read_text() == "do not stage"
    )
    assert all("--force" not in call for call in calls)
