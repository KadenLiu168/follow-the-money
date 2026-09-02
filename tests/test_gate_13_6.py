"""Executable hosted Feed workflow contract checks."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.validate_workflows import validate_repository_workflows

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_workflow_validator_is_executable():
    validate_repository_workflows(REPO_ROOT)


@pytest.mark.parametrize(
    ("needle", "replacement", "message"),
    [
        ("runs-on: ubuntu-latest", "runs-on: self-hosted", "hosted runner"),
        ("git push origin HEAD:main", "git push --force origin HEAD:main", "force"),
        ("deployment publish --phase pre", "git add .", "allowlist"),
    ],
)
def test_workflow_validator_rejects_deployment_contract_breaks(
    tmp_path: Path, needle: str, replacement: str, message: str
):
    workflow = REPO_ROOT / ".github/workflows/generate-feed.yml"
    altered = tmp_path / "generate-feed.yml"
    altered.write_text(workflow.read_text(encoding="utf-8").replace(needle, replacement))
    with pytest.raises(ValueError, match=message):
        validate_repository_workflows(REPO_ROOT, generate_feed_path=altered)


def test_workflow_validator_rejects_collection_for_migration_mode(tmp_path: Path):
    workflow = REPO_ROOT / ".github/workflows/generate-feed.yml"
    altered = tmp_path / "generate-feed.yml"
    text = workflow.read_text(encoding="utf-8").replace(
        "if: ${{ steps.prepare.outputs.mode == 'armed' }}",
        "if: ${{ steps.prepare.outputs.mode == 'armed' || steps.prepare.outputs.mode == 'migration' }}",
        1,
    )
    altered.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="collection must be armed-only"):
        validate_repository_workflows(REPO_ROOT, generate_feed_path=altered)


def test_workflow_validator_rejects_broad_generated_ci_ignore(tmp_path: Path):
    workflow = REPO_ROOT / ".github/workflows/ci-quality-gate.yml"
    altered = tmp_path / "test.yml"
    text = workflow.read_text(encoding="utf-8").replace("- feeds/latest.json", "- feeds/**")
    altered.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="paths-ignore"):
        validate_repository_workflows(REPO_ROOT, test_workflow_path=altered)


@pytest.mark.parametrize(
    ("needle", "replacement"),
    [
        ("deployment diagnostics", "deployment missing-diagnostics"),
        ("continue-on-error: true", "continue-on-error: false"),
    ],
)
def test_workflow_validator_requires_non_gating_failure_diagnostics(
    tmp_path: Path, needle: str, replacement: str
):
    workflow = REPO_ROOT / ".github/workflows/generate-feed.yml"
    altered = tmp_path / "generate-feed.yml"
    altered.write_text(workflow.read_text(encoding="utf-8").replace(needle, replacement))
    with pytest.raises(ValueError, match="diagnostics"):
        validate_repository_workflows(REPO_ROOT, generate_feed_path=altered)
