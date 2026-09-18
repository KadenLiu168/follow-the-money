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
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from follow_the_money.canonical import canonical_digest
from follow_the_money.config import load_config
from follow_the_money.feed.bundle import MANIFEST_FILENAME, artifact_relative_path, validate_bundle
from follow_the_money.feed.cli import run_feed as _run_feed
from follow_the_money.feed.validate import validate_feed
from follow_the_money.providers.adapters import (
    CftcAdapter,
    SecBeneficialOwnershipAdapter,
    SecEdgarAdapter,
    SecForm4Adapter,
    build_registry,
)
from follow_the_money.providers.http import FetchError
from follow_the_money.providers.urls import sec_archive_cik
from follow_the_money.schema import SchemaError

REPO_ROOT = Path(__file__).resolve().parents[1]
CFTC_FIXTURE = REPO_ROOT / "providers" / "cftc" / "fixtures" / "cot.json"

# The CFTC fixture publishes 2026-08-07T19:30:00.000Z (report date plus the
# documented Friday release boundary). The first cutoff keeps that report
# inside the 72h bootstrap window; the second cutoff is a complete next check
# that finds no new CFTC report while the prior weekly slice remains inside its
# seven-day validity window.
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


class _SecFixtureClient:
    def __init__(self, cik: str, name: str, kind: str = "13f") -> None:
        self.cik = cik
        self.name = name
        self.kind = kind
        self.accession = f"{cik}-26-000001"

    def get(self, url, headers=None, timeout=None, follow_redirects=True):
        if self.kind == "form4":
            if "data.sec.gov" in url:
                body = (
                    REPO_ROOT / "providers/sec_edgar/fixtures/form4/submissions.json"
                ).read_bytes()
            else:
                filename = Path(url).name
                filename = "mixed.xml" if filename == "primary_doc.xml" else filename
                body = (REPO_ROOT / "providers/sec_edgar/fixtures/form4" / filename).read_bytes()
        elif self.kind == "beneficial_ownership":
            if "data.sec.gov" in url:
                body = (
                    REPO_ROOT / "providers/sec_edgar/fixtures/beneficial_ownership/submissions.json"
                ).read_bytes()
            else:
                filename = Path(url).name
                if filename == "schedule13d.xml":
                    filename = "13d.xml"
                elif filename == "schedule13ga.xml":
                    filename = "13g-amendment.xml"
                elif filename == "schedule13g.xml":
                    body = (
                        REPO_ROOT
                        / "providers/sec_edgar/fixtures/beneficial_ownership/13g-amendment.xml"
                    ).read_bytes()
                    body = body.replace(b"SCHEDULE 13G/A", b"SCHEDULE 13G").replace(
                        b"<amendmentNumber>2</amendmentNumber>", b""
                    )
                    return SimpleNamespace(
                        body_bytes=body, content=body, status_code=200, headers={}, url=url
                    )
                body = (
                    REPO_ROOT / "providers/sec_edgar/fixtures/beneficial_ownership" / filename
                ).read_bytes()
        elif "data.sec.gov" in url:
            body = json.dumps(
                {
                    "cik": self.cik,
                    "name": self.name,
                    "tickers": [],
                    "filings": {
                        "recent": {
                            "form": ["13F-HR"],
                            "filingDate": ["2026-08-01"],
                            "reportDate": ["2026-06-30"],
                            "accessionNumber": [self.accession],
                            "acceptanceDateTime": ["2026-08-01T12:00:00Z"],
                            "primaryDocument": ["synthetic.xml"],
                            "cik": [self.cik],
                            "companyName": [self.name],
                        }
                    },
                }
            ).encode("utf-8")
        else:
            body = f"""<SEC-DOCUMENT><HEADER>CENTRAL INDEX KEY: {self.cik}\nACCESSION NUMBER: {self.accession}\nCONFORMED SUBMISSION TYPE: 13F-HR\nFILED AS OF DATE: 20260801</HEADER><XML><informationTable xmlns=\"http://www.sec.gov/edgar/document/thirteenf\"><infoTable><nameOfIssuer>Synthetic Issuer</nameOfIssuer><titleOfClass>Common Stock</titleOfClass><cusip>037833100</cusip><value>1234567</value><shrsOrPrnAmt><sshPrnamt>100</sshPrnamt><sshPrnamtType>SH</sshPrnamtType></shrsOrPrnAmt></infoTable></informationTable></XML></SEC-DOCUMENT>""".encode()
        return SimpleNamespace(body_bytes=body, content=body, status_code=200, headers={}, url=url)


