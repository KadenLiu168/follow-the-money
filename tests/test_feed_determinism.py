"""Deterministic identity and normalization regressions for the Feed."""

from __future__ import annotations

from copy import deepcopy
from datetime import timedelta
from decimal import ROUND_DOWN, ROUND_HALF_EVEN, Inexact, localcontext

from follow_the_money.canonical import canonical_bytes
from follow_the_money.config.model import WatchCompany
from follow_the_money.feed.dedupe import deduplicate_items, deterministic_item_order
from follow_the_money.feed.validate import recompute_feed_identity, semantic_feed_projection
from follow_the_money.providers.adapters import CftcAdapter, SecEdgarAdapter
from tests.test_cftc_cot import row
from tests.test_feed_bundle import T0, _feed, _news
from tests.test_sec_13f import FilingCandidate, candidate, xml


def test_item_order_and_deduplication_are_permutation_stable():
    first = _news("item-a", T0 - timedelta(hours=2))
    second = _news("item-b", T0 - timedelta(hours=1))
    second["source"]["url"] = first["source"]["url"]
    items_a, dropped_a = deduplicate_items([first, second])
    items_b, dropped_b = deduplicate_items([second, first])
    assert items_a == items_b
    assert dropped_a == dropped_b
    assert [item["id"] for item in deterministic_item_order(items_a)] == ["item-a"]


def test_execution_observations_do_not_change_semantic_identity():
    feed = _feed([_news()])
    digest, run_id = recompute_feed_identity(feed)
    changed = deepcopy(feed)
    changed["collection_started_at"] = "2026-08-11T00:19:00.000Z"
    changed["collection_completed_at"] = "2026-08-11T00:25:00.000Z"
    changed["generated_at"] = "2026-08-11T00:26:00.000Z"
    changed["provider_outcomes"][0]["retrieved_at"] = "2026-08-11T00:24:00.000Z"
    assert recompute_feed_identity(changed) == (digest, run_id)
    assert semantic_feed_projection(changed) == semantic_feed_projection(feed)


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

    def with_header(body: bytes, filing: FilingCandidate) -> bytes:
        header = (
            "<SEC-DOCUMENT>\n<HEADER>\n"
            "CENTRAL INDEX KEY: 0000000001\n"
            f"ACCESSION NUMBER: {filing.accession_number}\n"
            "CONFORMED SUBMISSION TYPE: 13F-HR\n"
            f"FILED AS OF DATE: {filing.filing_date.replace('-', '')}\n"
            "</HEADER>\n"
        ).encode()
        return header + body + b"</SEC-DOCUMENT>"

    return {
        "submissions": {"cik": "0000000001", "name": "Example Manager", "tickers": ["EXM"]},
        "current": current,
        "current_url": "https://www.sec.gov/Archives/edgar/data/0000000001/current.txt",
        "current_body": with_header(
            xml(
                [
                    {"cusip": "111111111", "amount": "12", "value": "90000", "issuer": "Alpha"},
                    {"cusip": "333333333", "amount": "3", "value": "30000", "issuer": "Gamma"},
                ],
                header=False,
            ),
            current,
        ),
        "previous": previous,
        "previous_url": "https://www.sec.gov/Archives/edgar/data/0000000001/previous.txt",
        "previous_body": with_header(
            xml(
                [
                    {"cusip": "111111111", "amount": "10", "value": "80000", "issuer": "Alpha"},
                    {"cusip": "222222222", "amount": "7", "value": "70000", "issuer": "Beta"},
                ],
                header=False,
            ),
            previous,
        ),
    }


def _sec_cftc_items():
    sec_item = SecEdgarAdapter(
        watched_company=WatchCompany("0000000001", "Configured Name", ("CFG",))
    ).normalize(_sec_raw(), {})[0]
    cftc_items = CftcAdapter().normalize(
        {
            "current_date": "2026-08-04",
            "previous_date": "2026-07-28",
            "current_rows": [row("2026-08-04", "001", "X", long="12", short="5")],
            "previous_rows": [row("2026-07-28", "001", "X", long="10", short="4")],
        },
        {},
    )
    return [sec_item, *cftc_items]


def test_sec_cftc_provider_and_feed_identity_ignore_ambient_decimal_context():
    with localcontext() as context:
        context.prec = 28
        context.rounding = ROUND_HALF_EVEN
        context.clear_flags()
        context.traps[Inexact] = False
        expected_items = _sec_cftc_items()
        expected_item_bytes = canonical_bytes(expected_items)
        expected_feed = _feed(expected_items)
        expected_identity = recompute_feed_identity(expected_feed)

    options: tuple[tuple[int, str, bool, bool], ...] = (
        (6, ROUND_DOWN, True, False),
        (28, ROUND_DOWN, False, True),
        (6, ROUND_HALF_EVEN, False, False),
    )
    for precision, rounding, flag_inexact, trap_inexact in options:
        with localcontext() as context:
            context.prec = precision
            context.rounding = rounding
            context.clear_flags()
            context.flags[Inexact] = flag_inexact
            context.traps[Inexact] = trap_inexact
            items = _sec_cftc_items()
            feed = _feed(items)
            assert items == expected_items
            assert canonical_bytes(items) == expected_item_bytes
            assert recompute_feed_identity(feed) == expected_identity
            assert (feed["content_digest"], feed["run_id"]) == expected_identity

    changed = deepcopy(expected_feed)
    changed["items"][0]["payload"]["report_period"] = "2022-12-30"
    assert recompute_feed_identity(changed) != expected_identity


def test_semantic_evidence_change_changes_identity():
    feed = _feed([_news()])
    changed = deepcopy(feed)
    changed["items"][0]["payload"]["title"] = "different title"
    assert recompute_feed_identity(changed) != recompute_feed_identity(feed)
