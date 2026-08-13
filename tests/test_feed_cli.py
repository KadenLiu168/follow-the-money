"""Task 4.7 — Feed CLI outcome-contract fixtures."""

from __future__ import annotations

import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

from follow_the_money.feed.cli import FeedExecutionError, FeedInputError, run_feed

REPO_ROOT = Path(__file__).resolve().parents[1]


def _empty_registry():
    return {}


def _cutoff() -> datetime:
    return datetime(2026, 8, 11, 0, 20, 0, tzinfo=UTC)


def test_no_provider_enabled_fails(tmp_path):
    with pytest.raises(FeedInputError, match="no provider enabled"):
        run_feed(
            config_path=str(REPO_ROOT / "config" / "config.yaml"),
            output_root=str(tmp_path / "out"),
            cutoff=_cutoff(),
            providers_fn=_empty_registry,
        )


@pytest.mark.parametrize(
    ("error", "expected_code"),
    [
        (FeedInputError("publication invalid non_advancing"), 2),
        (FeedExecutionError("config invalid provider"), 1),
    ],
)
def test_main_maps_typed_errors_without_inspecting_messages(
    monkeypatch, capsys, tmp_path, error, expected_code
):
    from follow_the_money.feed import cli as feed_cli

    def fail(**_kwargs):
        raise error

    monkeypatch.setattr(feed_cli, "run_feed", fail)
    assert feed_cli.main(["--output-root", str(tmp_path / "out")]) == expected_code
    captured = capsys.readouterr()
    assert str(error) in captured.err
    assert "Traceback" not in captured.err


def test_malformed_explicit_cutoff_is_input_exit_without_traceback(monkeypatch, capsys):
    from follow_the_money.feed import cli as feed_cli

    called = False

    def fail_if_called(**_kwargs):
        nonlocal called
        called = True
        raise AssertionError("invalid cutoff must be rejected before Feed execution")

    monkeypatch.setattr(feed_cli, "run_feed", fail_if_called)
    assert feed_cli.main(["--cutoff", "not-an-iso-date"]) == 2
    captured = capsys.readouterr()
    assert "--cutoff" in captured.err
    assert "Traceback" not in captured.err
    assert not called


def test_malformed_explicit_window_is_input_exit_without_traceback(monkeypatch, capsys):
    from follow_the_money.feed import cli as feed_cli

    monkeypatch.setattr(
        feed_cli,
        "run_feed",
        lambda **_kwargs: pytest.fail("invalid window must be rejected before Feed execution"),
    )
    assert feed_cli.main(["--window-start", "not-an-iso-date"]) == 2
    captured = capsys.readouterr()
    assert "--window-start" in captured.err
    assert "Traceback" not in captured.err


def test_invalid_config_is_input_error(tmp_path):
    with pytest.raises(FeedInputError):
        run_feed(
            config_path=str(tmp_path / "missing-config.yaml"),
            output_root=str(tmp_path / "out"),
            cutoff=_cutoff(),
            providers_fn=_empty_registry,
        )


def test_publication_failure_is_execution_error(tmp_path, monkeypatch):
    from follow_the_money.feed import cli as feed_cli
    from follow_the_money.feed.publish import PublishError

    class FakeAdapter:
        def fetch(self, window, client=None):
            return object()

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
                        "title": "声明",
                        "announced_at": "2026-08-11T00:10:00Z",
                        "raw_metadata": {},
                    },
                }
            ]

    def fail(**_kwargs):
        raise PublishError("config invalid publication")

    monkeypatch.setattr(feed_cli, "publish_feed", fail)
    with pytest.raises(FeedExecutionError):
        run_feed(
            config_path=str(REPO_ROOT / "config" / "config.yaml"),
            output_root=str(tmp_path / "out"),
            cutoff=_cutoff(),
            providers_fn=lambda: {"federal_reserve": FakeAdapter()},
            enabled_provider_ids=["federal_reserve"],
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
        [sys.executable, "-m", "follow_the_money.feed.cli", "--bogus-flag"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )
    assert proc.returncode == 2


def test_cli_help_exit_0():
    proc = subprocess.run(
        [sys.executable, "-m", "follow_the_money.feed.cli", "--help"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )
    assert proc.returncode == 0
    assert "--output-root" in proc.stdout
    assert "--dry-run" in proc.stdout


def test_package_importable_credential_free():
    # The package must import with no credential and no console entry point.
    proc = subprocess.run(
        [sys.executable, "-c", "import follow_the_money; print(follow_the_money.__version__)"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )
    assert proc.returncode == 0
    assert proc.stdout.strip() == "0.1.0"
    # No public console script remains; the old entry is absent.
    assert not (REPO_ROOT / "src" / "follow_the_money" / "__main__.py").exists()
    assert not (REPO_ROOT / "src" / "follow_the_money" / "cli.py").exists()
