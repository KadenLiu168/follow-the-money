"""Task 5.1-5.6 — Feed health, entity resolution, and candidate graph fixtures."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from follow_the_money.config import load_config
from follow_the_money.engine.candidates import (
    CandidateGraphError,
    build_edges,
    build_mention_nodes,
    connected_components,
    pack_blocks,
)
from follow_the_money.engine.entities import EntityResolver
from follow_the_money.engine.feed_health import (
    FeedLoadError,
    assess_health,
    check_calendar_horizon,
    load_latest_feed,
)
from follow_the_money.feed.validate import (
    assert_feed_identity,
    recompute_feed_identity,
    validate_feed,
)
from follow_the_money.ledger import Ledger, build_ledger_entry

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "config" / "config.yaml"
DEFAULT_PROVIDERS = REPO_ROOT / "config" / "providers.yaml"

T0 = datetime(2026, 8, 11, 0, 20, 0, tzinfo=UTC)


def _ts(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _cfg():
    return load_config(DEFAULT_CONFIG, DEFAULT_PROVIDERS, require_verified_enabled=False)


def _feed(**overrides) -> dict:
    feed = {
        "schema_version": 1,
        "run_id": "run_1",
        "window": {"start": _ts(T0 - timedelta(hours=72)), "end": _ts(T0)},
        "collection_started_at": _ts(T0 - timedelta(seconds=30)),
        "evidence_cutoff_at": _ts(T0),
        "collection_completed_at": _ts(T0 + timedelta(minutes=4)),
        "generated_at": _ts(T0 + timedelta(minutes=5)),
        "provider_outcomes": [],
        "producer": {"package_version": "0.1.0", "files": [], "fingerprint": "a" * 64},
        "feed_config": {"snapshot": {}, "hash": "b" * 64},
        "feed_schema": {"path": "schemas/feed.schema.json", "sha256": "c" * 64},
        "provider_contracts": [],
        "git": None,
        "content_digest": "d" * 64,
        "items": [],
        "pipeline": {"status": "healthy", "warnings": []},
        "calendar_horizon_end": _ts(T0 + timedelta(hours=26)),
    }
    feed.update(overrides)
    return feed


# ---------------------------------------------------------------------------
# Feed health
# ---------------------------------------------------------------------------


def test_healthy_feed_no_warnings():
    health = assess_health(
        _feed(),
        brief_generated_at=_ts(T0 + timedelta(minutes=10)),
        now=lambda: T0 + timedelta(minutes=10),
    )
    assert health.status == "healthy"
    assert health.warnings == []


def test_stale_boundary_30_minutes():
    # Exactly 30 minutes lag is allowed (not stale).
    health = assess_health(_feed(), brief_generated_at=_ts(T0 + timedelta(minutes=30)))
    assert health.status == "healthy"
    # 31 minutes is stale.
    health = assess_health(_feed(), brief_generated_at=_ts(T0 + timedelta(minutes=31)))
    assert health.status == "degraded"
    assert any("stale" in w for w in health.warnings)


def test_hard_lag_2h_refused():
    with pytest.raises(FeedLoadError, match="normal-mode maximum"):
        assess_health(_feed(), brief_generated_at=_ts(T0 + timedelta(hours=2, minutes=1)))


def test_clock_before_feed_cutoff():
    with pytest.raises(FeedLoadError, match="clock_before_feed"):
        assess_health(_feed(), brief_generated_at=_ts(T0 - timedelta(minutes=1)))


def test_clock_before_feed_generated():
    with pytest.raises(FeedLoadError, match="clock_before_feed"):
        assess_health(
            _feed(), brief_generated_at=_ts(T0 + timedelta(minutes=3))
        )  # < generated(+5m)


def test_degraded_feed_carries_warnings():
    feed = _feed()
    feed["pipeline"] = {"status": "degraded", "warnings": ["某来源不可用"]}
    health = assess_health(feed, brief_generated_at=_ts(T0 + timedelta(minutes=10)))
    assert health.status == "degraded"
    assert "某来源不可用" in health.warnings


def test_schema_valid_failure_feed_is_not_consumable():
    feed = _feed(pipeline={"status": "failure", "warnings": ["no accepted item"]})
    digest, run_id = recompute_feed_identity(feed)
    feed["content_digest"] = digest
    feed["run_id"] = run_id
    validate_feed(feed)
    assert_feed_identity(feed)

    with pytest.raises(FeedLoadError, match="pipeline.status=failure"):
        assess_health(feed, brief_generated_at=_ts(T0 + timedelta(minutes=10)))


def test_calendar_horizon_contract():
    check_calendar_horizon(_feed(), _ts(T0 + timedelta(minutes=10)))  # ok: horizon covers +24h
    with pytest.raises(FeedLoadError, match="calendar_horizon_end"):
        feed = _feed()
        feed["calendar_horizon_end"] = _ts(T0 + timedelta(hours=20))  # too short
        check_calendar_horizon(feed, _ts(T0 + timedelta(minutes=10)))


def test_load_latest_feed_missing(tmp_path):
    with pytest.raises(FeedLoadError, match="not found"):
        load_latest_feed(tmp_path / "nope.json")


def test_load_latest_feed_invalid(tmp_path):
    p = tmp_path / "latest.json"
    p.write_bytes(b"{not json")
    with pytest.raises(FeedLoadError, match="invalid"):
        load_latest_feed(p)


# ---------------------------------------------------------------------------
# Entity resolution
# ---------------------------------------------------------------------------


def test_known_fed_aliases_resolve():
    resolver = EntityResolver(_cfg().entities)
    for alias in ("Federal Reserve", "Fed", "FOMC"):
        r = resolver.resolve(alias)
        assert r.entity_id == "ent_fed"


def test_unknown_entity_preserved():
    resolver = EntityResolver(_cfg().entities)
    r = resolver.resolve("某神秘公司")
    assert r.entity_id is None
    assert r.display_name == "某神秘公司"


def test_ambiguous_alias_conflict():
    # An alias mapped to two entities yields ambiguous/conflict.
    from follow_the_money.config.model import Entity

    resolver = EntityResolver(
        [
            Entity(id="e1", name="同名", name_zh="同名甲", aliases=("重复名",)),
            Entity(id="e2", name="同名", name_zh="同名乙", aliases=("重复名",)),
        ]
    )
    r = resolver.resolve("重复名")
    assert r.ambiguous or r.conflict


# ---------------------------------------------------------------------------
# Candidate graph
# ---------------------------------------------------------------------------


def _seed(
    ledger: Ledger,
    *,
    evidence: str,
    subject: str,
    predicate: str,
    value: str,
    knowledge: datetime,
    origin: str = "news",
    title: str | None = None,
) -> None:
    entry = build_ledger_entry(
        entry_type="FACT",
        origin_payload=origin,
        evidence_id=evidence,
        subject=subject,
        predicate=predicate,
        effective_time=_ts(knowledge),
        effective_precision="instant",
        value=value,
        unit="unit",
        knowledge_available_at=_ts(knowledge),
        raw_subject=title,
    )
    ledger.add(entry)


def test_mention_nodes_only_seeds():
    ledger = Ledger()
    _seed(ledger, evidence="e1", subject="ent_a", predicate="p", value="1", knowledge=T0)
    _seed(ledger, evidence="e2", subject="ent_b", predicate="q", value="2", knowledge=T0)
    # non-seed (market_data) excluded
    ledger.add(
        build_ledger_entry(
            entry_type="OBSERVATION",
            origin_payload="market_data",
            evidence_id="e3",
            subject="idx",
            predicate="close",
            effective_time=_ts(T0),
            effective_precision="instant",
            value="3",
            unit="index",
            knowledge_available_at=_ts(T0),
        )
    )
    nodes = build_mention_nodes(ledger.entries())
    assert len(nodes) == 2


def test_equal_fact_key_edges():
    ledger = Ledger()
    _seed(ledger, evidence="e1", subject="ent_a", predicate="p", value="1", knowledge=T0)
    _seed(
        ledger,
        evidence="e2",
        subject="ent_a",
        predicate="p",
        value="1",
        knowledge=T0 + timedelta(hours=1),
    )
    facts = {f.fact_id: f for f in ledger.entries()}
    nodes = build_mention_nodes(ledger.entries())
    edges = build_edges(nodes, facts, EntityResolver([]))
    assert len(edges) == 1


def test_shared_entity_48h_boundary():
    ledger = Ledger()
    _seed(ledger, evidence="e1", subject="ent_a", predicate="p", value="1", knowledge=T0)
    _seed(
        ledger,
        evidence="e2",
        subject="ent_a",
        predicate="p",
        value="2",
        knowledge=T0 + timedelta(hours=48),
    )
    _seed(
        ledger,
        evidence="e3",
        subject="ent_a",
        predicate="p",
        value="3",
        knowledge=T0 + timedelta(hours=49),
    )
    _seed(
        ledger,
        evidence="e4",
        subject="ent_a",
        predicate="p",
        value="4",
        knowledge=T0 + timedelta(hours=98),
    )  # 49h from e3, 50h from e2
    facts = {f.fact_id: f for f in ledger.entries()}
    nodes = build_mention_nodes(ledger.entries())
    edges = build_edges(nodes, facts, EntityResolver([]))
    # e1-e2 at exactly 48h: edge. e2-e3 at 1h: edge. e3-e4 at 49h: NO edge.
    # e1-e3 at 49h: no edge. e1-e4/e2-e4: no edge.
    assert len(edges) == 2


def test_different_entities_never_join_on_title():
    ledger = Ledger()
    _seed(ledger, evidence="e1", subject="ent_a", predicate="p", value="1", knowledge=T0)
    _seed(
        ledger,
        evidence="e2",
        subject="ent_b",
        predicate="p",
        value="1",
        knowledge=T0 + timedelta(hours=1),
    )
    facts = {f.fact_id: f for f in ledger.entries()}
    nodes = build_mention_nodes(ledger.entries())
    edges = build_edges(nodes, facts, EntityResolver([]))
    assert len(edges) == 0


def test_bridge_evidence_no_evidence_only_edge():
    # Two seed facts from the SAME evidence with different subjects must not
    # connect merely by sharing the evidence.
    ledger = Ledger()
    _seed(ledger, evidence="bridge", subject="ent_a", predicate="p", value="1", knowledge=T0)
    _seed(
        ledger,
        evidence="bridge",
        subject="ent_b",
        predicate="q",
        value="2",
        knowledge=T0 + timedelta(hours=1),
    )
    facts = {f.fact_id: f for f in ledger.entries()}
    nodes = build_mention_nodes(ledger.entries())
    edges = build_edges(nodes, facts, EntityResolver([]))
    assert len(edges) == 0


def test_components_and_block_packing():
    ledger = Ledger()
    _seed(ledger, evidence="e1", subject="ent_a", predicate="p", value="1", knowledge=T0)
    _seed(
        ledger,
        evidence="e2",
        subject="ent_b",
        predicate="q",
        value="2",
        knowledge=T0 + timedelta(hours=1),
    )
    facts = {f.fact_id: f for f in ledger.entries()}
    nodes = build_mention_nodes(ledger.entries())
    edges = build_edges(nodes, facts, EntityResolver([]))
    components = connected_components(nodes, edges, facts)
    assert len(components) == 2  # disconnected
    blocks = pack_blocks(components)
    assert len(blocks) == 1  # both fit in one block
    assert blocks[0].seed_count == 2
    assert blocks[0].projected_records == 2


def test_component_identity_from_sorted_mention_ids():
    ledger = Ledger()
    _seed(ledger, evidence="e1", subject="ent_a", predicate="p", value="1", knowledge=T0)
    _seed(
        ledger,
        evidence="e2",
        subject="ent_b",
        predicate="q",
        value="2",
        knowledge=T0 + timedelta(hours=1),
    )
    facts = {f.fact_id: f for f in ledger.entries()}
    nodes = build_mention_nodes(ledger.entries())
    edges = build_edges(nodes, facts, EntityResolver([]))
    c1 = connected_components(nodes, edges, facts)
    c2 = connected_components(list(reversed(nodes)), edges, facts)
    assert [c.component_id for c in c1] == [c.component_id for c in c2]


def test_oversized_component_fails_before_resolver():
    # A single component with >24 seeds exceeds the seed bound.
    ledger = Ledger()
    for i in range(25):
        _seed(ledger, evidence=f"e{i}", subject="ent_a", predicate="p", value=str(i), knowledge=T0)
    facts = {f.fact_id: f for f in ledger.entries()}
    nodes = build_mention_nodes(ledger.entries())
    edges = build_edges(nodes, facts, EntityResolver([]))
    components = connected_components(nodes, edges, facts)
    assert len(components) == 1
    with pytest.raises(CandidateGraphError, match="candidate_group_too_large"):
        pack_blocks(components)


def test_capacity_exceeded_41_blocks():
    # 41 disconnected components, each with 20 seeds => each is exactly one
    # block (20-record limit), producing 41 blocks > 40 => capacity_exceeded.
    ledger = Ledger()
    for i in range(41):
        for j in range(20):
            _seed(
                ledger,
                evidence=f"e{i}_{j}",
                subject=f"ent_{i}",
                predicate="p",
                value=str(j),
                knowledge=T0 + timedelta(hours=i),
            )
    facts = {f.fact_id: f for f in ledger.entries()}
    nodes = build_mention_nodes(ledger.entries())
    edges = build_edges(nodes, facts, EntityResolver([]))
    components = connected_components(nodes, edges, facts)
    assert len(components) == 41
    with pytest.raises(CandidateGraphError, match="capacity_exceeded"):
        pack_blocks(components)
