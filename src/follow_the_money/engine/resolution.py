"""Candidate-block resolution into canonical events (task 7.3/7.4).

- Each component/block gets stable request-local aliases; proposals carry
  ``p00..p23`` response-position aliases.
- Every input seed occurs exactly once across proposals/unresolved groups
  (missing/duplicate/cross-component/non-seed membership rejects the whole
  response).
- Script-side canonical event construction is the sole owner of event IDs,
  ``fully_known_at``, and display labels.
- After Event IDs exist, derive canonical family IDs and unordered
  coexistence pairs under closed component-local rules.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from ..events import (
    build_event,
    story_family_id,
)
from ..ledger import Ledger
from .candidates import CandidateBlock, Component
from .entities import EntityResolver


class ResolutionError(ValueError):
    """Resolver output failed semantic validation."""


@dataclass(frozen=True)
class ComponentMaterialization:
    """Canonical Events and pairs derived from one resolver component."""

    events: tuple[dict[str, Any], ...]
    coexistence_pairs: tuple[tuple[str, str], ...]


def alias_component_ids(components: Sequence[Component]) -> dict[str, str]:
    """Stable request-local aliases (``c0``..) for components."""
    return {f"c{i}": c.component_id for i, c in enumerate(components)}


def validate_seed_coverage(
    *,
    block: CandidateBlock,
    proposals: Sequence[Mapping[str, Any]],
    unresolved: Sequence[Mapping[str, Any]],
) -> None:
    """Every seed in the block must appear exactly once across proposals/groups."""
    block_seeds: set[str] = set()
    for c in block.components:
        block_seeds.update(c.seed_fact_ids)

    assigned: set[str] = set()
    for proposal in proposals:
        for fid in proposal.get("event_defining_fact_ids", []):
            if fid not in block_seeds:
                raise ResolutionError(f"proposal references non-seed/out-of-block fact {fid!r}")
            if fid in assigned:
                raise ResolutionError(f"seed {fid!r} assigned more than once")
            assigned.add(fid)
    for group in unresolved:
        for fid in group.get("seed_fact_ids", []):
            if fid not in block_seeds:
                raise ResolutionError(f"unresolved group references out-of-block fact {fid!r}")
            if fid in assigned:
                raise ResolutionError(f"seed {fid!r} assigned more than once")
            assigned.add(fid)

    missing = block_seeds - assigned
    if missing:
        raise ResolutionError(f"seeds missing from resolver output: {sorted(missing)}")


def resolve_block(
    *,
    block: CandidateBlock,
    output: Mapping[str, Any],
    ledger: Ledger,
    resolver: EntityResolver,
    subject_zh_by_entity: Mapping[str, str] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Validate and merge one complete packed resolver block atomically.

    The response is validated against the request-local component aliases
    before any canonical Event is constructed.  Events are then emitted in
    block component order, with proposal order preserved inside each
    component.  The second return value is canonical unresolved audit data.
    """
    proposals = output.get("proposals", [])
    unresolved = output.get("unresolved_groups", [])
    if not isinstance(proposals, Sequence) or isinstance(proposals, (str, bytes)):
        raise ResolutionError("resolver proposals must be an array")
    if not isinstance(unresolved, Sequence) or isinstance(unresolved, (str, bytes)):
        raise ResolutionError("resolver unresolved_groups must be an array")
    if "component_alias" in output:
        raise ResolutionError("resolver output must not contain a top-level component_alias")

    aliases = alias_component_ids(block.components)
    components_by_alias = {
        alias: component for alias, component in zip(aliases, block.components, strict=True)
    }
    block_seeds: set[str] = set()
    for component in block.components:
        if block_seeds.intersection(component.seed_fact_ids):
            raise ResolutionError("resolver block contains duplicate component seed ownership")
        block_seeds.update(component.seed_fact_ids)

    proposals_by_alias: dict[str, list[Mapping[str, Any]]] = {alias: [] for alias in aliases}
    unresolved_by_alias: dict[str, list[Mapping[str, Any]]] = {alias: [] for alias in aliases}
    assigned: set[str] = set()
    positions: dict[str, Mapping[str, Any]] = {}
    relation_pairs: set[tuple[str, str]] = set()

    for index, proposal in enumerate(proposals):
        if not isinstance(proposal, Mapping):
            raise ResolutionError("proposal must be an object")
        alias = proposal.get("component_alias")
        if not isinstance(alias, str) or alias not in components_by_alias:
            raise ResolutionError(f"proposal references unknown component alias {alias!r}")
        component = components_by_alias[alias]
        if index >= 24:
            raise ResolutionError("resolver response contains more than 24 proposals")
        expected_position = f"p{index:02d}"
        position = proposal.get("position_alias")
        if not isinstance(position, str) or position != expected_position or position in positions:
            raise ResolutionError(
                f"proposal position aliases must be unique and canonical: expected {expected_position!r}"
            )
        positions[position] = proposal
        proposals_by_alias[alias].append(proposal)

        component_facts = {fact.fact_id for fact in component.facts}
        component_seeds = set(component.seed_fact_ids)
        component_evidence = set(component.evidence_ids)
        component_entities = {fact.subject for fact in component.facts if fact.subject}
        defining = _reference_list(proposal, "event_defining_fact_ids")
        supporting = _reference_list(proposal, "supporting_fact_ids")
        evidence = _reference_list(proposal, "evidence_ids")
        entities = _reference_list(proposal, "entity_ids")
        _require_unique(defining, "event defining seeds")
        _require_unique(supporting, "supporting facts")
        _require_unique(evidence, "evidence")
        _require_unique(entities, "entities")
        for fact_id in defining:
            if fact_id not in component_seeds:
                raise ResolutionError(
                    f"proposal references non-seed/out-of-component fact {fact_id!r}"
                )
            _assign_seed(assigned, fact_id)
        for fact_id in supporting:
            if fact_id not in component_facts:
                raise ResolutionError(
                    f"proposal references out-of-component supporting fact {fact_id!r}"
                )
        for evidence_id in evidence:
            if evidence_id not in component_evidence:
                raise ResolutionError(
                    f"proposal references out-of-component evidence {evidence_id!r}"
                )
        for entity_id in entities:
            if entity_id not in component_entities:
                raise ResolutionError(f"proposal references out-of-component entity {entity_id!r}")

        relations = proposal.get("coexistence_relations", [])
        if not isinstance(relations, Sequence) or isinstance(relations, (str, bytes)):
            raise ResolutionError("coexistence_relations must be an array")
        if len(relations) > 8:
            raise ResolutionError("coexistence_relations may contain at most 8 relations")
        relation_targets: set[str] = set()
        for relation in relations:
            if not isinstance(relation, Mapping):
                raise ResolutionError("coexistence relation must be an object")
            target = relation.get("other_proposal_alias")
            if not isinstance(target, str):
                raise ResolutionError("coexistence relation target must be a proposal alias")
            if relation.get("relation") != "distinct_material_development":
                raise ResolutionError("unsupported coexistence relation")
            if target in relation_targets or target == position:
                raise ResolutionError("coexistence relations must target distinct proposals once")
            relation_targets.add(target)
            relation_pairs.add((position, target))

    for group in unresolved:
        if not isinstance(group, Mapping):
            raise ResolutionError("unresolved group must be an object")
        alias = group.get("component_alias")
        if not isinstance(alias, str) or alias not in components_by_alias:
            raise ResolutionError(f"unresolved group references unknown component alias {alias!r}")
        component = components_by_alias[alias]
        unresolved_by_alias[alias].append(group)
        component_seeds = set(component.seed_fact_ids)
        component_evidence = set(component.evidence_ids)
        seeds = _reference_list(group, "seed_fact_ids")
        evidence = _reference_list(group, "evidence_ids")
        _require_unique(seeds, "unresolved seeds")
        _require_unique(evidence, "unresolved evidence")
        for fact_id in seeds:
            if fact_id not in component_seeds:
                raise ResolutionError(
                    f"unresolved group references non-seed/out-of-component fact {fact_id!r}"
                )
            _assign_seed(assigned, fact_id)
        for evidence_id in evidence:
            if evidence_id not in component_evidence:
                raise ResolutionError(
                    f"unresolved group references out-of-component evidence {evidence_id!r}"
                )

    missing = block_seeds - assigned
    if missing:
        raise ResolutionError(f"seeds missing from resolver output: {sorted(missing)}")
    if assigned != block_seeds:
        raise ResolutionError("resolver seed coverage contains an out-of-block assignment")

    for position, target in relation_pairs:
        target_proposal = positions.get(target)
        if target_proposal is None:
            raise ResolutionError(f"coexistence relation references unknown proposal {target!r}")
        if target_proposal.get("component_alias") != positions[position].get("component_alias"):
            raise ResolutionError("coexistence relation crosses component boundaries")
        if (target, position) not in relation_pairs:
            raise ResolutionError("coexistence relations must be symmetric")

    # All block-wide semantic checks complete: only now construct canonical Events.
    records: list[tuple[str, str, Mapping[str, Any], dict[str, Any]]] = []
    for alias, component in zip(aliases, block.components, strict=True):
        materialized = materialize_component_events(
            component=component,
            proposals=proposals_by_alias[alias],
            ledger=ledger,
            resolver=resolver,
            subject_zh_by_entity=subject_zh_by_entity,
        )
        records.extend(
            (alias, proposal["position_alias"], proposal, event)
            for proposal, event in zip(proposals_by_alias[alias], materialized.events, strict=True)
        )

    events = [event for _, _, _, event in records]

    normalized_unresolved: list[dict[str, Any]] = []
    for alias, component in zip(aliases, block.components, strict=True):
        for group in unresolved_by_alias[alias]:
            normalized_unresolved.append(
                {
                    "component_id": component.component_id,
                    "seed_fact_ids": sorted(group["seed_fact_ids"]),
                    "evidence_ids": sorted(group["evidence_ids"]),
                    "reason": group["reason"],
                }
            )
    return events, normalized_unresolved