class _CftcFixtureAdapter:
    """Production CftcAdapter served from the checked-in fixture."""

    provider_id = "cftc"

    def __init__(
        self,
        inner: CftcAdapter,
        *,
        error: Exception | None = None,
        body: bytes | None = None,
    ) -> None:
        self.inner = inner
        self.error = error
        self.body = body

    def fetch(self, window, client=None):
        if self.error is not None:
            raise self.error
        body = self.body if self.body is not None else CFTC_FIXTURE.read_bytes()
        return self.inner.fetch(window, _FixtureClientBody(body))

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
}


def _fixture_registry(
    error: Exception | None = None, *, cftc_body: bytes | None = None
) -> dict[str, Any]:
    """Every enabled production provider, each served its checked-in fixture."""
    registry = build_registry()
    wrapped: dict[str, Any] = {}
    for pid in registry.ids():
        inner = registry.get(pid)

        if pid == "cftc":
            wrapped[pid] = _CftcFixtureAdapter(
                cast(CftcAdapter, inner), error=error, body=cftc_body
            )
            continue
        if pid == "sec_edgar":

            class _SecFixtureServed:
                provider_id = "sec_edgar"

                def __init__(self, adapter) -> None:
                    self.adapter = adapter

                def fetch(self, window, client=None):
                    company = self.adapter._watched_company
                    return self.adapter.fetch(
                        window,
                        _SecFixtureClient(company.cik, f"Synthetic {company.cik}"),
                    )

                def normalize(self, raw, window):
                    return self.adapter.normalize(raw, window)

            cfg = load_config(
                REPO_ROOT / "config" / "config.yaml",
                REPO_ROOT / "config" / "providers.yaml",
                manifest_root=REPO_ROOT / "providers",
                require_verified_enabled=True,
            )
            sec_contract = cast(SecEdgarAdapter, inner)._contract
            wrapped[pid] = [
                _SecFixtureServed(SecEdgarAdapter(sec_contract, watched_company=company))
                for company in cfg.watched_companies
            ]

            class _SecSubtypeFixtureServed:
                provider_id = "sec_edgar"

                def __init__(self, adapter, kind: str, cik: str, name: str) -> None:
                    self.adapter = adapter
                    self.kind = kind
                    self.selection_kind = kind
                    self.cik = cik
                    self.name = name

                @property
                def selected_accessions(self):
                    return self.adapter.selected_accessions

                @property
                def selection_complete(self):
                    return self.adapter.selection_complete

                def fetch(self, window, client=None):
                    return self.adapter.fetch(
                        window, _SecFixtureClient(self.cik, self.name, self.kind)
                    )

                def normalize(self, raw, window):
                    return self.adapter.normalize(raw, window)

            wrapped[pid].extend(
                _SecSubtypeFixtureServed(
                    SecForm4Adapter(sec_contract, watched_issuer=issuer),
                    "form4",
                    issuer.cik,
                    issuer.name,
                )
                for issuer in cfg.watched_form4_issuers
            )
            wrapped[pid].extend(
                _SecSubtypeFixtureServed(
                    SecBeneficialOwnershipAdapter(sec_contract, watched_filer=filer),
                    "beneficial_ownership",
                    filer.cik,
                    filer.name,
                )
                for filer in cfg.watched_beneficial_ownership_filers
            )
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
    assert snapshot["contract_version"] == 2
    assert snapshot["payload_types"] == ["positioning"]
    assert snapshot["pagination"] == "page_number"
    assert snapshot["empty_valid_for_window"] is False
    assert snapshot["units"] == {"contracts": "contracts"}
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
    feed = _feed(output)
    sec_contract = next(
        c for c in manifest["provider_contracts"] if c["provider_id"] == "sec_edgar"
    )
    assert sec_contract["snapshot"]["contract_version"] == 4
    assert sec_contract["snapshot"]["units"] == {
        "13f_value_before_2023_01_03": "usd_thousands",
        "13f_value_from_2023_01_03": "usd",
        "reported_value_usd_thousands": "usd_thousands",
    }
    assert sec_contract["snapshot"]["max_filings_per_window"] == 20
    assert sec_contract["snapshot"]["ownership_xml_schema_versions"] == ["X0609"]
    assert sec_contract["snapshot"]["beneficial_ownership"]["schema_versions"] == ["X0202"]
    sec_items = [item for item in feed["items"] if item["provider_id"] == "sec_edgar"]
    assert len(sec_items) == 12
    assert all(
        "holdings" in item["payload"]
        for item in sec_items
        if item["payload"].get("filing_subtype") == "form13f"
    )
    assert (
        sum(item["payload"].get("filing_subtype") == "beneficial_ownership" for item in sec_items)
        == 2
    )

    # The CFTC item is inventoried only in the typed positioning artifact.
    inventory = {entry["domain"]: entry for entry in manifest["artifacts"]}
    assert inventory["positioning"]["item_count"] == 1
    artifact = json.loads(
        (output / artifact_relative_path("positioning", manifest["run_id"])).read_text(
            encoding="utf-8"
        )
    )
    assert [item["id"] for item in artifact["items"]] == [_cftc_item(feed)["id"]]
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
    item = _cftc_item(feed)
    assert item["payload"]["type"] == "positioning"
    assert item["payload"]["market_identity"] == {
        "cftc_contract_market_code": "088691",
        "contract_market_name": "GOLD",
    }
    assert item["payload"]["current_metrics"]["net_noncommercial"] == {
        "value": "46913",
        "unit": "contracts",
    }
    assert item["payload"]["comparison"]["status"] == "unavailable"
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


