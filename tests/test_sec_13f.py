"""Pure SEC 13F-HR selection, parsing, normalization, and comparison tests."""

from __future__ import annotations

from decimal import ROUND_DOWN, ROUND_HALF_EVEN, Inexact, localcontext

import pytest

from follow_the_money.providers.sec_13f import (
    FilingCandidate,
    compare_holdings,
    parse_complete_submission,
    select_filings,
)
from follow_the_money.schema import SchemaError


def submissions(rows):
    fields: dict[str, list[object | None]] = {
        key: []
        for key in (
            "form",
            "filingDate",
            "reportDate",
            "accessionNumber",
            "acceptanceDateTime",
            "primaryDocument",
            "cik",
        )
    }
    for row in rows:
        for key, values in fields.items():
            values.append(row.get(key))
    return {
        "cik": "0000000001",
        "name": "Example Manager",
        "tickers": ["EXM"],
        "filings": {"recent": fields},
    }


def candidate(
    *,
    accession="0000000001-23-000001",
    filed="2023-01-03",
    report="2022-12-31",
    accepted="2023-01-04T12:00:00Z",
):
    return FilingCandidate(
        "0000000001", accession, "13F-HR", report, f"{filed}T00:00:00.000Z", accepted
    )


def xml(rows, *, header=True):
    values = []
    for row in rows:
        optional = f"<putCall>{row['put_call']}</putCall>" if row.get("put_call") else ""
        figi = f"<figi>{row['figi']}</figi>" if row.get("figi") else ""
        values.append(
            "<infoTable>"
            f"<nameOfIssuer>{row.get('issuer', 'Issuer')}</nameOfIssuer>"
            f"<titleOfClass>{row.get('title', 'Class')}</titleOfClass>"
            f"<cusip>{row['cusip']}</cusip>{figi}{optional}"
            f"<value>{row['value']}</value>"
            f"<shrsOrPrnAmt><sshPrnamt>{row['amount']}</sshPrnamt><sshPrnamtType>{row.get('amount_type', 'SH')}</sshPrnamtType></shrsOrPrnAmt>"
            "</infoTable>"
        )
    prefix = ""
    if header:
        prefix = """<SEC-DOCUMENT>\n<HEADER>\nCENTRAL INDEX KEY: 0000000001\nACCESSION NUMBER: 0000000001-23-000001\nCONFORMED SUBMISSION TYPE: 13F-HR\nFILED AS OF DATE: 20230103\n</HEADER>\n"""
        suffix = "</SEC-DOCUMENT>"
    else:
        suffix = ""
    return (
        prefix
        + '<XML><informationTable xmlns="http://www.sec.gov/edgar/thirteenffiler">'
        + "".join(values)
        + "</informationTable></XML>"
        + suffix
    ).encode()


def test_selection_uses_acceptance_cutoff_exact_form_and_distinct_report_period():
    raw = submissions(
        [
            {
                "form": "13F-HR",
                "filingDate": "2023-01-03",
                "reportDate": "2022-09-30",
                "accessionNumber": "0000000001-23-000001",
                "acceptanceDateTime": "2023-01-03T10:00:00Z",
                "primaryDocument": "a.txt",
                "cik": "0000000001",
            },
            {
                "form": "13F-HR/A",
                "filingDate": "2023-01-04",
                "reportDate": "2022-09-30",
                "accessionNumber": "0000000001-23-000002",
                "acceptanceDateTime": "2023-01-04T10:00:00Z",
                "primaryDocument": "amend.txt",
                "cik": "0000000001",
            },
            {
                "form": "13F-HR",
                "filingDate": "2023-04-01",
                "reportDate": "2022-12-31",
                "accessionNumber": "0000000001-23-000003",
                "acceptanceDateTime": "2023-04-01T10:00:00Z",
                "primaryDocument": "b.txt",
                "cik": "0000000001",
            },
            {
                "form": "13F-HR",
                "filingDate": "2023-07-01",
                "reportDate": "2023-03-31",
                "accessionNumber": "0000000001-23-000004",
                "acceptanceDateTime": "2023-07-01T10:00:00Z",
                "primaryDocument": "c.txt",
                "cik": "0000000001",
            },
        ]
    )
    current, previous = select_filings(raw, "2023-07-01T10:00:00Z")
    assert current.accession_number == "0000000001-23-000003"  # at cutoff is excluded
    assert previous is not None
    assert previous.accession_number == "0000000001-23-000001"


