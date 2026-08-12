"""Candidate mention-level graph, components, and bounded blocks.

Design sections 5/8:

- Root nodes are ``(evidence_id, seed_fact_id, normalized subject key)``.
- Edges exist only via: equal complete canonical fact keys; shared exact
  entity within 48h + exact predicate/category or title Jaccard >= 0.45;
  entity-less same market/category within 12h and Jaccard >= 0.85.
- Components are connected components keyed by sorted mention-node IDs.
- Blocks are non-reordering next-fit packed whole components within the
  v1 20-projected-record / 24-seed / 32-KiB dynamic limits, at most 40 blocks.
- A component exceeding a bound fails ``candidate_group_too_large`` before
  resolver calls; >40 blocks fails ``capacity_exceeded``.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime

from ..canonical import canonical_text
from ..ledger import LedgerEntry, canonical_fact_key
from .entities import EntityResolver
from .title import title_jaccard  # reused closed similarity

V1_SHARED_ENTITY_HOURS = 48
V1_SHARED_ENTITY_JACCARD = 0.45
V1_ENTITYLESS_HOURS = 12
V1_ENTITYLESS_JACCARD = 0.85

MAX_PROJECTED_RECORDS = 20
MAX_SEEDS_PER_COMPONENT_BLOCK = 24
MAX_BLOCK_BYTES = 32 * 1024
MAX_BLOCKS = 40


class CandidateGraphError(ValueError):
    """Candidate graph/block failure (typed)."""


@dataclass(frozen=True)
class MentionNode:
    evidence_id: str
    seed_fact_id: str
    subject_key: str

    @property
    def id(self) -> str:
        payload = {
            "evidence_id": self.evidence_id,
            "seed_fact_id": self.seed_fact_id,
            "subject_key": self.subject_key,
        }
        digest = hashlib.sha256(canonical_text(payload).encode("utf-8")).hexdigest()
        return f"mn_{digest[:32]}"


@dataclass(frozen=True)
class Component:
    component_id: str
    mention_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    seed_fact_ids: tuple[str, ...]
    facts: tuple[LedgerEntry, ...]

    def projection_records(self) -> tuple[tuple[str, tuple[str, ...]], ...]:
        """Deduplicated sorted ``(evidence_id, allowed_fact_ids)`` records."""
        by_evidence: dict[str, set[str]] = {}
        for fact in self.facts:
            by_evidence.setdefault(fact.evidence_id, set()).add(fact.fact_id)
        records = sorted((ev, tuple(sorted(fids))) for ev, fids in by_evidence.items())
        return tuple((ev, fids) for ev, fids in records)


@dataclass
class CandidateBlock:
    block_id: str
    components: tuple[Component, ...]
    projected_records: int = 0
    seed_count: int = 0
    canonical_bytes: int = 0

    def aliases(self) -> dict[str, str]:
        return {f"c{i}": c.component_id for i, c in enumerate(self.components)}


def _subject_key(entry: LedgerEntry) -> str:
    return entry.subject or entry.raw_subject or "unresolved"


def build_mention_nodes(seed_entries: Iterable[LedgerEntry]) -> list[MentionNode]:
    nodes: list[MentionNode] = []
    for entry in seed_entries:
        if not entry.is_atomic_seed:
            continue
        nodes.append(
            MentionNode(
                evidence_id=entry.evidence_id,
                seed_fact_id=entry.fact_id,
                subject_key=_subject_key(entry),
            )
        )
    # Deterministic order.
    return sorted(nodes, key=lambda n: n.id)


def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _fact_entity(entry: LedgerEntry, resolver: EntityResolver) -> str | None:
    return (
        entry.subject
        if entry.subject and not entry.subject.startswith(("unresolved", "raw_"))
        else None
    )


def build_edges(
    nodes: Sequence[MentionNode],
    facts_by_id: Mapping[str, LedgerEntry],
    resolver: EntityResolver,
) -> set[tuple[str, str]]:
    """Undirected edges between mention nodes (deterministic)."""
    edges: set[tuple[str, str]] = set()
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            a, b = nodes[i], nodes[j]
            fa = facts_by_id[a.seed_fact_id]
            fb = facts_by_id[b.seed_fact_id]

            # (a) equal complete canonical fact keys (excluding lineage).
            if canonical_fact_key(fa) == canonical_fact_key(fb):
                edges.add((a.id, b.id))
                continue

            ta = _parse_ts(fa.knowledge_available_at)
            tb = _parse_ts(fb.knowledge_available_at)
            gap_hours = abs((ta - tb).total_seconds()) / 3600
            ea = _fact_entity(fa, resolver)
            eb = _fact_entity(fb, resolver)

            # (b) shared exact entity within 48h + exact predicate/category or Jaccard.
            if ea is not None and ea == eb and gap_hours <= V1_SHARED_ENTITY_HOURS:
                same_predicate = fa.predicate == fb.predicate
                title_sim = _title_sim_from_facts(fa, fb)
                if same_predicate or title_sim >= V1_SHARED_ENTITY_JACCARD:
                    edges.add((a.id, b.id))
                    continue

            # (c) entity-less same market/category within 12h and Jaccard >= 0.85.
            if ea is None and eb is None and gap_hours <= V1_ENTITYLESS_HOURS:
                same_market_category = (
                    fa.origin_payload == fb.origin_payload and fa.predicate == fb.predicate
                )
                if same_market_category and _title_sim_from_facts(fa, fb) >= V1_ENTITYLESS_JACCARD:
                    edges.add((a.id, b.id))
    return edges


def _title_sim_from_facts(a: LedgerEntry, b: LedgerEntry) -> float:
    ta = getattr(a, "raw_title", "") or ""
    tb = getattr(b, "raw_title", "") or ""
    if not ta or not tb:
        return 0.0
    return title_jaccard(ta, tb)


def connected_components(
    nodes: Sequence[MentionNode],
    edges: set[tuple[str, str]],
    facts_by_id: Mapping[str, LedgerEntry],
) -> list[Component]:
    """Connected components via union-find; keyed by sorted mention IDs."""
    parent = {n.id: n.id for n in nodes}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for a, b in edges:
        union(a, b)

    groups: dict[str, list[MentionNode]] = {}
    for node in nodes:
        groups.setdefault(find(node.id), []).append(node)

    components: list[Component] = []
    for members in groups.values():
        members_sorted = sorted(members, key=lambda n: n.id)
        mention_ids = tuple(n.id for n in members_sorted)
        evidence_ids = tuple(sorted({n.evidence_id for n in members_sorted}))
        seed_fact_ids = tuple(sorted({n.seed_fact_id for n in members_sorted}))
        facts = tuple(sorted((facts_by_id[fid] for fid in seed_fact_ids), key=lambda f: f.fact_id))
        cid = hashlib.sha256("|".join(mention_ids).encode("utf-8")).hexdigest()
        components.append(
            Component(
                component_id=f"comp_{cid[:32]}",
                mention_ids=mention_ids,
                evidence_ids=evidence_ids,
                seed_fact_ids=seed_fact_ids,
                facts=facts,
            )
        )
    return sorted(components, key=lambda c: c.component_id)


def _component_canonical_bytes(component: Component) -> int:
    records = component.projection_records()
    payload = {
        "component_id": component.component_id,
        "records": [{"evidence_id": r[0], "allowed_fact_ids": list(r[1])} for r in records],
        "seed_fact_ids": list(component.seed_fact_ids),
    }
    return len(canonical_text(payload).encode("utf-8"))


def pack_blocks(components: Sequence[Component]) -> list[CandidateBlock]:
    """Non-reordering next-fit packing of whole components.

    Append the next component only if every post-append bound remains
    satisfied; otherwise close the block and start the next. A component
    that alone exceeds a bound fails ``candidate_group_too_large``.
    """
    blocks: list[CandidateBlock] = []
    current: list[Component] = []
    records = 0
    seeds = 0
    size = 0

    def flush() -> None:
        nonlocal current, records, seeds, size
        if not current:
            return
        block_id = hashlib.sha256(
            "|".join(c.component_id for c in current).encode("utf-8")
        ).hexdigest()
        blocks.append(
            CandidateBlock(
                block_id=f"blk_{block_id[:32]}",
                components=tuple(current),
                projected_records=records,
                seed_count=seeds,
                canonical_bytes=size,
            )
        )
        current = []
        records = 0
        seeds = 0
        size = 0

    for component in components:
        c_records = len(component.projection_records())
        c_seeds = len(component.seed_fact_ids)
        c_bytes = _component_canonical_bytes(component)
        if (
            c_records > MAX_PROJECTED_RECORDS
            or c_seeds > MAX_SEEDS_PER_COMPONENT_BLOCK
            or c_bytes > MAX_BLOCK_BYTES
        ):
            raise CandidateGraphError(
                "candidate_group_too_large: a connected component exceeds a resolver-block bound"
            )
        if (
            records + c_records > MAX_PROJECTED_RECORDS
            or seeds + c_seeds > MAX_SEEDS_PER_COMPONENT_BLOCK
            or size + c_bytes > MAX_BLOCK_BYTES
        ):
            flush()
        current.append(component)
        records += c_records
        seeds += c_seeds
        size += c_bytes

    flush()

    if len(blocks) > MAX_BLOCKS:
        raise CandidateGraphError(f"capacity_exceeded: {len(blocks)} blocks > {MAX_BLOCKS}")
    return blocks
