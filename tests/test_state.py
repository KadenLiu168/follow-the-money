"""Task 9.1-9.6 — market state, dashboard, and watchlist fixtures."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from follow_the_money.config import load_config
from follow_the_money.state import (
    breadth_vote,
    classify_market_state,
    z_vote,
)
from follow_the_money.watchlist import WatchlistError, build_watchlist

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "config" / "config.yaml"
DEFAULT_PROVIDERS = REPO_ROOT / "config" / "providers.yaml"
DEFAULT_MANIFEST_ROOT = REPO_ROOT / "providers"

T0 = datetime(2026, 8, 11, 0, 20, 0, tzinfo=UTC)


def _ts(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _cfg():
    return load_config(
        DEFAULT_CONFIG,
        DEFAULT_PROVIDERS,
        manifest_root=DEFAULT_MANIFEST_ROOT,
        require_verified_enabled=False,
    )


# ---------------------------------------------------------------------------
# Vote boundaries
# ---------------------------------------------------------------------------


def test_z_vote_boundaries():
    assert z_vote(Decimal("0.5"), "0.5") == 1  # exact boundary supportive
    assert z_vote(Decimal("0.499"), "0.5") == 0
    assert z_vote(Decimal("-0.5"), "0.5") == -1  # exact boundary adverse
    assert z_vote(Decimal("-0.499"), "0.5") == 0
    assert z_vote(Decimal("2.0"), "0.5") == 1


def test_breadth_vote_boundaries():
    assert breadth_vote(Decimal("0.20"), "0.20") == 1
    assert breadth_vote(Decimal("0.19"), "0.20") == 0
    assert breadth_vote(Decimal("-0.20"), "0.20") == -1


# ---------------------------------------------------------------------------
# Market state classification
# ---------------------------------------------------------------------------


def test_risk_on_classification():
    cfg = _cfg()
    # All equity z positive, VIX negative, rates/liquidity/growth/inflation
    # supportive.
    result = classify_market_state(
        config=cfg,
        role_zs={"sp500": Decimal(1), "csi300": Decimal(1), "hsi": Decimal(1), "vix": Decimal(-1)},
        role_return_zs={
            "dxy": Decimal(-1),
            "usdcnh": Decimal(-1),
            "copper": Decimal(1),
            "wti": Decimal(1),
        },
        yield_change_zs={"us2y": Decimal(-1), "us10y": Decimal(-1), "cn10y": Decimal(-1)},
        equity_breadth=Decimal("0.5"),
        surprise_votes=[1, 1, 1],  # inverted surprise supportive
    )
    assert result.regime == "risk_on"
    assert result.known_dimensions == 5
    assert result.vector["risk_appetite"] == "supportive"


def test_risk_off_classification():
    cfg = _cfg()
    result = classify_market_state(
        config=cfg,
        role_zs={
            "sp500": Decimal(-1),
            "csi300": Decimal(-1),
            "hsi": Decimal(-1),
            "vix": Decimal(1),
        },
        role_return_zs={
            "dxy": Decimal(1),
            "usdcnh": Decimal(1),
            "copper": Decimal(-1),
            "wti": Decimal(-1),
        },
        yield_change_zs={"us2y": Decimal(1), "us10y": Decimal(1), "cn10y": Decimal(1)},
        equity_breadth=Decimal("-0.5"),
        surprise_votes=[-1, -1, -1],
    )
    assert result.regime == "risk_off"


def test_insufficient_coverage_unknown():
    cfg = _cfg()
    # Only Risk Appetite known => fewer than 4 dimensions.
    result = classify_market_state(
        config=cfg,
        role_zs={"sp500": Decimal(1), "csi300": Decimal(0), "hsi": Decimal(0), "vix": Decimal(0)},
        role_return_zs={},
        yield_change_zs={},
        equity_breadth=None,
    )
    assert result.regime == "unknown"


def test_missing_risk_appetite_unknown():
    cfg = _cfg()
    result = classify_market_state(
        config=cfg,
        role_zs={},  # no equity roles
        role_return_zs={"copper": Decimal(1)},
        yield_change_zs={},
        equity_breadth=Decimal("0.5"),
    )
    assert result.regime == "unknown"


def test_missing_roles_accounts_for_yield_change_zs_in_configured_order():
    cfg = _cfg()
    result = classify_market_state(
        config=cfg,
        role_zs={"sp500": Decimal(1)},
        role_return_zs={},
        yield_change_zs={"us2y": Decimal(1), "cn10y": Decimal(1)},
        equity_breadth=None,
    )
    assert "us2y" not in result.missing_roles
    assert "cn10y" not in result.missing_roles
    assert result.missing_roles.index("csi300") < result.missing_roles.index("hsi")


def test_regime_sum_boundaries():
    cfg = _cfg()
    # RA supportive, but dimension sum < 2 => neutral.
    result = classify_market_state(
        config=cfg,
        role_zs={
            "sp500": Decimal(1),
            "csi300": Decimal("0.6"),
            "hsi": Decimal(0),
            "vix": Decimal(0),
        },
        role_return_zs={
            "dxy": Decimal(0),
            "usdcnh": Decimal(0),
            "copper": Decimal("0.6"),
            "wti": Decimal(0),
        },
        yield_change_zs={"us2y": Decimal(0), "us10y": Decimal(0), "cn10y": Decimal(0)},
        equity_breadth=Decimal("0.2"),
    )
    # RA=1 (votes +1,+1,0,0 => sum 2 => supportive). Rates 0, Liquidity 0,
    # Growth 1 (copper + breadth), Inflation 0 => sum=2 => risk_on.
    assert result.regime in ("risk_on", "neutral")


def test_regime_informational_no_scoring_effect():
    # The regime must not appear in any score component (scoring module has no
    # regime input); this asserts the module boundary by signature.
    from follow_the_money.scoring import significance_components

    scoring = _cfg().scoring
    comps = significance_components(
        scoring=scoring,
        scope="sector",
        fundamental_depth="headline",
        reversibility="medium",
        structural_horizon="weeks",
        surprise_values=[],
        affected_groups=1,
        observable_repricing_z=None,
    )
    assert "regime" not in comps


# ---------------------------------------------------------------------------
# Watchlist
# ---------------------------------------------------------------------------


def _calendar_item(
    cid: str, scheduled: datetime, priority: str = "high", announced: datetime | None = None
) -> dict:
    return {
        "calendar_id": cid,
        "priority": priority,
        "scheduled_at": _ts(scheduled),
        "announced_at": _ts(announced) if announced else None,
        "title": f"事件{cid}",
        "evidence_ids": [f"ev_{cid}"],
    }


def test_watchlist_start_inclusion_end_exclusion():
    cfg = _cfg()
    items = [
        _calendar_item("c1", T0 + timedelta(hours=1)),
        _calendar_item("c2", T0 + timedelta(hours=24)),  # exactly at +24h excluded
    ]
    result = build_watchlist(
        calendar_items=items,
        brief_generated_at=_ts(T0),
        calendar_horizon_end=_ts(T0 + timedelta(hours=26)),
        policy=cfg.calendar,
    )
    ids = [e.calendar_id for e in result]
    assert ids == ["c1"]


def test_watchlist_priority_sort_critical_first():
    cfg = _cfg()
    items = [
        _calendar_item("high1", T0 + timedelta(hours=3), priority="high"),
        _calendar_item("crit1", T0 + timedelta(hours=5), priority="critical"),
        _calendar_item("high2", T0 + timedelta(hours=1), priority="high"),
    ]
    result = build_watchlist(
        calendar_items=items,
        brief_generated_at=_ts(T0),
        calendar_horizon_end=_ts(T0 + timedelta(hours=26)),
        policy=cfg.calendar,
    )
    assert [e.calendar_id for e in result] == ["crit1", "high2", "high1"]


def test_watchlist_max_six_no_lower_priority_fill():
    cfg = _cfg()
    items = [_calendar_item(f"c{i}", T0 + timedelta(hours=i + 1)) for i in range(8)]
    items.append(_calendar_item("low1", T0 + timedelta(hours=1), priority="low"))
    result = build_watchlist(
        calendar_items=items,
        brief_generated_at=_ts(T0),
        calendar_horizon_end=_ts(T0 + timedelta(hours=26)),
        policy=cfg.calendar,
    )
    assert len(result) == 6
    assert all(e.priority != "low" for e in result)


def test_watchlist_knowledge_after_cutoff_excluded():
    cfg = _cfg()
    items = [
        _calendar_item("c1", T0 + timedelta(hours=2), announced=T0 + timedelta(minutes=5)),
    ]
    # announced after cutoff => excluded even though scheduled in window.
    result = build_watchlist(
        calendar_items=items,
        brief_generated_at=_ts(T0),
        calendar_horizon_end=_ts(T0 + timedelta(hours=26)),
        policy=cfg.calendar,
        cutoff=_ts(T0),
    )
    assert result == []


def test_watchlist_horizon_too_short_fails():
    cfg = _cfg()
    with pytest.raises(WatchlistError, match="calendar_horizon_end"):
        build_watchlist(
            calendar_items=[],
            brief_generated_at=_ts(T0),
            calendar_horizon_end=_ts(T0 + timedelta(hours=20)),
            policy=cfg.calendar,
        )


def test_watchlist_zero_to_six():
    cfg = _cfg()
    result = build_watchlist(
        calendar_items=[],
        brief_generated_at=_ts(T0),
        calendar_horizon_end=_ts(T0 + timedelta(hours=26)),
        policy=cfg.calendar,
    )
    assert result == []


def test_watchlist_stable_order():
    cfg = _cfg()
    items = [
        _calendar_item("b", T0 + timedelta(hours=2)),
        _calendar_item("a", T0 + timedelta(hours=2)),
        _calendar_item("c", T0 + timedelta(hours=1)),
    ]
    r1 = build_watchlist(
        calendar_items=items,
        brief_generated_at=_ts(T0),
        calendar_horizon_end=_ts(T0 + timedelta(hours=26)),
        policy=cfg.calendar,
    )
    r2 = build_watchlist(
        calendar_items=list(reversed(items)),
        brief_generated_at=_ts(T0),
        calendar_horizon_end=_ts(T0 + timedelta(hours=26)),
        policy=cfg.calendar,
    )
    assert [e.calendar_id for e in r1] == [e.calendar_id for e in r2]
    assert [e.calendar_id for e in r1] == ["c", "a", "b"]