def test_selection_ignores_newer_amendment_after_exact_filing():
    raw = submissions(
        [
            {
                "form": "13F-HR",
                "filingDate": "2023-01-03",
                "reportDate": "2022-12-31",
                "accessionNumber": "0000000001-23-000001",
                "acceptanceDateTime": "2023-01-03T10:00:00Z",
                "primaryDocument": "exact.txt",
                "cik": "0000000001",
            },
            {
                "form": "13F-HR/A",
                "filingDate": "2023-01-04",
                "reportDate": "2022-12-31",
                "accessionNumber": "0000000001-23-000002",
                "acceptanceDateTime": "2023-01-04T10:00:00Z",
                "primaryDocument": "amendment.txt",
                "cik": "0000000001",
            },
        ]
    )

    current, previous = select_filings(raw, "2023-02-01T00:00:00Z")

    assert current.accession_number == "0000000001-23-000001"
    assert current.form == "13F-HR"
    assert previous is None


@pytest.mark.parametrize(
    "rows",
    [
        [
            {
                "form": "13F-HR",
                "filingDate": "2023-01-03",
                "reportDate": "2022-12-31",
                "accessionNumber": "0000000001-23-000001",
                "acceptanceDateTime": "2023-01-03T10:00:00Z",
                "primaryDocument": "exact.txt",
                "cik": "0000000001",
            },
            {
                "form": "13F-HR/A",
                "filingDate": "2023-01-04",
                "reportDate": "2022-12-31",
                "accessionNumber": "0000000001-23-000002",
                "acceptanceDateTime": "2023-01-04T10:00:00Z",
                "primaryDocument": "amendment.txt",
                "cik": "0000000001",
            },
        ],
        [
            {
                "form": "13F-HR/A",
                "filingDate": "2023-01-04",
                "reportDate": "2022-12-31",
                "accessionNumber": "0000000001-23-000002",
                "acceptanceDateTime": "2023-01-04T10:00:00Z",
                "primaryDocument": "amendment.txt",
                "cik": "0000000001",
            },
            {
                "form": "13F-HR",
                "filingDate": "2023-01-03",
                "reportDate": "2022-12-31",
                "accessionNumber": "0000000001-23-000001",
                "acceptanceDateTime": "2023-01-03T10:00:00Z",
                "primaryDocument": "exact.txt",
                "cik": "0000000001",
            },
        ],
    ],
)
def test_selection_exact_candidate_is_stable_for_input_permutations(rows):
    current, previous = select_filings(submissions(rows), "2023-02-01T00:00:00Z")

    assert current.accession_number == "0000000001-23-000001"
    assert current.form == "13F-HR"
    assert previous is None


def test_selection_amendment_only_fails_closed():
    with pytest.raises(SchemaError, match="no eligible exact SEC 13F-HR"):
        select_filings(
            submissions(
                [
                    {
                        "form": "13F-HR/A",
                        "filingDate": "2023-01-04",
                        "reportDate": "2022-12-31",
                        "accessionNumber": "0000000001-23-000002",
                        "acceptanceDateTime": "2023-01-04T10:00:00Z",
                        "primaryDocument": "amendment.txt",
                        "cik": "0000000001",
                    }
                ]
            ),
            "2023-02-01T00:00:00Z",
        )


def test_selection_can_have_no_previous_comparable_filing():
    raw = submissions(
        [
            {
                "form": "13F-HR",
                "filingDate": "2023-04-01",
                "reportDate": "2022-12-31",
                "accessionNumber": "0000000001-23-000003",
                "acceptanceDateTime": "2023-04-01T10:00:00Z",
                "primaryDocument": "b.txt",
                "cik": "0000000001",
            },
            {
                "form": "13F-HR",
                "filingDate": "2023-05-01",
                "reportDate": "2022-12-31",
                "accessionNumber": "0000000001-23-000004",
                "acceptanceDateTime": "2023-05-01T10:00:00Z",
                "primaryDocument": "c.txt",
                "cik": "0000000001",
            },
        ]
    )
    current, previous = select_filings(raw, "2023-06-01T00:00:00Z")
    assert current.accession_number.endswith("000004")
    assert previous is None


