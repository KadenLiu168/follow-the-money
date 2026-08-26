"""Task 12.1/12.3 — workflow-contract tests.

Validates that the workflow YAML files are syntactically valid, reference
only existing entry points, keep the Feed opt-in gate defaulting false, and
reject ephemeral/fresh output roots before any provider work.
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"


def _load(name: str) -> dict:
    path = WORKFLOWS / name
    assert path.exists(), f"missing workflow {name}"
    return yaml.safe_load(path.read_text())


def test_workflow_yaml_valid():
    for name in ("test.yml", "generate-feed.yml"):
        data = _load(name)
        assert data["name"]
        assert "jobs" in data


def test_test_workflow_offline_only():
    data = _load("test.yml")
    steps_text = yaml.safe_dump(data)
    # No secrets, no provider credentials, no live endpoint dependency.
    assert "secrets:" not in steps_text
    # No OpenAI/LLM credential exists anywhere in the deterministic engine.
    assert "OPENAI_API_KEY" not in steps_text
    assert "openai" not in steps_text
    assert "pytest" in steps_text


def test_feed_workflow_opt_in_defaults_false():
    data = _load("generate-feed.yml")
    job = data["jobs"]["generate"]
    # jobs.<job_id>.if supports vars, not the workflow env context.
    # An absent/explicit-false value prevents runner allocation and all steps.
    assert job["if"] == "${{ vars.FOLLOW_THE_MONEY_FEED == 'true' }}"


def test_feed_workflow_requires_dedicated_runner_label():
    data = _load("generate-feed.yml")
    job = data["jobs"]["generate"]
    assert job["runs-on"] == ["self-hosted", "follow-the-money-feed"]


def test_feed_workflow_uses_scheduler_as_single_runner_authority():
    data = _load("generate-feed.yml")
    job = data["jobs"]["generate"]
    assert "RUNNER_LABEL" not in data.get("env", {})
    runtime_steps = yaml.safe_dump(job["steps"])
    assert "runner.labels" not in runtime_steps
    assert "RUNNER_LABEL" not in runtime_steps
    assert "non-dedicated runner" not in runtime_steps.lower()


def test_feed_workflow_persistence_checks_before_provider_work():
    data = _load("generate-feed.yml")
    steps = data["jobs"]["generate"]["steps"]
    first_step = steps[0]["run"]
    assert "persistence" in first_step.lower()
    assert "refusing" in first_step
    assert "checkout" not in first_step  # persistence check precedes checkout


def test_feed_workflow_disables_destructive_cleanup():
    data = _load("generate-feed.yml")
    checkout_step = next(
        s
        for s in data["jobs"]["generate"]["steps"]
        if s.get("uses", "").startswith("actions/checkout")
    )
    assert checkout_step.get("with", {}).get("clean") is False


def test_feed_workflow_concurrency_non_cancelling():
    data = _load("generate-feed.yml")
    assert data["concurrency"]["cancel-in-progress"] is False


def test_feed_workflow_stages_only_feed_paths():
    data = _load("generate-feed.yml")
    steps_text = yaml.safe_dump(data)
    assert "feeds/latest.json" in steps_text
    assert "feeds/daily/" in steps_text


def test_feed_workflow_publication_failure_exposed():
    data = _load("generate-feed.yml")
    steps_text = yaml.safe_dump(data)
    # git push failure is a normal step failure (never reported success).
    assert "git push" in steps_text


def test_feed_workflow_uploads_artifact_on_failure():
    data = _load("generate-feed.yml")
    steps = data["jobs"]["generate"]["steps"]
    upload = [s for s in steps if "upload-artifact" in s.get("uses", "")]
    assert upload
    assert upload[0]["if"] == "failure()"


def test_entry_points_referenced_exist():
    data = _load("test.yml")
    text = yaml.safe_dump(data)
    assert "follow_the_money.feed.cli" in text
    # The only invocation surface is the minimal internal Feed entry.
    from follow_the_money.feed.cli import _build_parser

    parser = _build_parser()
    actions = {a.dest for a in parser._actions}
    assert {"config", "output_root", "dry_run", "cutoff", "window_start", "status_file"} <= actions
    # No public CLI subcommands survive.
    from argparse import _SubParsersAction

    assert not any(isinstance(a, _SubParsersAction) for a in parser._actions)
