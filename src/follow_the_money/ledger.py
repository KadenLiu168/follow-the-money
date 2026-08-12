"""Evidence Ledger — the immutable boundary before resolution.

Design sections 6/7:

- Source-derived entries are typed ``FACT``, ``CLAIM``, or ``OBSERVATION``;
  script-derived calculations add ``INFERENCE`` with parent IDs.
- Every entry carries a stable fact ID and a script-derived
  ``knowledge_available_at``.
- A versioned canonical fact key binds subject, predicate, effective
  reference time + granularity, value, and unit; provider/evidence lineage is
  represented separately and is not part of the semantic key.
- ``atomic_event_seed_fact_ids`` is exactly every ``FACT``/``CLAIM`` whose
  origin payload is one of ``news|macro_release|policy|filing|flow|positioning``
  — no predicate allowlist. ``market_data``/``calendar``/``OBSERVATION``/
  ``INFERENCE`` are never seeds.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from .canonical import canonical_text

SEED_ORIGINS = frozenset({"news", "macro_release", "policy", "filing", "flow", "positioning"})

FACT_TYPES = frozenset({"FACT", "CLAIM", "OBSERVATION", "INFERENCE"})


@dataclass(frozen=True)
class LedgerEntry:
    """One immutable ledger entry."""

    fact_id: str
    entry_type: str  # FACT | CLAIM | OBSERVATION | INFERENCE
    origin_payload: str  # news | macro_release | policy | ... | market_data | calendar
    evidence_id: str
    subject: str  # resolved entity ID or stable normalized raw subject
    predicate: str
    effective_time: str | None
    effective_precision: str  # instant | date | month | year
    value: str | None
    unit: str | None
    knowledge_available_at: str
    parent_ids: tuple[str, ...] = ()
    source_families: tuple[str, ...] = ()  # corroboration families
    tier_counts: Mapping[str, int] = field(default_factory=dict)
    conflicts: tuple[str, ...] = ()
    raw_subject: str | None = None

    @property
    def is_atomic_seed(self) -> bool:
        return self.entry_type in ("FACT", "CLAIM") and self.origin_payload in SEED_ORIGINS


def canonical_fact_key(entry: LedgerEntry) -> str:
    """Versioned canonical fact key (subject/predicate/effective-time+granularity/value/unit).

    The subject is the resolved entity ID when available, otherwise the stable
    normalized raw-subject identity; swapping values between subjects or times
    cannot collide because each field participates in the key.
    """
    payload: dict[str, Any] = {
        "subject": entry.subject,
        "predicate": entry.predicate,
        "effective_time": entry.effective_time,
        "effective_precision": entry.effective_precision,
        "value": entry.value,
        "unit": entry.unit,
    }
    return canonical_text(payload)


def stable_fact_id(entry: LedgerEntry, *, version: int = 1) -> str:
    """Stable pre-resolver fact ID (version + type/origin + canonical key + evidence lineage).

    ``entry_type`` and ``origin_payload`` participate so that a FACT and an
    OBSERVATION derived from the same evidence with the same canonical values
    remain distinct ledger entries.
    """
    key = canonical_fact_key(entry)
    h = hashlib.sha256(
        f"fact-v{version}|{entry.evidence_id}|{entry.entry_type}|{entry.origin_payload}|{key}".encode()
    )
    return f"fact_{h.hexdigest()[:32]}"


def build_ledger_entry(
    *,
    entry_type: str,
    origin_payload: str,
    evidence_id: str,
    subject: str,
    predicate: str,
    effective_time: str | None,
    effective_precision: str,
    value: str | None,
    unit: str | None,
    knowledge_available_at: str,
    parent_ids: tuple[str, ...] = (),
    source_families: tuple[str, ...] = (),
    tier_counts: Mapping[str, int] | None = None,
    conflicts: tuple[str, ...] = (),
    raw_subject: str | None = None,
) -> LedgerEntry:
    if entry_type not in FACT_TYPES:
        raise ValueError(f"invalid ledger entry type {entry_type!r}")
    entry = LedgerEntry(
        fact_id="",  # assigned after construction for hash stability
        entry_type=entry_type,
        origin_payload=origin_payload,
        evidence_id=evidence_id,
        subject=subject,
        predicate=predicate,
        effective_time=effective_time,
        effective_precision=effective_precision,
        value=value,
        unit=unit,
        knowledge_available_at=knowledge_available_at,
        parent_ids=parent_ids,
        source_families=tuple(sorted(source_families)),
        tier_counts=dict(tier_counts or {}),
        conflicts=tuple(sorted(conflicts)),
        raw_subject=raw_subject,
    )
    fid = stable_fact_id(entry)
    return LedgerEntry(
        fact_id=fid,
        entry_type=entry.entry_type,
        origin_payload=entry.origin_payload,
        evidence_id=entry.evidence_id,
        subject=entry.subject,
        predicate=entry.predicate,
        effective_time=entry.effective_time,
        effective_precision=entry.effective_precision,
        value=entry.value,
        unit=entry.unit,
        knowledge_available_at=entry.knowledge_available_at,
        parent_ids=entry.parent_ids,
        source_families=entry.source_families,
        tier_counts=entry.tier_counts,
        conflicts=entry.conflicts,
        raw_subject=entry.raw_subject,
    )


class Ledger:
    """Frozen ledger: entries are added once and never mutated."""

    def __init__(self) -> None:
        self._entries: dict[str, LedgerEntry] = {}

    def add(self, entry: LedgerEntry) -> LedgerEntry:
        if entry.fact_id in self._entries:
            raise ValueError(f"duplicate fact id {entry.fact_id!r}")
        self._entries[entry.fact_id] = entry
        return entry

    def get(self, fact_id: str) -> LedgerEntry:
        try:
            return self._entries[fact_id]
        except KeyError as exc:
            raise KeyError(f"unknown fact id {fact_id!r}") from exc

    def entries(self) -> tuple[LedgerEntry, ...]:
        return tuple(sorted(self._entries.values(), key=lambda e: e.fact_id))

    def seed_fact_ids(self) -> tuple[str, ...]:
        return tuple(e.fact_id for e in self.entries() if e.is_atomic_seed)

    def freeze(self) -> tuple[LedgerEntry, ...]:
        return self.entries()


def entry_to_record(entry: LedgerEntry) -> dict[str, Any]:
    """Closed JSON projection of one ledger entry (for run-bundle replay)."""
    return {
        "fact_id": entry.fact_id,
        "entry_type": entry.entry_type,
        "origin_payload": entry.origin_payload,
        "evidence_id": entry.evidence_id,
        "subject": entry.subject,
        "predicate": entry.predicate,
        "effective_time": entry.effective_time,
        "effective_precision": entry.effective_precision,
        "value": entry.value,
        "unit": entry.unit,
        "knowledge_available_at": entry.knowledge_available_at,
        "parent_ids": list(entry.parent_ids),
        "source_families": list(entry.source_families),
        "tier_counts": dict(entry.tier_counts),
        "conflicts": list(entry.conflicts),
        "raw_subject": entry.raw_subject,
    }


def ledger_to_records(ledger: Ledger) -> list[dict[str, Any]]:
    """Closed ordered JSON projection of the ledger (stable fact-ID order)."""
    return [entry_to_record(e) for e in ledger.entries()]