def test_information_table_aggregates_rows_and_normalizes_dollars_exactly():
    current = parse_complete_submission(
        xml(
            [
                {
                    "cusip": "037833100",
                    "amount": "1234",
                    "value": "1234567",
                    "issuer": "Zeta",
                    "title": "Common",
                    "figi": "BBG000BLNNH6",
                },
                {
                    "cusip": "037-833 100",
                    "amount": "6",
                    "value": "33",
                    "issuer": "Apple",
                    "title": "Common",
                },
            ]
        ),
        candidate(),
        source_url="https://www.sec.gov/Archives/edgar/data/0000000001/000000000123000001/0000000001-23-000001.txt",
    )
    assert current.value_normalization == {
        "source_unit": "usd",
        "formula_id": "usd_divided_by_1000",
    }
    assert current.holdings[0]["reported_amount"]["value"] == "1240"
    assert current.holdings[0]["reported_value_usd_thousands"]["value"] == "1234.6"
    assert current.holdings[0]["security"]["issuer_name"] == "Apple"
    assert current.holdings[0]["security"]["figi"] == "BBG000BLNNH6"


def test_pre_transition_and_boundary_use_filing_date_not_report_period():
    before = parse_complete_submission(
        xml([{"cusip": "037833100", "amount": "1", "value": "1234"}], header=False),
        candidate(filed="2023-01-02", report="2022-12-31"),
        source_url="https://www.sec.gov/a",
    )
    boundary = parse_complete_submission(
        xml([{"cusip": "037833100", "amount": "1", "value": "1234567"}], header=False),
        candidate(filed="2023-01-03", report="2022-12-31"),
        source_url="https://www.sec.gov/b",
    )
    assert before.holdings[0]["reported_value_usd_thousands"]["value"] == "1234"
    assert boundary.holdings[0]["reported_value_usd_thousands"]["value"] == "1234.567"


def test_conflicting_authority_and_ambiguous_or_malformed_tables_fail_closed():
    with pytest.raises(SchemaError, match="FILED AS OF DATE"):
        parse_complete_submission(
            xml([{"cusip": "037833100", "amount": "1", "value": "1"}]).replace(
                b"FILED AS OF DATE: 20230103", b"FILED AS OF DATE: 20230104"
            ),
            candidate(),
            source_url="https://www.sec.gov/a",
        )
    with pytest.raises(SchemaError, match="exactly one"):
        parse_complete_submission(
            b"<XML><informationTable><infoTable/></informationTable></XML><XML><informationTable><infoTable/></informationTable></XML>",
            candidate(),
            source_url="https://www.sec.gov/a",
        )
    with pytest.raises(SchemaError, match="malformed"):
        parse_complete_submission(
            b"<XML><informationTable><infoTable>", candidate(), source_url="https://www.sec.gov/a"
        )


def test_comparison_uses_amount_and_is_order_independent():
    previous = parse_complete_submission(
        xml(
            [
                {"cusip": "111111111", "amount": "10", "value": "100"},
                {"cusip": "222222222", "amount": "4", "value": "40"},
            ],
            header=False,
        ),
        candidate(
            accession="0000000001-22-000001",
            filed="2022-10-01",
            report="2022-06-30",
            accepted="2022-10-02T00:00:00Z",
        ),
        source_url="https://www.sec.gov/p",
    )
    current = parse_complete_submission(
        xml(
            [
                {"cusip": "222222222", "amount": "4", "value": "10"},
                {"cusip": "111111111", "amount": "12", "value": "90"},
                {"cusip": "333333333", "amount": "3", "value": "30"},
            ],
            header=False,
        ),
        candidate(
            accession="0000000001-23-000001",
            filed="2023-01-03",
            report="2022-12-31",
            accepted="2023-01-04T00:00:00Z",
        ),
        source_url="https://www.sec.gov/c",
    )
    rows = compare_holdings(current, previous)
    assert [row["security"]["cusip"] for row in rows] == ["111111111", "222222222", "333333333"]
    by_cusip = {row["security"]["cusip"]: row for row in rows}
    assert by_cusip["111111111"]["change_type"] == "increased"
    assert by_cusip["111111111"]["delta"]["reported_amount"]["value"] == "2"
    assert by_cusip["222222222"]["change_type"] == "unchanged"  # market value fell
    assert by_cusip["333333333"]["change_type"] == "new"
    assert by_cusip["333333333"]["previous"] is None

    matched = by_cusip["111111111"]
    derivations = matched.__getattribute__("derivations")
    current_facts = current.holdings[0]["_numeric_facts"]
    previous_facts = previous.holdings[0]["_numeric_facts"]
    assert derivations["reported_amount"].derivation.operation == "subtract"
    assert derivations["reported_amount"].derivation.inputs == (
        current_facts["reported_amount"],
        previous_facts["reported_amount"],
    )
    assert derivations["reported_value_usd_thousands"].derivation.inputs == (
        current_facts["reported_value_usd_thousands"],
        previous_facts["reported_value_usd_thousands"],
    )
    assert set(matched) == {"security", "current", "previous", "delta", "change_type"}


