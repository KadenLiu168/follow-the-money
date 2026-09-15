"""SEC v2 complete-slice and watched-CIK completeness regressions."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from follow_the_money.config.model import FreshnessContract, WatchCompany
from follow_the_money.feed import cli as feed_cli
from follow_the_money.feed.plan import ProviderOutcome
from follow_the_money.feed.snapshot import select_provider_slices
from tests.test_feed_cli import (
    _cutoff,
    _OutcomeAdapter,
    _planned_provider_ids,
    _source_complete_cfg,
    run_feed,
)

T0 = datetime(2026, 8, 11, 0, 20, tzinfo=UTC)


def _sec_slice_item(letter: str, *, revision: str) -> dict:
    cik = f"000000000{ord(letter) - ord('A') + 1}"
    accession = f"{cik}-26-{revision}-{letter}"
    return {
        "id": f"sec-edgar-{cik}",
        "provider_id": "sec_edgar",
        "source": {
            "id": f"source-{cik}",
            "name": "SEC EDGAR",
            "tier": "Tier 1",
            "kind": "filing",
            "url": f"https://www.sec.gov/Archives/edgar/data/{cik}/{letter}.txt",
            "published_at": "2026-08-10T00:10:00Z",
            "knowledge_available_at": "2026-08-10T00:10:00Z",
        },
        "payload": {
            "type": "filing",
            "form": "13F-HR",
            "company": cik,
            "accession_number": accession,
            "filed_at": "2023-01-03T00:00:00.000Z",
            "raw_metadata": {},
            "company_identity": {"cik": cik, "name": f"Company {letter}", "tickers": []},
            "report_period": "2022-12-31",
            "accepted_at": "2026-08-10T00:10:00Z",
            "value_normalization": {"source_unit": "usd", "formula_id": "usd_divided_by_1000"},
            "comparison": {
                "status": "unavailable",
                "previous_accession_number": None,
                "previous_report_period": None,
                "previous_accepted_at": None,
                "previous_filed_at": None,
                "previous_source_url": None,
                "previous_value_normalization": None,
                "reason": "no_previous_comparable_filing",
            },
            "holdings": [],
        },
    }


def test_sec_v2_changed_company_replaces_complete_a_to_h_slice():
    letters = "ABCDEFGH"
    prior = [
        _sec_slice_item(letter, revision="prior" if letter == "A" else "stable")
        for letter in letters
    ]
    current = [
        _sec_slice_item(letter, revision="current" if letter == "A" else "stable")
        for letter in letters
    ]
    outcome = ProviderOutcome("sec_edgar", state="healthy", retrieved_at="2026-08-11T00:21:00Z")

    result = select_provider_slices(
        outcomes={"sec_edgar": outcome},
        current_items=current,
        active_feed={
            "run_id": "prior-run",
            "items": prior,
            "provider_contracts": [
                {"provider_id": "sec_edgar", "snapshot": {"contract_version": 2}, "hash": "a" * 64}
            ],
        },
        contracts={"sec_edgar": FreshnessContract("event_driven", "checked_at")},
        current_contract_hashes={"sec_edgar": "b" * 64},
        empty_valid_for_window={"sec_edgar": True},
        evidence_cutoff_at="2026-08-11T00:20:00Z",
        strict_identity_provider_ids=("sec_edgar",),
        complete_state_provider_ids=("sec_edgar",),
    )

    selected = {item["id"]: item for item in result.items}
    expected = {item["id"]: item for item in current}
    assert selected == expected
    assert (
        selected["sec-edgar-0000000001"]["payload"]["accession_number"] == "0000000001-26-current-A"
    )
    assert set(selected) == {f"sec-edgar-000000000{index}" for index in range(1, 9)}
    assert outcome.freshness is not None
    assert outcome.freshness["status"] == "fresh"


def _sec_run_item(cik: str) -> dict:
    letter = chr(ord("A") + int(cik[-1]) - 1)
    return _sec_slice_item(letter, revision="run")


@pytest.mark.parametrize(
    ("present_ciks", "expected_ciks"),
    [
        (("0000000001",), {"0000000001"}),
        ((), set()),
    ],
)
def test_missing_watched_sec_cik_fails_without_prior_slice_fallback(
    tmp_path, monkeypatch, present_ciks, expected_ciks
):
    cfg = replace(
        _source_complete_cfg(),
        watched_companies=(
            WatchCompany("0000000001", "Company A", ()),
            WatchCompany("0000000002", "Company B", ()),
        ),
    )
    monkeypatch.setattr(feed_cli, "_load_app_config", lambda _path: cfg)
    planned = _planned_provider_ids(cfg)
    registry: dict[str, _OutcomeAdapter | list[_OutcomeAdapter]] = {
        provider_id: _OutcomeAdapter() for provider_id in planned
    }
    registry["sec_edgar"] = [
        _OutcomeAdapter(items=[_sec_run_item("0000000001")]),
        _OutcomeAdapter(items=[_sec_run_item("0000000002")]),
    ]
    output = tmp_path / "out"

    baseline = run_feed(
        output_root=str(output),
        cutoff=_cutoff(),
        providers_fn=lambda: registry,
        enabled_provider_ids=planned,
    )
    assert baseline.status == "healthy"
    previous_manifest = (output / "feed-manifest.json").read_bytes()

    registry["sec_edgar"] = [
        _OutcomeAdapter(items=[_sec_run_item(cik)] if cik in present_ciks else [])
        for cik in ("0000000001", "0000000002")
    ]
    published = False

    def fail_if_called(**_kwargs):
        nonlocal published
        published = True
        raise AssertionError("incomplete SEC acquisition must not publish")

    monkeypatch.setattr(feed_cli, "publish_bundle", fail_if_called)
    result = run_feed(
        output_root=str(output),
        cutoff=_cutoff().replace(hour=1),
        providers_fn=lambda: registry,
        enabled_provider_ids=planned,
    )

    assert result.feed is not None
    feed = result.feed
    sec_outcome = next(
        outcome for outcome in feed["provider_outcomes"] if outcome["provider_id"] == "sec_edgar"
    )
    sec_items = [item for item in feed["items"] if item["provider_id"] == "sec_edgar"]
    assert result.status == "failure"
    assert result.exit_code == 1
    assert not published
    assert (output / "feed-manifest.json").read_bytes() == previous_manifest
    assert sec_outcome["state"] == "partial"
    assert sec_outcome["availability"] == "failed"
    assert sec_outcome["freshness"]["status"] == "not_evaluated"
    assert sec_outcome["freshness"]["origin_contract_hash"] is None
    assert {item["payload"]["company_identity"]["cik"] for item in sec_items} == expected_ciks
