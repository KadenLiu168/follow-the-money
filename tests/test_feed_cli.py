"""Task 4.7 — Feed CLI outcome-contract fixtures."""

from __future__ import annotations

import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from follow_the_money.feed.cli import FeedExecutionError, FeedInputError, FeedRunResult, run_feed
from follow_the_money.providers.http import FetchError
from follow_the_money.providers.rate import RateStateError

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

    out = tmp_path / "out"
    baseline = run_feed(
        config_path=str(REPO_ROOT / "config" / "config.yaml"),
        output_root=str(out),
        cutoff=_cutoff(),
        providers_fn=lambda: {"federal_reserve": FakeAdapter()},
        enabled_provider_ids=["federal_reserve"],
    )
    assert baseline.status == "degraded"
    previous_latest = (out / "latest.json").read_bytes()

    monkeypatch.setattr(feed_cli, "publish_feed", fail)
    with pytest.raises(FeedExecutionError):
        run_feed(
            config_path=str(REPO_ROOT / "config" / "config.yaml"),
            output_root=str(out),
            cutoff=_cutoff().replace(hour=1),
            providers_fn=lambda: {"federal_reserve": FakeAdapter()},
            enabled_provider_ids=["federal_reserve"],
        )
    assert (out / "latest.json").read_bytes() == previous_latest


class _OutcomeAdapter:
    def __init__(self, *, items=None, error: Exception | None = None):
        self.items = items or []
        self.error = error

    def fetch(self, window, client=None):
        if self.error is not None:
            raise self.error
        return SimpleNamespace(body_bytes=b"fixture")

    def normalize(self, raw, window):
        return self.items


def _accepted_item(provider_id: str, item_id: str) -> dict:
    return {
        "id": item_id,
        "provider_id": provider_id,
        "source": {
            "id": f"{item_id}-source",
            "name": "Fixture source",
            "tier": "Tier 1",
            "kind": "news",
            "url": f"https://example.com/{item_id}",
            "published_at": "2026-08-11T00:10:00Z",
            "knowledge_available_at": "2026-08-11T00:10:00Z",
        },
        "payload": {
            "type": "policy",
            "title": item_id,
            "announced_at": "2026-08-11T00:10:00Z",
            "raw_metadata": {},
        },
    }


def test_failed_provider_and_successful_provider_are_degraded_with_both_causes(tmp_path):
    result = run_feed(
        output_root=str(tmp_path / "out"),
        cutoff=_cutoff(),
        dry_run=True,
        providers_fn=lambda: {
            "federal_reserve": _OutcomeAdapter(
                items=[_accepted_item("federal_reserve", "accepted")]
            ),
            "bls": _OutcomeAdapter(error=RuntimeError("provider unavailable")),
        },
        enabled_provider_ids=["federal_reserve", "bls"],
    )

    assert result.status == "degraded"
    assert result.exit_code == 0
    assert any("bls" in warning for warning in result.warnings)
    assert any("us_official_macro_policy" in warning for warning in result.warnings)


def test_dry_run_late_result_after_retained_evidence_is_execution_failure(tmp_path):
    clock = {"now": 0.0}

    class LateAdapter(_OutcomeAdapter):
        def fetch(self, window, client=None):
            clock["now"] = 285.0
            return super().fetch(window, client)

    out = tmp_path / "out"

    with pytest.raises(FeedExecutionError, match="pre_commit_deadline_exceeded"):
        run_feed(
            output_root=str(out),
            cutoff=_cutoff(),
            dry_run=True,
            providers_fn=lambda: {
                "yahoo_market": [
                    _OutcomeAdapter(items=[_accepted_item("yahoo_market", "accepted")]),
                    LateAdapter(items=[_accepted_item("yahoo_market", "late")]),
                ]
            },
            enabled_provider_ids=["yahoo_market"],
            monotonic_now=lambda: clock["now"],
        )

    assert not (out / "latest.json").exists()
    assert not list((out / "daily").rglob("*.json")) if (out / "daily").exists() else True


