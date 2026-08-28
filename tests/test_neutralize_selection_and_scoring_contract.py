"""ECO-29 RED contract tests for neutral scoring and complete ranking."""

from __future__ import annotations

import ast
import inspect
import shutil
from dataclasses import fields
from decimal import ROUND_DOWN, ROUND_UP, Decimal, getcontext, localcontext
from pathlib import Path

import pytest
import yaml

from follow_the_money.config import load_config
from follow_the_money.config.load import ConfigError
from follow_the_money.config.model import Scoring
from follow_the_money.scoring import (
    ScoringError,
    base_priority,
    event_relevance,
    event_significance,
    freshness_score,
    significance_components,
)
from follow_the_money.selection import RankedEvent, RankingInput, RankingResult, rank_events

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "config" / "config.yaml"
DEFAULT_PROVIDERS = REPO_ROOT / "config" / "providers.yaml"


def _scoring():
    return load_config(
        DEFAULT_CONFIG,
        DEFAULT_PROVIDERS,
        manifest_root=REPO_ROOT / "providers",
        require_verified_enabled=False,
    ).scoring


def _components(scoring: Scoring, **overrides):
    values = {
        "scoring": scoring,
        "scope": "cross_market",
        "fundamental_depth": "systemic",
        "reversibility": "effectively_irreversible",
        "structural_horizon": "years_plus",
        "surprise_values": [Decimal("2.5")],
        "affected_groups": 9,
        "observable_repricing_z": Decimal("3.2"),
    }
    values.update(overrides)
    return significance_components(**values)


def _item(
    event_id: str,
    base: str,
    *,
    confidence: str = "high",
    coverage: str = "1.0",
    family: str | None = None,
    known: str = "2026-08-11T01:00:00Z",
    pairs: frozenset[tuple[str, str]] = frozenset(),
) -> RankingInput:
    return RankingInput(
        event_id=event_id,
        fully_known_at=known,
        base_priority=Decimal(base),
        confidence=confidence,
        component_coverage=Decimal(coverage),
        story_family_id=family,
        coexistence_pairs=pairs,
    )


def _copy_contracts(tmp_path: Path) -> tuple[Path, Path]:
    config_path = tmp_path / "config.yaml"
    providers_path = tmp_path / "providers.yaml"
    shutil.copy2(DEFAULT_CONFIG, config_path)
    shutil.copy2(DEFAULT_PROVIDERS, providers_path)
    return config_path, providers_path


def _write_yaml(path: Path, value: dict) -> None:
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")


# ---------------------------------------------------------------------------
# RED numerical parity and neutral scoring contract
# ---------------------------------------------------------------------------


def test_frozen_all_known_and_partial_significance_oracles():
    scoring = _scoring()
    all_known, all_known_coverage = event_significance(_components(scoring))
    partial, partial_coverage = event_significance(
        _components(
            scoring,
            scope="unknown",
            fundamental_depth="headline",
            reversibility="medium",
            structural_horizon="weeks",
            surprise_values=[],
            affected_groups=9,
            observable_repricing_z=None,
        )
    )

    assert all_known == Decimal(95)
    assert all_known_coverage == Decimal(1)
    assert partial == Decimal(25)
    assert partial_coverage == Decimal("0.3")


def test_frozen_surprise_freshness_breadth_and_relevance_oracles():
    scoring = _scoring()
    surprise = _components(
        scoring,
        scope="sector",
        fundamental_depth="headline",
        reversibility="medium",
        structural_horizon="weeks",
        surprise_values=[Decimal("-0.4"), Decimal("1.5"), None],
        affected_groups=3,
        observable_repricing_z=None,
    )
    surprise_score = surprise["surprise"].value
    breadth_score = surprise["systemic_breadth"].value
    significance, coverage = event_significance(surprise)

    assert surprise_score == Decimal(50)
    assert breadth_score == Decimal("33.333333333333333333333333333333333333333333333333")
    assert significance == Decimal("32.916666666666666666666666666666666666666666666667")
    assert coverage == Decimal("0.8")
    assert [
        freshness_score(Decimal(value), scoring) for value in (6, "6.0001", 12, 24, 48, 49)
    ] == [
        Decimal(100),
        Decimal(75),
        Decimal(75),
        Decimal(50),
        Decimal(25),
        Decimal(0),
    ]
    assert event_relevance(
        scoring=scoring,
        age_hours=Decimal(12),
        cn_hk_exposure="direct",
        us_next_session_exposure="indirect",
        catalyst_present=True,
    ) == Decimal(80)
    assert event_relevance(
        scoring=scoring,
        age_hours=Decimal(12),
        cn_hk_exposure="indirect",
        us_next_session_exposure="none",
        catalyst_present=True,
    ) == Decimal("57.5")
    assert event_relevance(
        scoring=scoring,
        age_hours=Decimal(12),
        cn_hk_exposure="unknown",
        us_next_session_exposure="unknown",
        catalyst_present=True,
    ) == Decimal(45)
    assert event_relevance(
        scoring=scoring,
        age_hours=Decimal(49),
        cn_hk_exposure="none",
        us_next_session_exposure="none",
        catalyst_present=False,
    ) == Decimal(0)


