"""Validate repository-specific GitHub Actions contracts without GitHub access."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

GENERATED_PATHS = [
    ".feed-state/.follow-the-money-persistent",
    ".feed-state/feed-checkpoint.json",
    ".feed-state/rate-registry.json",
    ".feed-state/scope-*.json",
    ".feed-state/feed-run-lease.json",
    "feeds/latest.json",
    "feeds/daily/**/*.json",
]


def _load(path: Path) -> tuple[dict[str, Any], str]:
    try:
        text = path.read_text(encoding="utf-8")
        data = yaml.safe_load(text)
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"cannot load workflow {path}: {exc}") from exc
    if not isinstance(data, dict) or not data.get("name") or "jobs" not in data:
        raise ValueError(f"invalid workflow structure: {path}")
    return data, text


def _on(data: dict[str, Any]) -> dict[str, Any]:
    value = data.get("on")
    if value is None:
        value = next((item for key, item in data.items() if key is True), None)
    if not isinstance(value, dict):
        raise TypeError("workflow triggers must be a mapping")
    return value


def _require_order(text: str, *needles: str) -> None:
    positions = [text.find(needle) for needle in needles]
    if any(position < 0 for position in positions):
        missing = [needle for needle, position in zip(needles, positions) if position < 0]
        raise ValueError(f"workflow is missing required text: {missing}")
    if positions != sorted(positions):
        raise ValueError(f"workflow steps are out of order: {needles}")


def validate_repository_workflows(
    repo_root: Path,
    *,
    generate_feed_path: Path | None = None,
    test_workflow_path: Path | None = None,
) -> None:
    repo_root = Path(repo_root)
    test_path = test_workflow_path or repo_root / ".github" / "workflows" / "test.yml"
    feed_path = generate_feed_path or repo_root / ".github" / "workflows" / "generate-feed.yml"
    test_data, test_text = _load(test_path)
    feed_data, feed_text = _load(feed_path)

    test_on = _on(test_data)
    push = test_on.get("push")
    if not isinstance(push, dict) or push.get("paths-ignore") != GENERATED_PATHS:
        raise ValueError("test workflow paths-ignore must match generated-state allowlist")
    if "pull_request" not in test_on:
        raise ValueError("test workflow must retain pull_request trigger")
    if "OPENAI_API_KEY" in test_text or "pytest" not in test_text:
        raise ValueError("hosted test workflow must remain credential-free and run pytest")
    if (
        "actionlint" not in test_text
        or "invalid-workflow-level-runner-context.yml" not in test_text
    ):
        raise ValueError("test workflow must keep actionlint and invalid-context fixture checks")

    feed_on = _on(feed_data)
    if feed_on.get("schedule") != [{"cron": "20 0 * * *"}] or "workflow_dispatch" not in feed_on:
        raise ValueError(
            "Feed workflow must use the 08:20 Asia/Shanghai schedule and manual dispatch"
        )
    if feed_data.get("permissions") != {"contents": "write"}:
        raise ValueError("Feed workflow must request contents: write")
    if feed_data.get("concurrency") != {
        "group": "follow-the-money-feed",
        "cancel-in-progress": False,
    }:
        raise ValueError("Feed workflow must use non-cancelling concurrency")

    job = feed_data.get("jobs", {}).get("generate")
    if not isinstance(job, dict):
        raise TypeError("Feed workflow is missing generate job")
    if job.get("runs-on") != "ubuntu-latest" or "if" in job:
        raise ValueError("Feed workflow must use a hosted runner without opt-in")
    steps = job.get("steps")
    if not isinstance(steps, list):
        raise TypeError("Feed workflow steps must be a list")

    def step_named(name: str) -> dict[str, Any]:
        for step in steps:
            if isinstance(step, dict) and step.get("name") == name:
                return step
        raise ValueError(f"Feed workflow is missing {name!r} step")

    publish_step = step_named("Publish durable pre-network state")
    if publish_step.get("if") != (
        "${{ steps.prepare.outputs.mode == 'bootstrap' || "
        "steps.prepare.outputs.mode == 'migration' || steps.prepare.outputs.mode == 'armed' }}"
    ):
        raise ValueError(
            "Feed pre-network publication must include migration/bootstrap/armed modes"
        )
    collect_step = step_named("Collect Feed after durable arming")
    if collect_step.get("if") != "${{ steps.prepare.outputs.mode == 'armed' }}":
        raise ValueError("Feed collection must be armed-only")
    finalize_step = step_named("Finalize exact deployment state")
    if finalize_step.get("if") != "${{ always() && steps.prepare.outputs.mode == 'armed' }}":
        raise ValueError("Feed finalization must follow the armed collection path")
    diagnostics = [
        step
        for step in steps
        if isinstance(step, dict) and "diagnostics" in str(step.get("name", "")).lower()
    ]
    if len(diagnostics) != 1:
        raise ValueError("Feed workflow must define one failure diagnostics step")
    diagnostics_step = diagnostics[0]
    if diagnostics_step.get("if") != "${{ always() && steps.feed.outcome == 'failure' }}":
        raise ValueError("Feed diagnostics must be failure-only and always-run")
    if diagnostics_step.get("continue-on-error") is not True:
        raise ValueError("Feed diagnostics must be non-gating")
    diagnostics_run = diagnostics_step.get("run")
    if not isinstance(diagnostics_run, str) or any(
        value not in diagnostics_run
        for value in (
            "deployment diagnostics",
            "--status-file feed-status.json",
            '--summary-file "$GITHUB_STEP_SUMMARY"',
        )
    ):
        raise ValueError("Feed diagnostics must use only the private renderer inputs")
    for value, message in (
        ("FOLLOW_THE_MONEY_FEED", "opt-in"),
        ("FOLLOW_THE_MONEY_OUTPUT_ROOT", "external root"),
        ("self-hosted", "hosted runner"),
        ("--force", "force"),
        ("git reset", "reset"),
        ("git add .", "allowlist"),
        ("git add -A", "allowlist"),
    ):
        if value in feed_text:
            raise ValueError(f"Feed workflow contains forbidden {message} operation")
    if "git add feeds/" in feed_text:
        raise ValueError("Feed workflow staging must use an explicit allowlist")
    if "deployment publish --phase pre" not in feed_text and "git add ." in feed_text:
        raise ValueError("Feed workflow staging must use an explicit allowlist")
    for value in ("--product-root feeds", "--runtime-state-root .feed-state"):
        if value not in feed_text:
            raise ValueError(f"Feed workflow must pass explicit {value}")
    _require_order(
        feed_text,
        "actions/checkout",
        "follow_the_money.feed.deployment prepare",
        "deployment publish --phase pre",
        "deployment collect",
        "deployment finalize",
        "deployment diagnostics",
        "Preserve original Feed failure",
    )
    if "always()" not in feed_text or "steps.feed.outcome" not in feed_text:
        raise ValueError("Feed workflow must finalize always and preserve Feed failure")
    if "HEAD:main" not in feed_text:
        raise ValueError("Feed workflow must publish only to main with a normal fast-forward push")
    if "cat .feed-exit-code" not in feed_text or 'exit "$exit_code"' not in feed_text:
        raise ValueError("Feed workflow must preserve the .feed-exit-code authority")


def main() -> int:
    try:
        validate_repository_workflows(Path(__file__).resolve().parents[1])
    except (TypeError, ValueError) as exc:
        print(f"workflow contract invalid: {exc}", file=sys.stderr)
        return 1
    print("workflow contracts valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