def test_dry_run_provider_start_after_global_deadline_is_execution_failure(tmp_path, monkeypatch):
    from dataclasses import replace
    from threading import current_thread

    from follow_the_money.feed import cli as feed_cli

    cfg = feed_cli._load_app_config(None)
    cfg = replace(cfg, feed=replace(cfg.feed, global_concurrency=1))
    monkeypatch.setattr(feed_cli, "_load_app_config", lambda _path: cfg)
    clock = {"armed": False, "worker_reads": 0}

    def monotonic() -> float:
        if current_thread().name == "MainThread" or not clock["armed"]:
            return 0.0
        clock["worker_reads"] += 1
        return 0.0 if clock["worker_reads"] == 1 else 286.0

    class FirstAdapter(_OutcomeAdapter):
        def normalize(self, raw, window):
            clock["armed"] = True
            return super().normalize(raw, window)

    out = tmp_path / "out"

    with pytest.raises(FeedExecutionError, match="pre_commit_deadline_exceeded"):
        run_feed(
            output_root=str(out),
            cutoff=_cutoff(),
            dry_run=True,
            providers_fn=lambda: {
                "federal_reserve": FirstAdapter(
                    items=[_accepted_item("federal_reserve", "accepted")]
                ),
                "yahoo_market": _OutcomeAdapter(items=[_accepted_item("yahoo_market", "late")]),
            },
            enabled_provider_ids=["federal_reserve", "yahoo_market"],
            monotonic_now=monotonic,
        )

    assert not (out / "latest.json").exists()
    assert not list((out / "daily").rglob("*.json")) if (out / "daily").exists() else True


def test_rate_state_failure_remains_execution_error_with_other_accepted_evidence(
    tmp_path, monkeypatch
):
    from follow_the_money.feed import cli as feed_cli

    original = feed_cli._ensure_scope_state

    def fail_market_rate_state(rate, scope_id, cfg, now_fn):
        if scope_id == "yahoo_market":
            raise RateStateError("config invalid provider")
        return original(rate, scope_id, cfg, now_fn)

    monkeypatch.setattr(feed_cli, "_ensure_scope_state", fail_market_rate_state)
    out = tmp_path / "out"

    with pytest.raises(FeedExecutionError, match="config invalid provider"):
        run_feed(
            output_root=str(out),
            cutoff=_cutoff(),
            providers_fn=lambda: {
                "federal_reserve": _OutcomeAdapter(
                    items=[_accepted_item("federal_reserve", "accepted")]
                ),
                "yahoo_market": _OutcomeAdapter(items=[_accepted_item("yahoo_market", "market")]),
            },
            enabled_provider_ids=["federal_reserve", "yahoo_market"],
        )

    assert not (out / "latest.json").exists()
    assert not list((out / "daily").rglob("*.json")) if (out / "daily").exists() else True


def test_rate_wait_beyond_deadline_is_execution_failure_with_other_accepted_evidence(
    tmp_path, monkeypatch
):
    from follow_the_money.feed import cli as feed_cli

    def delay_beyond_deadline(state, *, now):
        return 10_000.0 if state.scope_id == "yahoo_market" else 0.0

    monkeypatch.setattr(feed_cli, "eligibility_delay", delay_beyond_deadline)
    out = tmp_path / "out"

    with pytest.raises(FeedExecutionError, match="rate_not_eligible_before_deadline"):
        run_feed(
            output_root=str(out),
            cutoff=_cutoff(),
            providers_fn=lambda: {
                "federal_reserve": _OutcomeAdapter(
                    items=[_accepted_item("federal_reserve", "accepted")]
                ),
                "yahoo_market": _OutcomeAdapter(items=[_accepted_item("yahoo_market", "market")]),
            },
            enabled_provider_ids=["federal_reserve", "yahoo_market"],
        )

    assert not (out / "latest.json").exists()
    assert not list((out / "daily").rglob("*.json")) if (out / "daily").exists() else True


