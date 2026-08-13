"""Validate the repository's GitHub Actions contracts without contacting GitHub."""

from __future__ import annotations

import shutil
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import yaml


def workflow_publication_mapping(
    *, output_root: Path, repository_root: Path, feed_status: dict[str, Any]
) -> dict[str, Path]:
    """Resolve the exact two Feed paths staged by ``generate-feed.yml``."""
    run_id = feed_status.get("run_id")
    cutoff = feed_status.get("evidence_cutoff_at")
    if not isinstance(run_id, str) or not run_id:
        raise ValueError("feed status missing run_id")
    if not isinstance(cutoff, str) or len(cutoff) < 10:
        raise ValueError("feed status missing evidence_cutoff_at")
    day = cutoff[:10]
    return {
        "dated_source": output_root / "daily" / day / f"{run_id}.json",
        "dated_destination": repository_root / "feeds" / "daily" / day / f"{run_id}.json",
        "latest_source": output_root / "latest.json",
        "latest_destination": repository_root / "feeds" / "latest.json",
    }


def stage_workflow_artifacts(
    *,
    output_root: Path,
    repository_root: Path,
    feed_status: dict[str, Any],
    copy_fn=shutil.copyfile,
) -> dict[str, Path]:
    """Behavioral model of the workflow's explicit staging step.

    ``copy_fn`` is injectable so tests can prove a partial publication failure
    without contacting GitHub or mutating any unrelated repository path.
    """
    paths = workflow_publication_mapping(
        output_root=Path(output_root),
        repository_root=Path(repository_root),
        feed_status=feed_status,
    )
    for key in ("dated_source", "latest_source"):
        source = paths[key]
        if not source.is_file() or source.stat().st_size == 0:
            raise ValueError(f"workflow source missing or empty: {source}")
    paths["dated_destination"].parent.mkdir(parents=True, exist_ok=True)
    copy_fn(paths["dated_source"], paths["dated_destination"])
    paths["latest_destination"].parent.mkdir(parents=True, exist_ok=True)
    copy_fn(paths["latest_source"], paths["latest_destination"])
    if paths["dated_source"].read_bytes() != paths["dated_destination"].read_bytes():
        raise ValueError("dated Feed staging verification failed")
    if paths["latest_source"].read_bytes() != paths["latest_destination"].read_bytes():
        raise ValueError("latest Feed staging verification failed")
    return paths


def _load(path: Path) -> tuple[dict[str, Any], str]:
    try:
        text = path.read_text(encoding="utf-8")
        data = yaml.safe_load(text)
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"cannot load workflow {path}: {exc}") from exc
    if not isinstance(data, dict) or not data.get("name") or "jobs" not in data:
        raise ValueError(f"invalid workflow structure: {path}")
    return data, text


def workflow_execution_plan(
    feed_data: dict[str, Any],
    feed_text: str,
    *,
    opt_in: str | None,
    runner_labels: Sequence[str] = (),
    output_root_exists: bool = False,
    persistence_marker: bool = False,
    rate_registry: bool = False,
) -> dict[str, bool]:
    """Model which Feed steps are reachable for a declared deployment state.

    This is deliberately a small reachability model, not a second YAML
    interpreter. ``validate_repository_workflows`` proves the step ordering;
    this function proves the default-false and preflight-failure boundaries
    with executable behavior-oriented tests.
    """
    job = feed_data.get("jobs", {}).get("generate")
    job_gate = (
        isinstance(job, dict) and job.get("if") == "${{ vars.FOLLOW_THE_MONEY_FEED == 'true' }}"
    )
    job_started = bool(job_gate and opt_in == "true")
    runner_ready = "follow-the-money-feed" in runner_labels
    persistent_ready = output_root_exists and persistence_marker and rate_registry
    capability_ready = runner_ready and persistent_ready
    return {
        "job_started": job_started,
        "persistent_capability_checks": job_started,
        "checkout": job_started and capability_ready,
        "provider_requests": job_started and capability_ready,
        "credential_access": job_started and capability_ready and "OPENAI_API_KEY" in feed_text,
        "output_root_access": job_started,
    }


def validate_repository_workflows(
    repo_root: Path,
    *,
    generate_feed_path: Path | None = None,
) -> None:
    repo_root = Path(repo_root)
    test_path = repo_root / ".github" / "workflows" / "test.yml"
    feed_path = generate_feed_path or repo_root / ".github" / "workflows" / "generate-feed.yml"
    _test_data, test_text = _load(test_path)
    feed_data, feed_text = _load(feed_path)

    if "OPENAI_API_KEY" in test_text or "pytest" not in test_text:
        raise ValueError("hosted test workflow must remain credential-free and run pytest")
    job = feed_data.get("jobs", {}).get("generate")
    if not isinstance(job, dict):
        raise TypeError("Feed workflow is missing generate job")
    if job.get("if") != "${{ vars.FOLLOW_THE_MONEY_FEED == 'true' }}":
        raise ValueError("Feed workflow opt-in gate must use the job-if vars context")
    if job.get("runs-on") != ["self-hosted", "follow-the-money-feed"]:
        raise ValueError("Feed workflow must require the dedicated self-hosted label")
    if "cancel-in-progress: false" not in feed_text:
        raise ValueError("Feed workflow must be non-cancelling")

    checkout_index = feed_text.find("actions/checkout")
    steps = job.get("steps", [])
    if not steps or not isinstance(steps[0], dict) or "run" not in steps[0]:
        raise ValueError("persistence/rate-state guard must be the first Feed step")
    guard = str(steps[0]["run"])
    if "FOLLOW_THE_MONEY_OUTPUT_ROOT" not in guard or ".follow-the-money-persistent" not in guard:
        raise ValueError("Feed workflow is missing persistent-root guard")
    if "rate-registry.json" not in guard:
        raise ValueError("Feed workflow is missing durable rate-state guard")
    if checkout_index < 0 or feed_text.find("rate-registry.json") > checkout_index:
        raise ValueError("durable capability checks must precede checkout")
    if "clean: true" in feed_text:
        raise ValueError("Feed workflow must not destructively clean the persistent root")
    if "git add feeds/daily/" in feed_text or "git add ." in feed_text or "git add -A" in feed_text:
        raise ValueError("Feed workflow staging must use an explicit allowlist")
    for required in (
        'cp -- "$DATED_SOURCE" "$DATED_DEST"',
        'cp -- "$OUTPUT_ROOT/latest.json" feeds/latest.json',
        'git add -- "$DATED_DEST" feeds/latest.json',
    ):
        if required not in feed_text:
            raise ValueError(f"Feed workflow is missing explicit publication mapping: {required}")
    if "git push" not in feed_text:
        raise ValueError("Feed workflow must expose Git publication failure")


def main() -> int:
    try:
        validate_repository_workflows(Path(__file__).resolve().parents[1])
    except ValueError as exc:
        print(f"workflow contract invalid: {exc}", file=sys.stderr)
        return 1
    print("workflow contracts valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
