"""Deterministic ranking and story-family penalty."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from .config.model import Scoring
from .market.formulas import normative_decimal_context

VALID_CONFIDENCE = frozenset({"high", "medium", "low", "unresolved"})


class RankingError(ValueError):
    """Ranking input violates the closed deterministic contract."""


def _ts_sort_key(value: str) -> datetime:
    return datetime.fromisoformat(value)


@dataclass(frozen=True)
class RankingInput:
    event_id: str
    fully_known_at: str
    base_priority: Decimal
    confidence: str  # high | medium | low | unresolved
    component_coverage: Decimal  # 0..1
    story_family_id: str | None = None
    coexistence_pairs: frozenset[tuple[str, str]] = frozenset()


@dataclass(frozen=True)
class RankedEvent:
    event_id: str
    base_priority: Decimal
    final_priority: Decimal


@dataclass
class RankingResult:
    ranked: list[RankedEvent]
    ineligible_reasons: dict[str, str] = field(default_factory=dict)


def _eligible(item: RankingInput, scoring: Scoring) -> bool:
    if item.confidence == "unresolved":
        return False
    return not item.component_coverage < Decimal(scoring.min_component_coverage) / 100


def rank_events(
    items: Sequence[RankingInput],
    scoring: Scoring,
) -> RankingResult:
    """Rank all eligible inputs with deterministic family penalties."""
    ineligible: dict[str, str] = {}
    eligible: list[RankingInput] = []
    for item in items:
        if item.confidence not in VALID_CONFIDENCE:
            raise RankingError(f"unsupported confidence: {item.confidence!r}")
        if not _eligible(item, scoring):
            ineligible[item.event_id] = (
                "unresolved" if item.confidence == "unresolved" else "below_coverage"
            )
            continue
        eligible.append(item)

    # Base-order freeze: sort by base priority desc, fully_known_at desc,
    # event ID asc.
    base_order = sorted(
        eligible,
        key=lambda item: (
            -item.base_priority,
            -_ts_sort_key(item.fully_known_at).timestamp(),
            item.event_id,
        ),
    )

    # Normalize the already validated incident-pair projections into one
    # immutable set. Resolver semantic errors must fail upstream.
    coexistence_pairs = frozenset(
        tuple(sorted(pair)) for item in items for pair in item.coexistence_pairs
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
        elif tuple(sorted((first_member[family], item.event_id))) not in coexistence_pairs:
            penalized.add(item.event_id)

    final: list[RankedEvent] = []
    for item in base_order:
        penalty = Decimal(scoring.family_penalty) if item.event_id in penalized else Decimal(0)
        with normative_decimal_context():
            final_priority = max(Decimal(0), item.base_priority - penalty)
        final.append(
            RankedEvent(
                event_id=item.event_id,
                base_priority=item.base_priority,
                final_priority=final_priority,
            )
        )

    fully_known_by_id = {item.event_id: item.fully_known_at for item in eligible}
    final_order = sorted(
        final,
        key=lambda event: (
            -event.final_priority,
            -_ts_sort_key(fully_known_by_id[event.event_id]).timestamp(),
            event.event_id,
        ),
    )
    return RankingResult(
        ranked=final_order,
        ineligible_reasons=dict(sorted(ineligible.items())),
    )
