"""GitHub Actions contract tests for the hosted Feed deployment."""

from __future__ import annotations

import subprocess
from argparse import _SubParsersAction
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"


def _load(name: str) -> dict:
    path = WORKFLOWS / name
    assert path.exists(), f"missing workflow {name}"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _on(data: dict) -> dict:
    return data.get("on", data.get(True, {}))


def test_workflow_yaml_valid():
    for name in ("ci-quality-gate.yml", "generate-feed.yml"):
        data = _load(name)
        assert data["name"]
        assert "jobs" in data


def test_test_workflow_offline_only_and_generated_push_boundary():
    data = _load("ci-quality-gate.yml")
    text = yaml.safe_dump(data)
    assert "secrets:" not in text
    assert "OPENAI_API_KEY" not in text
    assert "openai" not in text
    assert "pytest" in text
    assert _on(data)["push"]["paths-ignore"] == [
        ".feed-state/.follow-the-money-persistent",
        ".feed-state/feed-checkpoint.json",
        ".feed-state/rate-registry.json",
        ".feed-state/scope-*.json",
        ".feed-state/feed-run-lease.json",
        "feeds/latest.json",
    ]
    assert "pull_request" in _on(data)


def test_feed_workflow_is_active_on_hosted_runner_and_schedule():
    data = _load("generate-feed.yml")
    job = data["jobs"]["generate"]
    assert job["runs-on"] == "ubuntu-latest"
    assert "if" not in job
    assert _on(data)["schedule"] == [{"cron": "20 0 * * *"}]
    assert "workflow_dispatch" in _on(data)
    assert data["permissions"] == {"contents": "write"}
    assert data["concurrency"] == {
        "group": "follow-the-money-feed",
        "cancel-in-progress": False,
    }


def test_feed_workflow_has_no_external_root_or_opt_in_contract():
    data = _load("generate-feed.yml")
    text = (WORKFLOWS / "generate-feed.yml").read_text(encoding="utf-8")
    assert "FOLLOW_THE_MONEY_FEED" not in text
    assert "FOLLOW_THE_MONEY_OUTPUT_ROOT" not in text
    assert "self-hosted" not in text
    assert data.get("env") in (None, {})


def test_feed_workflow_orders_static_preflight_lease_push_feed_and_finalization():
    data = _load("generate-feed.yml")
    text = (WORKFLOWS / "generate-feed.yml").read_text(encoding="utf-8")
    assert "follow_the_money.feed.deployment prepare" in text
    assert "--product-root feeds" in text
    assert "--runtime-state-root .feed-state" in text
    assert '--mode "${{ steps.prepare.outputs.mode }}"' in text
    assert "git push origin HEAD:main" in text
    assert "--force" not in text
    assert "git reset" not in text
    assert "always()" in text
    assert "steps.feed.outcome" in text
    steps = data["jobs"]["generate"]["steps"]
    publish = next(
        step for step in steps if step.get("name") == "Publish durable pre-network state"
    )
    collect = next(
        step for step in steps if step.get("name") == "Collect Feed after durable arming"
    )
    finalize = next(step for step in steps if step.get("name") == "Finalize exact deployment state")
    assert "steps.prepare.outputs.mode == 'migration'" in publish["if"]
    assert collect["if"] == "${{ steps.prepare.outputs.mode == 'armed' }}"
    assert finalize["if"] == "${{ always() && steps.prepare.outputs.mode == 'armed' }}"
    assert text.index("actions/checkout") < text.index("deployment prepare")
    assert text.index("deployment prepare") < text.index("git push origin HEAD:main")
    assert text.index("git push origin HEAD:main") < text.index("deployment collect")
    assert text.index("deployment collect") < text.index("deployment finalize")
    assert text.index("deployment finalize") < text.index("deployment diagnostics")
    assert text.index("deployment diagnostics") < text.index("Preserve original Feed failure")


def test_feed_workflow_diagnostics_is_failure_only_non_gating_and_keeps_exit_authority():
    data = _load("generate-feed.yml")
    steps = data["jobs"]["generate"]["steps"]
    diagnostics = next(step for step in steps if "diagnostics" in step.get("name", "").lower())
    restoration = next(
        step for step in steps if step.get("name") == "Preserve original Feed failure"
    )

    assert diagnostics["if"] == "${{ always() && steps.feed.outcome == 'failure' }}"
    assert diagnostics["continue-on-error"] is True
    assert "deployment diagnostics" in diagnostics["run"]
    assert "--status-file feed-status.json" in diagnostics["run"]
    assert '--summary-file "$GITHUB_STEP_SUMMARY"' in diagnostics["run"]
    assert "cat .feed-exit-code" in restoration["run"]
    assert 'exit "$exit_code"' in restoration["run"]


def test_feed_workflow_stages_only_generated_state():
    text = (WORKFLOWS / "generate-feed.yml").read_text(encoding="utf-8")
    assert "git add ." not in text
    assert "git add -A" not in text
    assert "git add feeds/" not in text
    assert "deployment publish" in text
    assert "deployment finalize" in text


def test_rate_scope_state_is_trackable_by_generated_state_commits():
    result = subprocess.run(
        ["git", "check-ignore", "--no-index", ".feed-state/scope-0123456789abcdef.json"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1, result.stdout
    legacy = subprocess.run(
        ["git", "check-ignore", "--no-index", "feeds/scope-0123456789abcdef.json"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert legacy.returncode == 0, legacy.stdout


def test_entry_points_referenced_exist():
    data = _load("ci-quality-gate.yml")
    text = yaml.safe_dump(data)
    assert "follow_the_money.feed.cli" in text
    from follow_the_money.feed.cli import _build_parser

    parser = _build_parser()
    actions = {action.dest for action in parser._actions}
    assert {"config", "output_root", "dry_run", "cutoff", "window_start", "status_file"} <= actions
    assert not any(isinstance(action, _SubParsersAction) for action in parser._actions)
