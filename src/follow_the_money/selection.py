"""Deterministic final selection and story-family penalty.

Design section 13:

1. Compute base priority; remove unresolved/no-analysis/below-60%-coverage.
2. Classify full/compact capability from confidence (High + packet-passed
   conflict-free Medium are full-capable; Low is compact-capable only with
   Breaking/Unconfirmed label; unresolved ineligible).
3. Stable-sort by base priority desc, fully_known_at desc, event ID asc.
4. Within the frozen order, the first member of each script-derived
   non-singleton story family is unpenalized; each later member receives 15
   points unless its unordered pair with the frozen first member carries
   validated ``distinct_material_development``.
5. final_priority = max(0, base - penalty); discard below full/compact
   thresholds; re-sort; take first 12; full format for the first up to 3
   selected full-capable events with final_priority >= 60.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from .config.model import Scoring

PENALTY = "15"


def _ts_sort_key(value: str) -> datetime:
    return datetime.fromisoformat(value)


@dataclass(frozen=True)
class SelectionInput:
    event_id: str
    fully_known_at: str
    base_priority: Decimal
    confidence: str  # high | medium | low | unresolved
    component_coverage: Decimal  # 0..1
    analysis_present: bool = True
    packet_passed: bool = True
    conflict_free: bool = True
    breaking_label: bool = False
    story_family_id: str | None = None
    distinct_first_member: bool = False  # unordered pair with family first member


@dataclass(frozen=True)
class SelectedEvent:
    event_id: str
    final_priority: Decimal
    base_priority: Decimal
    format: str  # full | compact
    breaking_unconfirmed: bool = False


@dataclass
class SelectionResult:
    selected: list[SelectedEvent]
    ineligible_reasons: dict[str, str] = field(default_factory=dict)
    sparse_warning: bool = False


def _full_capable(item: SelectionInput, scoring: Scoring) -> bool:
    if item.confidence == "high":
        return True
    return bool(item.confidence == "medium" and item.packet_passed and item.conflict_free)


def _compact_capable(item: SelectionInput, scoring: Scoring) -> bool:
    if item.confidence == "high":
        return True
    if item.confidence == "medium" and item.packet_passed and item.conflict_free:
        return True
    return bool(item.confidence == "low" and item.breaking_label)


def _eligible(item: SelectionInput, scoring: Scoring) -> bool:
    if item.confidence == "unresolved":
        return False
    if not item.analysis_present:
        return False
    return not item.component_coverage < Decimal(scoring.min_component_coverage) / 100


def select_events(
    items: Sequence[SelectionInput],
    scoring: Scoring,
) -> SelectionResult:
    """The single normative selection pipeline."""
    ineligible: dict[str, str] = {}
    eligible: list[SelectionInput] = []
    for item in items:
        if not _eligible(item, scoring):
            reason = (
                "unresolved"
                if item.confidence == "unresolved"
                else ("no_analysis" if not item.analysis_present else "below_coverage")
            )
            ineligible[item.event_id] = reason
            continue
        eligible.append(item)

    # Base-order freeze: sort by base priority desc, fully_known_at desc,
    # event ID asc.
    base_order = sorted(
        eligible,
        key=lambda i: (
            -i.base_priority,
            -_ts_sort_key(i.fully_known_at).timestamp(),
            i.event_id,
        ),
    )
    # Story-family penalty within frozen order.
    first_member: dict[str, str] = {}
    penalized: set[str] = set()
    for item in base_order:
        family = item.story_family_id
        if not family:
            continue
        if family not in first_member:
            first_member[family] = item.event_id
        elif not item.distinct_first_member:
            penalized.add(item.event_id)

    final: list[SelectedEvent] = []
    for item in base_order:
        penalty = Decimal(PENALTY) if item.event_id in penalized else Decimal(0)
        final_priority = max(Decimal(0), item.base_priority - penalty)
        full = _full_capable(item, scoring)
        compact = _compact_capable(item, scoring)
        if full and final_priority >= Decimal(scoring.full_priority_threshold):
            final.append(
                SelectedEvent(
                    item.event_id,
                    final_priority,
                    item.base_priority,
                    "full",
                    breaking_unconfirmed=item.confidence == "low",
                )
            )
        elif compact and final_priority >= Decimal(scoring.compact_priority_threshold):
            final.append(
                SelectedEvent(
                    item.event_id,
                    final_priority,
                    item.base_priority,
                    "compact",
                    breaking_unconfirmed=item.confidence == "low",
                )
            )
        # else discarded (below thresholds)

    # Final sort: final priority desc, fully_known_at desc, ID asc.
    final_order = sorted(
        final,
        key=lambda s: (
            -s.final_priority,
            -_ts_sort_key(_fully_known_by_id(s.event_id, items)).timestamp(),
            s.event_id,
        ),
    )

    hard_max = scoring.hard_max_count
    chosen = final_order[:hard_max]

    # Full format: first up to max_full_events full-capable with priority >= 60.
    full_count = 0
    for i, sel in enumerate(chosen):
        if sel.format == "full" and full_count < scoring.max_full_events:
            full_count += 1
        elif sel.format == "full":
            # Full-capable outside the first three remains compact.
            chosen[i] = SelectedEvent(
                sel.event_id,
                sel.final_priority,
                sel.base_priority,
                "compact",
                breaking_unconfirmed=sel.breaking_unconfirmed,
            )

    sparse = len(chosen) < 3
    return SelectionResult(
        selected=list(chosen), ineligible_reasons=ineligible, sparse_warning=sparse
    )


def _fully_known_by_id(event_id: str, items: Sequence[SelectionInput]) -> str:
    for item in items:
        if item.event_id == event_id:
            return item.fully_known_at
    return ""
