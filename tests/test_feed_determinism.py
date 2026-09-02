"""make-feed-deterministic-and-truthful — RED regression coverage.

Covers the deterministic Feed contract:

- Provider-completion and item-input permutations never change the
  normalized semantic Feed (1.1/1.2).
- Lifecycle timestamps come from their real observed instants and are never
  offset-synthesized or reused (1.3).
- ``content_digest``/``run_id`` are computed from an explicit semantic
  projection; runtime audit metadata never participates, every semantic
  member does, and the legacy whole-envelope read path stays exact (1.4).
- Published Feed bytes are the shared canonical serialization and repeated
  semantic publication retains the first immutable artifact (1.5).
"""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from follow_the_money.canonical import canonical_bytes, canonical_digest
from follow_the_money.config import load_config
from follow_the_money.config.model import FetchRule
from follow_the_money.feed.cli import run_feed as _run_feed
from follow_the_money.feed.dedupe import deduplicate_items, deterministic_item_order
from follow_the_money.feed.plan import FeedPlan, ProviderOutcome
from follow_the_money.feed.publish import PublishError, publish_feed
from follow_the_money.feed.validate import (
    assert_feed_identity,
    recompute_feed_identity,
    semantic_feed_projection,
    validate_feed,
)
from follow_the_money.providers.http import FetchError, bounded_fetch
from follow_the_money.schema import SchemaError

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "config" / "config.yaml"
DEFAULT_PROVIDERS = REPO_ROOT / "config" / "providers.yaml"


def run_feed(**kwargs):
    if "runtime_state_root" not in kwargs and kwargs.get("output_root") is not None:
        output = Path(kwargs["output_root"])
        kwargs["runtime_state_root"] = str(output.parent / f".{output.name}-state")
    return _run_feed(**kwargs)


DEFAULT_MANIFEST_ROOT = REPO_ROOT / "providers"

T0 = datetime(2026, 8, 11, 0, 20, 0, tzinfo=UTC)


