"""Evidence confidence and conflict calculation (task 6.7/6.8).

Confidence is independent of significance. Per key fact:

- At least one non-conflicting Tier 1 source, or two independently originated
  Tier 2 source families => High.
- Exactly one Tier 2 source family => Medium.
- Tier 3-only support => Low.
- No support => unresolved.
- A material conflict caps the fact (and therefore the Event) at Medium.
- Duplicate URLs/mirrors/syndicated copies from one original publisher count
  once (one source family).

Event confidence = lowest key-fact confidence; any unresolved key fact
excludes the Event.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from ..ledger import LedgerEntry

CONFIDENCE_ORDER = ("high", "medium", "low", "unresolved")


@dataclass(frozen=True)
class ConfidenceResult:
    confidence: str  # high | medium | low | unresolved
    reasons: tuple[str, ...] = ()


def _tier1_families(entry: LedgerEntry) -> set[str]:
    counts = entry.tier_counts or {}
    return {fam for fam in entry.source_families if counts.get("Tier 1", 0) > 0 and fam}


def _tier2_families(entry: LedgerEntry) -> set[str]:
    counts = entry.tier_counts or {}
    return {fam for fam in entry.source_families if counts.get("Tier 2", 0) > 0 and fam}


def key_fact_confidence(entry: LedgerEntry) -> ConfidenceResult:
    """Confidence for one key fact, capped at Medium on material conflict."""
    reasons: list[str] = []
    if entry.conflicts:
        reasons.append("material_conflict_caps_medium")
        # Conflict caps even a Tier 1-supported fact at Medium.
        if _tier1_families(entry) or len(_tier2_families(entry)) >= 1:
            return ConfidenceResult("medium", tuple(reasons))

    tier1 = _tier1_families(entry)
    tier2 = _tier2_families(entry)

    if tier1:
        return ConfidenceResult("high", ("tier1_support",))
    if len(tier2) >= 2:
        return ConfidenceResult("high", ("two_independent_tier2_families",))
    if len(tier2) == 1:
        return ConfidenceResult("medium", ("single_tier2_family",))
    if entry.tier_counts and entry.tier_counts.get("Tier 3", 0) > 0:
        return ConfidenceResult("low", ("tier3_only",))
    return ConfidenceResult("unresolved", ("no_support",))


def event_confidence(key_facts: Sequence[LedgerEntry]) -> ConfidenceResult:
    """Event confidence = lowest key-fact confidence; unresolved excludes."""
    if not key_facts:
        return ConfidenceResult("unresolved", ("no_key_facts",))
    lowest = "high"
    reasons: list[str] = []
    for fact in key_facts:
        result = key_fact_confidence(fact)
        reasons.append(f"{fact.fact_id}:{result.confidence}")
        if CONFIDENCE_ORDER.index(result.confidence) > CONFIDENCE_ORDER.index(lowest):
            lowest = result.confidence
    return ConfidenceResult(lowest, tuple(reasons))


def count_source_families(entries: Iterable[LedgerEntry]) -> int:
    """Distinct source families across entries (mirrors count once)."""
    return len({fam for e in entries for fam in e.source_families})
