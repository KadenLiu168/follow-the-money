"""Regression contract for packed resolver blocks with multiple components."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
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
