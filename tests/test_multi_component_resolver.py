"""Regression contract for packed resolver blocks with multiple components."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from follow_the_money.engine.candidates import (
    CandidateBlock,
    Component,
    build_edges,
    build_mention_nodes,
    connected_components,
    pack_blocks,
)
from follow_the_money.engine.entities import EntityResolver
from follow_the_money.engine.resolution import ResolutionError
from follow_the_money.ledger import Ledger, build_ledger_entry
from follow_the_money.market.formulas import normative_decimal_context
from follow_the_money.pipeline import feed_to_ledger, run_pipeline
from follow_the_money.schema import SchemaError, validate_against

T0 = datetime(2026, 8, 11, 0, 20, tzinfo=UTC)


def _ts(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _component(prefix: str, count: int = 1) -> tuple[Component, list]:
    facts = []
    for i in range(count):
        facts.append(
            build_ledger_entry(
                entry_type="FACT",
                origin_payload="news",
                evidence_id=f"ev_{prefix}_{i}",
                subject=f"entity_{prefix}",
                predicate=f"predicate_{prefix}_{i}",
                effective_time=_ts(T0 + timedelta(minutes=i)),
                effective_precision="instant",
                value=str(i),
                unit="unit",
                knowledge_available_at=_ts(T0 + timedelta(minutes=i)),
            )
        )
    return (
        Component(
            component_id=f"comp_{prefix}",
            mention_ids=tuple(f"mention_{prefix}_{i}" for i in range(count)),
            evidence_ids=tuple(f"ev_{prefix}_{i}" for i in range(count)),
            seed_fact_ids=tuple(f.fact_id for f in facts),
            facts=tuple(facts),
        ),
        facts,
    )


def _block(*counts: int) -> tuple[CandidateBlock, Ledger, tuple[Component, ...]]:
    components = []
    all_facts = []
    for index, count in enumerate(counts):
        component, facts = _component(f"c{index}", count)
        components.append(component)
        all_facts.extend(facts)
    ledger = Ledger()
    for fact in all_facts:
        ledger.add(fact)
    components_tuple = tuple(components)
    return (
        CandidateBlock(
            block_id="block_multi",
            components=components_tuple,
            projected_records=sum(len(c.projection_records()) for c in components_tuple),
            seed_count=sum(len(c.seed_fact_ids) for c in components_tuple),
        ),
        ledger,
        components_tuple,
    )


def _proposal(
    *,
    position: str,
    component_alias: str,
    fact_id: str,
    evidence_id: str,
    entity_id: str,
    family: str = "unknown",
    relations: list[dict] | None = None,
) -> dict:
    return {
        "component_alias": component_alias,
        "position_alias": position,
        "event_type": "news",
        "event_defining_fact_ids": [fact_id],
        "evidence_ids": [evidence_id],
        "supporting_fact_ids": [],
        "entity_ids": [entity_id],
        "story_family_label": family,
        "coexistence_relations": relations or [],
    }


def _unresolved(*, component_alias: str, fact_id: str, evidence_id: str) -> dict:
    return {
        "component_alias": component_alias,
        "seed_fact_ids": [fact_id],
        "evidence_ids": [evidence_id],
        "reason": "ambiguous",
    }


def _resolver_output(proposals: list[dict], unresolved: list[dict]) -> dict:
    return {"proposals": proposals, "unresolved_groups": unresolved}


def _resolve_block(**kwargs):
    from follow_the_money.engine.resolution import resolve_block

    return resolve_block(**kwargs)


def test_resolver_schema_requires_item_level_component_ownership() -> None:
    valid = _resolver_output([], [])
    validate_against("resolver-output.schema.json", valid)

    old_shape = {
        "component_alias": "c0",
        "proposals": [],
        "unresolved_groups": [],
    }
    with pytest.raises(SchemaError):
        validate_against("resolver-output.schema.json", old_shape)

    mixed_shape = {**valid, "component_alias": "c0"}
    with pytest.raises(SchemaError):
        validate_against("resolver-output.schema.json", mixed_shape)

    unknown_shape = {**valid, "components": []}
    with pytest.raises(SchemaError):
        validate_against("resolver-output.schema.json", unknown_shape)

    missing_proposal_alias = _resolver_output([{"position_alias": "p00"}], [])
    with pytest.raises(SchemaError):
        validate_against("resolver-output.schema.json", missing_proposal_alias)

    missing_unresolved_alias = _resolver_output(
        [], [{"seed_fact_ids": ["fact_1"], "evidence_ids": ["ev_1"], "reason": "ambiguous"}]
    )
    with pytest.raises(SchemaError):
        validate_against("resolver-output.schema.json", missing_unresolved_alias)


def test_two_components_produce_two_events_in_canonical_component_order() -> None:
    block, ledger, components = _block(1, 1)
    f0, f1 = components[0].facts[0], components[1].facts[0]
    output = _resolver_output(
        [
            _proposal(
                position="p00",
                component_alias="c0",
                fact_id=f0.fact_id,
                evidence_id=f0.evidence_id,
                entity_id=f0.subject,
            ),
            _proposal(
                position="p01",
                component_alias="c1",
                fact_id=f1.fact_id,
                evidence_id=f1.evidence_id,
                entity_id=f1.subject,
            ),
        ],
        [],
    )

    events, unresolved = _resolve_block(
        block=block, output=output, ledger=ledger, resolver=EntityResolver([])
    )

    assert [event["key_fact_ids"] for event in events] == [[f0.fact_id], [f1.fact_id]]
    assert unresolved == []


def test_proposal_plus_unresolved_retains_later_component_audit_data() -> None:
    block, ledger, components = _block(1, 1)
    f0, f1 = components[0].facts[0], components[1].facts[0]
    events, unresolved = _resolve_block(
        block=block,
        output=_resolver_output(
            [
                _proposal(
                    position="p00",
                    component_alias="c0",
                    fact_id=f0.fact_id,
                    evidence_id=f0.evidence_id,
                    entity_id=f0.subject,
                )
            ],
            [_unresolved(component_alias="c1", fact_id=f1.fact_id, evidence_id=f1.evidence_id)],
        ),
        ledger=ledger,
        resolver=EntityResolver([]),
    )

    assert len(events) == 1
    assert unresolved == [
        {
            "component_id": components[1].component_id,
            "seed_fact_ids": [f1.fact_id],
            "evidence_ids": [f1.evidence_id],
            "reason": "ambiguous",
        }
    ]


def test_all_unresolved_is_a_valid_sparse_block_result() -> None:
    block, ledger, components = _block(1, 1)
    unresolved = [
        _unresolved(
            component_alias=f"c{i}",
            fact_id=component.facts[0].fact_id,
            evidence_id=component.evidence_ids[0],
        )
        for i, component in enumerate(components)
    ]

    events, normalized = _resolve_block(
        block=block,
        output=_resolver_output([], unresolved),
        ledger=ledger,
        resolver=EntityResolver([]),
    )

    assert events == []
    assert [group["component_id"] for group in normalized] == [
        components[0].component_id,
        components[1].component_id,
    ]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("component_alias", "c9"),
        ("event_defining_fact_ids", ["ghost"]),
        ("evidence_ids", ["ev_c1_0"]),
        ("entity_ids", ["entity_c1"]),
        ("supporting_fact_ids", ["ghost"]),
    ],
)
def test_component_local_reference_validation_rejects_the_complete_block(
    field: str, value: object
) -> None:
    block, ledger, components = _block(1, 1)
    f0 = components[0].facts[0]
    proposal = _proposal(
        position="p00",
        component_alias="c0",
        fact_id=f0.fact_id,
        evidence_id=f0.evidence_id,
        entity_id=f0.subject,
    )
    proposal[field] = value
    with pytest.raises(ResolutionError):
        _resolve_block(
            block=block,
            output=_resolver_output(
                [proposal],
                [
                    _unresolved(
                        component_alias="c1",
                        fact_id=components[1].facts[0].fact_id,
                        evidence_id=components[1].evidence_ids[0],
                    )
                ],
            ),
            ledger=ledger,
            resolver=EntityResolver([]),
        )


def test_later_component_invalid_result_returns_no_partial_events() -> None:
    block, ledger, components = _block(1, 1)
    f0, f1 = components[0].facts[0], components[1].facts[0]
    with pytest.raises(ResolutionError):
        _resolve_block(
            block=block,
            output=_resolver_output(
                [
                    _proposal(
                        position="p00",
                        component_alias="c0",
                        fact_id=f0.fact_id,
                        evidence_id=f0.evidence_id,
                        entity_id=f0.subject,
                    ),
                    _proposal(
                        position="p01",
                        component_alias="c9",
                        fact_id=f1.fact_id,
                        evidence_id=f1.evidence_id,
                        entity_id=f1.subject,
                    ),
                ],
                [],
            ),
            ledger=ledger,
            resolver=EntityResolver([]),
        )


def test_block_seed_partition_rejects_missing_and_duplicate_assignments() -> None:
    block, ledger, components = _block(1, 1)
    f0, f1 = components[0].facts[0], components[1].facts[0]
    proposal = _proposal(
        position="p00",
        component_alias="c0",
        fact_id=f0.fact_id,
        evidence_id=f0.evidence_id,
        entity_id=f0.subject,
    )
    with pytest.raises(ResolutionError, match="missing"):
        _resolve_block(
            block=block,
            output=_resolver_output([proposal], []),
            ledger=ledger,
            resolver=EntityResolver([]),
        )

    with pytest.raises(ResolutionError, match="more than once"):
        _resolve_block(
            block=block,
            output=_resolver_output(
                [proposal],
                [
                    _unresolved(
                        component_alias="c0",
                        fact_id=f0.fact_id,
                        evidence_id=f0.evidence_id,
                    ),
                    _unresolved(
                        component_alias="c1",
                        fact_id=f1.fact_id,
                        evidence_id=f1.evidence_id,
                    ),
                ],
            ),
            ledger=ledger,
            resolver=EntityResolver([]),
        )


def test_family_labels_are_component_local_and_positions_are_global() -> None:
    block, ledger, components = _block(2, 1)
    c0f0, c0f1 = components[0].facts
    c1f0 = components[1].facts[0]
    events, _ = _resolve_block(
        block=block,
        output=_resolver_output(
            [
                _proposal(
                    position="p00",
                    component_alias="c0",
                    fact_id=c0f0.fact_id,
                    evidence_id=c0f0.evidence_id,
                    entity_id=c0f0.subject,
                    family="f0",
                ),
                _proposal(
                    position="p01",
                    component_alias="c1",
                    fact_id=c1f0.fact_id,
                    evidence_id=c1f0.evidence_id,
                    entity_id=c1f0.subject,
                    family="f0",
                ),
                _proposal(
                    position="p02",
                    component_alias="c0",
                    fact_id=c0f1.fact_id,
                    evidence_id=c0f1.evidence_id,
                    entity_id=c0f1.subject,
                    family="f0",
                ),
            ],
            [],
        ),
        ledger=ledger,
        resolver=EntityResolver([]),
    )

    assert [event["key_fact_ids"] for event in events] == [
        [c0f0.fact_id],
        [c0f1.fact_id],
        [c1f0.fact_id],
    ]
    assert events[0]["story_family_id"] == events[1]["story_family_id"]
    assert events[0]["story_family_id"] != events[2]["story_family_id"]


def test_equivalent_proposal_order_preserves_family_and_pair_semantics() -> None:
    block, ledger, components = _block(2)
    first, second = components[0].facts

    def output(order: list[tuple[str, object]]) -> dict:
        proposals = []
        for position, fact in order:
            proposals.append(
                _proposal(
                    position=position,
                    component_alias="c0",
                    fact_id=fact.fact_id,
                    evidence_id=fact.evidence_id,
                    entity_id=fact.subject,
                    family="f0",
                    relations=[
                        {
                            "other_proposal_alias": "p01" if position == "p00" else "p00",
                            "relation": "distinct_material_development",
                        }
                    ],
                )
            )
        return _resolver_output(proposals, [])

    events_a, _ = _resolve_block(
        block=block,
        output=output([("p00", first), ("p01", second)]),
        ledger=ledger,
        resolver=EntityResolver([]),
    )
    events_b, _ = _resolve_block(
        block=block,
        output=output([("p00", second), ("p01", first)]),
        ledger=ledger,
        resolver=EntityResolver([]),
    )

    by_fact_a = {event["key_fact_ids"][0]: event for event in events_a}
    by_fact_b = {event["key_fact_ids"][0]: event for event in events_b}
    assert {
        fact_id: (event["story_family_id"], event["coexistence_pair_ids"])
        for fact_id, event in by_fact_a.items()
    } == {
        fact_id: (event["story_family_id"], event["coexistence_pair_ids"])
        for fact_id, event in by_fact_b.items()
    }


def test_relation_on_unknown_family_is_rejected() -> None:
    block, ledger, components = _block(2)
    f0, f1 = components[0].facts
    relations = [{"other_proposal_alias": "p01", "relation": "distinct_material_development"}]
    reciprocal = [{"other_proposal_alias": "p00", "relation": "distinct_material_development"}]
    with pytest.raises(ResolutionError):
        _resolve_block(
            block=block,
            output=_resolver_output(
                [
                    _proposal(
                        position="p00",
                        component_alias="c0",
                        fact_id=f0.fact_id,
                        evidence_id=f0.evidence_id,
                        entity_id=f0.subject,
                        relations=relations,
                    ),
                    _proposal(
                        position="p01",
                        component_alias="c0",
                        fact_id=f1.fact_id,
                        evidence_id=f1.evidence_id,
                        entity_id=f1.subject,
                        relations=reciprocal,
                    ),
                ],
                [],
            ),
            ledger=ledger,
            resolver=EntityResolver([]),
        )


def test_relation_across_family_labels_is_rejected() -> None:
    block, ledger, components = _block(2)
    f0, f1 = components[0].facts
    with pytest.raises(ResolutionError):
        _resolve_block(
            block=block,
            output=_resolver_output(
                [
                    _proposal(
                        position="p00",
                        component_alias="c0",
                        fact_id=f0.fact_id,
                        evidence_id=f0.evidence_id,
                        entity_id=f0.subject,
                        family="f0",
                        relations=[
                            {
                                "other_proposal_alias": "p01",
                                "relation": "distinct_material_development",
                            }
                        ],
                    ),
                    _proposal(
                        position="p01",
                        component_alias="c0",
                        fact_id=f1.fact_id,
                        evidence_id=f1.evidence_id,
                        entity_id=f1.subject,
                        family="f1",
                        relations=[
                            {
                                "other_proposal_alias": "p00",
                                "relation": "distinct_material_development",
                            }
                        ],
                    ),
                ],
                [],
            ),
            ledger=ledger,
            resolver=EntityResolver([]),
        )


def test_relation_enum_is_semantically_validated() -> None:
    block, ledger, components = _block(2)
    f0, f1 = components[0].facts
    invalid_relation = [{"other_proposal_alias": "p01", "relation": "other"}]
    reciprocal = [{"other_proposal_alias": "p00", "relation": "other"}]
    with pytest.raises(ResolutionError):
        _resolve_block(
            block=block,
            output=_resolver_output(
                [
                    _proposal(
                        position="p00",
                        component_alias="c0",
                        fact_id=f0.fact_id,
                        evidence_id=f0.evidence_id,
                        entity_id=f0.subject,
                        family="f0",
                        relations=invalid_relation,
                    ),
                    _proposal(
                        position="p01",
                        component_alias="c0",
                        fact_id=f1.fact_id,
                        evidence_id=f1.evidence_id,
                        entity_id=f1.subject,
                        family="f0",
                        relations=reciprocal,
                    ),
                ],
                [],
            ),
            ledger=ledger,
            resolver=EntityResolver([]),
        )


@pytest.mark.parametrize(
    "relations",
    [
        ([{"other_proposal_alias": "p01", "relation": "distinct_material_development"}], []),
        ([{"other_proposal_alias": "p00", "relation": "distinct_material_development"}], []),
        (
            [
                {"other_proposal_alias": "p01", "relation": "distinct_material_development"},
                {"other_proposal_alias": "p01", "relation": "distinct_material_development"},
            ],
            [],
        ),
        ([{"other_proposal_alias": "p99", "relation": "distinct_material_development"}], []),
    ],
)
def test_relation_graph_rejects_missing_reciprocal_self_duplicate_and_dangling(relations) -> None:
    block, ledger, components = _block(2)
    f0, f1 = components[0].facts
    with pytest.raises(ResolutionError):
        _resolve_block(
            block=block,
            output=_resolver_output(
                [
                    _proposal(
                        position="p00",
                        component_alias="c0",
                        fact_id=f0.fact_id,
                        evidence_id=f0.evidence_id,
                        entity_id=f0.subject,
                        family="f0",
                        relations=relations[0],
                    ),
                    _proposal(
                        position="p01",
                        component_alias="c0",
                        fact_id=f1.fact_id,
                        evidence_id=f1.evidence_id,
                        entity_id=f1.subject,
                        family="f0",
                        relations=relations[1],
                    ),
                ],
                [],
            ),
            ledger=ledger,
            resolver=EntityResolver([]),
        )


def test_position_aliases_are_exact_response_positions() -> None:
    block, ledger, components = _block(1)
    fact = components[0].facts[0]
    with pytest.raises(ResolutionError):
        _resolve_block(
            block=block,
            output=_resolver_output(
                [
                    _proposal(
                        position="p01",
                        component_alias="c0",
                        fact_id=fact.fact_id,
                        evidence_id=fact.evidence_id,
                        entity_id=fact.subject,
                    )
                ],
                [],
            ),
            ledger=ledger,
            resolver=EntityResolver([]),
        )


def test_unknown_families_are_event_specific_and_nonunknown_singletons_are_not_shared() -> None:
    block, ledger, components = _block(3)
    component = components[0]
    proposals = [
        _proposal(
            position=f"p{i:02d}",
            component_alias="c0",
            fact_id=fact.fact_id,
            evidence_id=fact.evidence_id,
            entity_id=fact.subject,
            family=family,
        )
        for i, (fact, family) in enumerate(
            zip(component.facts, ("unknown", "unknown", "f0"), strict=True)
        )
    ]
    events, _ = _resolve_block(
        block=block,
        output=_resolver_output(proposals, []),
        ledger=ledger,
        resolver=EntityResolver([]),
    )
    assert len({event["story_family_id"] for event in events}) == 3
    assert all(event["coexistence_pair_ids"] == [] for event in events)


def test_more_than_eight_relations_are_rejected_atomically() -> None:
    block, ledger, components = _block(10)
    proposals = []
    for index, fact in enumerate(components[0].facts):
        position = f"p{index:02d}"
        targets = [f"p{other:02d}" for other in range(10) if other != index]
        proposals.append(
            _proposal(
                position=position,
                component_alias="c0",
                fact_id=fact.fact_id,
                evidence_id=fact.evidence_id,
                entity_id=fact.subject,
                family="f0",
                relations=[
                    {
                        "other_proposal_alias": target,
                        "relation": "distinct_material_development",
                    }
                    for target in targets
                ],
            )
        )
    with pytest.raises(ResolutionError):
        _resolve_block(
            block=block,
            output=_resolver_output(proposals, []),
            ledger=ledger,
            resolver=EntityResolver([]),
        )


def test_cross_component_coexistence_relation_is_rejected() -> None:
    block, ledger, components = _block(1, 1)
    f0, f1 = components[0].facts[0], components[1].facts[0]
    with pytest.raises(ResolutionError):
        _resolve_block(
            block=block,
            output=_resolver_output(
                [
                    _proposal(
                        position="p00",
                        component_alias="c0",
                        fact_id=f0.fact_id,
                        evidence_id=f0.evidence_id,
                        entity_id=f0.subject,
                        relations=[
                            {
                                "other_proposal_alias": "p01",
                                "relation": "distinct_material_development",
                            }
                        ],
                    ),
                    _proposal(
                        position="p01",
                        component_alias="c1",
                        fact_id=f1.fact_id,
                        evidence_id=f1.evidence_id,
                        entity_id=f1.subject,
                    ),
                ],
                [],
            ),
            ledger=ledger,
            resolver=EntityResolver([]),
        )


def test_full_pipeline_retains_all_events_from_a_multi_item_feed() -> None:
    from types import SimpleNamespace

    from follow_the_money.config import load_config
    from follow_the_money.llm import ResponsesAdapter
    from tests.test_gate_13_3 import FakeClient, _news_item, _valid_feed

    repo_root = Path(__file__).resolve().parents[1]
    cfg = load_config(
        repo_root / "config" / "config.yaml",
        repo_root / "config" / "providers.yaml",
        require_verified_enabled=True,
    )
    feed = _valid_feed()
    feed["items"] = [
        _news_item(T0 - timedelta(hours=2), "美联储维持利率不变", "https://example.com/fed"),
        _news_item(
            T0 - timedelta(hours=1),
            "中东港口供应链出现中断",
            "https://example.com/port",
            eid="ev_2",
        ),
    ]
    resolver = EntityResolver(cfg.entities)
    ledger = feed_to_ledger(feed, cfg, resolver)
    nodes = build_mention_nodes(ledger.entries())
    components = connected_components(
        nodes,
        build_edges(nodes, {entry.fact_id: entry for entry in ledger.entries()}, resolver),
        {entry.fact_id: entry for entry in ledger.entries()},
    )
    blocks = pack_blocks(components)
    assert len(blocks) == 1 and len(blocks[0].components) == 2
    block = blocks[0]
    resolver_output = {
        "proposals": [
            {
                "component_alias": f"c{i}",
                "position_alias": f"p{i:02d}",
                "event_type": "news",
                "event_defining_fact_ids": [component.seed_fact_ids[0]],
                "evidence_ids": [component.evidence_ids[0]],
                "supporting_fact_ids": [],
                "entity_ids": [],
                "story_family_label": "unknown",
                "coexistence_relations": [],
            }
            for i, component in enumerate(block.components)
        ],
        "unresolved_groups": [],
    }
    analyst = {
        "packet_alias": "p0",
        "mechanisms": [],
        "implications": [],
        "reaction_attributions": [],
        "price_in": {
            "status": "unclear",
            "explanation": "证据不足。",
            "reference_aliases": ["e0"],
        },
        "indirect_indication": {"indicated": False, "reference_aliases": []},
        "asset_mappings": [],
        "alternatives": [],
        "watch_points": [],
        "scope": "unknown",
        "fundamental_depth": "unknown",
        "reversibility": "unknown",
        "structural_horizon": "unknown",
        "cn_hk_exposure": "unknown",
        "us_next_session_exposure": "unknown",
        "catalyst_calendar_ids": [],
        "audit_reasons": [],
    }
    outputs = {
        "resolver": resolver_output,
        "analyst": analyst,
        "editor": {
            "filled_slots": [
                {
                    "slot_alias": "s00",
                    "wording_fragment": "市场状态未判定。",
                    "reference_aliases": [],
                }
            ]
        },
        "audit": {"covered_claim_ids": [f"k{i:02d}" for i in range(14)], "findings": []},
    }
    client = FakeClient(outputs)
    adapter = ResponsesAdapter(
        model="gpt-test", client=SimpleNamespace(responses=client, create=client.create)
    )
    prompts = {
        "resolver": "Resolve atomic financial events",
        "analyst": "Analyze one verified",
        "editor": "Render the Chinese Morning",
        "audit": "Audit the Chinese Morning",
    }

    result = run_pipeline(
        cfg=cfg,
        feed=feed,
        brief_generated_at=_ts(T0 + timedelta(minutes=10)),
        adapter=adapter,
        resolver=resolver,
        prompts=prompts,
    )

    assert len(result.events) == 2
    assert result.unresolved_groups == []


def test_run_pipeline_materializes_family_pair_and_selection_exemption(monkeypatch) -> None:
    from types import SimpleNamespace

    from follow_the_money import editor as editor_module
    from follow_the_money import pipeline as pipeline_module
    from follow_the_money.config import load_config
    from follow_the_money.llm import ResponsesAdapter
    from follow_the_money.selection import select_events as real_select_events
    from tests.test_gate_13_3 import (
        FakeClient,
        _analyst_output,
        _news_item,
        _valid_feed,
    )

    repo_root = Path(__file__).resolve().parents[1]
    cfg = load_config(
        repo_root / "config" / "config.yaml",
        repo_root / "config" / "providers.yaml",
        require_verified_enabled=True,
    )
    feed = _valid_feed()
    feed["items"] = [
        _news_item(T0 - timedelta(hours=2), "美联储 FOMC 政策决定", "https://example.com/fed"),
        _news_item(
            T0 - timedelta(hours=1),
            "美联储 FOMC 政策决定更新",
            "https://example.com/fed-update",
            eid="ev_2",
        ),
        _news_item(
            T0 - timedelta(minutes=30),
            "美联储 FOMC 政策决定跟进",
            "https://example.com/fed-followup",
            eid="ev_3",
        ),
    ]
    resolver = EntityResolver(cfg.entities)
    ledger = feed_to_ledger(feed, cfg, resolver)
    nodes = build_mention_nodes(ledger.entries())
    components = connected_components(
        nodes,
        build_edges(nodes, {entry.fact_id: entry for entry in ledger.entries()}, resolver),
        {entry.fact_id: entry for entry in ledger.entries()},
    )
    assert len(components) == 1
    component = components[0]
    fact_a, fact_b, fact_c = component.facts
    fixture = json.loads(
        (repo_root / "evals" / "dataset" / "story_family_replay.json").read_bytes()
    )
    resolver_output = fixture["resolver"]
    assert [proposal["event_defining_fact_ids"] for proposal in resolver_output["proposals"]] == [
        [fact_a.fact_id],
        [fact_b.fact_id],
        [fact_c.fact_id],
    ]
    analyst = _analyst_output()
    outputs = {
        "resolver": resolver_output,
        "analyst": analyst,
        "editor": {"filled_slots": []},
        "audit": {"covered_claim_ids": [], "findings": []},
    }
    client = FakeClient(outputs)
    adapter = ResponsesAdapter(
        model="gpt-test", client=SimpleNamespace(responses=client, create=client.create)
    )
    captured: dict[str, object] = {}

    real_allocate_slots = editor_module.allocate_slots

    def allocate_slots(**kwargs):
        slots = real_allocate_slots(**kwargs)
        outputs["editor"]["filled_slots"] = [
            {
                "slot_alias": slot.alias,
                "wording_fragment": slot.kind,
                "reference_aliases": list(slot.exposed_aliases)
                if slot.owner != "market_state"
                else [],
            }
            for slot in slots
            if slot.required
        ]
        return slots

    real_audit_projection = pipeline_module._audit_projection

    def audit_projection(brief):
        projection = real_audit_projection(brief)
        outputs["audit"]["covered_claim_ids"] = [claim["alias"] for claim in projection["claims"]]
        return projection

    monkeypatch.setattr(editor_module, "allocate_slots", allocate_slots)
    monkeypatch.setattr(pipeline_module, "_audit_projection", audit_projection)

    def capture_selection(items, scoring):
        captured["items"] = list(items)
        return real_select_events(items, scoring)

    monkeypatch.setattr("follow_the_money.pipeline.select_events", capture_selection)

    result = run_pipeline(
        cfg=cfg,
        feed=feed,
        brief_generated_at=_ts(T0 + timedelta(minutes=10)),
        adapter=adapter,
        resolver=resolver,
        prompts={
            "resolver": "Resolve atomic financial events",
            "analyst": "Analyze one verified",
            "editor": "Render the Chinese Morning",
            "audit": "Audit the Chinese Morning",
        },
    )

    assert len(result.events) == 3
    assert [event["event_id"] for event in result.events] == [
        event["event_id"] for event in fixture["events"]
    ]
    assert len({event["story_family_id"] for event in result.events}) == 1
    pair_ab = tuple(sorted((result.events[0]["event_id"], result.events[1]["event_id"])))
    pair_bc = tuple(sorted((result.events[1]["event_id"], result.events[2]["event_id"])))
    assert [event["coexistence_pair_ids"] for event in result.events] == [
        [list(pair_ab)],
        [list(pair_ab), list(pair_bc)],
        [list(pair_bc)],
    ]
    assert [item.story_family_id for item in captured["items"]] == [
        result.events[0]["story_family_id"],
        result.events[1]["story_family_id"],
        result.events[2]["story_family_id"],
    ]
    assert all(
        item.coexistence_pairs == frozenset({pair_ab, pair_bc}) for item in captured["items"]
    )
    assert result.selected
    ordered = sorted(
        captured["items"],
        key=lambda item: (
            -item.base_priority,
            -datetime.fromisoformat(item.fully_known_at).timestamp(),
            item.event_id,
        ),
    )
    frozen_first = ordered[0].event_id
    selected_by_id = {selected.event_id: selected for selected in result.selected}
    assert set(selected_by_id) == {item.event_id for item in captured["items"]}
    for item in captured["items"]:
        pair = tuple(sorted((frozen_first, item.event_id)))
        expected = item.base_priority
        if item.event_id != frozen_first and pair not in {pair_ab, pair_bc}:
            with normative_decimal_context():
                expected -= Decimal(cfg.scoring.family_penalty)
        assert selected_by_id[item.event_id].final_priority == expected

    replayed = run_pipeline(
        cfg=cfg,
        feed=feed,
        brief_generated_at=_ts(T0 + timedelta(minutes=10)),
        adapter=None,
        resolver=resolver,
        prompts={"resolver": "", "analyst": "", "editor": "", "audit": ""},
        saved_llm={
            "resolver": [resolver_output],
            "analyst": [analyst, analyst, analyst],
            "editor": outputs["editor"],
            "language-audit": outputs["audit"],
        },
    )
    assert replayed.events == result.events
    assert replayed.selected == result.selected