def test_retry_wait_beyond_deadline_is_execution_failure_with_other_accepted_evidence(
    tmp_path,
):
    retrying = _OutcomeAdapter(error=FetchError("retry", retry_after_seconds=3600, retryable=True))
    out = tmp_path / "out"

    with pytest.raises(FeedExecutionError, match="retry_not_admitted_before_deadline"):
        run_feed(
            output_root=str(out),
            cutoff=_cutoff(),
            providers_fn=lambda: {
                "federal_reserve": _OutcomeAdapter(
                    items=[_accepted_item("federal_reserve", "accepted")]
                ),
                "yahoo_market": retrying,
            },
            enabled_provider_ids=["federal_reserve", "yahoo_market"],
        )

    assert not (out / "latest.json").exists()
    assert not list((out / "daily").rglob("*.json")) if (out / "daily").exists() else True


def test_rate_reconcile_failure_is_not_retried_as_provider_degradation(tmp_path, monkeypatch):
    from follow_the_money.feed import cli as feed_cli

    original = feed_cli.RateRegistry.reconcile
    failed = False

    def fail_market_reconcile_once(registry, state, **kwargs):
        nonlocal failed
        if state.scope_id == "yahoo_market" and not failed:
            failed = True
            raise RateStateError("provider unavailable during reconcile")
        return original(registry, state, **kwargs)

    monkeypatch.setattr(feed_cli.RateRegistry, "reconcile", fail_market_reconcile_once)
    out = tmp_path / "out"

    with pytest.raises(FeedExecutionError, match="provider unavailable during reconcile"):
        run_feed(
            output_root=str(out),
            cutoff=_cutoff(),
            providers_fn=lambda: {
                "federal_reserve": _OutcomeAdapter(
                    items=[_accepted_item("federal_reserve", "accepted")]
                ),
                "yahoo_market": _OutcomeAdapter(items=[_accepted_item("yahoo_market", "market")]),
            },
            enabled_provider_ids=["federal_reserve", "yahoo_market"],
        )

    assert failed
    assert not (out / "latest.json").exists()
    assert not list((out / "daily").rglob("*.json")) if (out / "daily").exists() else True


def test_all_permitted_empty_is_failure_in_dry_run(tmp_path):
    result = run_feed(
        output_root=str(tmp_path / "out"),
        cutoff=_cutoff(),
        dry_run=True,
        providers_fn=lambda: {"federal_reserve": _OutcomeAdapter()},
        enabled_provider_ids=["federal_reserve"],
    )

    assert result.status == "failure"
    assert result.exit_code == 1
    assert not (tmp_path / "out" / "latest.json").exists()
    assert (
        not list((tmp_path / "out" / "daily").rglob("*.json"))
        if (tmp_path / "out" / "daily").exists()
        else True
    )


def test_failure_does_not_call_publication_or_replace_latest(tmp_path, monkeypatch):
    from follow_the_money.feed import cli as feed_cli

    called = False

    def fail_if_called(**_kwargs):
        nonlocal called
        called = True
        raise AssertionError("failure candidates must not enter publication")

    monkeypatch.setattr(feed_cli, "publish_feed", fail_if_called)
    result = run_feed(
        output_root=str(tmp_path / "out"),
        cutoff=_cutoff(),
        providers_fn=lambda: {"federal_reserve": _OutcomeAdapter()},
        enabled_provider_ids=["federal_reserve"],
    )

    assert result.status == "failure"
    assert result.exit_code == 1
    assert not called
    assert not (tmp_path / "out" / "latest.json").exists()
    assert (
        not list((tmp_path / "out" / "daily").rglob("*.json"))
        if (tmp_path / "out" / "daily").exists()
        else True
    )


def test_failure_status_file_does_not_expose_success_paths(tmp_path, monkeypatch):
    from follow_the_money.feed import cli as feed_cli

    result = FeedRunResult(
        status="failure",
        exit_code=1,
        feed={
            "run_id": "failure-run",
            "evidence_cutoff_at": "2026-08-11T00:20:00Z",
        },
        warnings=["no accepted item"],
    )
    monkeypatch.setattr(feed_cli, "run_feed", lambda **_kwargs: result)
    status_file = tmp_path / "status.json"

    assert (
        feed_cli.main(
            ["--dry-run", "--output-root", str(tmp_path / "out"), "--status-file", str(status_file)]
        )
        == 1
    )
    payload = __import__("json").loads(status_file.read_text())
    assert payload == {"status": "failure", "warnings": ["no accepted item"]}


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
    assert not (out / "rate-registry.json").exists()
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
