"""Deterministic production-path tests for the activated CFTC weekly feed.

``run_feed`` resolves the checked-in production configuration itself (default
config/config.yaml + config/providers.yaml + provider manifests). Every
provider runs its real production adapter against the checked-in fixtures, so
these tests exercise the full production path — planning, acquisition, durable
rate coordination, cadence-aware slice selection, typed bundle routing, and
manifest-led publication — with no network access.

CFTC weekly semantics proven here:

1. A newly available report publishes the CFTC item only in the positioning
   artifact as ``fresh`` with original source-semantic timestamps.
2. A complete check with no new report carries the prior slice unchanged as
   ``valid_unchanged`` while operational timestamps advance independently.
3. A failed check after a prior snapshot stays incomplete with
   ``not_evaluated``, fails the command, and never replaces the active bundle.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from follow_the_money.canonical import canonical_digest
from follow_the_money.feed.bundle import MANIFEST_FILENAME, artifact_relative_path, validate_bundle
from follow_the_money.feed.cli import run_feed as _run_feed
from follow_the_money.providers.adapters import (
    CftcAdapter,
    YahooMarketAdapter,
    build_registry,
)
from follow_the_money.providers.http import FetchError

REPO_ROOT = Path(__file__).resolve().parents[1]
CFTC_FIXTURE = REPO_ROOT / "providers" / "cftc" / "fixtures" / "cot.json"

# The CFTC fixture publishes 2026-08-07T19:30:00.000Z (report date plus the
# documented Friday release boundary). The first cutoff keeps that report
# inside the 72h bootstrap window while staying within one market-session day
# of the Yahoo fixture's last observation; the second cutoff is a complete
# next check that finds no new CFTC report while the prior weekly slice is
# still inside its seven-day validity window.
CUTOFF_1 = datetime(2026, 8, 10, 17, 0, 0, tzinfo=UTC)
CUTOFF_2 = CUTOFF_1 + timedelta(hours=6)

EXPECTED_AS_OF = "2026-08-04T00:00:00.000Z"
EXPECTED_PUBLISHED = "2026-08-07T19:30:00.000Z"


def run_feed(**kwargs: Any):
    if "runtime_state_root" not in kwargs and kwargs.get("output_root") is not None:
        output = Path(kwargs["output_root"])
        kwargs["runtime_state_root"] = str(output.parent / f".{output.name}-state")
    return _run_feed(**kwargs)


class _FixtureClientBody:
    """Serves one checked-in fixture body through the bounded fetch seam."""

    def __init__(self, body: bytes) -> None:
        self.body = body

    def get(self, url, headers=None, timeout=None, follow_redirects=True):
        body = self.body
        return SimpleNamespace(
            body_bytes=body,
            content=body,
            status_code=200,
            headers={},
            url=url,
            json=lambda: json.loads(body.decode("utf-8")),
        )


class _CftcFixtureAdapter:
    """Production CftcAdapter served from the checked-in fixture."""

    provider_id = "cftc"

    def __init__(self, inner: CftcAdapter, *, error: Exception | None = None) -> None:
        self.inner = inner
        self.error = error

    def fetch(self, window, client=None):
        if self.error is not None:
            raise self.error
        return self.inner.fetch(window, _FixtureClientBody(CFTC_FIXTURE.read_bytes()))

    def normalize(self, raw, window):
        return self.inner.normalize(raw, window)


FIXTURE_BY_PROVIDER = {
    "federal_reserve": "providers/federal_reserve/fixtures/press_all.xml",
    "bls": "providers/bls/fixtures/news.release.xml",
    "sec_edgar": "providers/sec_edgar/fixtures/browse-13f.json",
    "pboc": "providers/pboc/fixtures/announcements.json",
    "nbs": "providers/nbs/fixtures/releases.json",
    "sse": "providers/sse/fixtures/notices.json",
    "szse": "providers/szse/fixtures/notices.json",
    "yahoo_market": "providers/yahoo_market/fixtures/chart.json",
}


def _fixture_registry(error: Exception | None = None) -> dict[str, Any]:
    """Every enabled production provider, each served its checked-in fixture."""
    registry = build_registry()
    wrapped: dict[str, Any] = {}
    for pid in registry.ids():
        inner = (
            YahooMarketAdapter(instrument="^GSPC", role_id="sp500")
            if pid == "yahoo_market"
            else registry.get(pid)
        )

        if pid == "cftc":
            wrapped[pid] = _CftcFixtureAdapter(inner, error=error)
            continue

        class _FixtureServed:
            def __init__(self, adapter) -> None:
                self.adapter = adapter
                self.provider_id = adapter.provider_id

            def fetch(self, window, client=None):
                fixture = REPO_ROOT / FIXTURE_BY_PROVIDER[self.provider_id]
                return self.adapter.fetch(window, _FixtureClientBody(fixture.read_bytes()))

            def normalize(self, raw, window):
                return self.adapter.normalize(raw, window)

        wrapped[pid] = _FixtureServed(inner)
    return wrapped


def _run(output_root: Path, cutoff: datetime, *, error: Exception | None = None):
    return run_feed(
        output_root=str(output_root),
        cutoff=cutoff,
        providers_fn=lambda: _fixture_registry(error),
    )


def _manifest(output_root: Path) -> dict[str, Any]:
    return json.loads((output_root / MANIFEST_FILENAME).read_text(encoding="utf-8"))


def _cftc_outcome(manifest: dict[str, Any]) -> dict[str, Any]:
    return next(o for o in manifest["provider_outcomes"] if o["provider_id"] == "cftc")


def _cftc_contract(manifest: dict[str, Any]) -> dict[str, Any]:
    return next(c for c in manifest["provider_contracts"] if c["provider_id"] == "cftc")


def _feed(output_root: Path) -> dict[str, Any]:
    return validate_bundle(output_root)


def _cftc_item(feed: dict[str, Any]) -> dict[str, Any]:
    items = [i for i in feed["items"] if i["provider_id"] == "cftc"]
    assert len(items) == 1
    return items[0]


def _assert_weekly_cadence_provenance(manifest: dict[str, Any]) -> None:
    contract = _cftc_contract(manifest)
    assert contract["hash"] == canonical_digest(contract["snapshot"])
    snapshot = contract["snapshot"]
    assert snapshot["tier"] == "Tier 1"
    assert snapshot["source_family_id"] == "cftc"
    assert snapshot["authentication"] == "none"
    assert snapshot["payload_types"] == ["positioning"]
    assert snapshot["freshness"] == {
        "cadence": "weekly",
        "reference_time": "data_as_of",
        "valid_for_seconds": 604800,
    }


# ---------------------------------------------------------------------------
# Newly available report
# ---------------------------------------------------------------------------


def test_new_cftc_report_publishes_only_in_positioning_artifact(tmp_path):
    output = tmp_path / "out"
    result = _run(output, CUTOFF_1)

    assert result.exit_code == 0
    assert result.status == "healthy"
    manifest = _manifest(output)

    # The CFTC item is inventoried only in the typed positioning artifact.
    inventory = {entry["domain"]: entry for entry in manifest["artifacts"]}
    assert inventory["positioning"]["item_count"] == 1
    artifact = json.loads(
        (output / artifact_relative_path("positioning", manifest["run_id"])).read_text(
            encoding="utf-8"
        )
    )
    assert [item["id"] for item in artifact["items"]] == [_cftc_item(_feed(output))["id"]]
    for domain, entry in inventory.items():
        if domain == "positioning":
            continue
        other = json.loads((output / entry["path"]).read_text(encoding="utf-8"))
        assert all(item["provider_id"] != "cftc" for item in other["items"])

    # Provider outcome: healthy with weekly-cadence fresh freshness.
    outcome = _cftc_outcome(manifest)
    assert outcome["state"] == "healthy"
    assert outcome["accepted"] == 1
    contract = _cftc_contract(manifest)
    assert outcome["freshness"] == {
        "cadence": "weekly",
        "status": "fresh",
        "origin_contract_hash": contract["hash"],
        "carried_forward_from_run_id": None,
    }
    _assert_weekly_cadence_provenance(manifest)

    # Original source-semantic timestamps are preserved verbatim.
    item = _cftc_item(_feed(output))
    assert item["payload"]["type"] == "positioning"
    assert item["payload"]["as_of"] == EXPECTED_AS_OF
    assert item["source"]["published_at"] == EXPECTED_PUBLISHED
    assert item["source"]["knowledge_available_at"] == EXPECTED_PUBLISHED


# ---------------------------------------------------------------------------
# No new report: carry the prior slice unchanged
# ---------------------------------------------------------------------------


def test_no_new_cftc_report_carries_prior_slice_unchanged(tmp_path):
    output = tmp_path / "out"
    first = _run(output, CUTOFF_1)
    assert first.exit_code == 0
    first_manifest = _manifest(output)
    first_outcome = _cftc_outcome(first_manifest)
    first_item = _cftc_item(_feed(output))

    second = _run(output, CUTOFF_2)
    assert second.exit_code == 0
    assert second.status == "healthy"
    second_manifest = _manifest(output)
    second_outcome = _cftc_outcome(second_manifest)
    second_item = _cftc_item(_feed(output))

    # The prior slice is carried unchanged: no source, knowledge, or
    # positioning.as_of timestamp is rewritten.
    assert second_item == first_item
    assert second_item["payload"]["as_of"] == EXPECTED_AS_OF
    assert second_item["source"]["published_at"] == EXPECTED_PUBLISHED

    assert second_outcome["freshness"] == {
        "cadence": "weekly",
        "status": "valid_unchanged",
        "origin_contract_hash": first_outcome["freshness"]["origin_contract_hash"],
        "carried_forward_from_run_id": first_manifest["run_id"],
    }

    # Current operational retrieval and generation timestamps advance
    # independently of the carried evidence.
    assert second_outcome["retrieved_at"] != first_outcome["retrieved_at"]
    assert second_manifest["evidence_cutoff_at"] != first_manifest["evidence_cutoff_at"]
    assert second_manifest["collection_started_at"] != first_manifest["collection_started_at"]
    assert second_manifest["generated_at"] != first_manifest["generated_at"]


# ---------------------------------------------------------------------------
# Acquisition failure with a prior valid snapshot
# ---------------------------------------------------------------------------


def test_cftc_failure_keeps_incomplete_outcome_and_active_bundle(tmp_path):
    output = tmp_path / "out"
    first = _run(output, CUTOFF_1)
    assert first.exit_code == 0
    manifest_before = (output / MANIFEST_FILENAME).read_bytes()

    second = _run(
        output,
        CUTOFF_2,
        error=FetchError("HTTP 503 from publicreporting.cftc.gov", status_code=503),
    )

    # The outcome remains incomplete with not_evaluated freshness and the
    # command fails; the prior slice does not substitute for success.
    assert second.status == "failure"
    assert second.exit_code == 1
    outcome = _cftc_outcome(second.feed)
    assert outcome["state"] == "failed"
    assert outcome["freshness"]["status"] == "not_evaluated"

    # The active bundle is not replaced.
    assert (output / MANIFEST_FILENAME).read_bytes() == manifest_before