def test_fractional_systemic_breadth_is_ambient_context_independent():
    scoring = _scoring()
    original_context = repr(getcontext())
    results = []

    for precision, rounding in ((6, ROUND_DOWN), (80, ROUND_UP)):
        with localcontext() as context:
            context.prec = precision
            context.rounding = rounding
            components = _components(scoring, affected_groups=3)
            significance, coverage = event_significance(components)
            results.append(
                (
                    components["systemic_breadth"].value,
                    significance,
                    coverage,
                )
            )

    assert repr(getcontext()) == original_context
    assert results == [
        (
            Decimal("33.333333333333333333333333333333333333333333333333"),
            Decimal("81.666666666666666666666666666666666666666666666667"),
            Decimal(1),
        ),
        (
            Decimal("33.333333333333333333333333333333333333333333333333"),
            Decimal("81.666666666666666666666666666666666666666666666667"),
            Decimal(1),
        ),
    ]


def test_significance_components_ignore_hostile_decimal_context():
    scoring = _scoring()
    original_context = repr(getcontext())
    results = []

    for precision, rounding in ((1, ROUND_UP), (80, ROUND_DOWN)):
        with localcontext() as context:
            context.prec = precision
            context.rounding = rounding
            components = _components(
                scoring,
                scope="sector",
                fundamental_depth="headline",
                reversibility="medium",
                structural_horizon="months",
                surprise_values=[Decimal("1.5")],
                affected_groups=3,
                observable_repricing_z=Decimal("-0.4999"),
            )
            significance, coverage = event_significance(components)
            results.append(
                (
                    {name: component.value for name, component in components.items()},
                    significance,
                    coverage,
                )
            )

    assert repr(getcontext()) == original_context
    assert results == [
        (
            {
                "fundamental_magnitude": Decimal("37.5"),
                "surprise": Decimal(50),
                "systemic_breadth": Decimal("33.333333333333333333333333333333333333333333333333"),
                "repricing_magnitude": Decimal(0),
                "persistence": Decimal("62.5"),
            },
            Decimal("34.166666666666666666666666666666666666666666666667"),
            Decimal(1),
        ),
        (
            {
                "fundamental_magnitude": Decimal("37.5"),
                "surprise": Decimal(50),
                "systemic_breadth": Decimal("33.333333333333333333333333333333333333333333333333"),
                "repricing_magnitude": Decimal(0),
                "persistence": Decimal("62.5"),
            },
            Decimal("34.166666666666666666666666666666666666666666666667"),
            Decimal(1),
        ),
    ]

    boundary = _components(scoring, observable_repricing_z=Decimal("-0.5"))
    assert boundary["repricing_magnitude"].value == Decimal(25)


def test_frozen_base_priority_and_hostile_decimal_context():
    scoring = _scoring()
    old_context = getcontext().copy()
    try:
        getcontext().prec = 6
        getcontext().rounding = ROUND_DOWN
        significance, coverage = event_significance(_components(scoring))
        relevance = event_relevance(
            scoring=scoring,
            age_hours=Decimal("6.0001"),
            cn_hk_exposure="indirect",
            us_next_session_exposure="direct",
            catalyst_present=True,
        )
        priority = base_priority(Decimal(80), Decimal(60), scoring)
    finally:
        getcontext().prec = old_context.prec
        getcontext().rounding = old_context.rounding

    assert (significance, coverage) == (Decimal(95), Decimal(1))
    assert relevance == Decimal("77.5")
    assert priority == Decimal("74.00")


