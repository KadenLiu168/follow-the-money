"""Versioned regression evaluation: metrics, gates, and offline runner.

Design section 18:

- Metrics: Major Event Recall@10, actual-count Top 3 Precision, Duplicate
  Story Rate, Unsupported Claim Rate, Causal Overclaim Rate. Zero
  denominators => ``not_applicable`` with ``0/0``, never silently dropped.
- Inventory units and IDs (not sentence tokenization) define claim units;
  complete unique claim-audit coverage required before scoring.
- Ranking stability: fixed versioned permutations; identity drift = set
  inequality, selection-order drift = ordered-ID difference, plus the
  full-event subset/order.
- V1 offline gates: zero Recall@10/Top-3-Precision decrease and zero
  Duplicate Story Rate increase vs the versioned baseline; unsupported/causal
  overclaim rates zero for fixture-backed outputs. Baseline changes require
  an explicit versioned update.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any


class EvalError(ValueError):
    """Evaluation setup or gate failure."""


@dataclass(frozen=True)
class Metric:
    name: str
    numerator: int
    denominator: int

    @property
    def applicable(self) -> bool:
        return self.denominator > 0

    @property
    def value(self) -> float | None:
        return self.numerator / self.denominator if self.applicable else None

    def as_report(self) -> dict[str, Any]:
        if not self.applicable:
            return {
                "name": self.name,
                "value": None,
                "numerator": 0,
                "denominator": 0,
                "applicable": False,
                "not_applicable": True,
            }
        return {
            "name": self.name,
            "value": self.value,
            "numerator": self.numerator,
            "denominator": self.denominator,
            "applicable": True,
            "not_applicable": False,
        }


def recall_at_10(expected_major_ids: Sequence[str], selected_ids: Sequence[str]) -> Metric:
    expected = set(expected_major_ids)
    first10 = set(selected_ids[:10])
    matched = len(expected & first10)
    return Metric("recall_at_10", matched, len(expected))


def top3_precision(expected_top3_ids: Sequence[str], full_event_ids: Sequence[str]) -> Metric:
    expected = set(expected_top3_ids)
    matched = len(expected & set(full_event_ids))
    # Actual count in the up-to-three full-event set.
    return Metric("top3_precision", matched, len(full_event_ids))


def duplicate_story_rate(selected_ids: Sequence[str], non_allowed_excess: int) -> Metric:
    return Metric("duplicate_story_rate", non_allowed_excess, len(selected_ids))


def unsupported_claim_rate(
    factual_denominator: int,
    unsupported_numerator: int,
) -> Metric:
    return Metric("unsupported_claim_rate", unsupported_numerator, factual_denominator)


def causal_overclaim_rate(
    causal_denominator: int,
    overclaim_numerator: int,
) -> Metric:
    return Metric("causal_overclaim_rate", overclaim_numerator, causal_denominator)


def _id_list_equal(a: Sequence[str], b: Sequence[str]) -> bool:
    return list(a) == list(b)


@dataclass(frozen=True)
class StabilityReport:
    identity_drift: bool
    selection_order_drift: bool
    full_event_subset_drift: bool
    full_event_order_drift: bool


def compare_ranking_stability(
    reference: Sequence[str],
    permuted: Sequence[str],
    reference_full: Sequence[str],
    permuted_full: Sequence[str],
) -> StabilityReport:
    return StabilityReport(
        identity_drift=set(reference) != set(permuted),
        selection_order_drift=not _id_list_equal(reference, permuted),
        full_event_subset_drift=set(reference_full) != set(permuted_full),
        full_event_order_drift=not _id_list_equal(reference_full, permuted_full),
    )


@dataclass
class DayReport:
    date: str
    metrics: dict[str, Metric]
    stability: StabilityReport | None = None
    errors: list[str] = field(default_factory=list)


@dataclass
class AggregateReport:
    metrics: dict[str, Metric]
    applicable_days: dict[str, int]
    non_applicable_days: dict[str, int]


def aggregate(days: Sequence[DayReport]) -> AggregateReport:
    names = {name for d in days for name in d.metrics}
    agg: dict[str, Metric] = {}
    applicable: dict[str, int] = {}
    non_applicable: dict[str, int] = {}
    for name in sorted(names):
        numerator = sum(d.metrics[name].numerator for d in days if name in d.metrics)
        denominator = sum(d.metrics[name].denominator for d in days if name in d.metrics)
        agg[name] = Metric(name, numerator, denominator)
        applicable[name] = sum(1 for d in days if name in d.metrics and d.metrics[name].applicable)
        non_applicable[name] = sum(
            1 for d in days if name in d.metrics and not d.metrics[name].applicable
        )
    return AggregateReport(
        metrics=agg, applicable_days=applicable, non_applicable_days=non_applicable
    )


def check_offline_gates(
    baseline: Mapping[str, float],
    current: Mapping[str, float],
    *,
    zero_drift_allowed: Sequence[str] = ("recall_at_10", "top3_precision"),
    zero_increase_allowed: Sequence[str] = ("duplicate_story_rate",),
) -> list[str]:
    """V1 zero-adverse-delta offline gates. Returns violation messages."""
    violations: list[str] = []
    for name in zero_drift_allowed:
        base = baseline.get(name)
        cur = current.get(name)
        if base is None or cur is None:
            continue
        if cur < base:
            violations.append(f"{name} decreased {base:.6f} -> {cur:.6f}")
    for name in zero_increase_allowed:
        base = baseline.get(name, 0.0)
        cur = current.get(name, 0.0)
        if cur > base:
            violations.append(f"{name} increased {base:.6f} -> {cur:.6f}")
    return violations
