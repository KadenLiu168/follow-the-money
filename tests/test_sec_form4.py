"""Pure SEC Form 4 selection, parsing, and adapter-boundary tests."""

from __future__ import annotations

import json
from copy import deepcopy
from decimal import ROUND_DOWN, ROUND_HALF_EVEN, localcontext
from pathlib import Path
from types import SimpleNamespace

import pytest

from follow_the_money.canonical import canonical_bytes, canonical_digest
from follow_the_money.config import load_config
from follow_the_money.feed.validate import recompute_feed_identity, validate_feed
from follow_the_money.providers.adapters import SecForm4Adapter
from follow_the_money.providers.http import stable_item_id
from follow_the_money.providers.manifest import load_manifest, manifest_to_provider_entry
from follow_the_money.providers.sec_form4 import (
    derive_form4_xml_url,
    parse_form4_document,
    select_form4_filings,
)
from follow_the_money.schema import SchemaError
from tests.test_feed_bundle import _feed

ROOT = Path(__file__).parents[1]
FIXTURES = ROOT / "providers" / "sec_edgar" / "fixtures" / "form4"
WINDOW = {"start": "2026-08-10T00:00:00Z", "end": "2026-08-11T00:00:00Z"}


def _submissions() -> dict:
    return json.loads((FIXTURES / "submissions.json").read_text(encoding="utf-8"))


def test_form4_selection_is_complete_half_open_and_deterministic():
    selected = select_form4_filings(_submissions(), WINDOW)
    assert [row.accession_number for row in selected] == [
        "0001067983-26-000002",
        "0001067983-26-000003",
    ]
    assert selected[0].form == "4"
    assert selected[1].form == "4/A"

    at_start = json.loads(json.dumps(_submissions()))
    at_start["filings"]["recent"]["acceptanceDateTime"][1] = WINDOW["start"]
    at_start["filings"]["recent"]["acceptanceDateTime"][2] = "2026-08-09T10:00:00Z"
    selected = select_form4_filings(at_start, WINDOW)
    assert selected[0].accepted_at.startswith("2026-08-10T00:00:00")

    at_cutoff = json.loads(json.dumps(_submissions()))
    at_cutoff["filings"]["recent"]["acceptanceDateTime"][0] = WINDOW["end"]
    assert len(select_form4_filings(at_cutoff, WINDOW)) == 1


def test_form4_selection_canonicalizes_nonmonotonic_source_order_and_ties():
    unordered = _submissions()
    recent = unordered["filings"]["recent"]
    for values in recent.values():
        values[0], values[1] = values[1], values[0]
    assert [row.accession_number for row in select_form4_filings(unordered, WINDOW)] == [
        "0001067983-26-000002",
        "0001067983-26-000003",
    ]

    tied = _submissions()
    tied["filings"]["recent"]["acceptanceDateTime"][0] = tied["filings"]["recent"][
        "acceptanceDateTime"
    ][1]
    assert [row.accession_number for row in select_form4_filings(tied, WINDOW)] == [
        "0001067983-26-000002",
        "0001067983-26-000003",
    ]


@pytest.mark.parametrize(
    "primary",
    [
        "/absolute.xml",
        "https://sec.gov/a.xml",
        "xslF345X06/../a.xml",
        "xslF345X05/ownership.xml",
        "other/a.xml",
        "a.txt",
        "a@b.xml",
    ],
)
def test_form4_raw_locator_is_narrowly_validated(primary: str):
    with pytest.raises(SchemaError):
        derive_form4_xml_url("0001067983", "0001067983-26-000002", primary)


