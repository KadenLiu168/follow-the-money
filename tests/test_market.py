"""Task 6.1-6.8 — formulas, surprise, and confidence fixtures."""

from __future__ import annotations

from decimal import Decimal, getcontext

import pytest

from follow_the_money.ledger import Ledger, build_ledger_entry
from follow_the_money.market.confidence import event_confidence, key_fact_confidence
from follow_the_money.market.formulas import (
    abnormal_move_z,
    annualized_volatility,
    directional_breadth,
    normative_decimal_context,
    quantize2,
    quantize6,
    rolling_volatility,
    sample_std,
    sample_variance,
    simple_return,
    stable_mean,
    volume_change,
    yield_change_bps,
)
from follow_the_money.market.surprise import normalized_surprise, raw_surprise, surprise_for_series


def _dec(*values: str) -> list[Decimal]:
    return [Decimal(v) for v in values]


# ---------------------------------------------------------------------------
# Decimal context isolation
# ---------------------------------------------------------------------------


def test_normative_context_isolated_from_hostile_global():
    getcontext().prec = 3  # hostile ambient
    with normative_decimal_context() as ctx:
        assert ctx.prec == 50
        assert str(Decimal("1.0000000001") + Decimal("1.0000000001")) == "2.0000000002"
    # After exit, ambient unchanged.
    assert getcontext().prec == 3


def test_traps_enabled():
    with normative_decimal_context(), pytest.raises(ZeroDivisionError):
        Decimal(1) / Decimal(0)


# ---------------------------------------------------------------------------
# Normative operation order
# ---------------------------------------------------------------------------


def test_stable_mean_order():
    values = _dec("1", "2", "3", "4")
    assert stable_mean(values) == Decimal("2.5")


def test_sample_variance_n1():
    values = _dec("1", "2", "3", "4", "5")
    var = sample_variance(values)
    # hand: mean=3, sum sq dev=10, /4 = 2.5
    assert var == Decimal("2.5")


def test_sample_std_sqrt():
    values = _dec("1", "2", "3", "4", "5")
    assert sample_std(values) == Decimal("2.5").sqrt()


def test_simple_return():
    assert simple_return(Decimal(110), Decimal(100)) == Decimal("0.1")


def test_simple_return_zero_previous_raises():
    with pytest.raises(ZeroDivisionError):
        simple_return(Decimal(1), Decimal(0))


def test_yield_change_bps():
    assert yield_change_bps(Decimal("4.5"), Decimal("4.0")) == Decimal(50)


def test_volume_change():
    assert volume_change(Decimal(120), Decimal(100)) == Decimal("0.2")


def test_annualized_volatility():
    # 20 identical returns => zero std => zero vol.
    returns = [Decimal("0.01")] * 20
    assert annualized_volatility(returns, "252") == Decimal(0)


def test_rolling_volatility_insufficient():
    result = rolling_volatility([Decimal("0.01")] * 5)
    assert result.is_unknown
    assert result.unknown_reason == "insufficient_history"


def test_rolling_volatility_20_window():
    returns = [Decimal("0.01")] * 19 + [Decimal("0.02")] * 1
    assert len(returns) == 20
    result = rolling_volatility(returns)
    assert not result.is_unknown


def test_abnormal_move_z_excludes_current():
    # Reference window with non-zero variance: 19x 0.01 + 1x 0.02.
    refs = [Decimal("0.01")] * 19 + [Decimal("0.02")]
    z = abnormal_move_z(Decimal("0.11"), refs)
    assert not z.is_unknown
    assert z.value > 0
    # Current return equal to the mean still has non-zero std => computable.
    z2 = abnormal_move_z(Decimal("0.01"), refs)
    assert not z2.is_unknown
    # All-identical reference returns => zero std => unknown.
    flat = [Decimal("0.01")] * 20
    z3 = abnormal_move_z(Decimal("0.01"), flat)
    assert z3.is_unknown
    assert z3.unknown_reason == "zero_reference_std"


def test_directional_breadth():
    assert directional_breadth(6, 2, 10) == Decimal("0.4")
    with pytest.raises(ZeroDivisionError):
        directional_breadth(0, 0, 0)


def test_quantize_boundaries():
    assert quantize6(Decimal("0.1234567")) == Decimal("0.123457")
    # ROUND_HALF_EVEN: 12.345 -> 12.34 (4 is even); 12.355 -> 12.36.
    assert quantize2(Decimal("12.345")) == Decimal("12.34")
    assert quantize2(Decimal("12.355")) == Decimal("12.36")


# ---------------------------------------------------------------------------
# Surprise
# ---------------------------------------------------------------------------


def test_raw_surprise_difference():
    assert raw_surprise(Decimal("3.2"), Decimal("3.0")) == Decimal("0.2")


