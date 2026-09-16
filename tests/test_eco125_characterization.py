"""ECO-125 pre-migration payload and canonical-byte characterization tests."""

from __future__ import annotations

import ast
from pathlib import Path

from follow_the_money.canonical import canonical_bytes
from follow_the_money.config.model import WatchCompany
from follow_the_money.providers.adapters import CftcAdapter, SecEdgarAdapter
from follow_the_money.providers.manifest import load_manifest
from follow_the_money.providers.sec_13f import FilingCandidate
from tests.test_cftc_cot import row
from tests.test_sec_13f import candidate, xml


def _with_submission_header(body: bytes, filing: FilingCandidate) -> bytes:
    accession = filing.accession_number
    filed = filing.filing_date.replace("-", "")
    header = (
        "<SEC-DOCUMENT>\n<HEADER>\n"
        "CENTRAL INDEX KEY: 0000000001\n"
        f"ACCESSION NUMBER: {accession}\n"
        "CONFORMED SUBMISSION TYPE: 13F-HR\n"
        f"FILED AS OF DATE: {filed}\n"
        "</HEADER>\n"
    ).encode()
    return header + body.replace(b"<XML>", b"<XML>", 1) + b"</SEC-DOCUMENT>"


def _sec_raw() -> dict[str, object]:
    current = candidate(
        accession="0000000001-23-000010",
        filed="2023-02-01",
        report="2022-12-31",
        accepted="2023-02-02T12:00:00Z",
    )
    previous = candidate(
        accession="0000000001-23-000009",
        filed="2023-01-04",
        report="2022-09-30",
        accepted="2023-01-05T12:00:00Z",
    )
    return {
        "submissions": {"cik": "0000000001", "name": "Example Manager", "tickers": ["EXM"]},
        "current": current,
        "current_url": "https://www.sec.gov/Archives/edgar/data/0000000001/current.txt",
        "current_body": _with_submission_header(
            xml(
                [
                    {
                        "cusip": "111111111",
                        "amount": "12",
                        "value": "90000",
                        "issuer": "Alpha",
                        "title": "Common",
                    },
                    {
                        "cusip": "333333333",
                        "amount": "3",
                        "value": "30000",
                        "issuer": "Gamma",
                        "title": "Common",
                    },
                ],
                header=False,
            ),
            current,
        ),
        "previous": previous,
        "previous_url": "https://www.sec.gov/Archives/edgar/data/0000000001/previous.txt",
        "previous_body": _with_submission_header(
            xml(
                [
                    {
                        "cusip": "111111111",
                        "amount": "10",
                        "value": "80000",
                        "issuer": "Alpha",
                        "title": "Common",
                    },
                    {
                        "cusip": "222222222",
                        "amount": "7",
                        "value": "70000",
                        "issuer": "Beta",
                        "title": "Common",
                    },
                ],
                header=False,
            ),
            previous,
        ),
    }


def _v2_sec_adapter() -> SecEdgarAdapter:
    manifest = dict(load_manifest("sec_edgar"))
    manifest["contract_version"] = 2
    return SecEdgarAdapter(
        manifest,
        watched_company=WatchCompany("0000000001", "Configured Name", ("CFG",)),
    )