def test_form4_selector_rejects_incomplete_duplicate_and_overbound_listing():
    incomplete = _submissions()
    incomplete["filings"]["recent"]["acceptanceDateTime"][2] = "2026-08-10T01:00:00Z"
    with pytest.raises(SchemaError, match="cover window.start"):
        select_form4_filings(incomplete, WINDOW)

    duplicate = _submissions()
    duplicate["filings"]["recent"]["accessionNumber"][1] = duplicate["filings"]["recent"][
        "accessionNumber"
    ][0]
    with pytest.raises(SchemaError, match="duplicated"):
        select_form4_filings(duplicate, WINDOW)

    overbound = {
        "cik": "0001067983",
        "filings": {
            "recent": {
                "form": ["4"] * 21,
                "filingDate": ["2026-08-10"] * 21,
                "reportDate": ["2026-08-09"] * 21,
                "accessionNumber": [f"0001067983-26-{index:06d}" for index in range(21, 0, -1)],
                "acceptanceDateTime": [
                    f"2026-08-10T{12 - (index // 60):02d}:{59 - (index % 60):02d}:00Z"
                    for index in range(20)
                ]
                + ["2026-08-10T00:00:00Z"],
                "primaryDocument": [f"form{index}.xml" for index in range(21)],
            }
        },
    }
    with pytest.raises(SchemaError, match="bound"):
        select_form4_filings(overbound, WINDOW)


def test_form4_selector_allows_complete_empty_listing():
    empty = _submissions()
    recent = empty["filings"]["recent"]
    recent["form"] = ["8-K"]
    recent["filingDate"] = ["2026-08-01"]
    recent["reportDate"] = ["2026-08-01"]
    recent["accessionNumber"] = ["0001067983-26-000001"]
    recent["acceptanceDateTime"] = ["2026-08-01T10:00:00Z"]
    recent["primaryDocument"] = ["notice.htm"]
    assert select_form4_filings(empty, WINDOW) == ()


def test_form4_selector_ignores_blank_dates_on_nonselected_forms():
    submissions = _submissions()
    recent = submissions["filings"]["recent"]
    recent["filingDate"][2] = ""
    recent["reportDate"][2] = ""

    assert [row.accession_number for row in select_form4_filings(submissions, WINDOW)] == [
        "0001067983-26-000002",
        "0001067983-26-000003",
    ]


def test_form4_selector_rejects_invalid_selected_report_date():
    submissions = _submissions()
    submissions["filings"]["recent"]["reportDate"][1] = "2026-02-30"

    with pytest.raises(SchemaError, match="report date"):
        select_form4_filings(submissions, WINDOW)


def test_form4_raw_locator_strips_verified_xsl_presentation_prefix():
    assert derive_form4_xml_url(
        "0001067983", "0001067983-26-000002", "xslF345X06/primary_doc.xml"
    ) == ("https://www.sec.gov/Archives/edgar/data/0001067983/000106798326000002/primary_doc.xml")


def test_form4_parser_binds_source_url_and_observed_xml_shape_to_the_selected_document():
    candidate = next(
        row
        for row in select_form4_filings(_submissions(), WINDOW)
        if row.accession_number == "0001067983-26-000002"
    )
    source_url = derive_form4_xml_url(
        candidate.issuer_cik, candidate.accession_number, candidate.primary_document
    )
    body = (FIXTURES / "mixed.xml").read_bytes()
    with pytest.raises(SchemaError, match="source URL"):
        parse_form4_document(body, candidate, source_url=source_url.replace(".xml", ".txt"))
    with pytest.raises(SchemaError, match="namespace"):
        parse_form4_document(
            body.replace(
                b"<ownershipDocument>",
                b'<ownershipDocument xmlns="http://www.sec.gov/ownership">',
                1,
            ),
            candidate,
            source_url=source_url,
        )
    with pytest.raises(SchemaError, match="ISO date"):
        parse_form4_document(
            body.replace(b"2026-08-09", b"2026-02-30", 1),
            candidate,
            source_url=source_url,
        )
    with pytest.raises(SchemaError, match="attributes"):
        parse_form4_document(
            body.replace(b"<issuer>", b'<issuer unrecognized="value">', 1),
            candidate,
            source_url=source_url,
        )
    with pytest.raises(SchemaError, match="reportingOwnerAddress contains unsupported"):
        parse_form4_document(
            body.replace(
                b"</reportingOwnerAddress>",
                b"<unrecognized/></reportingOwnerAddress>",
                1,
            ),
            candidate,
            source_url=source_url,
        )


def _parse(accession: str, form: str):
    candidate = next(
        row
        for row in select_form4_filings(_submissions(), WINDOW)
        if row.accession_number == accession
    )
    path = FIXTURES / ("amendment.xml" if form == "4/A" else "mixed.xml")
    return parse_form4_document(
        path.read_bytes(),
        candidate,
        source_url=derive_form4_xml_url(
            candidate.issuer_cik, candidate.accession_number, candidate.primary_document
        ),
    )