def test_neutral_scoring_names_replace_morning_and_brief_aliases():
    import follow_the_money.scoring as scoring_module

    assert hasattr(scoring_module, "event_relevance")
    assert hasattr(scoring_module, "base_priority")
    assert not hasattr(scoring_module, "morning_relevance")
    assert not hasattr(scoring_module, "brief_priority")
    assert {field.name for field in fields(scoring_module.EventScores)} == {
        "components",
        "significance",
        "coverage",
        "event_relevance",
        "base_priority",
    }


def test_unmapped_categorical_value_remains_fail_closed():
    with pytest.raises(ScoringError, match="missing categorical mapping"):
        significance_components(
            scoring=_scoring(),
            scope="not-configured",
            fundamental_depth="headline",
            reversibility="medium",
            structural_horizon="weeks",
            surprise_values=[],
            affected_groups=1,
            observable_repricing_z=None,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    (("cn_hk_exposure", "not-configured"), ("us_next_session_exposure", "not-configured")),
)
def test_unmapped_relevance_exposure_remains_fail_closed(field: str, value: str):
    inputs = {
        "scoring": _scoring(),
        "age_hours": Decimal(1),
        "cn_hk_exposure": "direct",
        "us_next_session_exposure": "direct",
        "catalyst_present": True,
    }
    inputs[field] = value

    with pytest.raises(ScoringError, match="missing categorical mapping"):
        event_relevance(**inputs)


# ---------------------------------------------------------------------------
# RED closed configuration contract
# ---------------------------------------------------------------------------


def test_shipped_configuration_uses_one_neutral_relevance_contract():
    raw = yaml.safe_load(DEFAULT_CONFIG.read_text(encoding="utf-8"))
    scoring = _scoring()

    assert raw["scoring"]["relevance_weights"] == [40, 25, 20, 15]
    assert scoring.relevance_weights == (40, 25, 20, 15)
    assert not hasattr(scoring, "morning_weights")
    assert not any(
        hasattr(scoring, name)
        for name in (
            "full_priority_threshold",
            "compact_priority_threshold",
            "target_count",
            "hard_max_count",
            "max_full_events",
        )
    )


@pytest.mark.parametrize(
    "legacy_key",
    (
        "morning_weights",
        "full_priority_threshold",
        "compact_priority_threshold",
        "target_count",
        "hard_max_count",
        "max_full_events",
    ),
)
def test_strict_loader_rejects_every_removed_scoring_key(tmp_path: Path, legacy_key: str):
    config_path, providers_path = _copy_contracts(tmp_path)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["scoring"][legacy_key] = [40, 25, 20, 15] if legacy_key == "morning_weights" else 1
    _write_yaml(config_path, config)

    with pytest.raises(ConfigError, match="unknown keys"):
        load_config(
            config_path,
            providers_path,
            require_verified_enabled=True,
            manifest_root=REPO_ROOT / "providers",
        )


# ---------------------------------------------------------------------------
# RED ranking shape, eligibility, ordering, and family semantics
# ---------------------------------------------------------------------------


def test_ranking_types_are_neutral_and_have_no_legacy_fields():
    assert {field.name for field in fields(RankingInput)} == {
        "event_id",
        "fully_known_at",
        "base_priority",
        "confidence",
        "component_coverage",
        "story_family_id",
        "coexistence_pairs",
    }
    assert {field.name for field in fields(RankedEvent)} == {
        "event_id",
        "base_priority",
        "final_priority",
    }
    assert {field.name for field in fields(RankingResult)} == {
        "ranked",
        "ineligible_reasons",
    }
    all_names = {
        field.name
        for model in (RankingInput, RankedEvent, RankingResult)
        for field in fields(model)
    }
    assert not all_names.intersection(
        {
            "analysis_present",
            "packet_passed",
            "conflict_free",
            "breaking_label",
            "format",
            "breaking_unconfirmed",
            "sparse_warning",
        }
    )
    assert "items" in inspect.signature(rank_events).parameters


def test_resolved_confidence_levels_rank_without_workflow_state():
    result = rank_events(
        [
            _item("high", "80"),
            _item("medium", "70", confidence="medium"),
            _item("low", "60", confidence="low"),
        ],
        _scoring(),
    )

    assert [event.event_id for event in result.ranked] == ["high", "medium", "low"]
    assert result.ineligible_reasons == {}


def test_only_unresolved_and_below_coverage_are_ineligible():
    result = rank_events(
        [
            _item("unresolved", "90", confidence="unresolved"),
            _item("below", "80", coverage="0.5"),
            _item("valid", "70", confidence="low"),
        ],
        _scoring(),
    )

    assert [event.event_id for event in result.ranked] == ["valid"]
    assert result.ineligible_reasons == {
        "unresolved": "unresolved",
        "below": "below_coverage",
    }


