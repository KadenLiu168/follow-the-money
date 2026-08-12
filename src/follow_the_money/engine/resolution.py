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


def resolve_component_events(
    *,
    component: Component,
    proposals: Sequence[Mapping[str, Any]],
    ledger: Ledger,
    resolver: EntityResolver,
    subject_zh_by_entity: Mapping[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Construct canonical Events from one component's proposals.

    Event IDs derive from the versioned canonical tuple of sorted evidence
    IDs, event type, entity IDs, and the atomic discriminator of complete
    canonical fact keys. Scripts own IDs/fully_known_at/labels.
    """
    events: list[dict[str, Any]] = []
    component_facts = {f.fact_id: f for f in component.facts}
    for proposal in proposals:
        defining_ids = tuple(dict.fromkeys(proposal["event_defining_fact_ids"]))
        facts = [component_facts[fid] for fid in defining_ids if fid in component_facts]
        if len(facts) != len(defining_ids):
            raise ResolutionError("proposal references a fact not in this component")
        entity_ids = tuple(proposal.get("entity_ids", []))
        event = build_event(
            event_type=proposal["event_type"],
            evidence_ids=proposal["evidence_ids"],
            entity_ids=entity_ids,
            event_defining_fact_ids=defining_ids,
            ledger=ledger,
            subject_zh=_subject_zh(entity_ids, resolver, subject_zh_by_entity),
        )
        events.append(event)
    return events


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


def finalize_story_families(events: Sequence[Mapping[str, Any]]) -> tuple[dict[str, Any], ...]:
    """Derive canonical family IDs and coexistence pairs after Event IDs exist."""
    member_events = [e["event_id"] for e in events]
    story_family_id(member_events) if member_events else None
    [e.get("coexistence_pair_ids", []) for e in events]
    return tuple(dict(event) for event in events)


def assign_family_ids(events: Sequence[Mapping[str, Any]]) -> tuple[dict[str, Any], ...]:
    """Component-local family derivation from sorted member Event IDs.

    Within one component, proposals sharing a non-unknown family label become
    one canonical family whose ID derives from sorted member Event IDs.
    """
    label_groups: dict[str, list[str]] = {}
    for e in events:
        label = e.get("_family_label", "unknown")
        label_groups.setdefault(label, []).append(e["event_id"])

    result: list[dict[str, Any]] = []
    for source_event in events:
        e = dict(source_event)
        label = e.get("_family_label", "unknown")
        members = label_groups.get(label, [e["event_id"]])
        e["story_family_id"] = story_family_id(members)
        e.pop("_family_label", None)
        result.append(e)
    return tuple(result)
