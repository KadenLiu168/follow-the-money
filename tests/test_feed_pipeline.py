"""Feed window and five-domain Provider coverage regressions."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from follow_the_money.config import load_config
from follow_the_money.feed.checkpoint import PreviousSuccess
from follow_the_money.feed.plan import FeedPlanError, ProviderOutcome, assess_pipeline, plan_window

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "config" / "config.yaml"
DEFAULT_PROVIDERS = REPO_ROOT / "config" / "providers.yaml"
DEFAULT_MANIFEST_ROOT = REPO_ROOT / "providers"
CUTOFF = datetime(2026, 8, 11, 0, 20, tzinfo=UTC)
PROVIDERS = (
    "bls",
    "cftc",
    "federal_reserve",
    "nbs",
    "pboc",
    "sec_edgar",
    "sse",
    "szse",
)


def _cfg():
    return load_config(
        DEFAULT_CONFIG,
        DEFAULT_PROVIDERS,
        manifest_root=DEFAULT_MANIFEST_ROOT,
        require_verified_enabled=True,
    )


def _previous_success(cutoff: datetime) -> PreviousSuccess:
    text = cutoff.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    return PreviousSuccess(text, f"{text}::{'a' * 32}")


def _outcomes(state: str = "healthy") -> dict[str, ProviderOutcome]:
    return {provider_id: ProviderOutcome(provider_id, state=state) for provider_id in PROVIDERS}


def test_first_run_uses_bounded_bootstrap_window():
    plan = plan_window(cutoff=CUTOFF, previous_success=None)
    assert plan.bootstrap
    assert datetime.fromisoformat(plan.window_start) == CUTOFF - timedelta(hours=72)
    assert plan.evidence_cutoff_at == "2026-08-11T00:20:00.000Z"


def test_later_window_advances_from_checkpoint():
    previous = _previous_success(CUTOFF)
    plan = plan_window(cutoff=CUTOFF + timedelta(hours=24), previous_success=previous)
    assert not plan.bootstrap
    assert plan.window_start == previous.evidence_cutoff_at


def test_non_advancing_cutoff_fails_closed():
    with pytest.raises(FeedPlanError, match="non_advancing_cutoff"):
        plan_window(cutoff=CUTOFF, previous_success=_previous_success(CUTOFF))


def test_gap_beyond_limit_is_bounded_and_reported():
    previous = _previous_success(CUTOFF)
    plan = plan_window(cutoff=CUTOFF + timedelta(hours=73), previous_success=previous)
    assert plan.bootstrap
    assert plan.gap_warning == (
        previous.evidence_cutoff_at,
        "2026-08-11T01:20:00.000Z",
    )


def test_all_eight_required_providers_can_satisfy_feed_coverage():
    cfg = _cfg()
    status, warnings = assess_pipeline(
        config=cfg,
        planned_provider_ids=PROVIDERS,
        outcomes=_outcomes(),
    )
    assert status == "healthy"
    assert warnings == []


def test_permitted_empty_still_satisfies_required_coverage():
    cfg = _cfg()
    outcomes = _outcomes("empty")
    status, warnings = assess_pipeline(
        config=cfg,
        planned_provider_ids=PROVIDERS,
        outcomes=outcomes,
    )
    assert status == "healthy"
    assert warnings == []


def test_cftc_is_required_and_blocked_exemption_is_degraded():
    cfg = _cfg()
    outcomes = _outcomes("empty")
    outcomes["cftc"] = ProviderOutcome(
        "cftc",
        state="failed",
        availability="blocked",
        availability_reason="HTTP 403",
        upstream_http_status=403,
    )
    status, warnings = assess_pipeline(
        config=cfg,
        planned_provider_ids=PROVIDERS,
        outcomes=outcomes,
    )
    assert status == "degraded"
    assert any("cftc" in warning and "blocked" in warning for warning in warnings)


def test_unconfirmed_provider_failure_is_not_degraded():
    cfg = _cfg()
    outcomes = _outcomes("empty")
    outcomes["cftc"] = ProviderOutcome("cftc", state="failed", error="timeout")
    status, warnings = assess_pipeline(
        config=cfg,
        planned_provider_ids=PROVIDERS,
        outcomes=outcomes,
    )
    assert status == "failure"
    assert any("cftc" in warning for warning in warnings)


def test_missing_or_duplicate_planned_provider_fails_closed():
    cfg = _cfg()
    outcomes = _outcomes()
    missing = list(PROVIDERS)
    missing.remove("cftc")
    status, warnings = assess_pipeline(
        config=cfg,
        planned_provider_ids=missing,
        outcomes=outcomes,
    )
    assert status == "failure"
    assert any("deficient coverage" in warning for warning in warnings)

    status, warnings = assess_pipeline(
        config=cfg,
        planned_provider_ids=[*PROVIDERS, "cftc"],
        outcomes=outcomes,
    )
    assert status == "failure"
    assert any("duplicate" in warning for warning in warnings)