def materialize_component_events(
    *,
    component: Component,
    proposals: Sequence[Mapping[str, Any]],
    ledger: Ledger,
    resolver: EntityResolver,
    subject_zh_by_entity: Mapping[str, str] | None = None,
) -> ComponentMaterialization:
    """Build all Events, then derive one component's family and pair semantics."""
    if len(proposals) > 24:
        raise ResolutionError("resolver response contains more than 24 proposals")

    normalized: list[tuple[str, Mapping[str, Any], tuple[Mapping[str, Any], ...]]] = []
    positions: set[str] = set()
    for proposal in proposals:
        if not isinstance(proposal, Mapping):
            raise ResolutionError("proposal must be an object")
        position = proposal.get("position_alias")
        if (
            not isinstance(position, str)
            or len(position) != 3
            or not position.startswith("p")
            or not position[1:].isdigit()
            or not 0 <= int(position[1:]) < 24
            or position in positions
        ):
            raise ResolutionError("proposal position_alias must be a unique p00..p23 alias")
        positions.add(position)
        label = proposal.get("story_family_label")
        if not isinstance(label, str) or not label:
            raise ResolutionError("story_family_label must be a non-empty string")
        relations = proposal.get("coexistence_relations", [])
        if not isinstance(relations, Sequence) or isinstance(relations, (str, bytes)):
            raise ResolutionError("coexistence_relations must be an array")
        if len(relations) > 8:
            raise ResolutionError("coexistence_relations may contain at most 8 relations")
        relation_targets: set[str] = set()
        for relation in relations:
            if not isinstance(relation, Mapping):
                raise ResolutionError("coexistence relation must be an object")
            target = relation.get("other_proposal_alias")
            if not isinstance(target, str):
                raise ResolutionError("coexistence relation target must be a proposal alias")
            if relation.get("relation") != "distinct_material_development":
                raise ResolutionError("unsupported coexistence relation")
            if target in relation_targets or target == position:
                raise ResolutionError("coexistence relations must target distinct proposals once")
            relation_targets.add(target)
        normalized.append((position, proposal, tuple(relations)))

    records: list[tuple[str, Mapping[str, Any], dict[str, Any]]] = []
    for position, proposal, _ in normalized:
        event = _build_component_event(
            component=component,
            proposal=proposal,
            ledger=ledger,
            resolver=resolver,
            subject_zh_by_entity=subject_zh_by_entity,
        )
        records.append((position, proposal, event))

    event_by_position = {position: event for position, _, event in records}
    labels_by_position = {
        position: proposal["story_family_label"] for position, proposal, _ in records
    }
    family_members: dict[str, list[str]] = {}
    for position, label in labels_by_position.items():
        if label != "unknown":
            family_members.setdefault(label, []).append(event_by_position[position]["event_id"])

    relation_pairs: set[tuple[str, str]] = set()
    pair_by_position: dict[str, set[tuple[str, str]]] = {
        position: set() for position in event_by_position
    }
    directed_relations: set[tuple[str, str]] = set()
    for position, proposal, relations in normalized:
        for relation in relations:
            target = relation.get("other_proposal_alias")
            if relation.get("relation") != "distinct_material_development":
                raise ResolutionError("unsupported coexistence relation")
            if target not in event_by_position:
                raise ResolutionError(
                    f"coexistence relation references unknown proposal {target!r}"
                )
            if target == position:
                raise ResolutionError("coexistence relation cannot be self-referential")
            if labels_by_position[position] == "unknown":
                raise ResolutionError("coexistence relation cannot attach to unknown family")
            if labels_by_position[position] != labels_by_position[target]:
                raise ResolutionError("coexistence relation crosses family boundaries")
            if len(family_members[labels_by_position[position]]) < 2:
                raise ResolutionError("coexistence relation cannot attach to singleton family")
            directed_relations.add((position, target))

    for position, target in directed_relations:
        if (target, position) not in directed_relations:
            raise ResolutionError("coexistence relations must be symmetric")
        pair = tuple(
            sorted((event_by_position[position]["event_id"], event_by_position[target]["event_id"]))
        )
        relation_pairs.add(pair)
        pair_by_position[position].add(pair)
        pair_by_position[target].add(pair)

    finalized: list[dict[str, Any]] = []
    for position, proposal, source_event in records:
        label = proposal["story_family_label"]
        members = family_members.get(label, []) if label != "unknown" else []
        family = story_family_id(members or [source_event["event_id"]])
        event = dict(source_event)
        event["story_family_id"] = family
        event["coexistence_pair_ids"] = [list(pair) for pair in sorted(pair_by_position[position])]
        finalized.append(event)

    return ComponentMaterialization(
        events=tuple(finalized),
        coexistence_pairs=tuple(sorted(relation_pairs)),
    )


