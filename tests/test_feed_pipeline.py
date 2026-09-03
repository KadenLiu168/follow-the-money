"""Task 4.3/4.4/4.5/4.6 — pipeline and publication fixtures."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from follow_the_money.config import load_config
from follow_the_money.feed.checkpoint import PreviousSuccess
from follow_the_money.feed.cli import run_feed as _run_feed
from follow_the_money.feed.plan import (
    FeedPlanError,
    ProviderOutcome,
    assess_pipeline,
    plan_window,
)
from follow_the_money.feed.publish import PublishError, publish_feed

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "config" / "config.yaml"
DEFAULT_PROVIDERS = REPO_ROOT / "config" / "providers.yaml"
DEFAULT_MANIFEST_ROOT = REPO_ROOT / "providers"


def run_feed(**kwargs):
    if "runtime_state_root" not in kwargs and kwargs.get("output_root") is not None:
        output = Path(kwargs["output_root"])
        kwargs["runtime_state_root"] = str(output.parent / f".{output.name}-state")
    return _run_feed(**kwargs)


def _cfg():
    return load_config(
        DEFAULT_CONFIG,
        DEFAULT_PROVIDERS,
        manifest_root=DEFAULT_MANIFEST_ROOT,
        require_verified_enabled=False,
    )


def _previous_success(cutoff: datetime) -> PreviousSuccess:
    cutoff_text = cutoff.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    return PreviousSuccess(cutoff_text, f"{cutoff_text}::" + "a" * 32)


def _publication_bytes(cutoff: datetime, digest: str = "a" * 64) -> bytes:
    return json.dumps(
        {"content_digest": digest, "evidence_cutoff_at": cutoff.isoformat().replace("+00:00", "Z")},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


# ---------------------------------------------------------------------------
# Window planning
# ---------------------------------------------------------------------------


def test_first_run_bootstrap():
    cutoff = datetime(2026, 8, 11, 0, 20, 0, tzinfo=UTC)
    plan = plan_window(cutoff=cutoff, previous_success=None)
    assert plan.bootstrap is True
    start = datetime.fromisoformat(plan.window_start)
    assert (cutoff - start).total_seconds() == 72 * 3600


def test_invalid_checkpoint_integrity():
    cutoff = datetime(2026, 8, 11, 0, 20, 0, tzinfo=UTC)
    previous = PreviousSuccess("not-a-timestamp", "not-a-run-id")
    with pytest.raises(FeedPlanError, match="invalid checkpoint cutoff"):
        plan_window(cutoff=cutoff, previous_success=previous)


def test_non_advancing_cutoff():
    latest_cutoff = datetime(2026, 8, 11, 0, 20, 0, tzinfo=UTC)
    with pytest.raises(FeedPlanError, match="non_advancing_cutoff"):
        plan_window(
            cutoff=latest_cutoff,
            previous_success=_previous_success(latest_cutoff),
        )
    # equal cutoff also fails
    with pytest.raises(FeedPlanError, match="non_advancing_cutoff"):
        plan_window(
            cutoff=latest_cutoff + timedelta(seconds=0),
            previous_success=_previous_success(latest_cutoff),
        )


def test_advancing_cutoff_starts_at_previous():
    latest_cutoff = datetime(2026, 8, 11, 0, 20, 0, tzinfo=UTC)
    new_cutoff = latest_cutoff + timedelta(hours=24)
    plan = plan_window(
        cutoff=new_cutoff,
        previous_success=_previous_success(latest_cutoff),
    )
    assert plan.window_start == latest_cutoff.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    assert plan.bootstrap is False
    assert plan.gap_warning is None


def test_gap_exactly_72h_no_warning():
    latest_cutoff = datetime(2026, 8, 11, 0, 20, 0, tzinfo=UTC)
    new_cutoff = latest_cutoff + timedelta(hours=72)
    plan = plan_window(
        cutoff=new_cutoff,
        previous_success=_previous_success(latest_cutoff),
    )
    assert plan.window_start == latest_cutoff.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    assert plan.gap_warning is None


def test_gap_over_72h_records_warning():
    latest_cutoff = datetime(2026, 8, 11, 0, 20, 0, tzinfo=UTC)
    new_cutoff = latest_cutoff + timedelta(hours=73)
    plan = plan_window(
        cutoff=new_cutoff,
        previous_success=_previous_success(latest_cutoff),
    )
    assert plan.gap_warning is not None
    uncovered_start, uncovered_end = plan.gap_warning
    assert uncovered_start < uncovered_end
    # bounded start = cutoff - 72h
    expected_start = new_cutoff - timedelta(hours=72)
    assert plan.window_start == expected_start.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


# ---------------------------------------------------------------------------
# Pipeline health accounting
# ---------------------------------------------------------------------------


def _planned_ids(outcomes: dict[str, ProviderOutcome]) -> tuple[str, ...]:
    return tuple(sorted(outcomes))


def _all_empty_cfg(cfg):
    return replace(
        cfg,
        providers=tuple(
            replace(provider, empty_valid_for_window=True) for provider in cfg.providers
        ),
    )


def test_healthy_six_row_coverage():
    cfg = _cfg()
    # Only a subset of the shipped (unverified) providers exist; simulate a
    # fully healthy matrix via synthetic providers matching row members.
    outcomes = {}
    for row in cfg.coverage.rows:
        for member in row.members:
            outcomes[member] = ProviderOutcome(member, state="healthy")
    status, warnings = assess_pipeline(
        config=cfg, planned_provider_ids=_planned_ids(outcomes), outcomes=outcomes
    )
    assert status == "healthy"
    assert warnings == []


def test_incomplete_provider_and_coverage_fail_with_accepted_evidence():
    cfg = _cfg()
    outcomes = {}
    for row in cfg.coverage.rows:
        for member in row.members:
            # First member of every row fails => below minimum everywhere.
            outcomes[member] = ProviderOutcome(member, state="failed")
    outcomes["federal_reserve"] = ProviderOutcome("federal_reserve", state="healthy", accepted=1)
    status, warnings = assess_pipeline(
        config=cfg, planned_provider_ids=_planned_ids(outcomes), outcomes=outcomes
    )
    assert status == "failure"
    assert any("incomplete" in w for w in warnings)
    assert any("deficient" in w for w in warnings)


def test_permitted_empty_counts_healthy_without_accepted_item():
    cfg = _all_empty_cfg(_cfg())
    outcomes = {}
    for row in cfg.coverage.rows:
        for member in row.members:
            outcomes[member] = ProviderOutcome(member, state="empty", accepted=0)
    status, warnings = assess_pipeline(
        config=cfg, planned_provider_ids=_planned_ids(outcomes), outcomes=outcomes
    )
    assert status == "healthy"
    assert warnings == []


def test_mixed_validity_with_accepted_item():
    cfg = _cfg()
    outcomes = {}
    for row in cfg.coverage.rows:
        for member in row.members:
            outcomes[member] = ProviderOutcome(member, state="healthy", accepted=1)
    outcomes["sec_edgar"] = ProviderOutcome("sec_edgar", state="failed")
    status, warnings = assess_pipeline(
        config=cfg, planned_provider_ids=_planned_ids(outcomes), outcomes=outcomes
    )
    assert status == "failure"
    # The failed member makes us_company_filings deficient (1/1 minimum).
    assert any("deficient" in w for w in warnings)


def test_source_complete_empty_is_healthy():
    cfg = _all_empty_cfg(_cfg())
    outcomes = {
        member: ProviderOutcome(member, state="empty")
        for row in cfg.coverage.rows
        for member in row.members
    }
    status, warnings = assess_pipeline(
        config=cfg, planned_provider_ids=_planned_ids(outcomes), outcomes=outcomes
    )
    assert status == "healthy"
    assert warnings == []


@pytest.mark.parametrize("http_status", [401, 403])
def test_wholly_blocked_provider_is_degraded_and_exempt(http_status):
    cfg = _all_empty_cfg(_cfg())
    outcomes = {
        member: ProviderOutcome(member, state="empty")
        for row in cfg.coverage.rows
        for member in row.members
    }
    blocked = ProviderOutcome(
        "bls",
        state="failed",
        availability="blocked",
        availability_reason=f"HTTP {http_status}",
        upstream_http_status=http_status,
    )
    outcomes["bls"] = blocked

    status, warnings = assess_pipeline(
        config=cfg, planned_provider_ids=_planned_ids(outcomes), outcomes=outcomes
    )

    assert status == "degraded"
    assert any("bls" in warning and "affected_coverage_groups" in warning for warning in warnings)
    assert blocked.to_dict()["affected_coverage_groups"] == []


def test_all_planned_providers_blocked_reduces_mandatory_minimums_to_zero():
    cfg = _all_empty_cfg(_cfg())
    outcomes = {
        provider.id: ProviderOutcome(
            provider.id,
            state="failed",
            availability="blocked",
            availability_reason="HTTP 403",
            upstream_http_status=403,
        )
        for provider in cfg.providers
        if provider.enabled
    }

    status, _warnings = assess_pipeline(
        config=cfg, planned_provider_ids=_planned_ids(outcomes), outcomes=outcomes
    )

    assert status == "degraded"


def test_optional_provider_blocking_degrades_without_changing_coverage():
    cfg = _all_empty_cfg(_cfg())
    outcomes = {
        provider.id: ProviderOutcome(provider.id, state="empty")
        for provider in cfg.providers
        if provider.enabled
    }
    outcomes["cftc"] = ProviderOutcome(
        "cftc",
        state="failed",
        availability="blocked",
        availability_reason="HTTP 403",
        upstream_http_status=403,
    )

    status, warnings = assess_pipeline(
        config=cfg, planned_provider_ids=_planned_ids(outcomes), outcomes=outcomes
    )

    assert status == "degraded"
    assert not any("deficient coverage" in warning for warning in warnings)


def test_mixed_blocked_and_unconfirmed_failure_remains_failure():
    cfg = _all_empty_cfg(_cfg())
    outcomes = {
        provider.id: ProviderOutcome(provider.id, state="empty")
        for provider in cfg.providers
        if provider.enabled
    }
    outcomes["bls"] = ProviderOutcome(
        "bls",
        state="failed",
        availability="blocked",
        availability_reason="HTTP 403",
        upstream_http_status=403,
    )
    outcomes["sse"] = ProviderOutcome("sse", state="failed", availability="failed")

    status, _warnings = assess_pipeline(
        config=cfg, planned_provider_ids=_planned_ids(outcomes), outcomes=outcomes
    )

    assert status == "failure"


def test_blocked_provider_with_partial_data_remains_failure():
    cfg = _all_empty_cfg(_cfg())
    outcomes = {
        member: ProviderOutcome(member, state="empty")
        for row in cfg.coverage.rows
        for member in row.members
    }
    outcomes["bls"] = ProviderOutcome(
        "bls",
        state="partial",
        accepted=1,
        availability="blocked",
        availability_reason="HTTP 403",
        upstream_http_status=403,
    )

    status, _warnings = assess_pipeline(
        config=cfg, planned_provider_ids=_planned_ids(outcomes), outcomes=outcomes
    )

    assert status == "failure"


def _all_healthy_outcomes(cfg) -> dict[str, ProviderOutcome]:
    return {
        member: ProviderOutcome(member, state="healthy", accepted=1)
        for row in cfg.coverage.rows
        for member in row.members
    }


def test_permitted_empty_contributes_to_coverage():
    cfg = _cfg()
    outcomes = _all_healthy_outcomes(cfg)
    outcomes["federal_reserve"] = ProviderOutcome("federal_reserve", state="empty")
    status, warnings = assess_pipeline(
        config=cfg, planned_provider_ids=_planned_ids(outcomes), outcomes=outcomes
    )

    assert status == "healthy"
    assert warnings == []


def test_non_permitted_empty_does_not_contribute_and_names_provider():
    cfg = _cfg()
    outcomes = _all_healthy_outcomes(cfg)
    outcomes["yahoo_market"] = ProviderOutcome("yahoo_market", state="empty")

    status, warnings = assess_pipeline(
        config=cfg, planned_provider_ids=_planned_ids(outcomes), outcomes=outcomes
    )

    assert status == "failure"
    assert any("yahoo_market" in warning for warning in warnings)
    assert any("verified_market_data" in warning for warning in warnings)


@pytest.mark.parametrize("state", ["partial", "failed", "skipped"])
def test_incomplete_provider_states_do_not_contribute_and_name_provider(state):
    cfg = _cfg()
    outcomes = _all_healthy_outcomes(cfg)
    outcomes["sec_edgar"] = ProviderOutcome("sec_edgar", state=state, accepted=1)

    status, warnings = assess_pipeline(
        config=cfg, planned_provider_ids=_planned_ids(outcomes), outcomes=outcomes
    )

    assert status == "failure"
    assert any("sec_edgar" in warning for warning in warnings)
    assert any("us_company_filings" in warning for warning in warnings)


def test_source_failure_retains_provider_and_group_warnings_without_zero_count_cause():
    cfg = _cfg()
    outcomes = {
        member: ProviderOutcome(member, state="empty")
        for row in cfg.coverage.rows
        for member in row.members
    }
    outcomes["sec_edgar"] = ProviderOutcome("sec_edgar", state="failed")
    outcomes["yahoo_market"] = ProviderOutcome("yahoo_market", state="empty")

    status, warnings = assess_pipeline(
        config=cfg, planned_provider_ids=_planned_ids(outcomes), outcomes=outcomes
    )

    assert status == "failure"
    assert not any("no accepted" in warning for warning in warnings)
    assert any("sec_edgar" in warning for warning in warnings)
    assert any("us_company_filings" in warning for warning in warnings)


def test_missing_terminal_outcome_fails_closed():
    cfg = _cfg()
    outcomes = _all_healthy_outcomes(cfg)
    planned = _planned_ids(outcomes)
    del outcomes["sec_edgar"]

    status, warnings = assess_pipeline(config=cfg, planned_provider_ids=planned, outcomes=outcomes)

    assert status == "failure"
    assert any("sec_edgar" in warning and "missing" in warning for warning in warnings)


def test_duplicate_planned_provider_fails_closed():
    cfg = _cfg()
    outcomes = _all_healthy_outcomes(cfg)
    planned = (*_planned_ids(outcomes), "sec_edgar")

    status, warnings = assess_pipeline(config=cfg, planned_provider_ids=planned, outcomes=outcomes)

    assert status == "failure"
    assert any("duplicate" in warning and "sec_edgar" in warning for warning in warnings)


def test_ambiguous_terminal_outcomes_fail_closed():
    cfg = _cfg()
    outcomes = _all_healthy_outcomes(cfg)
    outcomes["sec_edgar_alias"] = ProviderOutcome("sec_edgar", state="healthy")

    status, warnings = assess_pipeline(
        config=cfg, planned_provider_ids=_planned_ids(_all_healthy_outcomes(cfg)), outcomes=outcomes
    )

    assert status == "failure"
    assert any("ambiguous" in warning and "sec_edgar" in warning for warning in warnings)


def test_ambiguous_terminal_outcome_diagnostics_ignore_mapping_order():
    cfg = _cfg()
    canonical = ProviderOutcome("sec_edgar", state="failed", error="canonical failure")
    alias = ProviderOutcome("sec_edgar", state="healthy")
    base = _all_healthy_outcomes(cfg)
    base.pop("sec_edgar")

    first_status, first_warnings = assess_pipeline(
        config=cfg,
        planned_provider_ids=(*_planned_ids(base), "sec_edgar"),
        outcomes={**base, "sec_edgar": canonical, "sec_edgar_alias": alias},
    )
    second_status, second_warnings = assess_pipeline(
        config=cfg,
        planned_provider_ids=(*_planned_ids(base), "sec_edgar"),
        outcomes={**base, "sec_edgar_alias": alias, "sec_edgar": canonical},
    )

    assert first_status == second_status == "failure"
    assert first_warnings == second_warnings


@pytest.mark.parametrize(
    ("outcome", "expected_warning"),
    [
        (ProviderOutcome("sec_edgar", state="unknown"), "unknown state"),
        (ProviderOutcome("other", state="healthy"), "identity"),
    ],
)
def test_invalid_terminal_outcomes_fail_closed(outcome, expected_warning):
    cfg = _cfg()
    outcomes = _all_healthy_outcomes(cfg)
    outcomes["sec_edgar"] = outcome

    status, warnings = assess_pipeline(
        config=cfg, planned_provider_ids=_planned_ids(outcomes), outcomes=outcomes
    )

    assert status == "failure"
    assert any("sec_edgar" in warning and expected_warning in warning for warning in warnings)


def test_assessment_uses_only_planned_providers_and_future_plan_members():
    cfg = SimpleNamespace(
        providers=(
            SimpleNamespace(id="cftc", enabled=False, empty_valid_for_window=True),
            SimpleNamespace(id="yahoo_market", enabled=True, empty_valid_for_window=False),
        ),
        coverage=SimpleNamespace(rows=()),
    )
    unplanned = {
        "cftc": ProviderOutcome("cftc", state="failed"),
        "yahoo_market": ProviderOutcome("yahoo_market", state="failed"),
    }

    status, warnings = assess_pipeline(config=cfg, planned_provider_ids=(), outcomes=unplanned)

    assert status == "healthy"
    assert warnings == []

    future_cfg = SimpleNamespace(
        providers=(
            SimpleNamespace(id="future_provider", enabled=True, empty_valid_for_window=True),
        ),
        coverage=SimpleNamespace(
            rows=(
                SimpleNamespace(
                    group="future_group",
                    members=("future_provider",),
                    minimum=1,
                    optional=False,
                ),
            ),
        ),
    )
    status, warnings = assess_pipeline(
        config=future_cfg,
        planned_provider_ids=("future_provider",),
        outcomes={"future_provider": ProviderOutcome("future_provider", state="empty")},
    )

    assert status == "healthy"
    assert warnings == []


def _feed_item(provider_id: str, item_id: str) -> dict:
    return {
        "id": item_id,
        "provider_id": provider_id,
        "source": {
            "id": f"{item_id}-source",
            "name": "Fixture source",
            "tier": "Tier 1",
            "kind": "news",
            "url": f"https://example.com/{item_id}",
            "published_at": "2026-08-11T00:10:00Z",
            "knowledge_available_at": "2026-08-11T00:10:00Z",
        },
        "payload": {
            "type": "policy",
            "title": item_id,
            "announced_at": "2026-08-11T00:10:00Z",
            "raw_metadata": {},
        },
    }


class _FixtureAdapter:
    provider_id = "yahoo_market"

    def __init__(self, *, items=None, error: Exception | None = None):
        self.items = items or []
        self.error = error

    def fetch(self, window, client=None):
        if self.error is not None:
            raise self.error
        return SimpleNamespace(body_bytes=b"fixture")

    def normalize(self, raw, window):
        return self.items


def test_accepted_and_rejected_items_make_provider_partial(tmp_path):
    adapter = _FixtureAdapter(items=[_feed_item("yahoo_market", "accepted"), {"source": {}}])

    result = run_feed(
        output_root=str(tmp_path / "out"),
        cutoff=datetime(2026, 8, 11, 0, 20, tzinfo=UTC),
        dry_run=True,
        providers_fn=lambda: {"yahoo_market": adapter},
        enabled_provider_ids=["yahoo_market"],
    )

    assert result.status == "failure"
    assert result.feed is not None
    outcome = result.feed["provider_outcomes"][0]
    assert outcome["state"] == "partial"
    assert outcome["accepted"] == 1
    assert outcome["rejected"] == 1


def test_accepted_evidence_survives_later_failed_role_as_partial(tmp_path):
    adapters = [
        _FixtureAdapter(items=[_feed_item("yahoo_market", "accepted")]),
        _FixtureAdapter(error=RuntimeError("later role failed")),
    ]

    result = run_feed(
        output_root=str(tmp_path / "out"),
        cutoff=datetime(2026, 8, 11, 0, 20, tzinfo=UTC),
        dry_run=True,
        providers_fn=lambda: {"yahoo_market": adapters},
        enabled_provider_ids=["yahoo_market"],
    )

    assert result.status == "failure"
    assert result.feed is not None
    outcome = result.feed["provider_outcomes"][0]
    assert outcome["state"] == "partial"
    assert outcome["accepted"] == 1
    assert len(result.feed["items"]) == 1


@pytest.mark.parametrize("empty_first", [True, False])
def test_non_permitted_empty_and_accepted_roles_are_partial_in_any_order(tmp_path, empty_first):
    empty = _FixtureAdapter()
    accepted = _FixtureAdapter(items=[_feed_item("yahoo_market", "accepted")])
    adapters = [empty, accepted] if empty_first else [accepted, empty]

    result = run_feed(
        output_root=str(tmp_path / "out"),
        cutoff=datetime(2026, 8, 11, 0, 20, tzinfo=UTC),
        dry_run=True,
        providers_fn=lambda: {"yahoo_market": adapters},
        enabled_provider_ids=["yahoo_market"],
    )

    assert result.status == "failure"
    assert result.feed is not None
    outcome = result.feed["provider_outcomes"][0]
    assert outcome["state"] == "partial"
    assert outcome["accepted"] == 1
    assert len(result.feed["items"]) == 1


def test_all_rejected_provider_is_failed_not_empty(tmp_path):
    adapter = _FixtureAdapter(items=[{"source": {}}])

    result = run_feed(
        output_root=str(tmp_path / "out"),
        cutoff=datetime(2026, 8, 11, 0, 20, tzinfo=UTC),
        dry_run=True,
        providers_fn=lambda: {"yahoo_market": adapter},
        enabled_provider_ids=["yahoo_market"],
    )

    assert result.status == "failure"
    assert result.exit_code == 1
    assert result.feed is not None
    assert result.feed["provider_outcomes"][0]["state"] == "failed"


# ---------------------------------------------------------------------------
# Publication
# ---------------------------------------------------------------------------


def test_publish_latest_only(tmp_path):
    root = tmp_path / "out"
    root.mkdir()
    cutoff = datetime(2026, 8, 11, 0, 20, 0, tzinfo=UTC)
    feed = _publication_bytes(cutoff)
    result = publish_feed(
        output_root=root,
        cutoff=cutoff,
        run_id="run_1",
        feed_bytes=feed,
        latest_bytes=feed,
    )
    assert (root / "latest.json").read_bytes() == feed
    assert not (root / "daily").exists()
    assert result.latest_replaced


def test_publish_idempotent_same_run(tmp_path):
    root = tmp_path / "out"
    root.mkdir()
    cutoff = datetime(2026, 8, 11, 0, 20, 0, tzinfo=UTC)
    feed = _publication_bytes(cutoff)
    publish_feed(
        output_root=root, cutoff=cutoff, run_id="run_1", feed_bytes=feed, latest_bytes=feed
    )
    result = publish_feed(
        output_root=root, cutoff=cutoff, run_id="run_1", feed_bytes=feed, latest_bytes=feed
    )
    assert result.idempotent


def test_publish_equal_owner_incompatible_fails(tmp_path):
    root = tmp_path / "out"
    root.mkdir()
    cutoff = datetime(2026, 8, 11, 0, 20, 0, tzinfo=UTC)
    feed = _publication_bytes(cutoff)
    publish_feed(
        output_root=root, cutoff=cutoff, run_id="run_1", feed_bytes=feed, latest_bytes=feed
    )
    incompatible = json.dumps(
        {
            "content_digest": "a" * 64,
            "evidence_cutoff_at": cutoff.isoformat().replace("+00:00", "Z"),
            "marker": "different",
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    with pytest.raises(PublishError, match="equal ownership"):
        publish_feed(
            output_root=root,
            cutoff=cutoff,
            run_id="run_1",
            feed_bytes=incompatible,
            latest_bytes=incompatible,
        )


def test_publish_no_staging_leftovers(tmp_path):
    root = tmp_path / "out"
    root.mkdir()
    cutoff = datetime(2026, 8, 11, 0, 20, 0, tzinfo=UTC)
    feed = _publication_bytes(cutoff)
    publish_feed(
        output_root=root, cutoff=cutoff, run_id="run_1", feed_bytes=feed, latest_bytes=feed
    )
    leftovers = [p.name for p in root.rglob("*") if ".stage-" in p.name]
    assert leftovers == []


def test_publish_latest_ownership_mismatch_rejected(tmp_path):
    root = tmp_path / "out"
    root.mkdir()
    cutoff = datetime(2026, 8, 11, 0, 20, 0, tzinfo=UTC)
    feed = _publication_bytes(cutoff)
    # existing_latest_sha256 says the current latest has a different hash.
    with pytest.raises(PublishError, match="ownership mismatch"):
        publish_feed(
            output_root=root,
            cutoff=cutoff,
            run_id="run_1",
            feed_bytes=feed,
            latest_bytes=feed,
            existing_latest_sha256="0" * 64,
        )


def test_cutoff_timezone_does_not_create_dated_product(tmp_path):
    root = tmp_path / "out"
    root.mkdir()
    cutoff = datetime(2026, 8, 10, 20, 30, 0, tzinfo=UTC)
    feed = _publication_bytes(cutoff)

    result = publish_feed(
        output_root=root,
        cutoff=cutoff,
        run_id="run_1",
        feed_bytes=feed,
        latest_bytes=feed,
    )

    assert result.latest_replaced
    assert (root / "latest.json").read_bytes() == feed
    assert not (root / "daily").exists()