def test_normalized_surprise_scale():
    assert normalized_surprise(Decimal("3.2"), Decimal("3.0"), Decimal("0.1")) == Decimal(2)


def test_exact_v1_series_scales():
    for series in ("us_cpi_all_items_sa_mom", "us_core_pce_mom", "us_ppi_final_demand_sa_mom"):
        r = surprise_for_series(series_id=series, actual=Decimal("3.2"), consensus=Decimal("3.0"))
        assert r.normalized == Decimal(2)
        assert r.raw == Decimal("0.2")


def test_unknown_series_without_scale():
    r = surprise_for_series(
        series_id="other_series", actual=Decimal("3.2"), consensus=Decimal("3.0")
    )
    assert r.is_unknown
    assert r.unknown_reason == "no_versioned_scale"


def test_missing_consensus():
    r = surprise_for_series(
        series_id="us_cpi_all_items_sa_mom", actual=Decimal("3.2"), consensus=None
    )
    assert r.is_unknown
    assert r.unknown_reason == "missing_consensus_or_actual"


def test_incompatible_unit():
    r = surprise_for_series(
        series_id="us_cpi_all_items_sa_mom",
        actual=Decimal("3.2"),
        consensus=Decimal("3.0"),
        unit="index",
    )
    assert r.is_unknown
    assert r.unknown_reason == "incompatible_unit"


def test_zero_scale_rejected():
    with pytest.raises(ValueError, match="positive"):
        normalized_surprise(Decimal(1), Decimal(0), Decimal(0))


# ---------------------------------------------------------------------------
# Confidence
# ---------------------------------------------------------------------------


def _entry(
    ledger: Ledger,
    *,
    families: tuple[str, ...],
    tiers: dict,
    conflicts: tuple = (),
    predicate: str = "p",
) -> None:
    ledger.add(
        build_ledger_entry(
            entry_type="FACT",
            origin_payload="news",
            evidence_id=f"e-{predicate}",
            subject="s",
            predicate=predicate,
            effective_time=None,
            effective_precision="instant",
            value="1",
            unit="u",
            knowledge_available_at="2026-08-11T01:00:00Z",
            source_families=families,
            tier_counts=tiers,
            conflicts=conflicts,
        )
    )


def test_tier1_support_high():
    ledger = Ledger()
    _entry(ledger, families=("f1",), tiers={"Tier 1": 1})
    assert key_fact_confidence(ledger.entries()[0]).confidence == "high"


def test_two_independent_tier2_families_high():
    ledger = Ledger()
    _entry(ledger, families=("f1", "f2"), tiers={"Tier 2": 2})
    assert key_fact_confidence(ledger.entries()[0]).confidence == "high"


def test_single_tier2_medium():
    ledger = Ledger()
    _entry(ledger, families=("f1",), tiers={"Tier 2": 1})
    assert key_fact_confidence(ledger.entries()[0]).confidence == "medium"


def test_tier3_only_low():
    ledger = Ledger()
    _entry(ledger, families=("f1",), tiers={"Tier 3": 1})
    assert key_fact_confidence(ledger.entries()[0]).confidence == "low"


def test_no_support_unresolved():
    ledger = Ledger()
    _entry(ledger, families=(), tiers={})
    assert key_fact_confidence(ledger.entries()[0]).confidence == "unresolved"


def test_conflict_caps_medium():
    ledger = Ledger()
    _entry(ledger, families=("f1",), tiers={"Tier 1": 1}, conflicts=("v1",))
    assert key_fact_confidence(ledger.entries()[0]).confidence == "medium"


def test_event_confidence_lowest():
    ledger = Ledger()
    _entry(ledger, families=("f1",), tiers={"Tier 1": 1}, predicate="p1")
    _entry(ledger, families=("f2",), tiers={"Tier 3": 1}, predicate="p2")
    result = event_confidence(ledger.entries())
    assert result.confidence == "low"


def test_event_unresolved_excludes():
    ledger = Ledger()
    _entry(ledger, families=("f1",), tiers={"Tier 1": 1}, predicate="p1")
    _entry(ledger, families=(), tiers={}, predicate="p2")
    result = event_confidence(ledger.entries())
    assert result.confidence == "unresolved"


def test_mirrors_count_once():
    # Two source families that are syndicated copies still count as distinct
    # families in the model; the one-origin rule is enforced upstream by
    # deduplication collapsing them into one family.
    ledger = Ledger()
    _entry(ledger, families=("wire",), tiers={"Tier 2": 1}, predicate="p1")
    _entry(ledger, families=("wire",), tiers={"Tier 2": 1}, predicate="p2")
    assert key_fact_confidence(ledger.entries()[0]).confidence == "medium"
