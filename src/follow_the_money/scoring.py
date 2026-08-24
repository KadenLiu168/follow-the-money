"""Deterministic scoring (Event Significance, Event Relevance, Base Priority).

Design sections 12/13:

- All score components are on a closed 0..100 scale; weights 30/20/20/20/10.
- Missing-data policy: full denominator preserved, unknown component
  contributes zero, component coverage = known weights / total; >= 60%
  coverage required for every normally rankable event.
- Fundamental Magnitude known only when scope+fundamental_depth are
  non-unknown; Persistence only when reversibility+structural_horizon are
  non-unknown.
- Event Surprise: maximum absolute normalized surprise among available values
  attached to ``key_fact_ids``; no available value => whole component unknown.
- Systemic Breadth = affected_groups / 9 * 100; Repricing Magnitude uses the
  maximum observable absolute current-excluded reaction z among mapped-group
  proxies.
- Event Relevance: freshness ``evidence_cutoff_at - fully_known_at`` with
  fixed bins; exposure maps 100/50/0/0; catalyst present/absent 100/0.
- Base Priority = 0.70 * significance + 0.30 * event_relevance.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal

from .config.model import Scoring
from .market.formulas import normative_decimal_context

SIGNIFICANCE_COMPONENTS = (
    "fundamental_magnitude",
    "surprise",
    "systemic_breadth",
    "repricing_magnitude",
    "persistence",
)


class ScoringError(ValueError):
    """Scoring configuration or input failed closed."""


@dataclass(frozen=True)
class ComponentScore:
    value: Decimal | None
    weight: int
    known: bool
    unknown_reason: str | None = None


@dataclass(frozen=True)
class EventScores:
    components: Mapping[str, ComponentScore]
    significance: Decimal
    coverage: Decimal
    event_relevance: Decimal
    base_priority: Decimal

    @property
    def coverage_pct(self) -> Decimal:
        return self.coverage * 100


def _pct(value: int | str) -> Decimal:
    return Decimal(str(value)) / 100


def significance_components(
    *,
    scoring: Scoring,
    scope: str,
    fundamental_depth: str,
    reversibility: str,
    structural_horizon: str,
    surprise_values: Sequence[Decimal | None],
    affected_groups: int,
    observable_repricing_z: Decimal | None,
) -> dict[str, ComponentScore]:
    """Compute the five significance components with weights."""
    weights = scoring.significance_weights
    out: dict[str, ComponentScore] = {}

    # Fundamental Magnitude: mean of scope and fundamental_depth maps.
    if scope not in scoring.scope_map or fundamental_depth not in scoring.fundamental_depth_map:
        raise ScoringError("missing categorical mapping for scope/fundamental_depth")
    if scope == "unknown" or fundamental_depth == "unknown":
        out["fundamental_magnitude"] = ComponentScore(None, weights[0], False, "unknown_category")
    else:
        fm = (
            Decimal(scoring.scope_map[scope])
            + Decimal(scoring.fundamental_depth_map[fundamental_depth])
        ) / 2
        out["fundamental_magnitude"] = ComponentScore(fm, weights[0], True)

    # Surprise: max |normalized surprise| among available values.
    available = [v for v in surprise_values if v is not None]
    if available:
        with normative_decimal_context():
            peak = max((abs(v) for v in available), default=Decimal(0))
        score = _surprise_bin_score(peak, scoring.surprise_bins)
        out["surprise"] = ComponentScore(score, weights[1], True)
    else:
        out["surprise"] = ComponentScore(None, weights[1], False, "no_available_surprise")

    # Systemic Breadth: affected_groups / 9 * 100.
    if affected_groups is None or affected_groups < 0:
        out["systemic_breadth"] = ComponentScore(None, weights[2], False, "unclear_mappings")
    else:
        with normative_decimal_context():
            breadth = Decimal(affected_groups) / 9 * 100
        out["systemic_breadth"] = ComponentScore(breadth, weights[2], True)

    # Repricing Magnitude: max observable absolute reaction z via bins.
    if observable_repricing_z is not None:
        score = _surprise_bin_score(abs(observable_repricing_z), scoring.surprise_bins)
        out["repricing_magnitude"] = ComponentScore(score, weights[3], True)
    else:
        out["repricing_magnitude"] = ComponentScore(None, weights[3], False, "no_observable_proxy")

    # Persistence: mean of reversibility and structural_horizon maps.
    if (
        reversibility not in scoring.reversibility_map
        or structural_horizon not in scoring.structural_horizon_map
    ):
        raise ScoringError("missing categorical mapping for reversibility/structural_horizon")
    if reversibility == "unknown" or structural_horizon == "unknown":
        out["persistence"] = ComponentScore(None, weights[4], False, "unknown_category")
    else:
        p = (
            Decimal(scoring.reversibility_map[reversibility])
            + Decimal(scoring.structural_horizon_map[structural_horizon])
        ) / 2
        out["persistence"] = ComponentScore(p, weights[4], True)

    return out


def _surprise_bin_score(value: Decimal, bins: Sequence[tuple[str, str, int]]) -> Decimal:
    """Bin mapping: (boundary, op, score) with ``<`` or ``>=`` ops."""
    for boundary, op, score in bins:
        b = Decimal(boundary)
        if op == "<" and value < b:
            return Decimal(score)
        if op == ">=" and value >= b:
            return Decimal(score)
    return Decimal(0)


def event_significance(
    components: Mapping[str, ComponentScore],
    *,
    total_weight: int = 100,
) -> tuple[Decimal, Decimal]:
    """Weighted significance + coverage fraction (0..1)."""
    with normative_decimal_context():
        weighted = sum(
            (c.value * Decimal(c.weight)) if c.known and c.value is not None else Decimal(0)
            for c in components.values()
        )
        known_weight = sum(c.weight for c in components.values() if c.known)
        coverage = Decimal(known_weight) / Decimal(total_weight)
        significance = weighted / Decimal(total_weight)
    return significance, coverage


def freshness_score(age_hours: Decimal, scoring: Scoring) -> Decimal:
    """Freshness bins: <=6h:100, <=12h:75, <=24h:50, <=48h:25, older:0."""
    for hours, score in scoring.freshness_bins:
        if age_hours <= Decimal(hours):
            return Decimal(score)
    return Decimal(scoring.freshness_older_score)


def event_relevance(
    *,
    scoring: Scoring,
    age_hours: Decimal,
    cn_hk_exposure: str,
    us_next_session_exposure: str,
    catalyst_present: bool,
) -> Decimal:
    """40/25/20/15 weighted Event Relevance."""
    if (
        cn_hk_exposure not in scoring.exposure_map
        or us_next_session_exposure not in scoring.exposure_map
    ):
        raise ScoringError("missing categorical mapping for relevance exposure")
    w_fresh, w_cn, w_us, w_cat = scoring.relevance_weights
    with normative_decimal_context():
        fresh = freshness_score(age_hours, scoring)
        cn = Decimal(scoring.exposure_map[cn_hk_exposure])
        us = Decimal(scoring.exposure_map[us_next_session_exposure])
        cat = Decimal(
            scoring.catalyst_map["present"] if catalyst_present else scoring.catalyst_map["absent"]
        )
        total = (fresh * w_fresh + cn * w_cn + us * w_us + cat * w_cat) / 100
    return total


def base_priority(significance: Decimal, relevance: Decimal, scoring: Scoring) -> Decimal:
    w_sig, w_relevance = scoring.base_priority_weights
    with normative_decimal_context():
        return significance * Decimal(w_sig) + relevance * Decimal(w_relevance)
