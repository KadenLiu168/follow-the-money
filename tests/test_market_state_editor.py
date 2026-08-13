from __future__ import annotations

import pytest

from follow_the_money.brief import BriefError, assemble_brief
from follow_the_money.editor import allocate_slots, merge_editor_output


def test_market_state_editor_wording_is_authoritative_explanation_only():
    market_state = {
        "regime": "risk_on",
        "vector": {
            "risk_appetite": "supportive",
            "rates": "supportive",
            "liquidity": "neutral",
            "growth": "supportive",
            "inflation": "neutral",
        },
        "missing_roles": ["btc"],
        "explanation": "",
        "evidence_cutoff_at": "2026-08-11T00:20:00Z",
        "evidence_ids": ["market-ev"],
    }
    aliases = {"e0": "market-ev"}
    slots = allocate_slots(
        market_state=market_state,
        full_events=[],
        compact_events=[],
        watchlist=[],
        bottom_line_owners=[],
        evidence_aliases=aliases,
    )
    merged = merge_editor_output(
        slots=slots,
        editor_output={
            "filled_slots": [
                {
                    "slot_alias": "s00",
                    "wording_fragment": "风险偏好与增长数据共同支持风险资产。",
                    "reference_aliases": ["e0"],
                }
            ]
        },
        full_events=[],
        compact_events=[],
        market_state=market_state,
        watchlist=[],
        alias_to_evidence=aliases,
    )
    brief = assemble_brief(
        brief_id="brief_state",
        brief_generated_at="2026-08-11T00:30:00Z",
        brief_completed_at="2026-08-11T00:30:00Z",
        evidence_cutoff_at="2026-08-11T00:20:00Z",
        feed_run_id="feed_state",
        editor_output={
            "filled_slots": [
                {
                    "slot_alias": "s00",
                    "wording_fragment": "风险偏好与增长数据共同支持风险资产。",
                    "reference_aliases": ["e0"],
                }
            ]
        },
        alias_to_evidence=aliases,
        slot_meta=merged["slot_meta"],
        dashboard=[],
        market_state=merged["market_state"],
        full_events=[],
        compact_events=[],
        money_flow_section=[],
        watchlist=[],
        bottom_line=[],
        provenance={"feed_digest": "a" * 64, "config_hash": "b" * 64, "prompt_fingerprints": {}},
    )
    assert brief["market_state"]["explanation"] == "风险偏好与增长数据共同支持风险资产。"
    state_claim = brief["claim_inventory"][0]
    assert state_claim["text"] == brief["market_state"]["explanation"]
    assert state_claim["is_factual"] is True
    assert state_claim["reference_evidence_ids"] == ["market-ev"]
    assert brief["market_state"]["regime"] == "risk_on"
    assert brief["market_state"]["missing_roles"] == ["btc"]


def test_market_state_aliases_are_bounded_and_do_not_renumber_event_aliases():
    event_aliases = {"e0": "event-ev"}
    state_aliases = {f"e{i + 1}": f"market-{i}" for i in range(10)}
    aliases = {**event_aliases, **state_aliases}
    slots = allocate_slots(
        market_state={"evidence_ids": [f"market-{i}" for i in range(10)]},
        full_events=[{"event_id": "evt", "evidence_ids": ["event-ev"]}],
        compact_events=[],
        watchlist=[],
        bottom_line_owners=[],
        evidence_aliases=aliases,
    )
    assert slots[0].exposed_aliases == tuple(f"e{i + 1}" for i in range(8))
    assert slots[1].exposed_aliases == ("e0",)
    assert aliases["e0"] == "event-ev"


def test_classified_market_state_explanation_rejects_unexposed_alias():
    market_state = {
        "regime": "risk_on",
        "evidence_ids": ["market-ev"],
    }
    aliases = {"e0": "market-ev", "e9": "event-ev"}
    slots = allocate_slots(
        market_state=market_state,
        full_events=[{"event_id": "evt", "evidence_ids": ["event-ev"]}],
        compact_events=[],
        watchlist=[],
        bottom_line_owners=[],
        evidence_aliases=aliases,
    )
    with pytest.raises(BriefError, match="non-exposed"):
        merge_editor_output(
            slots=slots,
            editor_output={
                "filled_slots": [
                    {
                        "slot_alias": "s00",
                        "wording_fragment": "风险偏好改善。",
                        "reference_aliases": ["e9"],
                    }
                ]
            },
            full_events=[],
            compact_events=[],
            market_state=market_state,
            watchlist=[],
            alias_to_evidence=aliases,
        )


def test_classified_market_state_explanation_without_reference_fails_closed():
    market_state = {
        "regime": "risk_on",
        "evidence_ids": ["market-ev"],
    }
    aliases = {"e0": "market-ev"}
    slots = allocate_slots(
        market_state=market_state,
        full_events=[],
        compact_events=[],
        watchlist=[],
        bottom_line_owners=[],
        evidence_aliases=aliases,
    )
    with pytest.raises(BriefError, match="requires at least one evidence reference"):
        merge_editor_output(
            slots=slots,
            editor_output={
                "filled_slots": [
                    {
                        "slot_alias": "s00",
                        "wording_fragment": "风险偏好改善。",
                        "reference_aliases": [],
                    }
                ]
            },
            full_events=[],
            compact_events=[],
            market_state=market_state,
            watchlist=[],
            alias_to_evidence=aliases,
        )


def test_unknown_market_state_explanation_may_have_no_reference():
    market_state = {"regime": "unknown", "evidence_ids": []}
    slots = allocate_slots(
        market_state=market_state,
        full_events=[],
        compact_events=[],
        watchlist=[],
        bottom_line_owners=[],
        evidence_aliases={},
    )
    merged = merge_editor_output(
        slots=slots,
        editor_output={
            "filled_slots": [
                {
                    "slot_alias": "s00",
                    "wording_fragment": "市场状态证据不足，暂未判定。",
                    "reference_aliases": [],
                }
            ]
        },
        full_events=[],
        compact_events=[],
        market_state=market_state,
        watchlist=[],
        alias_to_evidence={},
    )
    assert merged["market_state"]["explanation"] == "市场状态证据不足，暂未判定。"