def test_mixed_form4_retains_owner_order_table_order_and_typed_branches():
    normalized = _parse("0001067983-26-000002", "4")
    payload = normalized.payload
    assert [owner["cik"] for owner in payload["reporting_owners"]] == [
        "0000000001",
        "0000000002",
    ]
    assert [entry["entry_kind"] for entry in payload["non_derivative_entries"]] == [
        "transaction",
        "holding",
    ]
    assert [entry["entry_kind"] for entry in payload["derivative_entries"]] == [
        "transaction",
        "holding",
    ]
    assert payload["non_derivative_entries"][0]["transaction_amount"]["branch"] == "shares"
    assert payload["non_derivative_entries"][1]["post_transaction_amount"]["branch"] == "value"
    assert payload["derivative_entries"][0]["underlying_security"]["amount"]["branch"] == "shares"
    assert [note["id"] for note in payload["footnotes"]] == ["F1", "F2"]
    assert payload["non_derivative_entries"][0]["transaction_amount"]["shares"]["value"] == "100.5"
    assert payload["non_derivative_entries"][0]["price_per_share"] == {
        "value": None,
        "unit": "usd_per_share",
        "footnote_ids": ["F1"],
    }
    assert "owner_signature" not in payload


def test_form4_amendment_is_an_independent_event_without_lineage():
    payload = _parse("0001067983-26-000003", "4/A").payload
    assert payload["is_amendment"] is True
    assert payload["date_of_original_submission"] == "2026-08-08"
    assert "amends_accession" not in payload


def test_form4_numeric_projection_is_ambient_decimal_context_independent():
    first = _parse("0001067983-26-000002", "4").payload
    with localcontext() as context:
        context.prec = 6
        context.rounding = ROUND_DOWN
        second = _parse("0001067983-26-000002", "4").payload
    with localcontext() as context:
        context.prec = 28
        context.rounding = ROUND_HALF_EVEN
        third = _parse("0001067983-26-000002", "4").payload
    assert canonical_bytes(first) == canonical_bytes(second) == canonical_bytes(third)


class _Response:
    def __init__(self, body: bytes, url: str):
        self.body_bytes = body
        self.content = body
        self.status_code = 200
        self.url = url
        self.headers: dict[str, str] = {}


class _Form4Client:
    def __init__(self, submissions: bytes, documents: dict[str, bytes]):
        self.submissions = submissions
        self.documents = documents
        self.requests: list[str] = []

    def get(self, url: str, **_kwargs):
        self.requests.append(url)
        if "/submissions/" in url:
            return _Response(self.submissions, url)
        return _Response(self.documents[url.rsplit("/", 1)[-1]], url)


def _v3_form4_feed(accession: str = "0001067983-26-000002", form: str = "4") -> dict:
    normalized = _parse(accession, form)
    payload = normalized.payload
    item = {
        "id": stable_item_id("sec_edgar", payload["accession_number"]),
        "provider_id": "sec_edgar",
        "source": {
            "id": "form4-semantic-source",
            "name": "SEC EDGAR",
            "tier": "Tier 1",
            "kind": "filing",
            "url": normalized.source_url,
            "published_at": payload["accepted_at"],
            "knowledge_available_at": payload["accepted_at"],
        },
        "payload": payload,
    }
    feed = _feed([item])
    feed["feed_config"]["snapshot"]["watched_form4_issuers"] = [
        {"cik": "0001067983", "name": "Berkshire Hathaway"}
    ]
    contract = next(
        contract
        for contract in feed["provider_contracts"]
        if contract["provider_id"] == "sec_edgar"
    )
    contract["snapshot"].update(
        {
            "contract_version": 3,
            "units": {
                "13f_value_before_2023_01_03": "usd_thousands",
                "13f_value_from_2023_01_03": "usd",
                "reported_value_usd_thousands": "usd_thousands",
            },
            "max_filings_per_window": 20,
            "ownership_xml_schema_versions": ["X0609"],
        }
    )
    contract["hash"] = canonical_digest(contract["snapshot"])
    outcome = next(
        outcome for outcome in feed["provider_outcomes"] if outcome["provider_id"] == "sec_edgar"
    )
    outcome["accepted"] = 1
    outcome["freshness"]["status"] = "fresh"
    outcome["freshness"]["origin_contract_hash"] = contract["hash"]
    feed["content_digest"], feed["run_id"] = recompute_feed_identity(feed)
    return feed


