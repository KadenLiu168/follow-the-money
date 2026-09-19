"""Internal Skill Feed preparation entry regressions."""

from __future__ import annotations

import importlib
import os
import shutil
import subprocess
from pathlib import Path

from follow_the_money.digest import _project_validated_feed
from follow_the_money.feed.validate import recompute_feed_identity
from tests.test_feed_bundle import _feed

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "skill" / "prepare-feed"


def _digest_module():
    return importlib.import_module("follow_the_money.digest")


def test_prepare_feed_emits_canonical_digest_context(monkeypatch, capsys):
    digest = _digest_module()
    feed = _feed()
    monkeypatch.setattr(digest, "consume_published_feed", lambda: feed)

    assert digest.main([]) == 0
    captured = capsys.readouterr()
    assert captured.out == _project_validated_feed(feed).canonical_bytes().decode("utf-8")
    assert captured.err == ""


def test_prepare_feed_emits_compact_limitations_instead_of_warnings(monkeypatch, capsys):
    digest = _digest_module()
    feed = _feed()
    cftc = next(
        outcome for outcome in feed["provider_outcomes"] if outcome["provider_id"] == "cftc"
    )
    cftc.update(
        state="failed",
        succeeded=False,
        failed=True,
        accepted=0,
        availability="blocked",
        availability_reason="HTTP 403",
        upstream_http_status=403,
        freshness={
            "cadence": "weekly",
            "status": "not_evaluated",
            "origin_contract_hash": None,
            "carried_forward_from_run_id": None,
        },
    )
    feed["pipeline"] = {"status": "degraded", "warnings": ["blocked Provider cftc"]}
    feed["content_digest"], feed["run_id"] = recompute_feed_identity(feed)
    monkeypatch.setattr(digest, "consume_published_feed", lambda: feed)

    assert digest.main([]) == 0
    captured = capsys.readouterr()
    assert captured.out == _project_validated_feed(feed).canonical_bytes().decode("utf-8")
    assert captured.err == ""
    assert "blocked Provider cftc" not in captured.out
    assert '"limitations":[{"affected_coverage_groups":["cftc_positioning"],"code":' in captured.out


def test_prepare_feed_reports_typed_failure_on_stderr(monkeypatch, capsys):
    digest = _digest_module()
    monkeypatch.setattr(
        digest,
        "consume_published_feed",
        lambda: (_ for _ in ()).throw(digest.FeedRemoteError("HTTP 503")),
    )

    assert digest.main([]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "prepare-feed: HTTP 503\n"


def test_prepare_feed_reports_projection_failure_without_partial_stdout(monkeypatch, capsys):
    digest = _digest_module()
    feed = _feed()
    feed["items"] = [{"id": "broken"}]
    monkeypatch.setattr(digest, "consume_published_feed", lambda: feed)

    assert digest.main([]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith("prepare-feed: ")


def test_prepare_feed_launcher_runs_from_symlinked_skill_outside_checkout():
    assert SCRIPT.is_file()
    skill = Path("/tmp") / f"follow-the-money-skill-{os.getpid()}"
    if skill.exists() or skill.is_symlink():
        skill.unlink()
    try:
        skill.symlink_to(REPO_ROOT, target_is_directory=True)
        env = {**os.environ, "PATH": "/usr/bin:/bin"}
        proc = subprocess.run(
            [str(skill / "scripts" / "skill" / "prepare-feed"), "--help"],
            cwd=Path("/tmp"),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        skill.unlink(missing_ok=True)

    assert proc.returncode == 0, proc.stderr
    assert "usage: prepare-feed" in proc.stdout


def test_prepare_feed_launcher_reports_missing_virtualenv(tmp_path):
    assert SCRIPT.is_file()
    copied = tmp_path / "repo" / "scripts" / "skill" / "prepare-feed"
    copied.parent.mkdir(parents=True)
    shutil.copy2(SCRIPT, copied)

    proc = subprocess.run([str(copied), "--help"], capture_output=True, text=True, check=False)

    assert proc.returncode == 2
    assert "run uv sync --frozen --all-groups" in proc.stderr