def test_sec_v2_payload_and_canonical_bytes_are_pinned_before_migration():
    item = _v2_sec_adapter().normalize(_sec_raw(), {})[0]

    assert item["payload"] == {
        "type": "filing",
        "form": "13F-HR",
        "company": "0000000001",
        "accession_number": "0000000001-23-000010",
        "filed_at": "2023-02-01T00:00:00.000Z",
        "raw_metadata": {},
        "company_identity": {"cik": "0000000001", "name": "Example Manager", "tickers": ["EXM"]},
        "report_period": "2022-12-31",
        "accepted_at": "2023-02-02T12:00:00Z",
        "value_normalization": {"source_unit": "usd", "formula_id": "usd_divided_by_1000"},
        "comparison": {
            "status": "available",
            "previous_accession_number": "0000000001-23-000009",
            "previous_report_period": "2022-09-30",
            "previous_accepted_at": "2023-01-05T12:00:00Z",
            "previous_filed_at": "2023-01-04T00:00:00.000Z",
            "previous_source_url": "https://www.sec.gov/Archives/edgar/data/0000000001/previous.txt",
            "previous_value_normalization": {
                "source_unit": "usd",
                "formula_id": "usd_divided_by_1000",
            },
            "reason": None,
        },
        "holdings": [
            {
                "security": {
                    "cusip": "111111111",
                    "figi": None,
                    "issuer_name": "Alpha",
                    "title_of_class": "Common",
                    "put_call": None,
                    "amount_type": "SH",
                },
                "current": {
                    "reported_amount": {"value": "12", "unit": "shares"},
                    "reported_value_usd_thousands": {"value": "90", "unit": "usd_thousands"},
                },
                "previous": {
                    "reported_amount": {"value": "10", "unit": "shares"},
                    "reported_value_usd_thousands": {"value": "80", "unit": "usd_thousands"},
                },
                "delta": {
                    "reported_amount": {"value": "2", "unit": "shares"},
                    "reported_value_usd_thousands": {"value": "10", "unit": "usd_thousands"},
                },
                "change_type": "increased",
            },
            {
                "security": {
                    "cusip": "222222222",
                    "figi": None,
                    "issuer_name": "Beta",
                    "title_of_class": "Common",
                    "put_call": None,
                    "amount_type": "SH",
                },
                "current": None,
                "previous": {
                    "reported_amount": {"value": "7", "unit": "shares"},
                    "reported_value_usd_thousands": {"value": "70", "unit": "usd_thousands"},
                },
                "delta": None,
                "change_type": "no_longer_reported",
            },
            {
                "security": {
                    "cusip": "333333333",
                    "figi": None,
                    "issuer_name": "Gamma",
                    "title_of_class": "Common",
                    "put_call": None,
                    "amount_type": "SH",
                },
                "current": {
                    "reported_amount": {"value": "3", "unit": "shares"},
                    "reported_value_usd_thousands": {"value": "30", "unit": "usd_thousands"},
                },
                "previous": None,
                "delta": None,
                "change_type": "new",
            },
        ],
    }
    assert canonical_bytes(item) == (
        b'{"id":"item_c23c34679461f3c9fa5059f445582d6e","payload":{"accepted_at":"2023-02-02T12:00:00Z","accession_number":"0000000001-23-000010","company":"0000000001","company_identity":{"cik":"0000000001","name":"Example Manager","tickers":["EXM"]},"comparison":{"previous_accepted_at":"2023-01-05T12:00:00Z","previous_accession_number":"0000000001-23-000009","previous_filed_at":"2023-01-04T00:00:00.000Z","previous_report_period":"2022-09-30","previous_source_url":"https://www.sec.gov/Archives/edgar/data/0000000001/previous.txt","previous_value_normalization":{"formula_id":"usd_divided_by_1000","source_unit":"usd"},"reason":null,"status":"available"},"filed_at":"2023-02-01T00:00:00.000Z","form":"13F-HR","holdings":[{"change_type":"increased","current":{"reported_amount":{"unit":"shares","value":"12"},"reported_value_usd_thousands":{"unit":"usd_thousands","value":"90"}},"delta":{"reported_amount":{"unit":"shares","value":"2"},"reported_value_usd_thousands":{"unit":"usd_thousands","value":"10"}},"previous":{"reported_amount":{"unit":"shares","value":"10"},"reported_value_usd_thousands":{"unit":"usd_thousands","value":"80"}},"security":{"amount_type":"SH","cusip":"111111111","figi":null,"issuer_name":"Alpha","put_call":null,"title_of_class":"Common"}},{"change_type":"no_longer_reported","current":null,"delta":null,"previous":{"reported_amount":{"unit":"shares","value":"7"},"reported_value_usd_thousands":{"unit":"usd_thousands","value":"70"}},"security":{"amount_type":"SH","cusip":"222222222","figi":null,"issuer_name":"Beta","put_call":null,"title_of_class":"Common"}},{"change_type":"new","current":{"reported_amount":{"unit":"shares","value":"3"},"reported_value_usd_thousands":{"unit":"usd_thousands","value":"30"}},"delta":null,"previous":null,"security":{"amount_type":"SH","cusip":"333333333","figi":null,"issuer_name":"Gamma","put_call":null,"title_of_class":"Common"}}],"raw_metadata":{},"report_period":"2022-12-31","type":"filing","value_normalization":{"formula_id":"usd_divided_by_1000","source_unit":"usd"}},"provider_id":"sec_edgar","source":{"id":"sec-item_c23c34679461f3c9fa5059f445582d6e","kind":"filing","knowledge_available_at":"2023-02-02T12:00:00.000Z","name":"SEC EDGAR","published_at":"2023-02-02T12:00:00.000Z","tier":"Tier 1","url":"https://www.sec.gov/Archives/edgar/data/0000000001/current.txt"}}'
    )