def test_corrected_same_date_cftc_report_removes_market_without_carry(tmp_path):
    # Both SEC/CFTC v2 slices are complete current-state slices, so carry
    # forward requires equal identity sets. A corrected same-date report that
    # drops a market while leaving the remaining item byte-identical must
    # replace the whole slice instead of carrying the removed market back.
    output = tmp_path / "out"
    fixture_dir = REPO_ROOT / "providers" / "cftc" / "fixtures"
    rows = json.loads((fixture_dir / "cot-current.json").read_text(encoding="utf-8"))
    silver = [row for row in rows if row["cftc_contract_market_code"] == "084691"]
    assert len(silver) == 1 and len(rows) == 2

    first = run_feed(
        output_root=str(output),
        cutoff=CUTOFF_1,
        providers_fn=lambda: _fixture_registry(cftc_body=json.dumps(rows).encode()),
    )
    assert first.exit_code == 0
    first_cftc = {
        item["id"]: item for item in _feed(output)["items"] if item["provider_id"] == "cftc"
    }
    assert len(first_cftc) == 2

    second = run_feed(
        output_root=str(output),
        cutoff=CUTOFF_2,
        providers_fn=lambda: _fixture_registry(cftc_body=json.dumps(silver).encode()),
    )
    assert second.exit_code == 0
    second_items = _feed(output)["items"]
    second_cftc = {item["id"]: item for item in second_items if item["provider_id"] == "cftc"}

    assert len(second_cftc) == 1
    (survivor_id, survivor) = next(iter(second_cftc.items()))
    assert survivor == first_cftc[survivor_id]
    assert second_cftc.keys() < first_cftc.keys()
    outcome = _cftc_outcome(_manifest(output))
    assert outcome["freshness"]["status"] != "valid_unchanged"
    assert outcome["freshness"]["carried_forward_from_run_id"] is None


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
    assert second.feed is not None
    outcome = _cftc_outcome(second.feed)
    assert outcome["state"] == "failed"
    assert outcome["freshness"]["status"] == "not_evaluated"

    # The active bundle is not replaced.
    assert (output / MANIFEST_FILENAME).read_bytes() == manifest_before


