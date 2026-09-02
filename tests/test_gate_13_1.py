"""Gate 13.1 — Provider and Feed production gate.

Proves the credential-free fixture-backed CLI run produces a valid healthy
(or explicitly degraded) Feed rather than ``no provider enabled``: every
mandatory v1 matrix row is verified-enabled, the real registry + collection
lock + durable rate-state + bounded clients + concurrency + deadlines are
wired into ``run_feed``, and the emitted Feed carries real schema/config/
provider-contract fingerprints.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from follow_the_money.feed.cli import FeedCliError, FeedExecutionError
from follow_the_money.feed.cli import run_feed as _run_feed
from follow_the_money.feed.validate import assert_feed_identity, validate_feed
from follow_the_money.providers.adapters import (
    YahooMarketAdapter,
    build_registry,
)
from follow_the_money.providers.http import FetchError

REPO_ROOT = Path(__file__).resolve().parents[1]
CUTOFF = datetime(2026, 8, 11, 0, 20, 0, tzinfo=UTC)


def run_feed(**kwargs):
    if "runtime_state_root" not in kwargs and kwargs.get("output_root") is not None:
        output = Path(kwargs["output_root"])
        kwargs["runtime_state_root"] = str(output.parent / f".{output.name}-state")
    return _run_feed(**kwargs)


FIXTURE_BY_PROVIDER = {
    "federal_reserve": "providers/federal_reserve/fixtures/press_all.xml",
    "bls": "providers/bls/fixtures/news.release.xml",
    "sec_edgar": "providers/sec_edgar/fixtures/browse-13f.json",
    "cftc": "providers/cftc/fixtures/cot.json",
    "pboc": "providers/pboc/fixtures/announcements.json",
    "nbs": "providers/nbs/fixtures/releases.json",
    "sse": "providers/sse/fixtures/notices.json",
    "szse": "providers/szse/fixtures/notices.json",
    "yahoo_market": "providers/yahoo_market/fixtures/chart.json",
}


def _fixture_client(provider_id: str) -> Any:
    body = (REPO_ROOT / FIXTURE_BY_PROVIDER[provider_id]).read_bytes()

    class _Client:
        def get(self, url, headers=None, timeout=None, follow_redirects=True):
            return SimpleNamespace(
                body_bytes=body,
                content=body,
                status_code=200,
                headers={},
                url=url,
                json=lambda: json.loads(body.decode("utf-8")),
            )

    return _Client()


class _FixtureAdapter:
    def __init__(self, inner, provider_id: str) -> None:
        self.inner = inner
        self.provider_id = provider_id

    def fetch(self, window, client=None):
        return self.inner.fetch(window, _fixture_client(self.provider_id))

    def normalize(self, raw, window):
        return self.inner.normalize(raw, window)


def _fixture_registry() -> dict[str, _FixtureAdapter]:
    registry = build_registry()
    ids = list(FIXTURE_BY_PROVIDER)
    wrapped = {pid: _FixtureAdapter(registry.get(pid), pid) for pid in ids}
    # Yahoo fans out over roles in production; use one representative role.
    wrapped["yahoo_market"] = _FixtureAdapter(
        YahooMarketAdapter(instrument="^GSPC", role_id="sp500"), "yahoo_market"
    )
    return wrapped


def test_all_mandatory_rows_verified_and_enabled():
    from follow_the_money.config import load_config

    cfg = load_config(
        REPO_ROOT / "config" / "config.yaml",
        REPO_ROOT / "config" / "providers.yaml",
        manifest_root=REPO_ROOT / "providers",
        require_verified_enabled=True,
    )
    for row in cfg.coverage.rows:
        enabled = [m for m in row.members if cfg.provider(m).enabled and cfg.provider(m).verified]
        assert len(enabled) >= row.minimum, f"{row.group}: verified enablement missing"


def test_fixture_backed_run_produces_valid_healthy_feed(tmp_path):
    state = tmp_path / ".out-state"
    result = run_feed(
        output_root=str(tmp_path / "out"),
        cutoff=CUTOFF,
        providers_fn=_fixture_registry,
    )
    assert result.exit_code == 0
    assert result.status == "healthy"
    feed = result.feed
    assert feed is not None
    validate_feed(feed)
    assert_feed_identity(feed)
    # Every mandatory provider contributed accepted items.
    for o in feed["provider_outcomes"]:
        assert o["state"] == "healthy", f"{o['provider_id']}: {o['error']}"
        assert o["accepted"] > 0
    # Real fingerprints, not placeholders.
    assert feed["feed_config"]["hash"] != "0" * 64
    assert feed["feed_schema"]["sha256"] != "0" * 64
    assert len(feed["provider_contracts"]) == 8
    # Latest is the only Feed product.
    assert (tmp_path / "out" / "latest.json").exists()
    assert not (tmp_path / "out" / "daily").exists()
    # Durable rate registry created.
    assert (state / "rate-registry.json").exists()


def test_fixture_backed_run_publishes_and_rate_debits(tmp_path):
    out = tmp_path / "out"
    state_root = tmp_path / ".out-state"
    result = run_feed(output_root=str(out), cutoff=CUTOFF, providers_fn=_fixture_registry)
    assert result.exit_code == 0
    registry = json.loads((state_root / "rate-registry.json").read_bytes())
    assert registry["version"] == "1"
    assert set(registry["scopes"]) >= {"us_gov", "sec_edgar", "china_gov", "yahoo_market"}
    # Scope states exist and were debited.
    scopes = list(state_root.glob("scope-*.json"))
    assert len(scopes) == 4
    for scope_file in scopes:
        state = json.loads(scope_file.read_bytes())
        assert state["status"] == "active"
        assert state["tokens"] != state["capacity"]  # debit happened


def test_retryable_provider_http_failure_uses_bounded_retry_matrix(tmp_path):
    class RetryAdapter:
        provider_id = "federal_reserve"

        def __init__(self):
            self.calls = 0

        def fetch(self, window, client=None):
            self.calls += 1
            if self.calls == 1:
                raise FetchError(
                    "HTTP 503 from federalreserve.gov",
                    status_code=503,
                    retry_after_seconds=0,
                    retryable=True,
                )
            return SimpleNamespace(body_bytes=b"unused")

        def normalize(self, raw, window):
            return [
                {
                    "id": "retry-item",
                    "provider_id": self.provider_id,
                    "source": {
                        "id": "retry-source",
                        "name": "Federal Reserve",
                        "tier": "Tier 1",
                        "kind": "news",
                        "url": "https://www.federalreserve.gov/newsevents/pressreleases/retry.htm",
                        "published_at": "2026-08-11T00:10:00Z",
                        "knowledge_available_at": "2026-08-11T00:10:00Z",
                    },
                    "payload": {
                        "type": "policy",
                        "title": "Retry success",
                        "announced_at": "2026-08-11T00:10:00Z",
                        "raw_metadata": {},
                    },
                }
            ]

    adapter = RetryAdapter()
    result = run_feed(
        output_root=str(tmp_path / "out"),
        cutoff=CUTOFF,
        providers_fn=lambda: {"federal_reserve": adapter},
        enabled_provider_ids=["federal_reserve"],
    )
    assert result.exit_code == 1
    outcome = next(
        row for row in result.feed["provider_outcomes"] if row["provider_id"] == "federal_reserve"
    )
    assert outcome["attempted"] == 2
    assert outcome["fetched"] == 1
    assert outcome["accepted"] == 1


def test_positive_retry_after_wait_is_admitted_before_retry(tmp_path):
    class RetryAfterAdapter:
        provider_id = "federal_reserve"

        def __init__(self):
            self.calls = 0

        def fetch(self, window, client=None):
            self.calls += 1
            if self.calls == 1:
                raise FetchError(
                    "HTTP 429 from federalreserve.gov",
                    status_code=429,
                    retry_after_seconds=7,
                    retryable=True,
                )
            return SimpleNamespace(body_bytes=b"unused")

        def normalize(self, raw, window):
            return [
                {
                    "id": "retry-after-item",
                    "provider_id": self.provider_id,
                    "source": {
                        "id": "retry-after-source",
                        "name": "Federal Reserve",
                        "tier": "Tier 1",
                        "kind": "news",
                        "url": "https://www.federalreserve.gov/newsevents/pressreleases/retry-after.htm",
                        "published_at": "2026-08-11T00:10:00Z",
                        "knowledge_available_at": "2026-08-11T00:10:00Z",
                    },
                    "payload": {
                        "type": "policy",
                        "title": "Retry-After success",
                        "announced_at": "2026-08-11T00:10:00Z",
                        "raw_metadata": {},
                    },
                }
            ]

    adapter = RetryAfterAdapter()
    waits: list[float] = []
    clock = {"seconds": 0.0}

    def now() -> datetime:
        return CUTOFF + timedelta(seconds=clock["seconds"])

    def sleep(delay: float) -> None:
        waits.append(delay)
        clock["seconds"] += delay

    result = run_feed(
        output_root=str(tmp_path / "out"),
        cutoff=CUTOFF,
        providers_fn=lambda: {"federal_reserve": adapter},
        enabled_provider_ids=["federal_reserve"],
        now_fn=now,
        sleep_fn=sleep,
    )
    assert result.exit_code == 1
    assert adapter.calls == 2
    assert waits == [7.0]


def test_retry_after_beyond_deadline_is_not_admitted(tmp_path):
    class RetryAfterAdapter:
        provider_id = "federal_reserve"

        def __init__(self):
            self.calls = 0

        def fetch(self, window, client=None):
            self.calls += 1
            raise FetchError(
                "HTTP 429 from federalreserve.gov",
                status_code=429,
                retry_after_seconds=3600,
                retryable=True,
            )

        def normalize(self, raw, window):
            return []

    adapter = RetryAfterAdapter()
    out = tmp_path / "out"
    with pytest.raises(FeedExecutionError, match="retry_not_admitted_before_deadline"):
        run_feed(
            output_root=str(out),
            cutoff=CUTOFF,
            providers_fn=lambda: {"federal_reserve": adapter},
            enabled_provider_ids=["federal_reserve"],
            sleep_fn=lambda _delay: pytest.fail(
                "Retry-After wait must not be admitted past deadline"
            ),
        )
    assert adapter.calls == 1
    assert not (out / "latest.json").exists()
    assert not list((out / "daily").rglob("*.json")) if (out / "daily").exists() else True


def test_no_provider_enabled_still_fails_closed(tmp_path):
    with pytest.raises(FeedCliError, match="no provider enabled"):
        run_feed(
            output_root=str(tmp_path / "out"),
            cutoff=CUTOFF,
            providers_fn=dict,
        )


def test_production_registry_includes_mandatory_and_optional_cftc():
    registry = build_registry()
    assert set(registry.ids()) == {
        "federal_reserve",
        "bls",
        "sec_edgar",
        "cftc",
        "pboc",
        "nbs",
        "sse",
        "szse",
        "yahoo_market",
    }


def test_each_core_adapter_emits_schema_valid_items():

    registry = build_registry()
    for pid, path in FIXTURE_BY_PROVIDER.items():
        (REPO_ROOT / path).read_bytes()
        client = _fixture_client(pid)
        adapter = registry.get(pid)
        window_start = "2026-08-01T00:20:00Z" if pid == "cftc" else "2026-08-08T00:20:00Z"
        window = {"start": window_start, "end": "2026-08-11T00:20:00Z"}
        raw = adapter.fetch(window, client)
        items = adapter.normalize(raw, window)
        assert items, f"{pid} produced no items from its fixture"
        # Items are schema-valid as Feed items (payload oneOf enforced).
        feed = {
            "schema_version": 1,
            "run_id": "x",
            "window": window,
            "collection_started_at": "2026-08-11T00:19:30Z",
            "evidence_cutoff_at": "2026-08-11T00:20:00Z",
            "collection_completed_at": "2026-08-11T00:24:00Z",
            "generated_at": "2026-08-11T00:25:00Z",
            "provider_outcomes": [],
            "producer": {"package_version": "0.1.0", "files": [], "fingerprint": "a" * 64},
            "feed_config": {"snapshot": {}, "hash": "b" * 64},
            "feed_schema": {"path": "x", "sha256": "c" * 64},
            "provider_contracts": [],
            "git": None,
            "content_digest": "d" * 64,
            "items": items,
            "pipeline": {"status": "healthy", "warnings": []},
        }
        from follow_the_money.feed.dedupe import deterministic_item_order
        from follow_the_money.feed.validate import recompute_feed_identity

        feed["items"] = deterministic_item_order(items)
        digest, run_id = recompute_feed_identity(feed)
        feed["content_digest"] = digest
        feed["run_id"] = run_id
        validate_feed(feed)
