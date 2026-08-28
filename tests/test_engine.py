"""Task 5.1-5.6 — Feed health, entity resolution, and candidate graph fixtures."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from follow_the_money.config import load_config
from follow_the_money.config.model import Entity
from follow_the_money.engine.candidates import (
    build_edges,
    build_mention_nodes,
    connected_components,
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


def test_exact_registry_membership_does_not_change_alias_or_fuzzy_resolution():
    resolver = EntityResolver(_cfg().entities)
    assert resolver.resolve("Fed").entity_id == "ent_fed"
    assert resolver.resolve("Reserve").entity_id == "ent_fed"


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
    raw_subject: str | None = None,
    effective: datetime | None = None,
):
    entry = build_ledger_entry(
        entry_type="FACT",
        origin_payload=origin,
        evidence_id=evidence,
        subject=subject,
        predicate=predicate,
        effective_time=_ts(effective or knowledge),
        effective_precision="instant",
        value=value,
        unit="unit",
        knowledge_available_at=_ts(knowledge),
        raw_subject=raw_subject,
    )
    ledger.add(entry)
    return entry


def _resolver(*entity_ids: str) -> EntityResolver:
    return EntityResolver(
        [Entity(id=entity_id, name=entity_id, name_zh=entity_id) for entity_id in entity_ids]
    )


def _candidate_edges(
    ledger: Ledger,
    resolver: EntityResolver,
    evidence_titles: dict[str, str] | None = None,
):
    facts = {f.fact_id: f for f in ledger.entries()}
    nodes = build_mention_nodes(ledger.entries())
    edges = build_edges(
        nodes,
        facts,
        resolver,
        evidence_titles=evidence_titles or {},
    )
    return facts, nodes, edges


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
        effective=T0,
    )
    _, _, edges = _candidate_edges(ledger, EntityResolver([]))
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
    _, _, edges = _candidate_edges(ledger, _resolver("ent_a"))
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
    _, _, edges = _candidate_edges(
        ledger,
        _resolver("ent_a", "ent_b"),
        {"e1": "Alpha beta gamma delta", "e2": "Alpha beta gamma epsilon"},
    )
    assert len(edges) == 0


def test_registry_recognizes_canonical_id_without_ent_prefix():
    ledger = Ledger()
    _seed(
        ledger,
        evidence="e1",
        subject="canonical-42",
        predicate="p",
        value="1",
        knowledge=T0,
    )
    _seed(
        ledger,
        evidence="e2",
        subject="canonical-42",
        predicate="q",
        value="2",
        knowledge=T0 + timedelta(hours=1),
    )
    _, _, edges = _candidate_edges(
        ledger,
        _resolver("canonical-42"),
        {"e1": "Alpha beta gamma delta", "e2": "Alpha beta gamma epsilon"},
    )
    assert len(edges) == 1


def test_unregistered_ent_prefix_does_not_create_canonical_entity_edge():
    ledger = Ledger()
    _seed(
        ledger,
        evidence="e1",
        subject="ent_missing",
        predicate="p",
        value="1",
        knowledge=T0,
    )
    _seed(
        ledger,
        evidence="e2",
        subject="ent_missing",
        predicate="q",
        value="2",
        knowledge=T0 + timedelta(hours=1),
    )
    _, _, edges = _candidate_edges(
        ledger,
        EntityResolver([]),
        {"e1": "Alpha beta gamma delta", "e2": "Alpha beta gamma epsilon"},
    )
    assert len(edges) == 0


@pytest.mark.parametrize("subject", ["raw_registered", "unresolved_registered"])
def test_registry_membership_overrides_raw_and_unresolved_prefixes(subject: str):
    ledger = Ledger()
    _seed(
        ledger,
        evidence="e1",
        subject=subject,
        predicate="p",
        value="1",
        knowledge=T0,
    )
    _seed(
        ledger,
        evidence="e2",
        subject=subject,
        predicate="q",
        value="2",
        knowledge=T0 + timedelta(hours=1),
    )
    _, _, edges = _candidate_edges(
        ledger,
        _resolver(subject),
        {"e1": "Alpha beta gamma delta", "e2": "Alpha beta gamma epsilon"},
    )
    assert len(edges) == 1


def test_configured_alias_is_not_a_canonical_id_for_candidate_grouping():
    ledger = Ledger()
    _seed(
        ledger,
        evidence="e1",
        subject="known alias",
        predicate="p",
        value="1",
        knowledge=T0,
    )
    _seed(
        ledger,
        evidence="e2",
        subject="known alias",
        predicate="q",
        value="2",
        knowledge=T0 + timedelta(hours=1),
    )
    resolver = EntityResolver(
        [
            Entity(
                id="canonical-42",
                name="Canonical Corp",
                name_zh="Canonical Corp",
                aliases=("known alias",),
            )
        ]
    )
    _, _, edges = _candidate_edges(
        ledger,
        resolver,
        {"e1": "Alpha beta gamma delta", "e2": "Alpha beta gamma epsilon"},
    )
    assert len(edges) == 0


def test_same_entity_title_edge_uses_explicit_evidence_titles_at_threshold():
    ledger = Ledger()
    _seed(
        ledger,
        evidence="e1",
        subject="ent_a",
        predicate="p",
        value="1",
        knowledge=T0,
        raw_subject="not an evidence title",
    )
    _seed(
        ledger,
        evidence="e2",
        subject="ent_a",
        predicate="q",
        value="2",
        knowledge=T0 + timedelta(hours=1),
        raw_subject="also not an evidence title",
    )
    _, _, edges = _candidate_edges(
        ledger,
        _resolver("ent_a"),
        {"e1": "Alpha beta gamma delta", "e2": "Alpha beta gamma epsilon"},
    )
    assert len(edges) == 1


def test_same_entity_title_edge_below_threshold_is_rejected():
    ledger = Ledger()
    _seed(ledger, evidence="e1", subject="ent_a", predicate="p", value="1", knowledge=T0)
    _seed(
        ledger,
        evidence="e2",
        subject="ent_a",
        predicate="q",
        value="2",
        knowledge=T0 + timedelta(hours=1),
    )
    _, _, edges = _candidate_edges(
        ledger,
        _resolver("ent_a"),
        {"e1": "Oil supply cut expected", "e2": "Oil supply cut announced"},
    )
    assert len(edges) == 0


@pytest.mark.parametrize("titles", [{"e1": "Alpha beta gamma delta"}, {"e1": "", "e2": ""}])
def test_missing_or_empty_evidence_title_does_not_create_title_edge(titles: dict[str, str]):
    ledger = Ledger()
    _seed(ledger, evidence="e1", subject="ent_a", predicate="p", value="1", knowledge=T0)
    _seed(
        ledger,
        evidence="e2",
        subject="ent_a",
        predicate="q",
        value="2",
        knowledge=T0 + timedelta(hours=1),
    )
    _, _, edges = _candidate_edges(ledger, _resolver("ent_a"), titles)
    assert len(edges) == 0


def test_missing_evidence_titles_never_fall_back_to_raw_subject():
    ledger = Ledger()
    _seed(
        ledger,
        evidence="e1",
        subject="ent_a",
        predicate="p",
        value="1",
        knowledge=T0,
        raw_subject="identical fallback title",
    )
    _seed(
        ledger,
        evidence="e2",
        subject="ent_a",
        predicate="q",
        value="2",
        knowledge=T0 + timedelta(hours=1),
        raw_subject="identical fallback title",
    )
    _, _, edges = _candidate_edges(ledger, _resolver("ent_a"))
    assert len(edges) == 0


def test_raw_subject_cannot_influence_title_similarity():
    ledger = Ledger()
    _seed(
        ledger,
        evidence="e1",
        subject="ent_a",
        predicate="p",
        value="1",
        knowledge=T0,
        raw_subject="unrelated raw subject one",
    )
    _seed(
        ledger,
        evidence="e2",
        subject="ent_a",
        predicate="q",
        value="2",
        knowledge=T0 + timedelta(hours=1),
        raw_subject="unrelated raw subject two",
    )
    _, _, edges = _candidate_edges(
        ledger,
        _resolver("ent_a"),
        {"e1": "Alpha beta gamma delta", "e2": "Alpha beta gamma epsilon"},
    )
    assert len(edges) == 1


def test_entityless_title_edge_observes_origin_predicate_time_and_threshold():
    ledger = Ledger()
    _seed(
        ledger,
        evidence="e1",
        subject="raw_a",
        predicate="p",
        value="1",
        knowledge=T0,
        origin="news",
    )
    _seed(
        ledger,
        evidence="e2",
        subject="raw_b",
        predicate="p",
        value="2",
        knowledge=T0 + timedelta(hours=12),
        origin="news",
    )
    _, _, edges = _candidate_edges(
        ledger,
        EntityResolver([]),
        {"e1": "China growth outlook improves", "e2": "China growth outlook improved"},
    )
    assert len(edges) == 1


@pytest.mark.parametrize(
    "origin,predicate,knowledge,titles",
    [
        (
            "filing",
            "p",
            T0 + timedelta(hours=1),
            {"e1": "China growth outlook improves", "e2": "China growth outlook improved"},
        ),
        (
            "news",
            "q",
            T0 + timedelta(hours=1),
            {"e1": "China growth outlook improves", "e2": "China growth outlook improved"},
        ),
        (
            "news",
            "p",
            T0 + timedelta(hours=13),
            {"e1": "China growth outlook improves", "e2": "China growth outlook improved"},
        ),
        (
            "news",
            "p",
            T0 + timedelta(hours=1),
            {"e1": "China growth outlook improves", "e2": "China growth outlook worsens"},
        ),
    ],
)
def test_entityless_title_edge_negative_boundaries(
    origin: str, predicate: str, knowledge: datetime, titles: dict[str, str]
):
    ledger = Ledger()
    _seed(ledger, evidence="e1", subject="raw_a", predicate="p", value="1", knowledge=T0)
    _seed(
        ledger,
        evidence="e2",
        subject="raw_b",
        predicate=predicate,
        value="2",
        knowledge=knowledge,
        origin=origin,
    )
    _, _, edges = _candidate_edges(ledger, EntityResolver([]), titles)
    assert len(edges) == 0


@pytest.mark.parametrize(
    "entity_ids,predicate,title_a,expected_edges",
    [
        (("ent_a",), "q", "0123456789a", 1),  # Jaccard = 0.45
        (("ent_a",), "q", "0123456789", 0),  # Jaccard = 0.40
        ((), "p", "0123456789abcdefghi", 1),  # Jaccard = 0.85
        ((), "p", "0123456789abcdefgh", 0),  # Jaccard = 0.80
    ],
)
def test_candidate_title_thresholds_are_exact_and_inclusive(
    entity_ids: tuple[str, ...], predicate: str, title_a: str, expected_edges: int
):
    ledger = Ledger()
    subject = "ent_a" if entity_ids else "raw_a"
    other_subject = subject if entity_ids else "raw_b"
    _seed(ledger, evidence="e1", subject=subject, predicate="p", value="1", knowledge=T0)
    _seed(
        ledger,
        evidence="e2",
        subject=other_subject,
        predicate=predicate,
        value="2",
        knowledge=T0 + timedelta(hours=1),
    )
    _, _, edges = _candidate_edges(
        ledger,
        _resolver(*entity_ids),
        {"e1": title_a, "e2": "0123456789abcdefghijkl"},
    )
    assert len(edges) == expected_edges


@pytest.mark.parametrize(
    "knowledge_gap,effective_gap,expected_edges",
    [
        (timedelta(hours=49), timedelta(hours=1), 0),
        (timedelta(hours=1), timedelta(hours=49), 1),
    ],
)
def test_candidate_time_window_uses_knowledge_availability(
    knowledge_gap: timedelta, effective_gap: timedelta, expected_edges: int
):
    ledger = Ledger()
    _seed(
        ledger,
        evidence="e1",
        subject="ent_a",
        predicate="p",
        value="1",
        knowledge=T0,
        effective=T0,
    )
    _seed(
        ledger,
        evidence="e2",
        subject="ent_a",
        predicate="p",
        value="2",
        knowledge=T0 + knowledge_gap,
        effective=T0 + effective_gap,
    )
    _, _, edges = _candidate_edges(ledger, _resolver("ent_a"))
    assert len(edges) == expected_edges


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
    _, _, edges = _candidate_edges(ledger, _resolver("ent_a", "ent_b"))
    assert len(edges) == 0


def test_components_are_returned_without_transport_packing():
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
    facts, nodes, edges = _candidate_edges(ledger, _resolver("ent_a", "ent_b"))
    components = connected_components(nodes, edges, facts)
    assert len(components) == 2  # disconnected
    assert [c.seed_fact_ids for c in components] == [
        (entry.fact_id,) for entry in sorted(ledger.entries(), key=lambda f: f.fact_id)
    ]


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
    facts, nodes, edges = _candidate_edges(ledger, _resolver("ent_a", "ent_b"))
    c1 = connected_components(nodes, edges, facts)
    c2 = connected_components(list(reversed(nodes)), edges, facts)
    assert [c.component_id for c in c1] == [c.component_id for c in c2]


def test_candidate_graph_is_fully_deterministic_under_fact_and_title_permutations():
    specs = [
        ("e1", "ent_a", "p", "1", T0, "news"),
        ("e2", "ent_a", "q", "2", T0 + timedelta(hours=1), "news"),
        ("e3", "ent_b", "p", "3", T0, "news"),
        ("e4", "raw_a", "p", "4", T0, "news"),
        ("e5", "raw_b", "p", "5", T0 + timedelta(hours=1), "news"),
    ]
    titles = {
        "e1": "Alpha beta gamma delta",
        "e2": "Alpha beta gamma epsilon",
        "e3": "Unrelated title",
        "e4": "China growth outlook improves",
        "e5": "China growth outlook improved",
    }

    def snapshot(order: list[int], title_order: list[str]):
        ledger = Ledger()
        entries = []
        for i in order:
            evidence, subject, predicate, value, knowledge, origin = specs[i]
            entries.append(
                _seed(
                    ledger,
                    evidence=evidence,
                    subject=subject,
                    predicate=predicate,
                    value=value,
                    knowledge=knowledge,
                    origin=origin,
                )
            )
        ordered_titles = {evidence: titles[evidence] for evidence in title_order}
        facts = {entry.fact_id: entry for entry in entries}
        nodes = build_mention_nodes(entries)
        edges = build_edges(
            nodes,
            facts,
            _resolver("ent_a", "ent_b"),
            evidence_titles=ordered_titles,
        )
        components = connected_components(nodes, edges, facts)
        return (
            tuple(node.id for node in nodes),
            tuple(sorted(edges)),
            tuple(component.mention_ids for component in components),
            tuple(component.component_id for component in components),
            tuple(component.seed_fact_ids for component in components),
        )

    first = snapshot(list(range(len(specs))), list(titles))
    second = snapshot(list(reversed(range(len(specs)))), list(reversed(titles)))
    assert second == first


def test_oversized_component_is_retained_without_transport_bound():
    # A single component with >24 seeds remains a complete domain component.
    ledger = Ledger()
    for i in range(25):
        _seed(ledger, evidence=f"e{i}", subject="ent_a", predicate="p", value=str(i), knowledge=T0)
    facts, nodes, edges = _candidate_edges(ledger, _resolver("ent_a"))
    components = connected_components(nodes, edges, facts)
    assert len(components) == 1
    assert len(components[0].seed_fact_ids) == 25


def test_large_component_payload_is_retained_without_transport_byte_bound():
    ledger = Ledger()
    entry = _seed(
        ledger,
        evidence="e1",
        subject="ent_a",
        predicate="p",
        value="x" * (32 * 1024 + 1),
        knowledge=T0,
    )
    facts, nodes, edges = _candidate_edges(ledger, _resolver("ent_a"))
    components = connected_components(nodes, edges, facts)
    assert len(components) == 1
    assert components[0].facts == (entry,)


def test_many_components_are_returned_without_transport_capacity():
    # 41 disconnected components remain in canonical order without a block cap.
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
    facts, nodes, edges = _candidate_edges(
        ledger,
        _resolver(*(f"ent_{i}" for i in range(41))),
    )
    components = connected_components(nodes, edges, facts)
    assert len(components) == 41
    assert [c.component_id for c in components] == sorted(c.component_id for c in components)
