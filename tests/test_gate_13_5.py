"""Gate 13.5 — real golden-day fixtures and offline replay validation."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from follow_the_money.eval_offline import (
    GoldenDatasetError,
    load_golden_dataset,
    run_offline_evaluation,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DATASET = REPO_ROOT / "evals" / "dataset"


def test_offline_runner_replays_recorded_fixture_outputs_by_default():
    aggregate, violations = run_offline_evaluation(DATASET)

    assert violations == []
    assert aggregate.metrics["recall_at_10"].denominator >= 30
    assert aggregate.metrics["unsupported_claim_rate"].numerator == 0
    assert aggregate.metrics["causal_overclaim_rate"].numerator == 0


def test_missing_fixture_reference_fails_before_scoring(tmp_path):
    manifest = json.loads((DATASET / "manifest.json").read_bytes())
    manifest["days"][0]["feed"] = "feeds/missing.json"
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(GoldenDatasetError, match="fixture missing"):
        load_golden_dataset(tmp_path)


def test_fixture_feed_identity_and_output_cross_reference_are_checked(tmp_path):
    manifest = json.loads((DATASET / "manifest.json").read_bytes())
    first = manifest["days"][0]
    feed_source = DATASET / first["feed"]
    output_source = DATASET / first["outputs"]
    feed_dir = tmp_path / "feeds"
    output_dir = tmp_path / "outputs"
    feed_dir.mkdir()
    output_dir.mkdir()
    feed = json.loads(feed_source.read_bytes())
    output = json.loads(output_source.read_bytes())
    output["feed_run_id"] = "tampered"
    (feed_dir / "one.json").write_bytes(json.dumps(feed).encode("utf-8"))
    (output_dir / "one.json").write_bytes(json.dumps(output).encode("utf-8"))
    first["feed"] = "feeds/one.json"
    first["outputs"] = "outputs/one.json"
    manifest["days"] = [first]
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(GoldenDatasetError, match="feed_run_id"):
        load_golden_dataset(tmp_path)


def test_offline_cli_replays_and_writes_machine_readable_evidence(tmp_path):
    report = tmp_path / "offline-report.json"
    completed = subprocess.run(
        [".venv/bin/follow-the-money", "eval", "--mode", "offline", "--output", str(report)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(report.read_bytes())
    assert payload["days"] >= 30
    assert payload["metrics"]["recall_at_10"]["denominator"] >= 30
    assert "evidence" in completed.stdout.lower()


def test_offline_cli_day_filter_evaluates_only_selected_fixture(tmp_path):
    report = tmp_path / "offline-report.json"
    completed = subprocess.run(
        [
            ".venv/bin/follow-the-money",
            "eval",
            "--mode",
            "offline",
            "--day",
            "2024-03-20",
            "--output",
            str(report),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(report.read_bytes())
    assert payload["days"] == 1
    assert payload["metrics"]["recall_at_10"]["denominator"] == 2
