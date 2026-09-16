"""Pure CFTC Legacy Futures-Only semantic tests."""

from __future__ import annotations

import json
from decimal import ROUND_DOWN, ROUND_HALF_EVEN, Inexact, localcontext
from pathlib import Path

import pytest

from follow_the_money.canonical import canonical_bytes
from follow_the_money.providers.cftc_cot import (
    compare_reports,
    normalize_report_rows,
    publication_boundary,
    select_report_dates,
)
from follow_the_money.schema import SchemaError

# Columns the Provider reads, as observed on the live Legacy Futures-Only
# dataset (see references/provider-source-verification.md). The spreading column
# is misspelled upstream, so the checked-in fixtures must reproduce that exact
# spelling.
OFFICIAL_COLUMNS = frozenset(
    {
        "id",
        "report_date_as_yyyy_mm_dd",
        "cftc_contract_market_code",
        "contract_market_name",
        "market_and_exchange_names",
        "open_interest_all",
        "noncomm_positions_long_all",
        "noncomm_positions_short_all",
        "noncomm_postions_spread_all",
    }
)


def row(date, code, name, long="10", short="4", spread="2", oi="100", stable=None):
    return {
        "id": stable or f"{date}-{code}",
        "report_date_as_yyyy_mm_dd": f"{date}T00:00:00.000",
        "cftc_contract_market_code": code,
        "contract_market_name": name,
        "noncomm_positions_long_all": long,
        "noncomm_positions_short_all": short,
        "noncomm_postions_spread_all": spread,
        "open_interest_all": oi,
    }


def test_numeric_fact_provenance_records_the_selected_cftc_source_fields():
    normalized = normalize_report_rows([row("2026-08-04", "001", "X", spread="7")], "2026-08-04")
    assert normalized["001"]["metrics"]["noncommercial_spreading"] == {
        "value": "7",
        "unit": "contracts",
    }
    assert normalized["001"]["_numeric_facts"]["noncommercial_spreading"].source_fields == (
        "noncomm_postions_spread_all",
    )

    renamed = row("2026-08-04", "002", "Y")
    renamed["noncommercial_long"] = renamed.pop("noncomm_positions_long_all")
    renamed["noncommercial_short"] = renamed.pop("noncomm_positions_short_all")
    renamed["noncommercial_spreading"] = renamed.pop("noncomm_postions_spread_all")
    renamed["open_interest"] = renamed.pop("open_interest_all")
    facts = normalize_report_rows([renamed], "2026-08-04")["002"]["_numeric_facts"]
    assert facts["noncommercial_long"].source_fields == ("noncommercial_long",)
    assert facts["noncommercial_short"].source_fields == ("noncommercial_short",)
    assert facts["noncommercial_spreading"].source_fields == ("noncommercial_spreading",)
    assert facts["open_interest"].source_fields == ("open_interest",)


def test_checked_in_fixtures_reproduce_the_official_row_shape():
    fixture_root = Path(__file__).resolve().parents[1] / "providers" / "cftc" / "fixtures"
    for name in ("cot.json", "cot-current.json", "cot-previous.json"):
        rows = json.loads((fixture_root / name).read_text(encoding="utf-8"))
        assert rows, name
        for fixture_row in rows:
            assert set(fixture_row).issubset(OFFICIAL_COLUMNS), name
            assert fixture_row["report_date_as_yyyy_mm_dd"].endswith("T00:00:00.000"), name


def test_missing_spreading_column_fails_closed():
    incomplete = row("2026-08-04", "001", "X")
    del incomplete["noncomm_postions_spread_all"]
    with pytest.raises(SchemaError, match="spreading"):
        normalize_report_rows([incomplete], "2026-08-04")


def test_report_selection_is_cutoff_aware_and_uses_distinct_dates():
    rows = [
        row("2026-08-04", "001", "X"),
        row("2026-08-11", "001", "X"),
        row("2026-08-18", "001", "X"),
    ]
    latest, previous = select_report_dates(rows, "2026-08-14T19:30:00Z")
    assert (latest, previous) == ("2026-08-04", None)
    assert publication_boundary("2026-08-04") == "2026-08-07T19:30:00.000Z"


def test_post_cutoff_publication_is_excluded_even_if_row_is_visible():
    rows = [row("2026-08-11", "001", "X")]
    with pytest.raises(SchemaError, match="no eligible"):
        select_report_dates(rows, "2026-08-14T19:30:00Z")


def test_code_matching_and_display_name_change_are_deterministic():
    previous = [row("2026-07-28", "001", "Old name")]
    current = [row("2026-08-04", "001", "New name")]
    result = compare_reports(
        current, previous, current_date="2026-08-04", previous_date="2026-07-28"
    )
    payload = result[0]["payload"]
    assert payload["market_identity"]["cftc_contract_market_code"] == "001"
    assert payload["comparison"]["status"] == "available"
    assert payload["comparison"]["previous_as_of"] == "2026-07-28T00:00:00.000Z"


def test_current_only_is_unavailable_and_previous_only_is_not_synthesized():
    previous = [row("2026-07-28", "001", "X"), row("2026-07-28", "002", "Y")]
    current = [row("2026-08-04", "001", "X"), row("2026-08-04", "003", "Z")]
    result = compare_reports(
        current, previous, current_date="2026-08-04", previous_date="2026-07-28"
    )
    assert [item["payload"]["market_identity"]["cftc_contract_market_code"] for item in result] == [
        "001",
        "003",
    ]
    assert result[1]["payload"]["comparison"]["status"] == "unavailable"
    assert result[1]["payload"]["previous_metrics"] is None


