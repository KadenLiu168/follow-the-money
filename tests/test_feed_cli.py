"""Task 4.7 — Feed CLI outcome-contract fixtures."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from follow_the_money.config import load_config
from follow_the_money.feed.checkpoint import FeedCheckpoint, read_checkpoint, write_checkpoint
from follow_the_money.feed.cli import (
    FeedExecutionError,
    FeedInputError,
    FeedRunResult,
)
from follow_the_money.feed.cli import (
    run_feed as _run_feed,
)
from follow_the_money.feed.validate import assert_feed_identity, validate_feed
from follow_the_money.providers.http import FetchError
from follow_the_money.providers.rate import RateStateError

REPO_ROOT = Path(__file__).resolve().parents[1]


def run_feed(**kwargs):
    if "runtime_state_root" not in kwargs and kwargs.get("output_root") is not None:
        output = Path(kwargs["output_root"])
        kwargs["runtime_state_root"] = str(output.parent / f".{output.name}-state")
    return _run_feed(**kwargs)


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


def test_feed_entry_rejects_one_path_used_as_both_product_and_runtime_root(tmp_path):
    shared_root = tmp_path / "feeds"

    with pytest.raises(FeedInputError, match="must be distinct"):
        _run_feed(
            output_root=str(shared_root),
            runtime_state_root=str(shared_root),
            cutoff=_cutoff(),
            providers_fn=_empty_registry,
        )

    assert not shared_root.exists()


def test_publication_failure_is_execution_error(tmp_path, monkeypatch):
    from follow_the_money.feed import cli as feed_cli
    from follow_the_money.feed.publish import PublishError

    def fail(**_kwargs):
        raise PublishError("config invalid publication")

    out = tmp_path / "out"
    cfg = _source_complete_cfg()
    monkeypatch.setattr(feed_cli, "_load_app_config", lambda _path: cfg)
    planned = _planned_provider_ids(cfg)
    registry = {provider_id: _OutcomeAdapter() for provider_id in planned}
    baseline = run_feed(
        output_root=str(out),
        cutoff=_cutoff(),
        providers_fn=lambda: registry,
        enabled_provider_ids=planned,
    )
    assert baseline.status == "healthy"
    previous_latest = (out / "latest.json").read_bytes()

    monkeypatch.setattr(feed_cli, "publish_feed", fail)
    with pytest.raises(FeedExecutionError):
        run_feed(
            output_root=str(out),
            cutoff=_cutoff().replace(hour=1),
            providers_fn=lambda: registry,
            enabled_provider_ids=planned,
        )
    assert (out / "latest.json").read_bytes() == previous_latest


class _OutcomeAdapter:
    def __init__(self, *, items=None, error: Exception | None = None):
        self.items = items or []
        self.error = error
        self.windows: list[dict[str, str]] = []

    def fetch(self, window, client=None):
        self.windows.append(dict(window))
        if self.error is not None:
            raise self.error
        return SimpleNamespace(body_bytes=b"fixture")

    def normalize(self, raw, window):
        return self.items


def _source_complete_cfg():
    cfg = load_config(
        REPO_ROOT / "config" / "config.yaml",
        REPO_ROOT / "config" / "providers.yaml",
        manifest_root=REPO_ROOT / "providers",
        require_verified_enabled=False,
    )
    return replace(
        cfg,
        providers=tuple(
            replace(provider, empty_valid_for_window=True) for provider in cfg.providers
        ),
    )


def _planned_provider_ids(cfg) -> list[str]:
    return [provider.id for provider in cfg.providers if provider.enabled]


def test_run_feed_separates_product_and_runtime_state_roots(tmp_path, monkeypatch):
    from follow_the_money.feed import cli as feed_cli

    cfg = _source_complete_cfg()
    monkeypatch.setattr(feed_cli, "_load_app_config", lambda _path: cfg)
    product_root = tmp_path / "products"
    runtime_root = tmp_path / "runtime"
    planned = _planned_provider_ids(cfg)
    registry = {provider_id: _OutcomeAdapter() for provider_id in planned}

    result = run_feed(
        output_root=str(product_root),
        runtime_state_root=str(runtime_root),
        cutoff=_cutoff(),
        providers_fn=lambda: registry,
        enabled_provider_ids=planned,
    )

    assert result.status == "healthy"
    assert (product_root / "latest.json").is_file()
    assert list((product_root / "daily").rglob("*.json"))
    assert (runtime_root / ".collection.lock").is_file()
    assert (runtime_root / "rate-registry.json").is_file()
    assert (runtime_root / "feed-checkpoint.json").is_file()
    assert read_checkpoint(runtime_root / "feed-checkpoint.json").previous_success is not None
    assert not (product_root / "rate-registry.json").exists()
    assert not (product_root / "feed-checkpoint.json").exists()


def _seed_checkpoint(path):
    write_checkpoint(path, FeedCheckpoint(previous_success=None))


def test_checkpoint_advances_after_accepted_publication_and_before_unlock(tmp_path, monkeypatch):
    from follow_the_money.feed import cli as feed_cli

    cfg = _source_complete_cfg()
    monkeypatch.setattr(feed_cli, "_load_app_config", lambda _path: cfg)
    product_root = tmp_path / "products"
    runtime_root = tmp_path / "runtime"
    checkpoint_path = runtime_root / "feed-checkpoint.json"
    _seed_checkpoint(checkpoint_path)
    planned = _planned_provider_ids(cfg)
    registry = {provider_id: _OutcomeAdapter() for provider_id in planned}
    events: list[str] = []
    original_publish = feed_cli.publish_feed
    original_write = feed_cli.write_checkpoint

    def publish(**kwargs):
        events.append("publish")
        return original_publish(**kwargs)

    def write(path, checkpoint):
        events.append("checkpoint")
        return original_write(path, checkpoint)

    monkeypatch.setattr(feed_cli, "publish_feed", publish)
    monkeypatch.setattr(feed_cli, "write_checkpoint", write)

    result = run_feed(
        output_root=str(product_root),
        runtime_state_root=str(runtime_root),
        cutoff=_cutoff(),
        providers_fn=lambda: registry,
        enabled_provider_ids=planned,
    )

    assert result.exit_code == 0
    assert events == ["publish", "checkpoint"]
    checkpoint = read_checkpoint(checkpoint_path)
    assert checkpoint.previous_success is not None
    assert checkpoint.previous_success.evidence_cutoff_at == result.feed["evidence_cutoff_at"]
    assert checkpoint.previous_success.run_id == result.feed["run_id"]


def test_accepted_degraded_publication_advances_checkpoint(tmp_path, monkeypatch):
    from follow_the_money.feed import cli as feed_cli

    cfg = _source_complete_cfg()
    monkeypatch.setattr(feed_cli, "_load_app_config", lambda _path: cfg)
    product_root = tmp_path / "products"
    runtime_root = tmp_path / "runtime"
    checkpoint_path = runtime_root / "feed-checkpoint.json"
    _seed_checkpoint(checkpoint_path)
    planned = _planned_provider_ids(cfg)
    registry = {provider_id: _OutcomeAdapter() for provider_id in planned}
    monkeypatch.setattr(feed_cli, "assess_pipeline", lambda **_kwargs: ("degraded", []))

    result = run_feed(
        output_root=str(product_root),
        runtime_state_root=str(runtime_root),
        cutoff=_cutoff(),
        providers_fn=lambda: registry,
        enabled_provider_ids=planned,
    )

    assert result.status == "degraded"
    assert result.exit_code == 0
    checkpoint = read_checkpoint(checkpoint_path)
    assert checkpoint.previous_success is not None
    assert checkpoint.previous_success.run_id == result.feed["run_id"]


@pytest.mark.parametrize(
    "outcome",
    [
        "dry_run",
        "source_failure",
        "candidate_validation",
        "publication_failure",
        "durability_unknown",
        "latest_not_replaced",
    ],
)
def test_failed_or_dry_run_outcomes_do_not_advance_checkpoint(tmp_path, monkeypatch, outcome):
    from follow_the_money.feed import cli as feed_cli

    cfg = _source_complete_cfg()
    monkeypatch.setattr(feed_cli, "_load_app_config", lambda _path: cfg)
    product_root = tmp_path / "products"
    runtime_root = tmp_path / "runtime"
    checkpoint_path = runtime_root / "feed-checkpoint.json"
    _seed_checkpoint(checkpoint_path)
    before = checkpoint_path.read_bytes()
    planned = _planned_provider_ids(cfg)
    registry = {provider_id: _OutcomeAdapter() for provider_id in planned}
    kwargs = {
        "output_root": str(product_root),
        "runtime_state_root": str(runtime_root),
        "cutoff": _cutoff(),
        "providers_fn": lambda: registry,
        "enabled_provider_ids": planned,
    }

    if outcome == "dry_run":
        kwargs["dry_run"] = True
    elif outcome == "source_failure":
        registry["bls"] = _OutcomeAdapter(error=RuntimeError("provider unavailable"))
    elif outcome == "candidate_validation":
        from follow_the_money.schema import SchemaError

        monkeypatch.setattr(
            feed_cli,
            "validate_feed",
            lambda _feed: (_ for _ in ()).throw(SchemaError("invalid candidate")),
        )
    else:
        from follow_the_money.feed.publish import PublishError

        if outcome == "publication_failure":
            monkeypatch.setattr(
                feed_cli,
                "publish_feed",
                lambda **_kwargs: (_ for _ in ()).throw(PublishError("publication failed")),
            )
        elif outcome == "durability_unknown":
            monkeypatch.setattr(
                feed_cli,
                "publish_feed",
                lambda **_kwargs: SimpleNamespace(
                    commit_durability_unknown=True, latest_replaced=True
                ),
            )
        else:
            monkeypatch.setattr(
                feed_cli,
                "publish_feed",
                lambda **_kwargs: SimpleNamespace(
                    commit_durability_unknown=False, latest_replaced=False
                ),
            )

    if outcome in {
        "candidate_validation",
        "publication_failure",
        "durability_unknown",
        "latest_not_replaced",
    }:
        with pytest.raises(FeedExecutionError):
            run_feed(**kwargs)
    else:
        run_feed(**kwargs)

    assert checkpoint_path.read_bytes() == before
    assert not (product_root / "latest.json").exists()


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


def test_failed_provider_and_successful_provider_fail_with_both_causes(tmp_path):
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

    assert result.status == "failure"
    assert result.exit_code == 1
    assert any(
        "bls" in warning and "failed" in warning and "provider unavailable" in warning
        for warning in result.warnings
    )
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


def test_incomplete_single_empty_provider_is_failure_in_dry_run(tmp_path):
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


def test_source_complete_empty_feed_publishes_and_advances_window(tmp_path, monkeypatch):
    from follow_the_money.feed import cli as feed_cli

    cfg = _source_complete_cfg()
    monkeypatch.setattr(feed_cli, "_load_app_config", lambda _path: cfg)
    planned = _planned_provider_ids(cfg)
    registry = {provider_id: _OutcomeAdapter() for provider_id in planned}
    out = tmp_path / "out"

    first = run_feed(
        output_root=str(out),
        cutoff=_cutoff(),
        providers_fn=lambda: registry,
        enabled_provider_ids=planned,
    )

    assert first.status == "healthy"
    assert first.exit_code == 0
    assert first.feed is not None
    assert first.feed["items"] == []
    latest_path = out / "latest.json"
    latest = json.loads(latest_path.read_text(encoding="utf-8"))
    validate_feed(latest)
    assert_feed_identity(latest)
    assert latest["evidence_cutoff_at"] == first.feed["evidence_cutoff_at"]
    assert latest["provider_outcomes"]
    dated = out / "daily" / "2026-08-11" / f"{latest['run_id']}.json"
    assert dated.is_file()
    assert dated.read_bytes() == latest_path.read_bytes()

    second = run_feed(
        output_root=str(out),
        cutoff=_cutoff().replace(hour=1),
        providers_fn=lambda: registry,
        enabled_provider_ids=planned,
    )

    assert second.status == "healthy"
    assert second.exit_code == 0
    assert all(
        adapter.windows[1]["start"] == latest["evidence_cutoff_at"] for adapter in registry.values()
    )


def test_source_incomplete_run_keeps_latest_and_reports_provider_diagnostics(tmp_path, monkeypatch):
    from follow_the_money.feed import cli as feed_cli

    cfg = _source_complete_cfg()
    monkeypatch.setattr(feed_cli, "_load_app_config", lambda _path: cfg)
    planned = _planned_provider_ids(cfg)
    out = tmp_path / "out"
    baseline_registry = {provider_id: _OutcomeAdapter() for provider_id in planned}
    baseline = run_feed(
        output_root=str(out),
        cutoff=_cutoff(),
        providers_fn=lambda: baseline_registry,
        enabled_provider_ids=planned,
    )
    assert baseline.status == "healthy"
    previous_latest = (out / "latest.json").read_bytes()
    previous_dated = sorted((out / "daily").rglob("*.json"))

    registry = {
        provider_id: _OutcomeAdapter(
            error=RuntimeError("provider unavailable") if provider_id == "bls" else None
        )
        for provider_id in planned
    }
    published = False

    def fail_if_called(**_kwargs):
        nonlocal published
        published = True
        raise AssertionError("source-incomplete Feed must not publish")

    monkeypatch.setattr(feed_cli, "publish_feed", fail_if_called)
    result = run_feed(
        output_root=str(out),
        cutoff=_cutoff().replace(hour=1),
        providers_fn=lambda: registry,
        enabled_provider_ids=planned,
    )

    diagnostics = "\n".join(result.warnings)
    assert result.status == "failure"
    assert result.exit_code == 1
    assert not published
    assert (out / "latest.json").read_bytes() == previous_latest
    assert sorted((out / "daily").rglob("*.json")) == previous_dated
    assert "bls" in diagnostics
    assert "failed" in diagnostics
    assert "provider unavailable" in diagnostics
    assert "us_official_macro_policy" in diagnostics
    assert "source completeness failed" in result.message
    assert "bls" in result.message


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
        warnings=["source incomplete: provider_id=bls state=failed error=provider unavailable"],
    )
    monkeypatch.setattr(feed_cli, "run_feed", lambda **_kwargs: result)
    status_file = tmp_path / "status.json"

    assert (
        feed_cli.main(
            ["--dry-run", "--output-root", str(tmp_path / "out"), "--status-file", str(status_file)]
        )
        == 1
    )
    payload = json.loads(status_file.read_text())
    assert payload == {
        "status": "failure",
        "warnings": ["source incomplete: provider_id=bls state=failed error=provider unavailable"],
    }


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
    # The one-provider fixture leaves mandatory groups incomplete, but
    # dry-run still publishes no dated/latest artifact.
    assert not (out / "latest.json").exists()
    assert not list((out / "daily").glob("**/*.json")) if (out / "daily").exists() else True
    assert not (out / "rate-registry.json").exists()
    assert result.feed is not None
    assert result.feed["pipeline"]["status"] == "failure"


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