def _reference_list(value: Mapping[str, Any], field: str) -> list[str]:
    refs = value.get(field, [])
    if not isinstance(refs, Sequence) or isinstance(refs, (str, bytes)):
        raise ResolutionError(f"{field} must be an array")
    if not all(isinstance(ref, str) for ref in refs):
        raise ResolutionError(f"{field} must contain strings")
    return list(refs)


def _require_unique(values: Sequence[str], name: str) -> None:
    if len(values) != len(set(values)):
        raise ResolutionError(f"{name} contain duplicate references")


def _assign_seed(assigned: set[str], fact_id: str) -> None:
    if fact_id in assigned:
        raise ResolutionError(f"seed {fact_id!r} assigned more than once")
    assigned.add(fact_id)


def _build_component_event(
    *,
    component: Component,
    proposal: Mapping[str, Any],
    ledger: Ledger,
    resolver: EntityResolver,
    subject_zh_by_entity: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    defining_ids = tuple(proposal["event_defining_fact_ids"])
    component_facts = {fact.fact_id: fact for fact in component.facts}
    facts = [component_facts[fid] for fid in defining_ids if fid in component_facts]
    if len(facts) != len(defining_ids):
        raise ResolutionError("proposal references a fact not in this component")
    return build_event(
        event_type=proposal["event_type"],
        evidence_ids=proposal["evidence_ids"],
        entity_ids=proposal.get("entity_ids", []),
        event_defining_fact_ids=defining_ids,
        ledger=ledger,
        subject_zh=_subject_zh(proposal.get("entity_ids", []), resolver, subject_zh_by_entity),
    )


def _subject_zh(entity_ids, resolver, override) -> str:
    if override and entity_ids:
        for eid in entity_ids:
            if eid in override:
                return override[eid]
    if entity_ids:
        resolved = resolver.resolve(entity_ids[0])
        if resolved.entity_id:
            return resolved.display_name
    return "相关主体"