def test_minimum_component_coverage_is_inclusive():
    result = rank_events([_item("boundary", "70", coverage="0.6")], _scoring())

    assert [event.event_id for event in result.ranked] == ["boundary"]


def test_unknown_confidence_fails_closed_before_ranking():
    with pytest.raises(ValueError, match="confidence"):
        rank_events([_item("invalid", "70", confidence="not-resolved")], _scoring())


def test_all_eligible_events_are_returned_without_historical_limit():
    result = rank_events(
        [_item(f"e{i:02d}", str(100 - i)) for i in range(15)],
        _scoring(),
    )

    assert len(result.ranked) == 15
    assert {event.event_id for event in result.ranked} == {f"e{i:02d}" for i in range(15)}


def test_base_and_final_tie_breaks_are_deterministic():
    result = rank_events(
        [
            _item("b", "80", known="2026-08-11T01:00:00Z"),
            _item("a", "80", known="2026-08-11T02:00:00Z"),
            _item("c", "65", known="2026-08-11T02:00:00Z", family="fam"),
            _item("d", "80", known="2026-08-11T02:00:00Z", family="fam"),
        ],
        _scoring(),
    )

    assert [event.event_id for event in result.ranked] == ["a", "d", "b", "c"]


def test_ranking_is_input_permutation_invariant():
    items = [
        _item("a", "80", family="fam", known="2026-08-11T01:00:00Z"),
        _item("b", "75", family="fam", known="2026-08-11T02:00:00Z"),
        _item("c", "70", family="other"),
        _item("u", "90", confidence="unresolved"),
        _item("z", "85", coverage="0.5"),
    ]
    first = rank_events(items, _scoring())
    second = rank_events(list(reversed(items)), _scoring())

    def signature(result):
        return (
            list(result.ineligible_reasons.items()),
            [
                (event.event_id, event.base_priority, event.final_priority)
                for event in result.ranked
            ],
        )

    assert signature(first) == signature(second)


def test_configured_penalty_zero_floor_and_exact_first_pair_exemption():
    scoring = _scoring()
    result = rank_events(
        [
            _item("first", "80", family="fam"),
            _item("paired", "75", family="fam", pairs=frozenset({("paired", "first")})),
            _item("floor", "8", family="fam"),
        ],
        scoring,
    )
    by_id = {event.event_id: event for event in result.ranked}

    assert by_id["first"].final_priority == Decimal(80)
    assert by_id["paired"].final_priority == Decimal(75)
    assert by_id["floor"].final_priority == Decimal(0)


def test_later_to_later_pair_is_not_transitive():
    pairs = frozenset({("A", "B"), ("B", "C")})
    result = rank_events(
        [
            _item("A", "80", family="fam", pairs=pairs),
            _item("B", "75", family="fam", pairs=pairs),
            _item("C", "70", family="fam", pairs=pairs),
        ],
        _scoring(),
    )
    by_id = {event.event_id: event for event in result.ranked}

    assert by_id["B"].final_priority == Decimal(75)
    assert by_id["C"].final_priority == Decimal(55)


# ---------------------------------------------------------------------------
# RED repository boundary
# ---------------------------------------------------------------------------


def test_feed_and_production_modules_do_not_call_retained_scoring_or_ranking():
    source_root = REPO_ROOT / "src" / "follow_the_money"
    for path in source_root.rglob("*.py"):
        if path.name in {"scoring.py", "selection.py"}:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                imported_module = node.module or ""
                imported_names = {alias.name for alias in node.names}
                assert not (
                    imported_module
                    in {
                        "follow_the_money.scoring",
                        "follow_the_money.selection",
                    }
                    or (node.level > 0 and imported_module in {"scoring", "selection"})
                    or (
                        imported_module in {"", "follow_the_money"}
                        and imported_names.intersection({"scoring", "selection"})
                    )
                ), path
            if isinstance(node, ast.Import):
                assert all(
                    alias.name
                    not in {
                        "follow_the_money.scoring",
                        "follow_the_money.selection",
                    }
                    for alias in node.names
                ), path

    assert not (REPO_ROOT / "schemas" / "scoring.schema.json").exists()
    assert not (REPO_ROOT / "schemas" / "ranking.schema.json").exists()
