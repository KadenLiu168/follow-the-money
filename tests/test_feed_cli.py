"""Task 4.7 — Feed CLI outcome-contract fixtures."""

from __future__ import annotations

import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

from follow_the_money.feed.cli import FeedCliError, run_feed

REPO_ROOT = Path(__file__).resolve().parents[1]


def _empty_registry():
    return {}


def _cutoff() -> datetime:
    return datetime(2026, 8, 11, 0, 20, 0, tzinfo=UTC)


def test_no_provider_enabled_fails(tmp_path):
    with pytest.raises(FeedCliError, match="no provider enabled"):
        run_feed(
            config_path=str(REPO_ROOT / "config" / "config.yaml"),
            output_root=str(tmp_path / "out"),
            cutoff=_cutoff(),
            providers_fn=_empty_registry,
        )


def test_dry_run_publishes_nothing(tmp_path):
    out = tmp_path / "out"
    # Registry with one healthy fake provider.
    from types import SimpleNamespace

    class FakeAdapter:
        provider_id = "federal_reserve"

        def fetch(self, window, client=None):
            return SimpleNamespace(body_bytes=b"<rss version='2.0'><channel></channel></rss>")

        def normalize(self, raw, window):
            return [
                {
                    "id": "item_fake",
                    "provider_id": "federal_reserve",
                    "source": {
                        "id": "src-1",
                        "name": "Federal Reserve",
                        "tier": "Tier 1",
                        "kind": "news",
                        "url": "https://www.federalreserve.gov/newsevents/pressreleases/monetary20260811a.htm",
                        "published_at": "2026-08-11T00:10:00Z",
                        "knowledge_available_at": "2026-08-11T00:10:00Z",
                    },
                    "payload": {
                        "type": "policy",
                        "title": "美联储声明",
                        "announced_at": "2026-08-11T00:10:00Z",
                        "raw_metadata": {},
                    },
                }
            ]

    registry = {"federal_reserve": FakeAdapter()}
    result = run_feed(
        config_path=str(REPO_ROOT / "config" / "config.yaml"),
        output_root=str(out),
        cutoff=_cutoff(),
        dry_run=True,
        providers_fn=lambda: registry,
        enabled_provider_ids=["federal_reserve"],
    )
    # Result requires all rows healthy; with one provider the run degrades,
    # but dry-run publishes no dated/latest artifact.
    assert not (out / "latest.json").exists()
    assert not list((out / "daily").glob("**/*.json")) if (out / "daily").exists() else True
    assert result.feed is not None
    assert result.feed["pipeline"]["status"] in ("healthy", "degraded")


def test_cli_usage_error_exit_2():
    proc = subprocess.run(
        [sys.executable, "-m", "follow_the_money", "feed", "--bogus-flag"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )
    assert proc.returncode == 2


def test_cli_help_exit_0():
    proc = subprocess.run(
        [sys.executable, "-m", "follow_the_money", "--help"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )
    assert proc.returncode == 0
    assert "feed" in proc.stdout


def test_cli_missing_module_runs():
    # The package must be importable and expose the console entry point.
    proc = subprocess.run(
        [sys.executable, "-c", "import follow_the_money; print(follow_the_money.__version__)"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )
    assert proc.returncode == 0
    assert proc.stdout.strip() == "0.1.0"
