"""Task 8.3-8.8 — scoring, selection, and story-family fixtures."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from follow_the_money.config import load_config
from follow_the_money.scoring import (
    ScoringError,
    brief_priority,
    event_significance,
    freshness_score,
    morning_relevance,
    significance_components,
)
from follow_the_money.selection import (
    SelectionInput,
    select_events,
)

REPO_ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "config" / "config.yaml"
DEFAULT_PROVIDERS = REPO_ROOT / "config" / "providers.yaml"


def _scoring():
    return load_config(DEFAULT_CONFIG, DEFAULT_PROVIDERS, require_verified_enabled=False).scoring


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
# Morning relevance / freshness
# ---------------------------------------------------------------------------


def test_freshness_bins():
    scoring = _scoring()
    assert freshness_score(Decimal(6), scoring) == 100
    assert freshness_score(Decimal("6.0001"), scoring) == 75
    assert freshness_score(Decimal(12), scoring) == 75
    assert freshness_score(Decimal(24), scoring) == 50
    assert freshness_score(Decimal(48), scoring) == 25
    assert freshness_score(Decimal(49), scoring) == 0


def test_morning_relevance_weights():
    scoring = _scoring()
    mr = morning_relevance(
        scoring=scoring,
        age_hours=Decimal(1),
        cn_hk_exposure="direct",
        us_next_session_exposure="direct",
        catalyst_present=True,
    )
    # fresh 100*0.40 + 100*0.25 + 100*0.20 + 100*0.15 = 100
    assert mr == 100
    mr2 = morning_relevance(
        scoring=scoring,
        age_hours=Decimal(49),
        cn_hk_exposure="none",
        us_next_session_exposure="none",
        catalyst_present=False,
    )
    assert mr2 == 0


def test_exposure_map():
    scoring = _scoring()
    assert scoring.exposure_map["direct"] == 100
    assert scoring.exposure_map["indirect"] == 50
    assert scoring.exposure_map["none"] == 0
    assert scoring.exposure_map["unknown"] == 0


def test_brief_priority_formula():
    scoring = _scoring()
    priority = brief_priority(Decimal(80), Decimal(60), scoring)
    # 0.70*80 + 0.30*60 = 74
    assert priority == Decimal(74)


# ---------------------------------------------------------------------------
# Selection pipeline
# ---------------------------------------------------------------------------


def _item(
    event_id: str,
    base: str,
    confidence: str = "high",
    coverage: str = "1.0",
    family: str | None = None,
    coexistence_pairs: frozenset[tuple[str, str]] = frozenset(),
    analysis: bool = True,
    packet: bool = True,
    conflict_free: bool = True,
    breaking: bool = False,
    known: str = "2026-08-11T01:00:00Z",
) -> SelectionInput:
    return SelectionInput(
        event_id=event_id,
        fully_known_at=known,
        base_priority=Decimal(base),
        confidence=confidence,
        component_coverage=Decimal(coverage),
        analysis_present=analysis,
        packet_passed=packet,
        conflict_free=conflict_free,
        breaking_label=breaking,
        story_family_id=family,
        coexistence_pairs=coexistence_pairs,
    )


def test_selection_basic_high_priority():
    scoring = _scoring()
    result = select_events([_item("e1", "90"), _item("e2", "50"), _item("e3", "30")], scoring)
    assert [s.event_id for s in result.selected] == ["e1", "e2"]
    assert result.selected[0].format == "full"
    assert result.selected[1].format == "compact"


def test_selection_below_thresholds_discarded():
    scoring = _scoring()
    result = select_events([_item("e1", "35")], scoring)  # below compact 40
    assert result.selected == []


def test_selection_full_threshold_60():
    scoring = _scoring()
    result = select_events([_item("e1", "59"), _item("e2", "61")], scoring)
    formats = {s.event_id: s.format for s in result.selected}
    assert formats == {"e2": "full", "e1": "compact"}


def test_unresolved_ineligible():
    scoring = _scoring()
    result = select_events([_item("e1", "90", confidence="unresolved")], scoring)
    assert result.selected == []
    assert result.ineligible_reasons["e1"] == "unresolved"


def test_no_analysis_ineligible():
    scoring = _scoring()
    result = select_events([_item("e1", "90", analysis=False)], scoring)
    assert result.selected == []
    assert result.ineligible_reasons["e1"] == "no_analysis"


def test_below_coverage_ineligible():
    scoring = _scoring()
    result = select_events([_item("e1", "90", coverage="0.5")], scoring)
    assert result.selected == []
    assert result.ineligible_reasons["e1"] == "below_coverage"


def test_medium_packet_gate():
    scoring = _scoring()
    # packet-passed conflict-free Medium is full-capable.
    r1 = select_events([_item("e1", "80", confidence="medium", packet=True)], scoring)
    assert r1.selected[0].format == "full"
    # packet-failed Medium is neither full nor compact-capable.
    r2 = select_events([_item("e1", "80", confidence="medium", packet=False)], scoring)
    assert r2.selected == []


def test_low_breaking_compact_only():
    scoring = _scoring()
    r1 = select_events([_item("e1", "80", confidence="low", breaking=True)], scoring)
    assert r1.selected[0].format == "compact"
    assert r1.selected[0].breaking_unconfirmed
    r2 = select_events([_item("e1", "80", confidence="low", breaking=False)], scoring)
    assert r2.selected == []


def test_hard_max_twelve():
    scoring = _scoring()
    items = [_item(f"e{i}", str(100 - i)) for i in range(15)]
    result = select_events(items, scoring)
    assert len(result.selected) == 12


def test_target_ten_informational_only():
    scoring = _scoring()
    # 12 qualifying events retained despite target of 10.
    items = [_item(f"e{i}", str(90 - i)) for i in range(12)]
    result = select_events(items, scoring)
    assert len(result.selected) == 12


def test_fewer_than_three_sparse_warning():
    scoring = _scoring()
    result = select_events([_item("e1", "90"), _item("e2", "50")], scoring)
    assert result.sparse_warning


def test_stable_tie_break():
    scoring = _scoring()
    a = [
        _item("e1", "80", known="2026-08-11T01:00:00Z"),
        _item("e2", "80", known="2026-08-11T02:00:00Z"),
    ]
    b = list(reversed(a))
    ra = select_events(a, scoring)
    rb = select_events(b, scoring)
    assert [s.event_id for s in ra.selected] == ["e2", "e1"]
    assert [s.event_id for s in rb.selected] == ["e2", "e1"]


def test_story_family_penalty():
    scoring = _scoring()
    items = [
        _item("e1", "80", family="fam_x"),
        _item("e2", "75", family="fam_x"),  # later member, no distinct pair
        _item("e3", "70", family="fam_y"),
    ]
    result = select_events(items, scoring)
    # e2 penalized 15 => 60 final, still passes full threshold.
    by_id = {s.event_id: s for s in result.selected}
    assert by_id["e2"].final_priority == Decimal(60)
    assert by_id["e2"].format == "full"


def test_story_family_penalty_uses_configured_value():
    scoring = replace(_scoring(), family_penalty="20")
    result = select_events(
        [_item("e1", "80", family="fam_x"), _item("e2", "75", family="fam_x")],
        scoring,
    )
    by_id = {s.event_id: s for s in result.selected}
    assert by_id["e2"].final_priority == Decimal(55)


def test_distinct_first_member_exempt():
    scoring = _scoring()
    items = [
        _item("e1", "80", family="fam_x"),
        _item("e2", "75", family="fam_x", coexistence_pairs=frozenset({("e1", "e2")})),
    ]
    result = select_events(items, scoring)
    by_id = {s.event_id: s for s in result.selected}
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
    result = select_events(items, scoring)
    by_id = {s.event_id: s for s in result.selected}
    assert by_id["B"].final_priority == Decimal(75)
    assert by_id["C"].final_priority == Decimal(55)


def test_later_to_later_pair_does_not_exempt_against_frozen_first():
    scoring = _scoring()
    pairs = frozenset({("B", "C")})
    result = select_events(
        [
            _item("A", "80", family="fam_z", coexistence_pairs=pairs),
            _item("B", "75", family="fam_z", coexistence_pairs=pairs),
            _item("C", "70", family="fam_z", coexistence_pairs=pairs),
        ],
        scoring,
    )
    by_id = {s.event_id: s for s in result.selected}
    assert by_id["B"].final_priority == Decimal(60)
    assert by_id["C"].final_priority == Decimal(55)


def test_family_penalty_can_cross_compact_threshold():
    scoring = _scoring()
    result = select_events(
        [_item("A", "80", family="fam_z"), _item("B", "54", family="fam_z")],
        scoring,
    )
    assert [s.event_id for s in result.selected] == ["A"]


def test_priority_floor_zero():
    scoring = _scoring()
    items = [_item("e1", "10", family="fam_q"), _item("e2", "8", family="fam_q")]
    result = select_events(items, scoring)
    # e2: 8 - 15 = -7 => floored to 0; below compact 40 => discarded.
    assert all(s.event_id != "e2" for s in result.selected)