def test_no_previous_keeps_change_fields_null_and_previous_only_is_not_synthesized():
    filing = parse_complete_submission(
        xml([{"cusip": "037833100", "amount": "1", "value": "100"}]),
        candidate(),
        source_url="https://www.sec.gov/a",
    )
    row = compare_holdings(filing, None)[0]
    assert row["current"] is not None
    assert row["previous"] is None and row["delta"] is None and row["change_type"] is None


def _contextual_sec_comparison(
    *, precision: int, rounding: str, trap_inexact: bool, flag_inexact: bool
):
    with localcontext() as context:
        context.prec = precision
        context.rounding = rounding
        context.clear_flags()
        context.flags[Inexact] = flag_inexact
        context.traps[Inexact] = trap_inexact
        current = parse_complete_submission(
            xml(
                [
                    {
                        "cusip": "111111111",
                        "amount": "123456789012.345",
                        "value": "123456789012.345",
                    },
                    {"cusip": "111111111", "amount": "0.655", "value": "0.655"},
                ],
                header=False,
            ),
            candidate(accession="0000000001-23-current", filed="2023-02-01"),
            source_url="https://www.sec.gov/current",
        )
        previous = parse_complete_submission(
            xml(
                [{"cusip": "111111111", "amount": "123456789000", "value": "123456789000"}],
                header=False,
            ),
            candidate(
                accession="0000000001-23-previous",
                filed="2023-01-04",
                report="2022-09-30",
                accepted="2023-01-05T00:00:00Z",
            ),
            source_url="https://www.sec.gov/previous",
        )
        return compare_holdings(current, previous)


def test_sec_numeric_output_is_independent_of_ambient_decimal_context():
    expected = _contextual_sec_comparison(
        precision=28, rounding=ROUND_HALF_EVEN, trap_inexact=False, flag_inexact=False
    )
    options = (
        (28, ROUND_DOWN, True, True),
        (6, ROUND_DOWN, False, True),
        (6, ROUND_HALF_EVEN, False, False),
    )
    for precision, rounding, trap_inexact, flag_inexact in options:
        assert (
            _contextual_sec_comparison(
                precision=precision,
                rounding=rounding,
                trap_inexact=trap_inexact,
                flag_inexact=flag_inexact,
            )
            == expected
        )


def test_key_dimensions_and_conflicting_figi_are_conservative():
    filing = parse_complete_submission(
        xml(
            [
                {"cusip": "037833100", "amount": "1", "value": "1", "put_call": "PUT"},
                {"cusip": "037833100", "amount": "1", "value": "1", "put_call": "CALL"},
                {"cusip": "037833100", "amount": "1", "value": "1", "amount_type": "PRN"},
            ]
        ),
        candidate(),
        source_url="https://www.sec.gov/a",
    )
    assert len(filing.holdings) == 3
    with pytest.raises(SchemaError, match="conflicting FIGI"):
        parse_complete_submission(
            xml(
                [
                    {"cusip": "037833100", "amount": "1", "value": "1", "figi": "FIGI-A"},
                    {"cusip": "037833100", "amount": "1", "value": "1", "figi": "FIGI-B"},
                ]
            ),
            candidate(),
            source_url="https://www.sec.gov/a",
        )
