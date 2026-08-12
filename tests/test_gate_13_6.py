"""Gate 13.6 — executable workflow and publication contract checks."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts.validate_workflows import (
    stage_workflow_artifacts,
    validate_repository_workflows,
    workflow_execution_plan,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_workflow_validator_is_executable():
    validate_repository_workflows(REPO_ROOT)
    completed = subprocess.run(
        [".venv/bin/python", "scripts/validate_workflows.py"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "valid" in completed.stdout.lower()


def test_feed_workflow_checks_durable_rate_state_before_checkout():
    text = (REPO_ROOT / ".github/workflows/generate-feed.yml").read_text()
    assert "if: ${{ vars.FOLLOW_THE_MONEY_FEED == 'true' }}" in text
    assert "if: ${{ env.FEED_OPT_IN == 'true' }}" not in text
    assert "rate-registry.json" in text
    assert text.index("rate-registry.json") < text.index("actions/checkout")
    assert "feeds/daily/ ||" not in text
    assert 'git add -- "$DATED_DEST" feeds/latest.json' in text
    assert 'cp -- "$DATED_SOURCE" "$DATED_DEST"' in text
    assert 'cp -- "$OUTPUT_ROOT/latest.json" feeds/latest.json' in text


def test_default_false_workflow_gate_blocks_all_restricted_access():
    import yaml

    workflow_path = REPO_ROOT / ".github/workflows/generate-feed.yml"
    feed_data = yaml.safe_load(workflow_path.read_text())
    plan = workflow_execution_plan(
        feed_data,
        workflow_path.read_text(),
        opt_in=None,
        runner_labels=("self-hosted", "follow-the-money-feed"),
        output_root_exists=True,
        persistence_marker=True,
        rate_registry=True,
    )
    assert plan == {
        "job_started": False,
        "persistent_capability_checks": False,
        "checkout": False,
        "provider_requests": False,
        "credential_access": False,
        "output_root_access": False,
    }


def test_true_workflow_requires_capabilities_before_provider_requests():
    import yaml

    workflow_path = REPO_ROOT / ".github/workflows/generate-feed.yml"
    feed_data = yaml.safe_load(workflow_path.read_text())
    blocked = workflow_execution_plan(
        feed_data,
        workflow_path.read_text(),
        opt_in="true",
        runner_labels=("self-hosted", "follow-the-money-feed"),
        output_root_exists=True,
        persistence_marker=True,
        rate_registry=False,
    )
    assert blocked["job_started"] is True
    assert blocked["persistent_capability_checks"] is True
    assert blocked["checkout"] is False
    assert blocked["provider_requests"] is False

    allowed = workflow_execution_plan(
        feed_data,
        workflow_path.read_text(),
        opt_in="true",
        runner_labels=("self-hosted", "follow-the-money-feed"),
        output_root_exists=True,
        persistence_marker=True,
        rate_registry=True,
    )
    assert allowed["checkout"] is True
    assert allowed["provider_requests"] is True
    assert allowed["credential_access"] is False


def test_workflow_validator_rejects_broad_staging(tmp_path):
    workflow = REPO_ROOT / ".github/workflows/generate-feed.yml"
    altered = tmp_path / "generate-feed.yml"
    altered.write_text(
        workflow.read_text().replace(
            'git add -- "$DATED_DEST" feeds/latest.json', "git add feeds/daily/"
        )
    )
    try:
        validate_repository_workflows(REPO_ROOT, generate_feed_path=altered)
    except ValueError as exc:
        assert "allowlist" in str(exc)
    else:
        raise AssertionError("broad workflow staging was accepted")


def test_workflow_validator_rejects_job_if_env_context(tmp_path):
    workflow = REPO_ROOT / ".github/workflows/generate-feed.yml"
    altered = tmp_path / "generate-feed.yml"
    altered.write_text(
        workflow.read_text().replace(
            "if: ${{ vars.FOLLOW_THE_MONEY_FEED == 'true' }}",
            "if: ${{ env.FEED_OPT_IN == 'true' }}",
        )
    )
    with pytest.raises(ValueError, match="vars context"):
        validate_repository_workflows(REPO_ROOT, generate_feed_path=altered)


def test_workflow_publication_maps_only_run_scoped_paths(tmp_path):
    output_root = tmp_path / "persistent"
    repo_root = tmp_path / "checkout"
    dated = output_root / "daily" / "2026-08-11" / "run-1.json"
    latest = output_root / "latest.json"
    dated.parent.mkdir(parents=True)
    output_root.mkdir(exist_ok=True)
    dated.write_bytes(b"dated-feed")
    latest.write_bytes(b"latest-feed")

    paths = stage_workflow_artifacts(
        output_root=output_root,
        repository_root=repo_root,
        feed_status={"run_id": "run-1", "evidence_cutoff_at": "2026-08-11T00:20:00Z"},
    )

    assert paths["dated_destination"].read_bytes() == b"dated-feed"
    assert paths["latest_destination"].read_bytes() == b"latest-feed"
    assert sorted(str(p.relative_to(repo_root)) for p in repo_root.rglob("*")) == [
        "feeds",
        "feeds/daily",
        "feeds/daily/2026-08-11",
        "feeds/daily/2026-08-11/run-1.json",
        "feeds/latest.json",
    ]


def test_workflow_publication_failure_is_observable(tmp_path):
    output_root = tmp_path / "persistent"
    repo_root = tmp_path / "checkout"
    dated = output_root / "daily" / "2026-08-11" / "run-1.json"
    dated.parent.mkdir(parents=True)
    output_root.mkdir(exist_ok=True)
    dated.write_bytes(b"dated-feed")
    (output_root / "latest.json").write_bytes(b"latest-feed")
    calls = {"count": 0}

    def fail_on_latest(source, destination):
        calls["count"] += 1
        if calls["count"] == 2:
            raise OSError("simulated latest staging failure")
        return __import__("shutil").copyfile(source, destination)

    with pytest.raises(OSError, match="simulated latest staging failure"):
        stage_workflow_artifacts(
            output_root=output_root,
            repository_root=repo_root,
            feed_status={"run_id": "run-1", "evidence_cutoff_at": "2026-08-11T00:20:00Z"},
            copy_fn=fail_on_latest,
        )
    assert (repo_root / "feeds/daily/2026-08-11/run-1.json").is_file()
    assert not (repo_root / "feeds/latest.json").exists()