def _ts(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _cfg():
    return load_config(
        DEFAULT_CONFIG,
        DEFAULT_PROVIDERS,
        manifest_root=DEFAULT_MANIFEST_ROOT,
        require_verified_enabled=False,
    )


def _source_complete_cfg():
    cfg = _cfg()
    return replace(
        cfg,
        providers=tuple(
            replace(provider, empty_valid_for_window=True) for provider in cfg.providers
        ),
    )


def _outcome(
    pid: str,
    state: str = "healthy",
    *,
    accepted: int = 1,
    retrieved_at: str | None = None,
    error: str | None = None,
) -> dict:
    return {
        "provider_id": pid,
        "state": state,
        "attempted": 1 if state != "skipped" else 0,
        "fetched": 1 if retrieved_at is not None else 0,
        "succeeded": state in ("healthy", "empty", "partial"),
        "empty": state == "empty",
        "partial": state == "partial",
        "failed": state == "failed",
        "skipped": state == "skipped",
        "accepted": accepted,
        "rejected": 0,
        "error": error,
        "retrieved_at": retrieved_at,
    }


def _news_item(
    item_id: str,
    provider_id: str,
    *,
    knowledge: datetime,
    title: str = "标题",
    url: str | None = None,
) -> dict:
    return {
        "id": item_id,
        "provider_id": provider_id,
        "source": {
            "id": f"{item_id}-source",
            "name": f"Source {provider_id}",
            "tier": "Tier 1",
            "kind": "news",
            "url": url or f"https://example.com/{item_id}",
            "published_at": _ts(knowledge),
            "knowledge_available_at": _ts(knowledge),
        },
        "payload": {
            "type": "news",
            "title": title,
            "snippet": "s",
            "occurred_at": _ts(knowledge),
            "raw_metadata": {},
        },
    }


def _base_feed(
    *,
    started: datetime = T0 - timedelta(minutes=2),
    cutoff: datetime = T0,
    retrieved: datetime = T0 + timedelta(minutes=1),
    completed: datetime = T0 + timedelta(minutes=3),
    generated: datetime = T0 + timedelta(minutes=4),
    outcomes: list[dict] | None = None,
    items: list[dict] | None = None,
    pipeline_status: str = "degraded",
    coverage_gap: dict | None = None,
) -> dict:
    return {
        "schema_version": 1,
        "run_id": "",
        "window": {"start": _ts(cutoff - timedelta(hours=72)), "end": _ts(cutoff)},
        "collection_started_at": _ts(started),
        "evidence_cutoff_at": _ts(cutoff),
        "collection_completed_at": _ts(completed),
        "generated_at": _ts(generated),
        "provider_outcomes": outcomes or [],
        "producer": {"package_version": "0.1.0", "files": [], "fingerprint": "a" * 64},
        "feed_config": {"snapshot": {}, "hash": "b" * 64},
        "feed_schema": {"path": "schemas/feed.schema.json", "sha256": "c" * 64},
        "provider_contracts": [],
        "git": None,
        "content_digest": "0" * 64,
        "items": items or [],
        "pipeline": {
            "status": pipeline_status,
            "warnings": [],
            "coverage_gap": coverage_gap,
        },
    }


def _identity_feed(**kwargs) -> dict:
    """Base feed with semantic identity attached; validates cleanly."""
    feed = _base_feed(**kwargs)
    digest, run_id = recompute_feed_identity(feed)
    feed["content_digest"] = digest
    feed["run_id"] = run_id
    return feed


class _FixtureAdapter:
    def __init__(self, items: list[dict] | None = None, error: Exception | None = None):
        self.items = items or []
        self.error = error

    def fetch(self, window, client=None):
        if self.error is not None:
            raise self.error
        return SimpleNamespace(body_bytes=b"fixture")

    def normalize(self, raw, window):
        return self.items


class _ScriptedClock:
    """Returns distinct scripted instants; repeats the last on over-calls."""

    def __init__(self, values: list[datetime]):
        self._values = list(values)
        self.calls: list[datetime] = []

    def __call__(self) -> datetime:
        instant = self._values[min(len(self.calls), len(self._values) - 1)]
        self.calls.append(instant)
        return instant


# ---------------------------------------------------------------------------
# 1.1 Provider-completion permutations
# ---------------------------------------------------------------------------


def _permutation_outcomes() -> dict[str, ProviderOutcome]:
    return {
        "federal_reserve": ProviderOutcome(
            "federal_reserve",
            state="healthy",
            attempted=1,
            fetched=1,
            accepted=2,
            retrieved_at=_ts(T0 + timedelta(seconds=10)),
        ),
        "bls": ProviderOutcome("bls", state="failed", attempted=2, error="HTTP 503"),
        "cftc": ProviderOutcome("cftc", state="skipped"),
    }


def test_outcome_serialization_is_ascending_provider_id_regardless_of_completion_order():
    from follow_the_money.feed import cli as feed_cli

    cfg = _cfg()
    plan = FeedPlan(
        window_start=_ts(T0 - timedelta(hours=72)),
        evidence_cutoff_at=_ts(T0),
        bootstrap=True,
    )
    outcomes = _permutation_outcomes()
    # Same terminal states recorded under different completion schedules.
    outcomes_scrambled = {pid: outcomes[pid] for pid in ("cftc", "federal_reserve", "bls")}

    def build(outcomes_map):
        return feed_cli._build_feed(
            cfg=cfg,
            plan=plan,
            started_at=T0 - timedelta(minutes=2),
            completed_at=T0 + timedelta(minutes=3),
            outcomes=outcomes_map,
            items=[],
            status="degraded",
            warnings=[],
            now_fn=lambda: T0 + timedelta(minutes=4),
        )

    feed_a = build(outcomes)
    feed_b = build(outcomes_scrambled)
    ids = [o["provider_id"] for o in feed_a["provider_outcomes"]]
    assert ids == ["bls", "cftc", "federal_reserve"]
    assert [o["provider_id"] for o in feed_b["provider_outcomes"]] == ids
    assert feed_b["provider_outcomes"] == feed_a["provider_outcomes"]
    assert semantic_feed_projection(feed_b) == semantic_feed_projection(feed_a)
    assert feed_b["content_digest"] == feed_a["content_digest"]
    assert feed_b["run_id"] == feed_a["run_id"]
    # Healthy, failed, and skipped outcomes are all represented exactly once.
    assert {o["provider_id"]: o["state"] for o in feed_a["provider_outcomes"]} == {
        "bls": "failed",
        "cftc": "skipped",
        "federal_reserve": "healthy",
    }


def test_run_feed_outcome_order_and_identity_survive_submission_permutations(tmp_path):
    items_by_provider = {
        "bls": [_news_item("bls-item", "bls", knowledge=T0 - timedelta(hours=2))],
        "cftc": [_news_item("cftc-item", "cftc", knowledge=T0 - timedelta(hours=3))],
        "federal_reserve": [
            _news_item("fed-item", "federal_reserve", knowledge=T0 - timedelta(hours=1))
        ],
    }

    def registry(order):
        return {pid: _FixtureAdapter(items=items_by_provider.get(pid, [])) for pid in order}

    def failing_registry(order):
        reg = registry(order)
        reg["sec_edgar"] = _FixtureAdapter(error=RuntimeError("provider unavailable"))
        return reg

    def run(reg, enabled):
        return run_feed(
            output_root=str(tmp_path / ("-".join(enabled))),
            cutoff=T0,
            dry_run=True,
            providers_fn=lambda: reg,
            enabled_provider_ids=enabled,
        )

    # Same providers submitted in different schedules, one failing.
    ids = ["bls", "cftc", "federal_reserve", "sec_edgar"]
    result_a = run(failing_registry(ids), ids)
    result_b = run(failing_registry(list(reversed(ids))), list(reversed(ids)))
    assert result_a.exit_code == 1 and result_b.exit_code == 1
    for result in (result_a, result_b):
        assert [o["provider_id"] for o in result.feed["provider_outcomes"]] == ids
        assert {o["provider_id"]: o["state"] for o in result.feed["provider_outcomes"]} == {
            "bls": "healthy",
            "cftc": "healthy",
            "federal_reserve": "healthy",
            "sec_edgar": "failed",
        }
    assert semantic_feed_projection(result_a.feed) == semantic_feed_projection(result_b.feed)
    assert result_a.feed["content_digest"] == result_b.feed["content_digest"]
    assert result_a.feed["run_id"] == result_b.feed["run_id"]


# ---------------------------------------------------------------------------
# 1.2 Item-input permutations
# ---------------------------------------------------------------------------


def test_exact_url_duplicate_permutations_are_identical():
    a = _news_item("i1", "p1", knowledge=T0 - timedelta(hours=2), url="https://a.example.com/x")
    b = _news_item("i2", "p2", knowledge=T0 - timedelta(hours=1), url="https://a.example.com/x")
    results = [deduplicate_items(perm) for perm in ((a, b), (b, a))]
    for items, dropped in results:
        assert [i["id"] for i in items] == ["i1"]  # earliest knowledge survives
        assert dropped == ["i2"]
        lineage = [entry["id"] for entry in items[0]["source_lineage"]]
        assert lineage == ["i1", "i2"]  # contributing-item total order
    assert results[0] == results[1]


def test_same_source_near_duplicate_permutations_are_identical():
    a = _news_item(
        "i1",
        "p1",
        knowledge=T0 - timedelta(hours=2),
        title="美联储宣布加息25个基点",
        url="https://a.example.com/1",
    )
    b = _news_item(
        "i2",
        "p1",
        knowledge=T0 - timedelta(hours=1),
        title="美联储宣布加息25个基点。",
        url="https://a.example.com/2",
    )
    results = [deduplicate_items(perm) for perm in ((a, b), (b, a))]
    for items, dropped in results:
        assert [i["id"] for i in items] == ["i1"]
        assert dropped == ["i2"]
    assert results[0] == results[1]


def test_feed_identity_survives_item_input_permutations(tmp_path):
    items = [
        _news_item("i2", "p2", knowledge=T0 - timedelta(hours=1), url="https://a.example.com/x"),
        _news_item("i1", "p1", knowledge=T0 - timedelta(hours=2), url="https://a.example.com/x"),
    ]

    def run(permutation):
        result = run_feed(
            output_root=str(tmp_path / "out"),
            cutoff=T0,
            dry_run=True,
            providers_fn=lambda: {"p1": _FixtureAdapter(items=permutation)},
            enabled_provider_ids=["p1"],
        )
        return result

    result_a = run(items)
    result_b = run(list(reversed(items)))
    assert result_a.exit_code == 1 and result_b.exit_code == 1
    feed_a, feed_b = result_a.feed, result_b.feed
    assert [i["id"] for i in feed_a["items"]] == ["i1"]
    assert [i["id"] for i in feed_b["items"]] == ["i1"]
    assert [e["id"] for e in feed_a["items"][0]["source_lineage"]] == ["i1", "i2"]
    assert [e["id"] for e in feed_b["items"][0]["source_lineage"]] == ["i1", "i2"]
    assert semantic_feed_projection(feed_a) == semantic_feed_projection(feed_b)
    assert feed_a["content_digest"] == feed_b["content_digest"]
    assert feed_a["run_id"] == feed_b["run_id"]


def test_final_item_order_is_total_order():
    items = [
        _news_item("i1", "p1", knowledge=T0 - timedelta(hours=2)),
        _news_item("i2", "p1", knowledge=T0 - timedelta(hours=1)),
        _news_item("i3", "p1", knowledge=T0 - timedelta(hours=2)),
    ]
    ordered = deterministic_item_order(items)
    keys = [(i["source"]["knowledge_available_at"], i["id"]) for i in ordered]
    assert keys == sorted(keys)
    assert [i["id"] for i in ordered] == ["i1", "i3", "i2"]


# ---------------------------------------------------------------------------
# 1.3 Injected-clock lifecycle
# ---------------------------------------------------------------------------


def test_lifecycle_timestamps_come_from_observed_instants(tmp_path):
    started = T0 - timedelta(minutes=1)
    retrieved = T0 + timedelta(minutes=1)
    completed = T0 + timedelta(minutes=2)
    generated = T0 + timedelta(minutes=3)
    clock = _ScriptedClock([started, retrieved, completed, generated])

    result = run_feed(
        output_root=str(tmp_path / "out"),
        cutoff=T0,
        dry_run=True,
        providers_fn=lambda: {
            "federal_reserve": _FixtureAdapter(
                items=[_news_item("fed", "federal_reserve", knowledge=T0 - timedelta(hours=1))]
            )
        },
        enabled_provider_ids=["federal_reserve"],
        now_fn=clock,
    )

    assert result.exit_code == 1
    feed = result.feed
    # Exactly the four lifecycle instants were observed, in order.
    assert clock.calls == [started, retrieved, completed, generated]
    assert feed["collection_started_at"] == _ts(started)
    assert feed["provider_outcomes"][0]["retrieved_at"] == _ts(retrieved)
    assert feed["collection_completed_at"] == _ts(completed)
    assert feed["generated_at"] == _ts(generated)
    # Ordering: started <= cutoff <= retrieved <= completed <= generated.
    assert started < T0 < retrieved < completed < generated
    # No synthetic cutoff offset and no reused/copied timestamps.
    assert feed["collection_started_at"] != _ts(T0 - timedelta(seconds=30))
    assert feed["generated_at"] != feed["collection_completed_at"]
    assert feed["generated_at"] != feed["evidence_cutoff_at"]


def test_lifecycle_timestamps_normalize_aware_clock_to_utc(tmp_path):
    shanghai = timezone(timedelta(hours=8))
    cutoff = T0.astimezone(shanghai)
    started = (T0 - timedelta(minutes=1)).astimezone(shanghai)
    retrieved = (T0 + timedelta(minutes=1)).astimezone(shanghai)
    completed = (T0 + timedelta(minutes=2)).astimezone(shanghai)
    generated = (T0 + timedelta(minutes=3)).astimezone(shanghai)
    clock = _ScriptedClock([started, retrieved, completed, generated])

    result = run_feed(
        output_root=str(tmp_path / "out"),
        cutoff=cutoff,
        dry_run=True,
        providers_fn=lambda: {
            "federal_reserve": _FixtureAdapter(
                items=[_news_item("fed", "federal_reserve", knowledge=T0 - timedelta(hours=1))]
            )
        },
        enabled_provider_ids=["federal_reserve"],
        now_fn=clock,
    )

    assert result.exit_code == 1
    assert result.feed["collection_started_at"] == _ts(T0 - timedelta(minutes=1))
    assert result.feed["evidence_cutoff_at"] == _ts(T0)
    assert result.feed["provider_outcomes"][0]["retrieved_at"] == _ts(T0 + timedelta(minutes=1))
    assert result.feed["collection_completed_at"] == _ts(T0 + timedelta(minutes=2))
    assert result.feed["generated_at"] == _ts(T0 + timedelta(minutes=3))


def test_http_error_response_records_truthful_retrieved_at(tmp_path):
    started = T0 - timedelta(minutes=1)
    retrieved = T0 + timedelta(minutes=1)
    completed = T0 + timedelta(minutes=2)
    generated = T0 + timedelta(minutes=3)
    clock = _ScriptedClock([started, retrieved, completed, generated])

    result = run_feed(
        output_root=str(tmp_path / "out"),
        cutoff=T0,
        dry_run=True,
        providers_fn=lambda: {
            "federal_reserve": _FixtureAdapter(error=FetchError("HTTP 503", status_code=503))
        },
        enabled_provider_ids=["federal_reserve"],
        now_fn=clock,
    )

    assert result.exit_code == 1
    assert clock.calls == [started, retrieved, completed, generated]
    assert result.feed["provider_outcomes"][0]["retrieved_at"] == _ts(retrieved)


def test_transport_failure_without_response_keeps_retrieved_at_null(tmp_path):
    result = run_feed(
        output_root=str(tmp_path / "out"),
        cutoff=T0,
        dry_run=True,
        providers_fn=lambda: {
            "federal_reserve": _FixtureAdapter(error=FetchError("connection refused"))
        },
        enabled_provider_ids=["federal_reserve"],
    )

    assert result.exit_code == 1
    assert result.feed["provider_outcomes"][0]["retrieved_at"] is None


def test_rejected_concrete_response_preserves_observed_lifecycle_signal():
    class Client:
        def get(self, url, **kwargs):
            return SimpleNamespace(
                status_code=200,
                content=b"too large",
                headers={},
                url="https://example.com/feed",
            )

    with pytest.raises(FetchError, match="response exceeds") as exc_info:
        bounded_fetch(
            Client(),
            "https://example.com/feed",
            max_bytes=1,
            fetch_rules=[FetchRule("example.com")],
            redirect_rules=[FetchRule("example.com")],
        )

    assert exc_info.value.response_observed


# ---------------------------------------------------------------------------
# 1.4 Legacy and semantic identity vectors
# ---------------------------------------------------------------------------


def _legacy_identity(feed: dict) -> tuple[str, str]:
    legacy = canonical_digest(
        {k: v for k, v in feed.items() if k not in ("content_digest", "run_id")}
    )
    return legacy, f"{feed['evidence_cutoff_at']}::{legacy[:32]}"


def test_literal_legacy_and_semantic_vectors_both_validate_and_differ():
    outcomes = [_outcome("federal_reserve", retrieved_at=_ts(T0 + timedelta(minutes=1)))]
    items = [_news_item("i1", "federal_reserve", knowledge=T0 - timedelta(hours=1))]
    feed = _base_feed(outcomes=outcomes, items=items)

    semantic_digest, semantic_run_id = recompute_feed_identity(feed)
    legacy_digest, legacy_run_id = _legacy_identity(feed)
    assert semantic_digest == "7470dc920f40fff56e74818716eb75373bc448c2b9006563c09562864dbee261"
    assert semantic_run_id == ("2026-08-11T00:20:00.000Z::7470dc920f40fff56e74818716eb7537")
    assert legacy_digest == "89810e86a7e9471b5b4b515c4bfb498cd57cefde7b22bd64378798c1a598d19c"
    assert legacy_run_id == ("2026-08-11T00:20:00.000Z::89810e86a7e9471b5b4b515c4bfb498c")

    semantic = deepcopy(feed)
    semantic["content_digest"] = semantic_digest
    semantic["run_id"] = semantic_run_id
    validate_feed(semantic)
    assert_feed_identity(semantic)  # semantic read path

    legacy = deepcopy(feed)
    legacy["content_digest"] = legacy_digest
    legacy["run_id"] = legacy_run_id
    validate_feed(legacy)
    assert_feed_identity(legacy)  # legacy whole-envelope read path


def test_runtime_timestamps_never_change_semantic_identity():
    outcomes = [_outcome("federal_reserve", retrieved_at=_ts(T0 + timedelta(minutes=1)))]
    feed = _identity_feed(outcomes=outcomes)
    digest, run_id = feed["content_digest"], feed["run_id"]
    validate_feed(feed)
    assert_feed_identity(feed)

    # Every execution-audit timestamp may move without changing identity.
    for field, new_value in [
        ("collection_started_at", _ts(T0 - timedelta(minutes=5))),
        ("collection_completed_at", _ts(T0 + timedelta(minutes=3, seconds=30))),
        ("generated_at", _ts(T0 + timedelta(minutes=10))),
    ]:
        mutated = deepcopy(feed)
        mutated[field] = new_value
        assert recompute_feed_identity(mutated) == (digest, run_id)
        validate_feed(mutated)
        assert_feed_identity(mutated)

    mutated = deepcopy(feed)
    mutated["provider_outcomes"][0]["retrieved_at"] = _ts(T0 + timedelta(minutes=2))
    assert recompute_feed_identity(mutated) == (digest, run_id)
    validate_feed(mutated)
    assert_feed_identity(mutated)

    mutated = deepcopy(feed)
    mutated["pipeline"]["warnings"] = ["different truthful execution diagnostic"]
    assert recompute_feed_identity(mutated) == (digest, run_id)
    validate_feed(mutated)
    assert_feed_identity(mutated)

    # The legacy vector for the same content does change with timestamps.
    legacy_digest, _ = _legacy_identity(feed)
    legacy_mutated, _ = _legacy_identity(mutated)
    assert legacy_digest != legacy_mutated


def test_legacy_identity_is_exact_not_permissive():
    outcomes = [_outcome("federal_reserve", retrieved_at=_ts(T0 + timedelta(minutes=1)))]
    feed = _base_feed(outcomes=outcomes)
    legacy_digest, legacy_run_id = _legacy_identity(feed)
    feed["content_digest"] = legacy_digest
    feed["run_id"] = legacy_run_id
    validate_feed(feed)
    assert_feed_identity(feed)

    # Any audit-timestamp change breaks the exact legacy vector and there is
    # no semantic match either: fail closed.
    mutated = deepcopy(feed)
    mutated["collection_completed_at"] = _ts(T0 + timedelta(minutes=7))
    with pytest.raises(SchemaError, match="content_digest"):
        assert_feed_identity(mutated)


def test_legacy_identity_accepts_prechange_provider_completion_order():
    """A valid legacy v1 artifact may preserve worker completion order.

    Removing the exact-legacy compatibility branch from stable-order
    validation must make this test fail; newly written semantic Feeds remain
    subject to ascending provider ordering.
    """
    feed = _base_feed(
        outcomes=[
            _outcome("federal_reserve", retrieved_at=_ts(T0 + timedelta(minutes=1))),
            _outcome("bls", retrieved_at=_ts(T0 + timedelta(minutes=2))),
        ]
    )
    legacy_digest, legacy_run_id = _legacy_identity(feed)
    feed["content_digest"] = legacy_digest
    feed["run_id"] = legacy_run_id

    validate_feed(feed)
    assert_feed_identity(feed)


def test_every_semantic_projection_member_changes_identity():
    outcomes = [_outcome("federal_reserve", retrieved_at=_ts(T0 + timedelta(minutes=1)))]
    items = [_news_item("i1", "federal_reserve", knowledge=T0 - timedelta(hours=1))]
    feed = _base_feed(outcomes=outcomes, items=items)
    digest, run_id = recompute_feed_identity(feed)
    assert run_id == f"{feed['evidence_cutoff_at']}::{digest[:32]}"

    def mutate(kind, target):
        if kind == "schema_version":
            target["schema_version"] = 2
        elif kind == "window.start":
            target["window"]["start"] = _ts(T0 - timedelta(hours=48))
        elif kind == "evidence_cutoff_at":
            target["evidence_cutoff_at"] = _ts(T0 + timedelta(hours=1))
        elif kind == "outcome.accepted":
            target["provider_outcomes"][0]["accepted"] = 3
        elif kind == "outcome.error":
            target["provider_outcomes"][0]["error"] = "changed"
        elif kind == "producer":
            target["producer"]["fingerprint"] = "f" * 64
        elif kind == "feed_config":
            target["feed_config"]["hash"] = "e" * 64
        elif kind == "feed_schema":
            target["feed_schema"]["sha256"] = "d" * 64
        elif kind == "provider_contracts":
            target["provider_contracts"] = [{"provider_id": "p", "snapshot": {}, "hash": "9" * 64}]
        elif kind == "items":
            target["items"].append(
                _news_item("i2", "federal_reserve", knowledge=T0 - timedelta(hours=2))
            )
        elif kind == "pipeline.status":
            target["pipeline"]["status"] = "healthy"
        elif kind == "pipeline.coverage_gap":
            target["pipeline"]["coverage_gap"] = {
                "uncovered_start": _ts(T0 - timedelta(hours=12)),
                "uncovered_end": _ts(T0 - timedelta(hours=6)),
            }

    for kind in (
        "schema_version",
        "window.start",
        "evidence_cutoff_at",
        "outcome.accepted",
        "outcome.error",
        "producer",
        "feed_config",
        "feed_schema",
        "provider_contracts",
        "items",
        "pipeline.status",
        "pipeline.coverage_gap",
    ):
        mutated = deepcopy(feed)
        mutate(kind, mutated)
        assert recompute_feed_identity(mutated)[0] != digest, kind


# ---------------------------------------------------------------------------
# 1.5 Canonical Feed bytes and semantic publication
# ---------------------------------------------------------------------------


def test_published_bytes_are_canonical_bytes(tmp_path, monkeypatch):
    from follow_the_money.feed import cli as feed_cli

    cfg = _source_complete_cfg()
    monkeypatch.setattr(feed_cli, "_load_app_config", lambda _path: cfg)
    planned = [provider.id for provider in cfg.providers if provider.enabled]
    out = tmp_path / "out"
    registry = {
        provider_id: _FixtureAdapter(
            items=(
                [_news_item("fed", "federal_reserve", knowledge=T0 - timedelta(hours=1))]
                if provider_id == "federal_reserve"
                else []
            )
        )
        for provider_id in planned
    }
    result = run_feed(
        output_root=str(out),
        cutoff=T0,
        providers_fn=lambda: registry,
        enabled_provider_ids=planned,
    )
    assert result.exit_code == 0
    feed = result.feed
    expected = canonical_bytes(feed)
    assert (out / "latest.json").read_bytes() == expected
    dated = next((out / "daily").rglob("*.json"))
    assert dated.read_bytes() == expected
    # Canonical round-trip: parsing and re-serializing reproduces the bytes.
    parsed = json.loads(expected.decode("utf-8"))
    assert canonical_bytes(parsed) == expected
    assert parsed == feed


def _semantic_publication_bytes(
    *,
    started: datetime,
    retrieved: datetime,
    completed: datetime,
    generated: datetime,
    items: list[dict],
) -> tuple[bytes, str]:
    feed = _base_feed(
        started=started,
        retrieved=retrieved,
        completed=completed,
        generated=generated,
        outcomes=[_outcome("federal_reserve", retrieved_at=_ts(retrieved))],
        items=items,
    )
    digest, run_id = recompute_feed_identity(feed)
    feed["content_digest"] = digest
    feed["run_id"] = run_id
    return canonical_bytes(feed), run_id


def test_same_semantic_identity_with_different_audit_timing_is_idempotent(tmp_path):
    root = tmp_path / "out"
    items = [_news_item("i1", "federal_reserve", knowledge=T0 - timedelta(hours=1))]
    bytes_1, run_id = _semantic_publication_bytes(
        started=T0 - timedelta(minutes=5),
        retrieved=T0 + timedelta(minutes=1),
        completed=T0 + timedelta(minutes=3),
        generated=T0 + timedelta(minutes=4),
        items=items,
    )
    bytes_2, run_id_2 = _semantic_publication_bytes(
        started=T0 - timedelta(minutes=1),
        retrieved=T0 + timedelta(minutes=2),
        completed=T0 + timedelta(minutes=6),
        generated=T0 + timedelta(minutes=7),
        items=items,
    )
    assert run_id_2 == run_id
    assert bytes_1 != bytes_2

    first = publish_feed(
        output_root=root, cutoff=T0, run_id=run_id, feed_bytes=bytes_1, latest_bytes=bytes_1
    )
    assert first.latest_replaced and not first.idempotent
    second = publish_feed(
        output_root=root, cutoff=T0, run_id=run_id, feed_bytes=bytes_2, latest_bytes=bytes_2
    )
    assert second.idempotent
    assert not second.latest_replaced
    dated = root / "daily" / "2026-08-11" / f"{run_id}.json"
    assert dated.read_bytes() == bytes_1  # first immutable artifact retained
    assert (root / "latest.json").read_bytes() == bytes_1


def test_idempotent_recovery_repairs_latest_from_retained_dated_bytes(tmp_path):
    root = tmp_path / "out"
    items = [_news_item("i1", "federal_reserve", knowledge=T0 - timedelta(hours=1))]
    bytes_1, run_id = _semantic_publication_bytes(
        started=T0 - timedelta(minutes=5),
        retrieved=T0 + timedelta(minutes=1),
        completed=T0 + timedelta(minutes=3),
        generated=T0 + timedelta(minutes=4),
        items=items,
    )
    bytes_2, _ = _semantic_publication_bytes(
        started=T0 - timedelta(minutes=1),
        retrieved=T0 + timedelta(minutes=2),
        completed=T0 + timedelta(minutes=6),
        generated=T0 + timedelta(minutes=7),
        items=items,
    )
    # Crash state: dated committed, latest absent.
    date_dir = root / "daily" / "2026-08-11"
    date_dir.mkdir(parents=True)
    (date_dir / f"{run_id}.json").write_bytes(bytes_1)

    result = publish_feed(
        output_root=root, cutoff=T0, run_id=run_id, feed_bytes=bytes_2, latest_bytes=bytes_2
    )
    assert result.idempotent
    assert result.latest_replaced
    # latest is repaired from the retained dated bytes, not the later envelope.
    assert (root / "latest.json").read_bytes() == bytes_1
    assert (date_dir / f"{run_id}.json").read_bytes() == bytes_1


def test_same_path_semantic_mismatch_fails_closed(tmp_path):
    root = tmp_path / "out"
    items = [_news_item("i1", "federal_reserve", knowledge=T0 - timedelta(hours=1))]
    bytes_1, run_id = _semantic_publication_bytes(
        started=T0 - timedelta(minutes=5),
        retrieved=T0 + timedelta(minutes=1),
        completed=T0 + timedelta(minutes=3),
        generated=T0 + timedelta(minutes=4),
        items=items,
    )
    publish_feed(
        output_root=root, cutoff=T0, run_id=run_id, feed_bytes=bytes_1, latest_bytes=bytes_1
    )
    # Different semantic evidence (different items => different digest).
    different = _semantic_publication_bytes(
        started=T0 - timedelta(minutes=5),
        retrieved=T0 + timedelta(minutes=1),
        completed=T0 + timedelta(minutes=3),
        generated=T0 + timedelta(minutes=4),
        items=[_news_item("i-other", "federal_reserve", knowledge=T0 - timedelta(hours=2))],
    )[0]
    with pytest.raises(PublishError, match="incompatible content"):
        publish_feed(
            output_root=root,
            cutoff=T0,
            run_id=run_id,
            feed_bytes=different,
            latest_bytes=different,
        )
    dated = root / "daily" / "2026-08-11" / f"{run_id}.json"
    assert dated.read_bytes() == bytes_1  # immutable artifact untouched


def test_invalid_existing_dated_bytes_fail_closed(tmp_path):
    root = tmp_path / "out"
    items = [_news_item("i1", "federal_reserve", knowledge=T0 - timedelta(hours=1))]
    bytes_2, run_id = _semantic_publication_bytes(
        started=T0 - timedelta(minutes=1),
        retrieved=T0 + timedelta(minutes=2),
        completed=T0 + timedelta(minutes=6),
        generated=T0 + timedelta(minutes=7),
        items=items,
    )
    date_dir = root / "daily" / "2026-08-11"
    date_dir.mkdir(parents=True)
    (date_dir / f"{run_id}.json").write_bytes(b"{corrupt")

    with pytest.raises(PublishError, match="incompatible content"):
        publish_feed(
            output_root=root, cutoff=T0, run_id=run_id, feed_bytes=bytes_2, latest_bytes=bytes_2
        )
    assert (date_dir / f"{run_id}.json").read_bytes() == b"{corrupt"


def test_non_canonical_candidate_bytes_rejected(tmp_path):
    root = tmp_path / "out"
    feed = _identity_feed(outcomes=[])
    non_canonical = json.dumps(feed, indent=2).encode("utf-8")
    with pytest.raises(PublishError, match="canonical"):
        publish_feed(
            output_root=root,
            cutoff=T0,
            run_id=feed["run_id"],
            feed_bytes=non_canonical,
            latest_bytes=non_canonical,
        )
    assert not (root / "latest.json").exists()


# ---------------------------------------------------------------------------
# Strengthened semantic validation (task 3.4)
# ---------------------------------------------------------------------------


def test_validation_rejects_unordered_provider_outcomes():
    feed = _identity_feed(
        outcomes=[
            _outcome("federal_reserve", retrieved_at=_ts(T0 + timedelta(minutes=1))),
            _outcome("bls", retrieved_at=_ts(T0 + timedelta(minutes=1))),
        ]
    )
    with pytest.raises(SchemaError, match="ascending provider_id"):
        validate_feed(feed)


def test_validation_rejects_duplicate_provider_outcomes():
    feed = _identity_feed(
        outcomes=[
            _outcome("bls", retrieved_at=_ts(T0 + timedelta(minutes=1))),
            _outcome("bls", retrieved_at=_ts(T0 + timedelta(minutes=2))),
        ]
    )
    with pytest.raises(SchemaError, match="ascending provider_id"):
        validate_feed(feed)


def test_validation_rejects_unordered_items():
    feed = _identity_feed(
        outcomes=[],
        items=[
            _news_item("i2", "p1", knowledge=T0 - timedelta(hours=1)),
            _news_item("i1", "p1", knowledge=T0 - timedelta(hours=2)),
        ],
    )
    with pytest.raises(SchemaError, match="knowledge_available_at"):
        validate_feed(feed)


def test_null_retrieved_at_allowed_for_work_without_observed_response():
    feed = _identity_feed(
        outcomes=[
            _outcome("bls", state="failed", accepted=0, error="HTTP 503"),
            _outcome("cftc", state="skipped", accepted=0),
        ]
    )
    validate_feed(feed)
    assert_feed_identity(feed)