def test_input_row_order_does_not_change_output():
    current = [row("2026-08-04", "002", "Y"), row("2026-08-04", "001", "X")]
    previous = [row("2026-07-28", "001", "X"), row("2026-07-28", "002", "Y")]
    first = compare_reports(
        current, previous, current_date="2026-08-04", previous_date="2026-07-28"
    )
    second = compare_reports(
        list(reversed(current)),
        list(reversed(previous)),
        current_date="2026-08-04",
        previous_date="2026-07-28",
    )
    assert first == second


def test_150_market_complete_universe_is_order_independent():
    current = [row("2026-08-04", f"{index:03d}", f"Market {index}") for index in range(150)]
    previous = [row("2026-07-28", f"{index:03d}", f"Market {index}") for index in range(150)]

    normalized = normalize_report_rows(current, "2026-08-04")
    first = compare_reports(
        current, previous, current_date="2026-08-04", previous_date="2026-07-28"
    )
    second = compare_reports(
        list(reversed(current)),
        list(reversed(previous)),
        current_date="2026-08-04",
        previous_date="2026-07-28",
    )

    expected_codes = {f"{index:03d}" for index in range(150)}
    assert set(normalized) == expected_codes
    assert len(first) == 150
    assert {
        item["payload"]["market_identity"]["cftc_contract_market_code"] for item in first
    } == expected_codes
    assert canonical_bytes(first) == canonical_bytes(second)


def test_numeric_arithmetic_and_every_delta_are_typed_contracts():
    current = [row("2026-08-04", "001", "X", long="12", short="5", spread="3", oi="110")]
    previous = [row("2026-07-28", "001", "X", long="10", short="4", spread="2", oi="100")]
    payload = compare_reports(
        current, previous, current_date="2026-08-04", previous_date="2026-07-28"
    )[0]["payload"]
    assert payload["current_metrics"]["net_noncommercial"] == {"value": "7", "unit": "contracts"}
    assert payload["delta_metrics"]["noncommercial_long"] == {"value": "2", "unit": "contracts"}
    assert payload["delta_metrics"]["net_noncommercial"] == {"value": "1", "unit": "contracts"}
    assert (
        payload["derivations"]["net_noncommercial"]["formula_id"]
        == "noncommercial_long_minus_short"
    )


def test_internal_provenance_is_ordered_and_not_projected_to_cftc_payload():
    current_rows = [row("2026-08-04", "001", "X", long="12", short="5")]
    previous_rows = [row("2026-07-28", "001", "X", long="10", short="4")]
    current = normalize_report_rows(current_rows, "2026-08-04")
    previous = normalize_report_rows(previous_rows, "2026-07-28")
    item = compare_reports(
        current_rows,
        previous_rows,
        current_date="2026-08-04",
        previous_date="2026-07-28",
    )[0]
    payload = item["payload"]
    provenance = payload.__getattribute__("provenance")
    net = provenance["net_noncommercial"]
    assert net.derivation.operation == "subtract"
    assert net.derivation.inputs == (
        current["001"]["_numeric_facts"]["noncommercial_long"],
        current["001"]["_numeric_facts"]["noncommercial_short"],
    )
    net_delta = provenance["delta_metrics"]["net_noncommercial"]
    assert net_delta.derivation.inputs == (
        current["001"]["_numeric_facts"]["net_noncommercial"],
        previous["001"]["_numeric_facts"]["net_noncommercial"],
    )
    assert set(payload) == {
        "type",
        "instrument_id",
        "as_of",
        "position",
        "raw_metadata",
        "market_identity",
        "current_metrics",
        "previous_metrics",
        "delta_metrics",
        "comparison",
        "derivations",
    }
    assert not hasattr(net.derivation, "formula_id")


def test_duplicate_codes_and_numeric_failures_fail_closed():
    with pytest.raises(SchemaError, match="duplicate"):
        normalize_report_rows(
            [row("2026-08-04", "001", "X"), row("2026-08-04", "001", "Other")], "2026-08-04"
        )
    with pytest.raises(SchemaError, match="invalid"):
        normalize_report_rows([row("2026-08-04", "001", "X", long="not-number")], "2026-08-04")


def _contextual_cftc_comparison(
    *, precision: int, rounding: str, trap_inexact: bool, flag_inexact: bool
):
    current = [
        row(
            "2026-08-04",
            "001",
            "X",
            long="123456789.123456789",
            short="0.123456789",
            spread="3",
            oi="110",
        )
    ]
    previous = [
        row(
            "2026-07-28",
            "001",
            "X",
            long="123456789.023456789",
            short="0.023456789",
            spread="2",
            oi="100",
        )
    ]
    with localcontext() as context:
        context.prec = precision
        context.rounding = rounding
        context.clear_flags()
        context.flags[Inexact] = flag_inexact
        context.traps[Inexact] = trap_inexact
        return compare_reports(
            current,
            previous,
            current_date="2026-08-04",
            previous_date="2026-07-28",
        )


def test_cftc_numeric_output_is_independent_of_ambient_decimal_context():
    expected = _contextual_cftc_comparison(
        precision=28, rounding=ROUND_HALF_EVEN, trap_inexact=False, flag_inexact=False
    )
    options = (
        (28, ROUND_DOWN, True, True),
        (6, ROUND_DOWN, False, True),
        (6, ROUND_HALF_EVEN, False, False),
    )
    for precision, rounding, trap_inexact, flag_inexact in options:
        assert (
            _contextual_cftc_comparison(
                precision=precision,
                rounding=rounding,
                trap_inexact=trap_inexact,
                flag_inexact=flag_inexact,
            )
            == expected
        )


def test_directional_fields_are_not_part_of_the_pure_payload():
    payload = compare_reports([row("2026-08-04", "001", "X")], None, current_date="2026-08-04")[0][
        "payload"
    ]
    assert not {"bullish", "bearish", "signal", "score"}.intersection(payload)