def test_form4_feed_semantics_are_bounded_to_window_url_owners_and_subtype():
    feed = _v3_form4_feed()
    validate_feed(feed)

    out_of_window = deepcopy(feed)
    out_of_window["items"][0]["payload"]["accepted_at"] = "2026-08-07T00:00:00.000Z"
    out_of_window["items"][0]["source"]["published_at"] = "2026-08-07T00:00:00.000Z"
    out_of_window["items"][0]["source"]["knowledge_available_at"] = "2026-08-07T00:00:00.000Z"
    with pytest.raises(SchemaError, match="acceptance time"):
        validate_feed(out_of_window)

    bad_url = deepcopy(feed)
    bad_url["items"][0]["source"]["url"] = bad_url["items"][0]["source"]["url"].replace(
        ".xml", ".txt"
    )
    with pytest.raises(SchemaError, match="official raw XML URL"):
        validate_feed(bad_url)

    wrong_accession_url = deepcopy(feed)
    wrong_accession_url["items"][0]["source"]["url"] = wrong_accession_url["items"][0]["source"][
        "url"
    ].replace("000106798326000002", "000106798326999999")
    with pytest.raises(SchemaError, match="official raw XML URL"):
        validate_feed(wrong_accession_url)

    wrong_item_id = deepcopy(feed)
    wrong_item_id["items"][0]["id"] = "other-item"
    with pytest.raises(SchemaError, match="item identity"):
        validate_feed(wrong_item_id)

    invalid_report_period = deepcopy(feed)
    invalid_report_period["items"][0]["payload"]["report_period"] = "2026-02-30"
    with pytest.raises(SchemaError, match="report_period.*date"):
        validate_feed(invalid_report_period)

    invalid_transaction_date = deepcopy(feed)
    invalid_transaction_date["items"][0]["payload"]["non_derivative_entries"][0][
        "transaction_date"
    ] = "2026-02-30"
    with pytest.raises(SchemaError, match="transaction_date.*date"):
        validate_feed(invalid_transaction_date)

    amendment = _v3_form4_feed("0001067983-26-000003", "4/A")
    validate_feed(amendment)
    invalid_original_submission_date = deepcopy(amendment)
    invalid_original_submission_date["items"][0]["payload"]["date_of_original_submission"] = (
        "2026-02-30"
    )
    with pytest.raises(SchemaError, match="date_of_original_submission.*date"):
        validate_feed(invalid_original_submission_date)

    forbidden = deepcopy(feed)
    forbidden["items"][0]["payload"]["amendment_effectiveness"] = "effective"
    with pytest.raises(SchemaError):
        validate_feed(forbidden)


def test_sec_v3_complete_slice_rejects_missing_watched_13f_items():
    feed = _v3_form4_feed()
    feed["items"] = []
    feed["feed_config"]["snapshot"]["watched_companies"] = [
        {"cik": "0000000001", "name": "Required 13F manager", "tickers": []}
    ]
    outcome = next(
        outcome for outcome in feed["provider_outcomes"] if outcome["provider_id"] == "sec_edgar"
    )
    outcome.update({"state": "empty", "accepted": 0, "empty": True})
    outcome["freshness"].update({"status": "no_snapshot", "origin_contract_hash": None})
    feed["content_digest"], feed["run_id"] = recompute_feed_identity(feed)

    with pytest.raises(SchemaError, match="complete slice"):
        validate_feed(feed)


@pytest.mark.parametrize(
    "forbidden_key",
    (
        "signal",
        "bullish",
        "bearish",
        "sentiment",
        "confidence",
        "importance",
        "recommendation",
        "holding_delta",
        "calculated_transaction_value",
        "generic_fact",
        "amendment_effectiveness",
    ),
)
def test_form4_payload_rejects_analysis_and_generic_fact_fields(forbidden_key: str):
    feed = _v3_form4_feed()
    feed["items"][0]["payload"][forbidden_key] = True
    with pytest.raises(SchemaError):
        validate_feed(feed)


