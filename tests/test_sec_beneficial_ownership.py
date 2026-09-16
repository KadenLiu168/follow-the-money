"""Focused Schedule 13D/G selection, admission, and projection tests."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from follow_the_money.providers.adapters import SecBeneficialOwnershipAdapter
from follow_the_money.providers.manifest import load_manifest, manifest_to_provider_entry
from follow_the_money.providers.sec_beneficial_ownership import (
    build_shared_historical_candidate_index,
    compare_beneficial_ownership,
    deduplicate_beneficial_ownership_candidates,
    derive_beneficial_ownership_historical_url,
    derive_beneficial_ownership_xml_url,
    is_unsupported_historical_document,
    parse_beneficial_ownership_document,
    parse_schedule_13d_document,
    parse_schedule_13g_document,
    select_beneficial_ownership_filings,
)
from follow_the_money.schema import SchemaError

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "providers" / "sec_edgar" / "fixtures" / "beneficial_ownership"
WINDOW = {"start": "2026-08-09T00:00:00Z", "end": "2026-08-11T00:00:00Z"}


def submissions() -> dict:
    return json.loads((FIXTURES / "submissions.json").read_text(encoding="utf-8"))


def candidates():
    return select_beneficial_ownership_filings(submissions(), WINDOW)


def test_schedule_13d_g_selection_uses_acceptance_boundaries_and_source_order():
    selected = candidates()
    assert [candidate.form for candidate in selected] == ["SCHEDULE 13D", "SCHEDULE 13G/A"]
    assert selected[0].accepted_at == "2026-08-10T00:00:00.000Z"
    assert selected[1].accepted_at == "2026-08-10T01:00:00.000Z"

    at_cutoff = deepcopy(submissions())
    at_cutoff["filings"]["recent"]["acceptanceDateTime"][1] = "2026-08-11T00:00:00Z"
    assert len(select_beneficial_ownership_filings(at_cutoff, WINDOW)) == 1

    overbound = deepcopy(submissions())
    recent = overbound["filings"]["recent"]
    for index in range(10, 18):
        recent["form"].append("SCHEDULE 13D")
        recent["filingDate"].append("2026-08-10")
        recent["reportDate"].append("")
        recent["accessionNumber"].append(f"0001067983-26-{index:06d}")
        recent["acceptanceDateTime"].append(f"2026-08-10T01:{index:02d}:00Z")
        recent["primaryDocument"].append(f"schedule{index}.xml")
    with pytest.raises(SchemaError, match="bound"):
        select_beneficial_ownership_filings(overbound, WINDOW)


def test_schedule_13d_and_13g_structured_projection_is_evidence_only():
    selected = candidates()
    candidate_13d, candidate_13g = selected
    url_13d = derive_beneficial_ownership_xml_url(
        candidate_13d.filer_cik, candidate_13d.accession_number, candidate_13d.primary_document
    )
    url_13g = derive_beneficial_ownership_xml_url(
        candidate_13g.filer_cik, candidate_13g.accession_number, candidate_13g.primary_document
    )
    parsed_13d = parse_schedule_13d_document(
        (FIXTURES / "13d.xml").read_bytes(), candidate_13d, source_url=url_13d
    )
    parsed_13g = parse_schedule_13g_document(
        (FIXTURES / "13g-amendment.xml").read_bytes(), candidate_13g, source_url=url_13g
    )
    assert parsed_13d.payload["filing_subtype"] == "beneficial_ownership"
    assert parsed_13d.payload["current_snapshot"]["ownership_class"]["identity_basis"] == "cusip"
    assert len(parsed_13d.payload["current_snapshot"]["reporting_positions"]) == 2
    assert (
        parsed_13d.payload["current_snapshot"]["reporting_positions"][1]["identity_basis"]
        == "source_name"
    )
    no_cik_body = (
        (FIXTURES / "13d.xml")
        .read_bytes()
        .replace(b"<reportingPersonCik>0000000001</reportingPersonCik>", b"")
        .replace(
            b"<reportingPersonName>First Reporting Person</reportingPersonName>",
            b"<reportingPersonName>First Reporting Person</reportingPersonName>\n"
            b"      <filerCik>0001067983</filerCik>",
        )
    )
    no_cik = parse_schedule_13d_document(no_cik_body, candidate_13d, source_url=url_13d)
    assert no_cik.payload["current_snapshot"]["reporting_positions"][0]["source_cik"] is None
    assert (
        parsed_13d.payload["current_snapshot"]["group_evidence"]["aggregate_shares"]["value"]
        == "1500"
    )
    assert parsed_13g.payload["is_amendment"] is True
    assert parsed_13g.payload["amendment_number"] == 2
    assert (
        parsed_13g.payload["current_snapshot"]["ownership_class"]["identity_basis"] == "class_title"
    )
    assert "raw_metadata" not in parsed_13d.payload
    assert "credentials" not in str(parsed_13d.payload).lower()


def test_schedule_13d_g_selection_rejects_incomplete_duplicate_and_reorders_source_rows():
    unordered = deepcopy(submissions())
    recent = unordered["filings"]["recent"]
    for values in recent.values():
        values[1], values[2] = values[2], values[1]
    assert [
        row.accession_number for row in select_beneficial_ownership_filings(unordered, WINDOW)
    ] == [
        "0001067983-26-000005",
        "0001067983-26-000006",
    ]

    incomplete = deepcopy(submissions())
    incomplete["filings"]["recent"]["acceptanceDateTime"][1] = WINDOW["end"]
    incomplete["filings"]["recent"]["acceptanceDateTime"][3] = WINDOW["end"]
    with pytest.raises(SchemaError, match="cover window.start"):
        select_beneficial_ownership_filings(incomplete, WINDOW)

    duplicate = deepcopy(submissions())
    duplicate["filings"]["recent"]["accessionNumber"][2] = duplicate["filings"]["recent"][
        "accessionNumber"
    ][1]
    with pytest.raises(SchemaError, match="duplicated"):
        select_beneficial_ownership_filings(duplicate, WINDOW)


def test_schedule_13d_g_cross_listing_deduplication_is_canonical_and_conflicts_fail():
    candidate = candidates()[0]
    assert deduplicate_beneficial_ownership_candidates([candidate, candidate]) == (candidate,)
    conflicting = replace(candidate, primary_document="other.xml")
    with pytest.raises(SchemaError, match="conflicting"):
        deduplicate_beneficial_ownership_candidates([candidate, conflicting])


def test_schedule_13d_g_safe_locator_rejects_unapproved_paths():
    candidate = candidates()[0]
    with pytest.raises(SchemaError):
        derive_beneficial_ownership_xml_url(
            candidate.filer_cik,
            candidate.accession_number,
            "../document.xml",
        )
    with pytest.raises(SchemaError):
        derive_beneficial_ownership_xml_url(
            candidate.filer_cik,
            candidate.accession_number,
            "xslSCHEDULE_13G_X01/document.html",
        )
    with pytest.raises(SchemaError):
        derive_beneficial_ownership_xml_url(
            candidate.filer_cik,
            candidate.accession_number,
            "xslSCHEDULE_13G_X99/document.xml",
        )


def test_schedule_13d_g_adapter_fetches_listing_and_selected_documents_once():
    class Response:
        def __init__(self, body: bytes, url: str):
            self.body_bytes = body
            self.content = body
            self.status_code = 200
            self.url = url
            self.headers: dict[str, str] = {}

    class Client:
        def __init__(self):
            self.requests: list[str] = []
            self.historical_13g = (FIXTURES / "13g-amendment.xml").read_bytes()
            self.historical_13g = self.historical_13g.replace(
                b"SCHEDULE 13G/A", b"SCHEDULE 13G"
            ).replace(b"<amendmentNumber>2</amendmentNumber>", b"")

        def get(self, url: str, **_kwargs):
            self.requests.append(url)
            if "/submissions/CIK" in url:
                body = (FIXTURES / "submissions.json").read_bytes()
            elif "000106798326000005" in url:
                body = (FIXTURES / "13d.xml").read_bytes()
            elif "000106798326000006" in url:
                body = (FIXTURES / "13g-amendment.xml").read_bytes()
            elif "000106798326000007" in url:
                body = self.historical_13g
            else:
                raise AssertionError(url)
            return Response(body, url)

    entry = manifest_to_provider_entry(load_manifest("sec_edgar"))
    adapter = SecBeneficialOwnershipAdapter(entry, watched_cik="0001067983")
    client = Client()
    raw = adapter.fetch(WINDOW, client)
    assert len(client.requests) == 3
    assert raw["historical_documents"] == []
    items = adapter.normalize(raw, WINDOW)
    assert len(client.requests) == 4
    assert len(raw["historical_documents"]) == 1
    assert client.requests[0].endswith("CIK0001067983.json")
    assert [item["payload"]["accession_number"] for item in items] == [
        "0001067983-26-000005",
        "0001067983-26-000006",
    ]
    by_accession = {item["payload"]["accession_number"]: item for item in items}
    assert by_accession["0001067983-26-000005"]["payload"]["comparison"]["reason"] == (
        "history_not_evaluated"
    )
    assert by_accession["0001067983-26-000006"]["payload"]["comparison"]["status"] == ("available")
    assert adapter.selection_complete is True
    assert adapter.selected_accessions == tuple(
        item["payload"]["accession_number"] for item in items
    )


def test_schedule_13d_g_comparison_normalizes_percentage_points_before_subtraction():
    current_candidate = candidates()[0]
    previous_candidate = replace(
        current_candidate,
        accession_number="0001067983-26-000004",
        accepted_at="2026-08-01T00:00:00.000Z",
        filed_at="2026-08-01T00:00:00.000Z",
    )
    source_url = derive_beneficial_ownership_xml_url(
        current_candidate.filer_cik,
        current_candidate.accession_number,
        current_candidate.primary_document,
    )
    previous_url = derive_beneficial_ownership_xml_url(
        previous_candidate.filer_cik,
        previous_candidate.accession_number,
        previous_candidate.primary_document,
    )
    current = parse_schedule_13d_document(
        (FIXTURES / "13d.xml").read_bytes(), current_candidate, source_url=source_url
    )
    previous_body = (
        (FIXTURES / "13d.xml").read_bytes().replace(b">1000<", b">800<").replace(b">5.5<", b">4.5<")
    )
    previous = parse_schedule_13d_document(
        previous_body, previous_candidate, source_url=previous_url
    )
    compared = compare_beneficial_ownership(current, previous)
    position = compared.payload["current_snapshot"]["reporting_positions"][0]
    assert compared.payload["comparison"]["status"] == "available"
    assert position["comparison"]["shares_delta"]["value"] == "200"
    assert position["comparison"]["percentage_delta"]["value"] == "1"
    assert (
        compared.payload["previous_snapshot"]["group_evidence"]["aggregate_shares"][
            "source_field_refs"
        ][0]["snapshot"]
        == "previous"
    )


def test_schedule_13d_g_xml_rejects_entity_and_unknown_namespace():
    candidate = candidates()[0]
    url = derive_beneficial_ownership_xml_url(
        candidate.filer_cik, candidate.accession_number, candidate.primary_document
    )
    body = (FIXTURES / "13d.xml").read_text(encoding="utf-8")
    with pytest.raises(SchemaError, match="DTD/entity"):
        parse_beneficial_ownership_document(
            body.replace("<edgarSubmission>", "<!DOCTYPE x><edgarSubmission>"),
            candidate,
            source_url=url,
        )
    with pytest.raises(SchemaError, match="namespace"):
        parse_beneficial_ownership_document(
            body.replace(
                "<edgarSubmission>", '<edgarSubmission xmlns="https://unexpected.example">'
            ),
            candidate,
            source_url=url,
        )


def test_schedule_13d_g_legacy_history_locators_and_schema_versions_are_typed():
    candidate = candidates()[0]
    for locator in ("legacy.xml", "legacy.htm", "legacy.html", "legacy.txt"):
        url = derive_beneficial_ownership_historical_url(
            candidate.filer_cik,
            candidate.accession_number,
            locator,
        )
        assert url.endswith(f"/{locator}")
    assert is_unsupported_historical_document(
        b"<schemaVersion>X0201</schemaVersion>",
        candidate,
        allowed_schema_versions=("X0202",),
    )
    legacy_candidate = replace(candidate, primary_document="legacy.txt")
    assert is_unsupported_historical_document(
        b"<schemaVersion>X0202</schemaVersion>",
        legacy_candidate,
        allowed_schema_versions=("X0202",),
    )


def test_schedule_13d_g_identity_unavailable_stops_before_history_documents():
    candidate = candidates()[0]
    body = (FIXTURES / "13d.xml").read_bytes().replace(b"<issuerCik>0000789019</issuerCik>", b"")
    url = derive_beneficial_ownership_xml_url(
        candidate.filer_cik, candidate.accession_number, candidate.primary_document
    )
    current = parse_schedule_13d_document(body, candidate, source_url=url)
    calls: list[str] = []
    index = build_shared_historical_candidate_index(
        [current],
        [candidate, replace(candidate, accession_number="0001067983-26-000004")],
        lambda value: calls.append(value.accession_number),
        history_complete=False,
        history_evaluated=True,
    )
    resolution = index.resolutions[candidate.accession_number]
    assert resolution.reason == "reporting_identity_not_comparable"
    assert calls == []


def test_schedule_13d_g_history_exhaustion_is_not_initial_filing():
    candidate = candidates()[0]
    current_url = derive_beneficial_ownership_xml_url(
        candidate.filer_cik, candidate.accession_number, candidate.primary_document
    )
    current = parse_schedule_13d_document(
        (FIXTURES / "13d.xml").read_bytes(), candidate, source_url=current_url
    )
    other_candidate = replace(
        candidate,
        accession_number="0001067983-26-000003",
        accepted_at="2026-08-08T00:00:00.000Z",
        filed_at="2026-08-08T00:00:00.000Z",
    )
    other_url = derive_beneficial_ownership_xml_url(
        other_candidate.filer_cik,
        other_candidate.accession_number,
        other_candidate.primary_document,
    )
    other = parse_schedule_13d_document(
        (FIXTURES / "13d.xml")
        .read_bytes()
        .replace(b"<cusip>123456789</cusip>", b"<cusip>987654321</cusip>"),
        other_candidate,
        source_url=other_url,
    )
    history_start = datetime(2026, 8, 9, tzinfo=UTC)
    history = [
        replace(
            other_candidate,
            accession_number=f"0001067983-26-{index:06d}",
            accepted_at=(history_start + timedelta(minutes=index))
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            filed_at="2026-08-09T00:00:00.000Z",
        )
        for index in range(65)
    ]
    index = build_shared_historical_candidate_index(
        [current],
        history,
        lambda _candidate: other,
        max_candidate_documents=64,
        history_complete=False,
        history_evaluated=True,
    )
    assert index.resolutions[candidate.accession_number].reason == (
        "history_candidate_bound_exhausted"
    )

    complete = build_shared_historical_candidate_index(
        [current],
        [candidate],
        lambda _candidate: current,
        max_candidate_documents=64,
        history_complete=True,
        history_evaluated=True,
    )
    assert complete.resolutions[candidate.accession_number].status == "initial_filing"


def test_schedule_13d_g_unsupported_previous_is_not_skipped():
    candidate = candidates()[0]
    current_url = derive_beneficial_ownership_xml_url(
        candidate.filer_cik, candidate.accession_number, candidate.primary_document
    )
    current = parse_schedule_13d_document(
        (FIXTURES / "13d.xml").read_bytes(), candidate, source_url=current_url
    )
    unsupported = replace(
        candidate,
        accession_number="0001067983-26-000004",
        accepted_at="2026-08-09T00:00:00.000Z",
        filed_at="2026-08-09T00:00:00.000Z",
        primary_document="legacy.htm",
    )
    older = replace(
        unsupported,
        accession_number="0001067983-26-000003",
        accepted_at="2026-08-08T00:00:00.000Z",
        filed_at="2026-08-08T00:00:00.000Z",
        primary_document=candidate.primary_document,
    )
    calls: list[str] = []

    def load(value):
        calls.append(value.accession_number)
        return None if value.accession_number == unsupported.accession_number else current

    index = build_shared_historical_candidate_index(
        [current],
        [unsupported, older],
        load,
        history_complete=True,
        history_evaluated=True,
    )
    resolution = index.resolutions[candidate.accession_number]
    assert resolution.reason == "previous_format_unsupported"
    assert resolution.candidate is unsupported
    assert calls == [unsupported.accession_number]


def test_schedule_13d_g_empty_current_selection_does_not_fetch_history():
    listing = submissions()
    recent = listing["filings"]["recent"]
    recent["form"] = ["8-K" for _ in recent["form"]]
    listing["filings"]["files"] = [{"name": "CIK0001067983-submissions-001.json"}]

    class Client:
        def __init__(self):
            self.requests: list[str] = []

        def get(self, url: str, **_kwargs):
            self.requests.append(url)
            body = json.dumps(listing).encode("utf-8")
            return SimpleNamespace(
                body_bytes=body,
                content=body,
                status_code=200,
                url=url,
                headers={},
            )

    entry = manifest_to_provider_entry(load_manifest("sec_edgar"))
    adapter = SecBeneficialOwnershipAdapter(entry, watched_cik="0001067983")
    client = Client()
    raw = adapter.fetch(WINDOW, client)
    assert len(client.requests) == 1
    assert raw["historical_candidates"] == ()
    assert adapter.normalize(raw, WINDOW) == []