def test_sec_v4_beneficial_ownership_payload_rejects_analysis_and_generic_fields(tmp_path):
    result = _run(tmp_path / "out", CUTOFF_1)
    assert result.exit_code == 0
    assert result.feed is not None
    beneficial = next(
        item
        for item in result.feed["items"]
        if item["payload"].get("filing_subtype") == "beneficial_ownership"
    )
    for forbidden_key in (
        "bullish",
        "takeover_likelihood",
        "control_change",
        "importance",
        "signal",
        "recommendation",
        "generic_fact",
        "amends_accession",
    ):
        changed = deepcopy(result.feed)
        changed_item = next(item for item in changed["items"] if item["id"] == beneficial["id"])
        changed_item["payload"][forbidden_key] = True
        with pytest.raises(SchemaError):
            validate_feed(changed)


def test_sec_v4_beneficial_ownership_validator_binds_provenance_and_legacy_refs(tmp_path):
    result = _run(tmp_path / "out", CUTOFF_1)
    assert result.exit_code == 0
    assert result.feed is not None
    item = next(
        item
        for item in result.feed["items"]
        if item["payload"].get("filing_subtype") == "beneficial_ownership"
        and item["payload"].get("previous_snapshot") is None
    )

    changed = deepcopy(result.feed)
    changed_item = next(value for value in changed["items"] if value["id"] == item["id"])
    changed_item["payload"]["filed_at"] = "2026-08-10T00:00:00.001Z"
    with pytest.raises(SchemaError):
        validate_feed(changed)

    changed = deepcopy(result.feed)
    changed_item = next(value for value in changed["items"] if value["id"] == item["id"])
    changed_item["source"]["name"] = "SEC  EDGAR"
    with pytest.raises(SchemaError):
        validate_feed(changed)

    changed = deepcopy(result.feed)
    changed_item = next(value for value in changed["items"] if value["id"] == item["id"])
    current_url = changed_item["payload"]["current_snapshot"]["document_url"]
    changed_item["payload"]["current_snapshot"]["document_url"] = (
        current_url.rsplit("/", 1)[0] + "/other.xml"
    )
    with pytest.raises(SchemaError):
        validate_feed(changed)

    changed = deepcopy(result.feed)
    changed_item = next(value for value in changed["items"] if value["id"] == item["id"])
    changed_item["payload"]["current_snapshot"]["reporting_positions"][0]["source_field_refs"][0][
        "field"
    ] = "reporting_person[0].arbitrary"
    with pytest.raises(SchemaError):
        validate_feed(changed)

    changed = deepcopy(result.feed)
    changed_item = next(value for value in changed["items"] if value["id"] == item["id"])
    changed_item["payload"]["comparison"] = {
        "status": "unavailable",
        "reason": "previous_format_unsupported",
        "previous": {
            "accession_number": "0001067983-26-000007",
            "accepted_at": "2026-08-01T10:00:00.000Z",
            "document_url": (
                "https://www.sec.gov/Archives/edgar/data/1067983/000106798326000007/legacy.htm"
            ),
        },
    }
    validate_feed(changed)
    changed_item = next(value for value in changed["items"] if value["id"] == item["id"])
    changed_item["payload"]["comparison"]["previous"]["document_url"] = (
        "https://www.sec.gov/Archives/edgar/data/0/000106798326000007/legacy.htm"
    )
    with pytest.raises(SchemaError):
        validate_feed(changed)

    # A padded Archive CIK is the redirecting alias, not the canonical locator the
    # producer derives, so the validator rejects it on the current document too.
    changed = deepcopy(result.feed)
    changed_item = next(value for value in changed["items"] if value["id"] == item["id"])
    filer = changed_item["payload"]["company"]
    canonical_url = changed_item["payload"]["document_url"]
    padded_url = canonical_url.replace(f"/data/{sec_archive_cik(filer)}/", f"/data/{filer}/")
    assert padded_url != canonical_url
    changed_item["payload"]["document_url"] = padded_url
    changed_item["payload"]["current_snapshot"]["document_url"] = padded_url
    changed_item["source"]["url"] = padded_url
    with pytest.raises(SchemaError):
        validate_feed(changed)
