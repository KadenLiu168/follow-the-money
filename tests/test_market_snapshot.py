"""Production MarketSnapshot fixtures for the activation Change."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, localcontext

import exchange_calendars as xcals
import pytest

from follow_the_money.config import load_config
from follow_the_money.market.formulas import (
    normative_decimal_context,
    quantize2,
    quantize6,
    simple_return,
)
from follow_the_money.market.snapshot import RoleMetric, build_market_snapshot

from .test_config import DEFAULT_CONFIG, DEFAULT_MANIFEST_ROOT, DEFAULT_PROVIDERS


def _verified_config():
    cfg = load_config(
        DEFAULT_CONFIG,
        DEFAULT_PROVIDERS,
        manifest_root=DEFAULT_MANIFEST_ROOT,
    )
    return replace(
        cfg,
        roles=tuple(replace(role, mapping_verified=True) for role in cfg.roles),
    )


def _ts(day: datetime) -> str:
    return day.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _feed(role_id: str, values: list[str], *, unit: str, start: datetime) -> dict:
    observations = [
        {
            "as_of": _ts(start + timedelta(days=i)),
            "available_at": _ts(start + timedelta(days=i, minutes=5)),
            "value": value,
            "unit": unit,
        }
        for i, value in enumerate(values)
    ]
    return {
        "evidence_cutoff_at": _ts(start + timedelta(days=len(values), hours=1)),
        "items": [
            {
                "id": f"ev-{role_id}",
                "provider_id": "yahoo_market",
                "source": {"knowledge_available_at": observations[-1]["available_at"]},
                "payload": {
                    "type": "market_data",
                    "instrument_id": role_id,
                    "unit": unit,
                    "observations": observations,
                    "raw_metadata": {},
                },
            }
        ],
    }


def test_price_role_uses_21_changes_and_current_excluded_reference_window():
    cfg = _verified_config()
    start = datetime(2026, 7, 1, tzinfo=UTC)
    values = [str(100 + i * i) for i in range(22)]
    with localcontext() as ctx:
        ctx.prec = 2
        snapshot = build_market_snapshot(_feed("btc", values, unit="price", start=start), cfg)

    metric = snapshot.metrics["btc"]
    assert len(metric.changes) == 21
    assert len(metric.reference_changes) == 20
    assert metric.current_change == metric.changes[-1]
    assert metric.reference_changes == metric.changes[:-1]
    assert metric.z_score is not None
    assert metric.output_change == quantize6(metric.current_change)


def test_yield_role_uses_basis_points_and_not_raw_level():
    cfg = _verified_config()
    sessions = xcals.get_calendar("XNYS").sessions_in_range("2026-06-01", "2026-08-01")[-22:]
    values = [str(4 + i * i / 100) for i in range(22)]
    feed = _feed("us10y", values, unit="percent", start=datetime(2026, 6, 1, tzinfo=UTC))
    observations = feed["items"][0]["payload"]["observations"]
    calendar = xcals.get_calendar("XNYS")
    for observation, session in zip(observations, sessions):
        timestamp = calendar.schedule.loc[session, "close"].to_pydatetime()
        observation["as_of"] = _ts(timestamp)
        observation["available_at"] = _ts(timestamp + timedelta(minutes=5))
    feed["evidence_cutoff_at"] = _ts(
        calendar.schedule.loc[sessions[-1], "close"].to_pydatetime() + timedelta(hours=1)
    )
    snapshot = build_market_snapshot(feed, cfg)
    metric = snapshot.metrics["us10y"]
    assert metric.change_kind == "yield_bps"
    assert metric.current_change != Decimal(values[-1])
    assert metric.output_change == quantize2(metric.current_change)


def test_anomaly_boundary_is_inclusive_at_exact_two():
    metric = RoleMetric(
        role_id="btc",
        unit="price",
        change_kind="return",
        current_change=Decimal(1),
        z_score=Decimal("2.0"),
        available=True,
    )
    assert metric.anomalous is True


def test_cutoff_equality_is_eligible():
    cfg = _verified_config()
    start = datetime(2026, 7, 1, tzinfo=UTC)
    feed = _feed("btc", [str(100 + i * i) for i in range(22)], unit="price", start=start)
    last_label = datetime.fromisoformat(feed["items"][0]["payload"]["observations"][-1]["as_of"])
    feed["evidence_cutoff_at"] = _ts(last_label + timedelta(days=1, minutes=5))
    assert build_market_snapshot(feed, cfg).metrics["btc"].available is True


def test_partial_current_session_is_excluded_fail_closed():
    cfg = _verified_config()
    start = datetime(2026, 7, 1, tzinfo=UTC)
    feed = _feed("btc", [str(100 + i * i) for i in range(22)], unit="price", start=start)
    last_label = datetime.fromisoformat(feed["items"][0]["payload"]["observations"][-1]["as_of"])
    cutoff = last_label + timedelta(days=1, minutes=5) - timedelta(seconds=1)
    feed["evidence_cutoff_at"] = _ts(cutoff)
    snapshot = build_market_snapshot(feed, cfg)
    assert snapshot.metrics["btc"].available is False
    assert snapshot.metrics["btc"].unknown_reason in {
        "current_partial_session",
        "insufficient_history",
    }


def test_exchange_daily_open_timestamp_is_not_treated_as_completed_close():
    cfg = _verified_config()
    calendar = xcals.get_calendar("XNYS")
    sessions = calendar.sessions_in_range("2026-06-01", "2026-08-01")[-22:]
    observations = []
    for i, label in enumerate(sessions):
        market_open = calendar.schedule.loc[label, "open"].to_pydatetime()
        observations.append(
            {
                "as_of": _ts(market_open),
                "available_at": _ts(market_open + timedelta(minutes=5)),
                "value": str(100 + i * i),
                "unit": "index",
            }
        )
    latest_open = calendar.schedule.loc[sessions[-1], "open"].to_pydatetime()
    feed = {
        "evidence_cutoff_at": _ts(latest_open + timedelta(minutes=10)),
        "items": [
            {
                "id": "ev-sp500",
                "payload": {
                    "type": "market_data",
                    "instrument_id": "sp500",
                    "unit": "index",
                    "observations": observations,
                },
            }
        ],
    }
    metric = build_market_snapshot(feed, cfg).metrics["sp500"]
    assert metric.available is False
    assert metric.unknown_reason == "current_partial_session"


def test_missing_expected_session_is_not_compressed():
    cfg = _verified_config()
    start = datetime(2026, 7, 1, tzinfo=UTC)
    feed = _feed("btc", [str(100 + i * i) for i in range(22)], unit="price", start=start)
    del feed["items"][0]["payload"]["observations"][10]
    snapshot = build_market_snapshot(feed, cfg)
    assert snapshot.metrics["btc"].unknown_reason == "missing_expected_session"


def test_post_cutoff_observation_fails_role_closed_instead_of_using_older_window():
    cfg = _verified_config()
    start = datetime(2026, 7, 1, tzinfo=UTC)
    feed = _feed("btc", [str(100 + i * i) for i in range(22)], unit="price", start=start)
    cutoff = datetime.fromisoformat(feed["evidence_cutoff_at"])
    feed["items"][0]["payload"]["observations"].append(
        {
            "as_of": _ts(cutoff + timedelta(seconds=1)),
            "available_at": None,
            "value": "999",
            "unit": "price",
        }
    )

    metric = build_market_snapshot(feed, cfg).metrics["btc"]
    assert metric.available is False
    assert metric.unknown_reason == "post_cutoff_observation"


def test_duplicate_session_label_is_unknown():
    cfg = _verified_config()
    start = datetime(2026, 7, 1, tzinfo=UTC)
    feed = _feed("btc", [str(100 + i * i) for i in range(22)], unit="price", start=start)
    observations = feed["items"][0]["payload"]["observations"]
    observations[-1]["as_of"] = observations[-2]["as_of"]
    snapshot = build_market_snapshot(feed, cfg)
    assert snapshot.metrics["btc"].unknown_reason == "duplicate_session_label"


def test_wrong_unit_and_zero_reference_std_are_explicit():
    cfg = _verified_config()
    start = datetime(2026, 7, 1, tzinfo=UTC)
    wrong = _feed("btc", [str(100 + i) for i in range(22)], unit="percent", start=start)
    assert build_market_snapshot(wrong, cfg).metrics["btc"].unknown_reason == "incompatible_unit"
    observation_mismatch = _feed(
        "btc", [str(100 + i) for i in range(22)], unit="price", start=start
    )
    observation_mismatch["items"][0]["payload"]["observations"][0]["unit"] = "percent"
    assert (
        build_market_snapshot(observation_mismatch, cfg).metrics["btc"].unknown_reason
        == "incompatible_unit"
    )
    constant = _feed("btc", ["100"] * 22, unit="price", start=start)
    metric = build_market_snapshot(constant, cfg).metrics["btc"]
    assert metric.available is True
    assert metric.z_score is None
    assert metric.unknown_reason == "zero_reference_std"


def test_session_boundary_uses_real_calendar_even_under_error_warning_policy():
    """Lock the production/test code path to the real exchange calendar.

    pytest promotes DeprecationWarning to an error; the snapshot must still
    consult the configured calendar (holidays excluded) instead of diverting
    onto a weekday-only fallback that production would not use.
    """
    import warnings

    from follow_the_money.market.snapshot import _session_label

    cfg = _verified_config()
    session = next(s for s in cfg.sessions if s.id == "us_equities")
    calendar = xcals.get_calendar("XNYS")
    holiday = date(2026, 7, 3)  # Independence Day (observed, 2026-07-03)
    assert holiday.weekday() < 5  # a weekday, so a weekday-only fallback would accept it
    assert "2026-07-03" not in [
        str(x.date()) for x in calendar.sessions_in_range("2026-07-03", "2026-07-03")
    ]
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        assert (
            _session_label(
                datetime(holiday.year, holiday.month, holiday.day, 20, tzinfo=UTC), session
            )
            is None
        )
        assert _session_label(datetime(2026, 7, 2, 20, tzinfo=UTC), session) == "2026-07-02"


def test_holiday_observation_is_not_a_session_label():
    cfg = _verified_config()
    calendar = xcals.get_calendar("XNYS")
    sessions = list(calendar.sessions_in_range("2026-06-01", "2026-07-31"))
    session_labels = {str(s.date()) for s in sessions}
    window = sessions[-22:]
    first, last = window[0].date(), window[-1].date()
    holiday = next(
        d
        for d in (first + timedelta(days=i) for i in range((last - first).days + 1))
        if d.weekday() < 5 and d.isoformat() not in session_labels
    )
    observations = []
    for i, label in enumerate(window):
        close = calendar.schedule.loc[label, "close"].to_pydatetime()
        observations.append(
            {
                "as_of": _ts(close),
                "available_at": _ts(close + timedelta(minutes=5)),
                "value": str(100 + i * i),
                "unit": "index",
            }
        )
    observations.append(
        {
            "as_of": _ts(datetime(holiday.year, holiday.month, holiday.day, 20, tzinfo=UTC)),
            "available_at": None,
            "value": "9999",
            "unit": "index",
        }
    )
    observations.sort(key=lambda o: o["as_of"])
    feed = {
        "evidence_cutoff_at": _ts(
            calendar.schedule.loc[window[-1], "close"].to_pydatetime() + timedelta(hours=1)
        ),
        "items": [
            {
                "id": "ev-sp500",
                "payload": {
                    "type": "market_data",
                    "instrument_id": "sp500",
                    "unit": "index",
                    "observations": observations,
                },
            }
        ],
    }
    metric = build_market_snapshot(feed, cfg).metrics["sp500"]
    assert metric.available is True
    assert len(metric.changes) == 21
    with normative_decimal_context():
        expected = simple_return(Decimal(541), Decimal(500))
    assert metric.current_change == expected


def test_continuous_245_weekday_boundary_and_weekend_exclusion():
    cfg = _verified_config()
    days: list[datetime] = []
    cursor = datetime(2026, 6, 1, tzinfo=UTC)
    while len(days) < 22:
        if cursor.weekday() < 5:
            days.append(cursor)
        cursor += timedelta(days=1)
    observations = [
        {"as_of": _ts(day), "available_at": None, "value": str(100 + i * i), "unit": "index"}
        for i, day in enumerate(days)
    ]
    observations.append(
        {
            "as_of": _ts(datetime(2026, 6, 6, tzinfo=UTC)),  # Saturday inside the window
            "available_at": None,
            "value": "9999",
            "unit": "index",
        }
    )
    observations.sort(key=lambda o: o["as_of"])
    feed = {
        "evidence_cutoff_at": _ts(datetime(2026, 7, 1, 0, 5, tzinfo=UTC)),
        "items": [
            {
                "id": "ev-dxy",
                "payload": {
                    "type": "market_data",
                    "instrument_id": "dxy",
                    "unit": "index",
                    "observations": observations,
                },
            }
        ],
    }
    # 22 weekdays end 2026-06-30; its 24/5 UTC boundary is 2026-07-01T00:05Z.
    metric = build_market_snapshot(feed, cfg).metrics["dxy"]
    assert metric.available is True
    assert len(metric.changes) == 21
    with normative_decimal_context():
        expected = simple_return(Decimal(541), Decimal(500))
    assert metric.current_change == expected
    feed["evidence_cutoff_at"] = _ts(datetime(2026, 7, 1, 0, 4, 59, tzinfo=UTC))
    metric = build_market_snapshot(feed, cfg).metrics["dxy"]
    assert metric.available is False
    assert metric.unknown_reason == "current_partial_session"


def test_continuous_247_utc_day_boundary_uses_exact_lag():
    cfg = _verified_config()
    start = datetime(2026, 7, 1, tzinfo=UTC)
    feed = _feed("btc", [str(100 + i * i) for i in range(22)], unit="price", start=start)
    boundary = start + timedelta(days=22, minutes=5)  # 2026-07-23T00:05Z
    feed["evidence_cutoff_at"] = _ts(boundary - timedelta(seconds=1))
    metric = build_market_snapshot(feed, cfg).metrics["btc"]
    assert metric.available is False
    assert metric.unknown_reason == "current_partial_session"
    feed["evidence_cutoff_at"] = _ts(boundary)
    assert build_market_snapshot(feed, cfg).metrics["btc"].available is True


def test_insufficient_history_is_explicit_without_compression():
    cfg = _verified_config()
    start = datetime(2026, 7, 1, tzinfo=UTC)
    fifteen = _feed("btc", [str(100 + i * i) for i in range(15)], unit="price", start=start)
    metric = build_market_snapshot(fifteen, cfg).metrics["btc"]
    assert metric.available is False
    assert metric.unknown_reason == "insufficient_history"
    twenty_one = _feed("btc", [str(100 + i * i) for i in range(21)], unit="price", start=start)
    metric = build_market_snapshot(twenty_one, cfg).metrics["btc"]
    assert metric.available is False
    assert metric.unknown_reason == "missing_expected_session"
    twenty = _feed("btc", [str(100 + i * i) for i in range(20)], unit="price", start=start)
    metric = build_market_snapshot(twenty, cfg).metrics["btc"]
    assert metric.available is False
    assert metric.unknown_reason == "missing_expected_session"


@pytest.mark.parametrize(
    "role_id",
    ["hsi", "vix", "us2y", "us10y", "cn10y", "dxy", "usdcnh", "copper", "wti", "gold", "btc"],
)
def test_unverified_mapping_fails_closed_even_with_complete_observations(role_id):
    cfg = load_config(
        DEFAULT_CONFIG,
        DEFAULT_PROVIDERS,
        manifest_root=DEFAULT_MANIFEST_ROOT,
    )
    role = cfg.role(role_id)
    feed = _feed(
        role_id,
        [str(4 + i / 100) for i in range(22)],
        unit=role.unit,
        start=datetime(2026, 7, 1, tzinfo=UTC),
    )
    metric = build_market_snapshot(feed, cfg).metrics[role_id]
    assert metric.available is False
    assert metric.unknown_reason == "unverified_mapping"


def test_unverified_mapping_guard_wins_over_matching_canonical_feed_item():
    cfg = load_config(
        DEFAULT_CONFIG,
        DEFAULT_PROVIDERS,
        manifest_root=DEFAULT_MANIFEST_ROOT,
    )
    role = cfg.role("csi300")
    feed = _feed(
        "csi300",
        [str(300 + i / 100) for i in range(22)],
        unit=role.unit,
        start=datetime(2026, 7, 1, tzinfo=UTC),
    )

    metric = build_market_snapshot(feed, cfg).metrics["csi300"]

    assert metric.available is False
    assert metric.unknown_reason == "unverified_mapping"


def test_dashboard_projection_keeps_all_roles_in_configured_order_and_typed_units():
    cfg = _verified_config()
    start = datetime(2026, 7, 1, tzinfo=UTC)
    feed = _feed("btc", [str(100 + i * i) for i in range(22)], unit="price", start=start)
    dashboard = build_market_snapshot(feed, cfg).dashboard
    assert [row["role_id"] for row in dashboard] == list(cfg.role_ids)
    btc = dashboard[-1]
    assert btc["return_pct"] is not None
    assert "yield_change_bps" not in btc
    us10y = dashboard[4]
    assert us10y["available"] is False
    assert us10y["yield_change_bps"] is None
    assert "return_pct" not in us10y
    assert "raw" not in str(us10y).lower()


def test_long_bounded_history_uses_only_the_last_22_expected_sessions():
    cfg = _verified_config()
    start = datetime(2025, 11, 1, tzinfo=UTC)
    values = [str(100 + i * i) for i in range(260)]
    snapshot = build_market_snapshot(_feed("btc", values, unit="price", start=start), cfg)
    metric = snapshot.metrics["btc"]
    assert metric.available is True
    assert len(metric.changes) == 21


def test_latest_cutoff_eligible_macro_surprise_is_inverted_and_tie_broken_by_evidence_id():
    cfg = _verified_config()
    cutoff = "2026-08-11T00:20:00.000Z"
    feed = {
        "evidence_cutoff_at": cutoff,
        "items": [
            {
                "id": "z-release",
                "source": {"knowledge_available_at": "2026-08-10T00:00:00.000Z"},
                "payload": {
                    "type": "macro_release",
                    "series_id": "us_cpi_all_items_sa_mom",
                    "released_at": "2026-08-09T00:00:00.000Z",
                    "actual": {"value": "0.1", "unit": "percent"},
                    "consensus": {"value": "0.0", "unit": "percent"},
                    "observation_period": None,
                    "raw_metadata": {},
                },
            },
            {
                "id": "a-release",
                "source": {"knowledge_available_at": "2026-08-10T00:00:00.000Z"},
                "payload": {
                    "type": "macro_release",
                    "series_id": "us_cpi_all_items_sa_mom",
                    "released_at": "2026-08-09T00:00:00.000Z",
                    "actual": {"value": "0.2", "unit": "percent"},
                    "consensus": {"value": "0.0", "unit": "percent"},
                    "observation_period": None,
                    "raw_metadata": {},
                },
            },
        ],
    }
    snapshot = build_market_snapshot(feed, cfg)
    assert snapshot.surprise_vote_by_series["us_cpi_all_items_sa_mom"] == -1
    assert snapshot.evidence_ids[-1] == "z-release"


def test_incompatible_or_unavailable_surprises_contribute_no_vote():
    cfg = _verified_config()
    cutoff = "2026-08-11T00:20:00.000Z"

    def release(item_id: str, payload: dict, knowledge: str) -> dict:
        return {
            "id": item_id,
            "source": {"knowledge_available_at": knowledge},
            "payload": {"type": "macro_release", "series_id": "us_cpi_all_items_sa_mom", **payload},
        }

    feed = {
        "evidence_cutoff_at": cutoff,
        "items": [
            release(
                "unit-mismatch",
                {
                    "actual": {"value": "0.1", "unit": "percent"},
                    "consensus": {"value": "0.0", "unit": "index"},
                },
                "2026-08-10T00:00:00.000Z",
            ),
            release(
                "missing-consensus",
                {
                    "actual": {"value": "0.1", "unit": "percent"},
                    "consensus": {"value": None, "unit": "percent"},
                },
                "2026-08-10T00:00:00.000Z",
            ),
            release(
                "post-cutoff",
                {
                    "actual": {"value": "0.1", "unit": "percent"},
                    "consensus": {"value": "0.0", "unit": "percent"},
                },
                "2026-08-11T00:20:01.000Z",
            ),
            release(
                "non-v1-series",
                {
                    "actual": {"value": "0.1", "unit": "percent"},
                    "consensus": {"value": "0.0", "unit": "percent"},
                },
                "2026-08-10T00:00:00.000Z",
            ),
        ],
    }
    feed["items"][3]["payload"]["series_id"] = "us_other_series_mom"
    snapshot = build_market_snapshot(feed, cfg)
    assert snapshot.surprise_votes == ()
    assert snapshot.surprise_vote_by_series == {}
    assert snapshot.evidence_ids == ()


def test_equity_breadth_is_unknown_when_no_member_is_observable():
    cfg = _verified_config()
    start = datetime(2026, 7, 1, tzinfo=UTC)
    feed = _feed("btc", [str(100 + i * i) for i in range(22)], unit="price", start=start)
    snapshot = build_market_snapshot(feed, cfg)
    assert snapshot.equity_breadth is None


def test_surprise_vote_boundaries_are_inclusive_at_exact_half():
    cfg = _verified_config()
    cutoff = "2026-08-11T00:20:00.000Z"

    def feed_for(actual: str) -> dict:
        return {
            "evidence_cutoff_at": cutoff,
            "items": [
                {
                    "id": "release",
                    "source": {"knowledge_available_at": "2026-08-10T00:00:00.000Z"},
                    "payload": {
                        "type": "macro_release",
                        "series_id": "us_cpi_all_items_sa_mom",
                        "actual": {"value": actual, "unit": "percent"},
                        "consensus": {"value": "0.0", "unit": "percent"},
                    },
                }
            ],
        }

    # scale 0.1: normalized +0.5 votes adverse (inverted -1), -0.5 votes
    # supportive (inverted +1), inside the band votes 0.
    assert build_market_snapshot(feed_for("0.05"), cfg).surprise_votes == (-1,)
    assert build_market_snapshot(feed_for("-0.05"), cfg).surprise_votes == (1,)
    assert build_market_snapshot(feed_for("0.049"), cfg).surprise_votes == (0,)


def test_contributor_evidence_order_is_roles_then_macro_series():
    cfg = _verified_config()
    cutoff = datetime(2026, 8, 11, 0, 20, tzinfo=UTC)
    feed = _feed(
        "btc",
        [str(100 + i * i) for i in range(22)],
        unit="price",
        start=datetime(2026, 7, 1, tzinfo=UTC),
    )
    feed["evidence_cutoff_at"] = _ts(cutoff)
    feed["items"].append(
        {
            "id": "z-release",
            "source": {"knowledge_available_at": _ts(cutoff - timedelta(minutes=1))},
            "payload": {
                "type": "macro_release",
                "series_id": "us_cpi_all_items_sa_mom",
                "actual": {"value": "0.15", "unit": "percent"},
                "consensus": {"value": "0.10", "unit": "percent"},
            },
        }
    )
    snapshot = build_market_snapshot(feed, cfg)
    assert snapshot.evidence_ids[-2:] == ("ev-btc", "z-release")


def test_equity_breadth_uses_observable_subset_and_counts_zero_returns():
    cfg = _verified_config()
    calendars = {
        role: xcals.get_calendar(calendar)
        for role, calendar in {
            "sp500": "XNYS",
            "csi300": "XSHG",
        }.items()
    }
    sessions = {
        role: calendar.sessions_in_range("2026-06-01", "2026-08-01")[-22:]
        for role, calendar in calendars.items()
    }
    cutoff = max(
        calendar.schedule.loc[labels[-1], "close"].to_pydatetime()
        for calendar, labels in ((calendars[r], sessions[r]) for r in sessions)
    ) + timedelta(hours=1)
    items = []
    values_by_role = {
        "sp500": [str(100 + i) for i in range(22)],
        "csi300": ["200"] * 22,
    }
    units = {"sp500": "index", "csi300": "index", "hsi": "index"}
    for role_id, labels in sessions.items():
        calendar = calendars[role_id]
        observations = []
        for value, label in zip(values_by_role[role_id], labels):
            close = calendar.schedule.loc[label, "close"].to_pydatetime()
            observations.append(
                {
                    "as_of": _ts(close),
                    "available_at": _ts(close + timedelta(minutes=5)),
                    "value": value,
                    "unit": units[role_id],
                }
            )
        items.append(
            {
                "id": f"ev-{role_id}",
                "source": {"knowledge_available_at": _ts(cutoff)},
                "payload": {
                    "type": "market_data",
                    "instrument_id": role_id,
                    "unit": units[role_id],
                    "observations": observations,
                    "raw_metadata": {},
                },
            }
        )
    snapshot = build_market_snapshot({"evidence_cutoff_at": _ts(cutoff), "items": items}, cfg)
    assert snapshot.equity_breadth == Decimal("0.5")
