"""Task 8.3-8.8 — scoring, selection, and story-family fixtures."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from follow_the_money.config import load_config
from follow_the_money.scoring import (
    ScoringError,
    base_priority,
    event_relevance,
    event_significance,
    freshness_score,
    significance_components,
)
from follow_the_money.selection import RankingInput, rank_events

REPO_ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "config" / "config.yaml"
DEFAULT_PROVIDERS = REPO_ROOT / "config" / "providers.yaml"
DEFAULT_MANIFEST_ROOT = REPO_ROOT / "providers"


def _scoring():
    return load_config(
        DEFAULT_CONFIG,
        DEFAULT_PROVIDERS,
        manifest_root=DEFAULT_MANIFEST_ROOT,
        require_verified_enabled=False,
    ).scoring


# ---------------------------------------------------------------------------
# Significance components
# ---------------------------------------------------------------------------


def test_significance_known_all_components():
    scoring = _scoring()
    comps = significance_components(
        scoring=scoring,
        scope="cross_market",
        fundamental_depth="systemic",
        reversibility="effectively_irreversible",
        structural_horizon="years_plus",
        surprise_values=[Decimal("2.5")],
        affected_groups=9,
        observable_repricing_z=Decimal("3.2"),
    )
    assert all(c.known for c in comps.values())
    sig, coverage = event_significance(comps)
    assert coverage == Decimal(1)
    assert 0 <= sig <= 100


def test_significance_unknown_component_zero_and_coverage():
    scoring = _scoring()
    comps = significance_components(
        scoring=scoring,
        scope="unknown",  # FM unknown
        fundamental_depth="headline",
        reversibility="medium",
        structural_horizon="weeks",
        surprise_values=[],
        affected_groups=9,
        observable_repricing_z=None,
    )
    # FM unknown (weight 30), surprise unknown (20), repricing unknown (20).
    assert comps["fundamental_magnitude"].known is False
    assert comps["surprise"].known is False
    assert comps["repricing_magnitude"].known is False
    sig, coverage = event_significance(comps)
    # known weights: systemic_breadth 20 + persistence 10 = 30 => 0.30.
    assert coverage == Decimal("0.3")
    assert sig > 0  # breadth contributes


def test_missing_categorical_mapping_rejected():
    scoring = _scoring()
    with pytest.raises(ScoringError, match="missing categorical mapping"):
        significance_components(
            scoring=scoring,
            scope="bogus",
            fundamental_depth="headline",
            reversibility="medium",
            structural_horizon="weeks",
            surprise_values=[],
            affected_groups=1,
            observable_repricing_z=None,
        )


def test_surprise_bins():
    scoring = _scoring()
    comps = significance_components(
        scoring=scoring,
        scope="sector",
        fundamental_depth="headline",
        reversibility="medium",
        structural_horizon="weeks",
        surprise_values=[Decimal("0.49")],
        affected_groups=0,
        observable_repricing_z=None,
    )
    assert comps["surprise"].value == 0  # <0.5 bin
    comps2 = significance_components(
        scoring=scoring,
        scope="sector",
        fundamental_depth="headline",
        reversibility="medium",
        structural_horizon="weeks",
        surprise_values=[Decimal("0.5")],
        affected_groups=0,
        observable_repricing_z=None,
    )
    assert comps2["surprise"].value == 25  # <1 bin


def test_surprise_multi_key_maximum_absolute():
    scoring = _scoring()
    comps = significance_components(
        scoring=scoring,
        scope="sector",
        fundamental_depth="headline",
        reversibility="medium",
        structural_horizon="weeks",
        surprise_values=[Decimal("-0.4"), Decimal("1.5"), None],
        affected_groups=0,
        observable_repricing_z=None,
    )
    # max |..| = 1.5 => <2 bin => 50
    assert comps["surprise"].value == 50


def test_systemic_breadth_nine_groups():
    scoring = _scoring()
    comps = significance_components(
        scoring=scoring,
        scope="sector",
        fundamental_depth="headline",
        reversibility="medium",
        structural_horizon="weeks",
        surprise_values=[],
        affected_groups=9,
        observable_repricing_z=None,
    )
    assert comps["systemic_breadth"].value == 100


def test_weights_sum_100():
    scoring = _scoring()
    assert sum(scoring.significance_weights) == 100
    assert scoring.significance_weights == (30, 20, 20, 20, 10)


# ---------------------------------------------------------------------------
# Event relevance / freshness
# ---------------------------------------------------------------------------


def test_freshness_bins():
    scoring = _scoring()
    assert freshness_score(Decimal(6), scoring) == 100
    assert freshness_score(Decimal("6.0001"), scoring) == 75
    assert freshness_score(Decimal(12), scoring) == 75
    assert freshness_score(Decimal(24), scoring) == 50
    assert freshness_score(Decimal(48), scoring) == 25
    assert freshness_score(Decimal(49), scoring) == 0


def test_event_relevance_weights():
    scoring = _scoring()
    relevance = event_relevance(
        scoring=scoring,
        age_hours=Decimal(1),
        cn_hk_exposure="direct",
        us_next_session_exposure="direct",
        catalyst_present=True,
    )
    # fresh 100*0.40 + 100*0.25 + 100*0.20 + 100*0.15 = 100
    assert relevance == 100
    relevance2 = event_relevance(
        scoring=scoring,
        age_hours=Decimal(49),
        cn_hk_exposure="none",
        us_next_session_exposure="none",
        catalyst_present=False,
    )
    assert relevance2 == 0


def test_exposure_map():
    scoring = _scoring()
    assert scoring.exposure_map["direct"] == 100
    assert scoring.exposure_map["indirect"] == 50
    assert scoring.exposure_map["none"] == 0
    assert scoring.exposure_map["unknown"] == 0


def test_base_priority_formula():
    scoring = _scoring()
    priority = base_priority(Decimal(80), Decimal(60), scoring)
    # 0.70*80 + 0.30*60 = 74
    assert priority == Decimal(74)


# ---------------------------------------------------------------------------
# Ranking pipeline
# ---------------------------------------------------------------------------


def _item(
    event_id: str,
    base: str,
    confidence: str = "high",
    coverage: str = "1.0",
    family: str | None = None,
    coexistence_pairs: frozenset[tuple[str, str]] = frozenset(),
    known: str = "2026-08-11T01:00:00Z",
) -> RankingInput:
    return RankingInput(
        event_id=event_id,
        fully_known_at=known,
        base_priority=Decimal(base),
        confidence=confidence,
        component_coverage=Decimal(coverage),
        story_family_id=family,
        coexistence_pairs=coexistence_pairs,
    )


def test_ranking_returns_complete_ordered_eligible_set():
    scoring = _scoring()
    result = rank_events([_item("e1", "90"), _item("e2", "50"), _item("e3", "30")], scoring)
    assert [event.event_id for event in result.ranked] == ["e1", "e2", "e3"]


def test_ranking_does_not_apply_priority_thresholds():
    scoring = _scoring()
    result = rank_events([_item("e1", "35")], scoring)
    assert [event.event_id for event in result.ranked] == ["e1"]


def test_ranking_accepts_all_resolved_confidence_levels():
    scoring = _scoring()
    result = rank_events(
        [
            _item("high", "80"),
            _item("medium", "70", confidence="medium"),
            _item("low", "60", confidence="low"),
        ],
        scoring,
    )
    assert [event.event_id for event in result.ranked] == ["high", "medium", "low"]


def test_unresolved_ineligible():
    scoring = _scoring()
    result = rank_events([_item("e1", "90", confidence="unresolved")], scoring)
    assert result.ranked == []
    assert result.ineligible_reasons["e1"] == "unresolved"


def test_below_coverage_ineligible():
    scoring = _scoring()
    result = rank_events([_item("e1", "90", coverage="0.5")], scoring)
    assert result.ranked == []
    assert result.ineligible_reasons["e1"] == "below_coverage"


def test_ranking_returns_more_than_historical_brief_limit():
    scoring = _scoring()
    result = rank_events([_item(f"e{i}", str(100 - i)) for i in range(15)], scoring)
    assert len(result.ranked) == 15


def test_stable_tie_break():
    scoring = _scoring()
    a = [
        _item("e1", "80", known="2026-08-11T01:00:00Z"),
        _item("e2", "80", known="2026-08-11T02:00:00Z"),
    ]
    b = list(reversed(a))
    ra = rank_events(a, scoring)
    rb = rank_events(b, scoring)
    assert [event.event_id for event in ra.ranked] == ["e2", "e1"]
    assert [event.event_id for event in rb.ranked] == ["e2", "e1"]


def test_story_family_penalty():
    scoring = _scoring()
    items = [
        _item("e1", "80", family="fam_x"),
        _item("e2", "75", family="fam_x"),  # later member, no distinct pair
        _item("e3", "70", family="fam_y"),
    ]
    result = rank_events(items, scoring)
    by_id = {event.event_id: event for event in result.ranked}
    assert by_id["e2"].final_priority == Decimal(60)


def test_story_family_penalty_uses_configured_value():
    scoring = replace(_scoring(), family_penalty="20")
    result = rank_events(
        [_item("e1", "80", family="fam_x"), _item("e2", "75", family="fam_x")],
        scoring,
    )
    by_id = {event.event_id: event for event in result.ranked}
    assert by_id["e2"].final_priority == Decimal(55)


def test_distinct_first_member_exempt():
    scoring = _scoring()
    items = [
        _item("e1", "80", family="fam_x"),
        _item("e2", "75", family="fam_x", coexistence_pairs=frozenset({("e1", "e2")})),
    ]
    result = rank_events(items, scoring)
    by_id = {event.event_id: event for event in result.ranked}
    assert by_id["e2"].final_priority == Decimal(75)


def test_penalty_not_transitive():
    scoring = _scoring()
    # A-B and B-C distinct pairs but no A-C; C is still penalized (pair with
    # first member A absent).
    items = [
        _item("A", "80", family="fam_z"),
        _item("B", "75", family="fam_z", coexistence_pairs=frozenset({("A", "B"), ("B", "C")})),
        _item("C", "70", family="fam_z", coexistence_pairs=frozenset({("A", "B"), ("B", "C")})),
    ]
    result = rank_events(items, scoring)
    by_id = {event.event_id: event for event in result.ranked}
    assert by_id["B"].final_priority == Decimal(75)
    assert by_id["C"].final_priority == Decimal(55)


def test_later_to_later_pair_does_not_exempt_against_frozen_first():
    scoring = _scoring()
    pairs = frozenset({("B", "C")})
    result = rank_events(
        [
            _item("A", "80", family="fam_z", coexistence_pairs=pairs),
            _item("B", "75", family="fam_z", coexistence_pairs=pairs),
            _item("C", "70", family="fam_z", coexistence_pairs=pairs),
        ],
        scoring,
    )
    by_id = {event.event_id: event for event in result.ranked}
    assert by_id["B"].final_priority == Decimal(60)
    assert by_id["C"].final_priority == Decimal(55)


def test_priority_floor_zero():
    scoring = _scoring()
    items = [_item("e1", "10", family="fam_q"), _item("e2", "8", family="fam_q")]
    result = rank_events(items, scoring)
    by_id = {event.event_id: event for event in result.ranked}
    assert by_id["e2"].final_priority == Decimal(0)
