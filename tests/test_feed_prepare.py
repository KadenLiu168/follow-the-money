"""Internal Skill Feed preparation entry regressions."""

from __future__ import annotations

import importlib
import os
import shutil
import subprocess
from pathlib import Path

from follow_the_money.canonical import canonical_bytes
from tests.test_feed_boundary import _valid_v3_blocked_feed
from tests.test_feed_bundle import _feed

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "skill" / "prepare-feed"


def _remote_module():
    return importlib.import_module("follow_the_money.feed.remote")


def test_prepare_feed_emits_canonical_logical_feed(monkeypatch, capsys):
    remote = _remote_module()
    feed = _feed()
    monkeypatch.setattr(remote, "consume_published_feed", lambda: feed)

    assert remote.main([]) == 0
    captured = capsys.readouterr()
    assert captured.out == canonical_bytes(feed).decode("utf-8")
    assert captured.err == ""


def test_prepare_feed_preserves_degraded_warnings_on_stderr(monkeypatch, capsys):
    remote = _remote_module()
    feed = _valid_v3_blocked_feed()
    monkeypatch.setattr(remote, "consume_published_feed", lambda: feed)

    assert remote.main([]) == 0
    captured = capsys.readouterr()
    assert captured.out == canonical_bytes(feed).decode("utf-8")
    assert captured.err == "warning: blocked Provider p\n"


def test_prepare_feed_reports_typed_failure_on_stderr(monkeypatch, capsys):
    remote = _remote_module()
    monkeypatch.setattr(
        remote,
        "consume_published_feed",
        lambda: (_ for _ in ()).throw(remote.FeedRemoteError("HTTP 503")),
    )

    assert remote.main([]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "prepare-feed: HTTP 503\n"


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