def test_end_to_end_v3_fixture_feed_combines_13f_and_form4_deterministically(tmp_path):
    from follow_the_money.feed.bundle import artifact_relative_path
    from tests.test_cftc_activation import CUTOFF_1, _fixture_registry, run_feed

    def registry_with_form4():
        registry = _fixture_registry()
        config = load_config(
            ROOT / "config" / "config.yaml",
            ROOT / "config" / "providers.yaml",
            manifest_root=ROOT / "providers",
            require_verified_enabled=True,
        )
        issuer = config.watched_form4_issuers[0]
        adapter = SecForm4Adapter(
            next(provider for provider in config.providers if provider.id == "sec_edgar"),
            watched_issuer=issuer,
        )
        fixture_root = FIXTURES

        class FixtureClient:
            def get(self, url, **_kwargs):
                filename = "submissions.json" if "/submissions/" in url else Path(url).name
                filename = "mixed.xml" if filename == "primary_doc.xml" else filename
                body = (fixture_root / filename).read_bytes()
                return SimpleNamespace(
                    body_bytes=body,
                    content=body,
                    status_code=200,
                    headers={},
                    url=url,
                )

        class FixtureForm4:
            provider_id = "sec_edgar"

            @property
            def selected_accessions(self):
                return adapter.selected_accessions

            @property
            def selection_complete(self):
                return adapter.selection_complete

            def fetch(self, window, client=None):
                return adapter.fetch(window, FixtureClient())

            def normalize(self, raw, window):
                return adapter.normalize(raw, window)

        registry["sec_edgar"].append(FixtureForm4())
        return registry

    def run_fixture(root):
        return run_feed(
            output_root=str(root / "out"),
            runtime_state_root=str(root / "state"),
            cutoff=CUTOFF_1,
            providers_fn=registry_with_form4,
        )

    first = run_fixture(tmp_path / "first")
    second = run_fixture(tmp_path / "second")
    assert first.exit_code == second.exit_code == 0
    assert first.status == second.status == "healthy"
    assert first.feed is not None and second.feed is not None
    assert first.feed["run_id"] == second.feed["run_id"]
    assert first.feed["content_digest"] == second.feed["content_digest"]
    first_sec = [item for item in first.feed["items"] if item["provider_id"] == "sec_edgar"]
    assert len(first_sec) == 10
    assert [item["payload"]["filing_subtype"] for item in first_sec] == [
        "form13f",
    ] * 8 + ["form4", "form4"]
    first_artifact = (
        tmp_path / "first" / "out" / artifact_relative_path("filing", first.feed["run_id"])
    ).read_bytes()
    second_artifact = (
        tmp_path / "second" / "out" / artifact_relative_path("filing", second.feed["run_id"])
    ).read_bytes()
    assert first_artifact == second_artifact


def test_form4_adapter_performs_listing_then_every_selected_raw_xml_request():
    manifest = dict(load_manifest("sec_edgar"))
    manifest["contract_version"] = 3
    manifest["form4"] = {
        "max_filings_per_window": 20,
        "ownership_xml_schema_versions": ["X0609"],
    }
    entry = manifest_to_provider_entry(manifest)
    candidates = select_form4_filings(_submissions(), WINDOW)
    documents = {
        "primary_doc.xml": (FIXTURES / "mixed.xml").read_bytes(),
        "amendment.xml": (FIXTURES / "amendment.xml").read_bytes(),
    }
    client = _Form4Client((FIXTURES / "submissions.json").read_bytes(), documents)
    adapter = SecForm4Adapter(entry, watched_cik="0001067983")
    items = adapter.normalize(adapter.fetch(WINDOW, client), WINDOW)
    assert len(client.requests) == 1 + len(candidates)
    assert client.requests[0].endswith("CIK0001067983.json")
    assert [item["payload"]["accession_number"] for item in items] == [
        row.accession_number for row in candidates
    ]
    assert adapter.selection_complete is True
    assert adapter.selected_accessions == tuple(row.accession_number for row in candidates)
    assert all(item["source"]["url"].endswith(".xml") for item in items)
