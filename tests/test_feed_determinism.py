"""Deterministic identity and normalization regressions for the Feed."""

from __future__ import annotations

from copy import deepcopy
from datetime import timedelta

from follow_the_money.feed.dedupe import deduplicate_items, deterministic_item_order
from follow_the_money.feed.validate import recompute_feed_identity, semantic_feed_projection
from tests.test_feed_bundle import T0, _feed, _news


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


def test_semantic_evidence_change_changes_identity():
    feed = _feed([_news()])
    changed = deepcopy(feed)
    changed["items"][0]["payload"]["title"] = "different title"
    assert recompute_feed_identity(changed) != recompute_feed_identity(feed)