def test_cftc_v2_payloads_and_canonical_bytes_are_pinned_before_migration():
    current = [
        row("2026-08-04", "001", "X", long="12", short="5", spread="3", oi="110"),
        row("2026-08-04", "003", "Z", long="8", short="2", spread="1", oi="90"),
    ]
    previous = [
        row("2026-07-28", "001", "X", long="10", short="4", spread="2", oi="100"),
        row("2026-07-28", "002", "Y", long="7", short="3", spread="1", oi="80"),
    ]
    items = CftcAdapter().normalize(
        {
            "current_date": "2026-08-04",
            "previous_date": "2026-07-28",
            "current_rows": current,
            "previous_rows": previous,
        },
        {},
    )

    assert [item["payload"] for item in items] == [
        {
            "type": "positioning",
            "instrument_id": "X",
            "as_of": "2026-08-04T00:00:00.000Z",
            "position": {"value": "12", "unit": "contracts"},
            "raw_metadata": {},
            "market_identity": {"cftc_contract_market_code": "001", "contract_market_name": "X"},
            "current_metrics": {
                "noncommercial_long": {"value": "12", "unit": "contracts"},
                "noncommercial_short": {"value": "5", "unit": "contracts"},
                "noncommercial_spreading": {"value": "3", "unit": "contracts"},
                "open_interest": {"value": "110", "unit": "contracts"},
                "net_noncommercial": {"value": "7", "unit": "contracts"},
            },
            "previous_metrics": {
                "noncommercial_long": {"value": "10", "unit": "contracts"},
                "noncommercial_short": {"value": "4", "unit": "contracts"},
                "noncommercial_spreading": {"value": "2", "unit": "contracts"},
                "open_interest": {"value": "100", "unit": "contracts"},
                "net_noncommercial": {"value": "6", "unit": "contracts"},
            },
            "delta_metrics": {
                "noncommercial_long": {"value": "2", "unit": "contracts"},
                "noncommercial_short": {"value": "1", "unit": "contracts"},
                "noncommercial_spreading": {"value": "1", "unit": "contracts"},
                "open_interest": {"value": "10", "unit": "contracts"},
                "net_noncommercial": {"value": "1", "unit": "contracts"},
            },
            "comparison": {
                "status": "available",
                "previous_as_of": "2026-07-28T00:00:00.000Z",
                "reason": None,
            },
            "derivations": {"net_noncommercial": {"formula_id": "noncommercial_long_minus_short"}},
        },
        {
            "type": "positioning",
            "instrument_id": "Z",
            "as_of": "2026-08-04T00:00:00.000Z",
            "position": {"value": "8", "unit": "contracts"},
            "raw_metadata": {},
            "market_identity": {"cftc_contract_market_code": "003", "contract_market_name": "Z"},
            "current_metrics": {
                "noncommercial_long": {"value": "8", "unit": "contracts"},
                "noncommercial_short": {"value": "2", "unit": "contracts"},
                "noncommercial_spreading": {"value": "1", "unit": "contracts"},
                "open_interest": {"value": "90", "unit": "contracts"},
                "net_noncommercial": {"value": "6", "unit": "contracts"},
            },
            "previous_metrics": None,
            "delta_metrics": None,
            "comparison": {
                "status": "unavailable",
                "previous_as_of": "2026-07-28T00:00:00.000Z",
                "reason": "market_absent_from_previous_report",
            },
            "derivations": {"net_noncommercial": {"formula_id": "noncommercial_long_minus_short"}},
        },
    ]
    assert canonical_bytes(items) == (
        b'[{"id":"item_36c7b8af71aea9756df30280482b8b7d","payload":{"as_of":"2026-08-04T00:00:00.000Z","comparison":{"previous_as_of":"2026-07-28T00:00:00.000Z","reason":null,"status":"available"},"current_metrics":{"net_noncommercial":{"unit":"contracts","value":"7"},"noncommercial_long":{"unit":"contracts","value":"12"},"noncommercial_short":{"unit":"contracts","value":"5"},"noncommercial_spreading":{"unit":"contracts","value":"3"},"open_interest":{"unit":"contracts","value":"110"}},"delta_metrics":{"net_noncommercial":{"unit":"contracts","value":"1"},"noncommercial_long":{"unit":"contracts","value":"2"},"noncommercial_short":{"unit":"contracts","value":"1"},"noncommercial_spreading":{"unit":"contracts","value":"1"},"open_interest":{"unit":"contracts","value":"10"}},"derivations":{"net_noncommercial":{"formula_id":"noncommercial_long_minus_short"}},"instrument_id":"X","market_identity":{"cftc_contract_market_code":"001","contract_market_name":"X"},"position":{"unit":"contracts","value":"12"},"previous_metrics":{"net_noncommercial":{"unit":"contracts","value":"6"},"noncommercial_long":{"unit":"contracts","value":"10"},"noncommercial_short":{"unit":"contracts","value":"4"},"noncommercial_spreading":{"unit":"contracts","value":"2"},"open_interest":{"unit":"contracts","value":"100"}},"raw_metadata":{},"type":"positioning"},"provider_id":"cftc","source":{"id":"cftc-item_36c7b8af71aea9756df30280482b8b7d","kind":"positioning","knowledge_available_at":"2026-08-07T19:30:00.000Z","name":"CFTC Commitments of Traders","published_at":"2026-08-07T19:30:00.000Z","tier":"Tier 1","url":"https://publicreporting.cftc.gov/resource/6dca-aqww/2026-08-04-001.json"}},{"id":"item_0d421fc0057246003352f7deba183031","payload":{"as_of":"2026-08-04T00:00:00.000Z","comparison":{"previous_as_of":"2026-07-28T00:00:00.000Z","reason":"market_absent_from_previous_report","status":"unavailable"},"current_metrics":{"net_noncommercial":{"unit":"contracts","value":"6"},"noncommercial_long":{"unit":"contracts","value":"8"},"noncommercial_short":{"unit":"contracts","value":"2"},"noncommercial_spreading":{"unit":"contracts","value":"1"},"open_interest":{"unit":"contracts","value":"90"}},"delta_metrics":null,"derivations":{"net_noncommercial":{"formula_id":"noncommercial_long_minus_short"}},"instrument_id":"Z","market_identity":{"cftc_contract_market_code":"003","contract_market_name":"Z"},"position":{"unit":"contracts","value":"8"},"previous_metrics":null,"raw_metadata":{},"type":"positioning"},"provider_id":"cftc","source":{"id":"cftc-item_0d421fc0057246003352f7deba183031","kind":"positioning","knowledge_available_at":"2026-08-07T19:30:00.000Z","name":"CFTC Commitments of Traders","published_at":"2026-08-07T19:30:00.000Z","tier":"Tier 1","url":"https://publicreporting.cftc.gov/resource/6dca-aqww/2026-08-04-003.json"}}]'
    )


def test_closed_projection_and_semantic_import_surface():
    sec_item = _v2_sec_adapter().normalize(_sec_raw(), {})[0]
    cftc_item = CftcAdapter().normalize(
        {
            "current_date": "2026-08-04",
            "previous_date": None,
            "current_rows": [row("2026-08-04", "001", "X")],
            "previous_rows": None,
        },
        {},
    )[0]

    def keys(value: object) -> set[str]:
        if isinstance(value, dict):
            result = set(value)
            for child in value.values():
                result.update(keys(child))
            return result
        if isinstance(value, list):
            nested_keys: set[str] = set()
            for child in value:
                nested_keys.update(keys(child))
            return nested_keys
        return set()

    generic_fields = {"fact", "facts", "source_fields", "operation", "inputs", "provenance"}
    assert not generic_fields.intersection(keys(sec_item["payload"]))
    assert not generic_fields.intersection(keys(cftc_item["payload"]))

    semantic_root = Path(__file__).resolve().parents[1] / "src" / "follow_the_money" / "semantic"
    for path in semantic_root.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not {"config", "feed", "providers"}.intersection(node.module.split("."))
