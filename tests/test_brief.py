"""Task 2.9/2.10 — editor-output ownership and authoritative Brief assembly."""

from __future__ import annotations

import pytest

from follow_the_money.brief import (
    DASHBOARD_CLAIM_COUNT,
    EDITOR_MAX_SLOTS,
    MAX_CLAIMS,
    BriefError,
    assemble_brief,
    build_degraded_report,
)
from follow_the_money.schema import SchemaError, validate_against

ALIASES = {"ev_1": "evidence_1", "ev_2": "evidence_2"}


def _market_state(**overrides) -> dict:
    ms = {
        "regime": "neutral",
        "vector": {
            "risk_appetite": "neutral",
            "rates": "neutral",
            "liquidity": "neutral",
            "growth": "neutral",
            "inflation": "neutral",
        },
        "missing_roles": [],
        "explanation": "市场状态说明",
    }
    ms.update(overrides)
    return ms


def _dashboard(n: int = 13) -> list[dict]:
    return [{"role_id": f"r{i}", "available": True, "display": f"角色{i}"} for i in range(n)]


def _full_event(event_id: str = "evt_1", **overrides) -> dict:
    ev = {
        "event_id": event_id,
        "display_label": "美联储政策",
        "confidence": "high",
        "fact_summary": "事实摘要",
        "why_it_matters": "为何重要",
        "reaction_attribution": "反应归因",
        "price_in": "定价状态",
        "money_flow": "资金流",
        "asset_mappings": "资产映射",
        "alternative": "替代解读",
        "uncertainty": "不确定性",
        "source_links": ["https://a.example.com/1"],
    }
    ev.update(overrides)
    return ev


def _compact_event(event_id: str = "evt_2", **overrides) -> dict:
    ev = {
        "event_id": event_id,
        "display_label": "次要事件",
        "confidence": "medium",
        "fact_summary": "事实",
        "why_it_matters": "为何重要",
        "uncertainty": "不确定",
        "source_links": ["https://a.example.com/2"],
    }
    ev.update(overrides)
    return ev


def _editor(slots: list[dict] | None = None) -> dict:
    return {
        "filled_slots": slots
        or [
            {
                "slot_alias": "s00",
                "wording_fragment": "市场维持风险偏好。",
                "reference_aliases": ["ev_1"],
            }
        ]
    }


def _slot_meta(slots: list[dict] | None = None) -> dict:
    slots = slots or [{"slot_alias": "s00"}]
    return {
        s["slot_alias"]: {
            "slot_kind": s.get("slot_kind", "market_state_explanation"),
            "is_factual": s.get("is_factual", False),
            "is_causal": s.get("is_causal", False),
        }
        for s in slots
    }


def _brief_kwargs(**overrides) -> dict:
    kw = {
        "brief_id": "brief_1",
        "brief_generated_at": "2026-08-11T00:25:00Z",
        "brief_completed_at": "2026-08-11T00:26:00Z",
        "evidence_cutoff_at": "2026-08-11T00:20:00Z",
        "feed_run_id": "feed_run_1",
        "editor_output": _editor(),
        "alias_to_evidence": ALIASES,
        "slot_meta": _slot_meta(),
        "dashboard": _dashboard(),
        "market_state": _market_state(),
        "full_events": [_full_event()],
        "compact_events": [_compact_event()],
        "money_flow_section": [],
        "watchlist": [],
        "bottom_line": [{"event_id": "evt_1", "text": "结论一"}],
        "warnings": ["提示"],
        "provenance": {"feed_digest": "a" * 64, "config_hash": "b" * 64, "prompt_fingerprints": {}},
    }
    kw.update(overrides)
    return kw


# ---------------------------------------------------------------------------
# Positive
# ---------------------------------------------------------------------------


def test_assemble_brief_valid():
    brief = assemble_brief(**_brief_kwargs())
    validate_against("brief.schema.json", brief)
    assert brief["mode"] == "normal"
    assert brief["headings"][0] == "市场仪表盘"
    assert brief["headings"][-1] == "结论"
    assert len(brief["claim_inventory"]) == 1 + DASHBOARD_CLAIM_COUNT


def test_full_compact_event_shape():
    brief = assemble_brief(**_brief_kwargs())
    assert len(brief["full_events"]) == 1
    assert len(brief["compact_events"]) == 1


def test_claim_inventory_reference_resolution():
    brief = assemble_brief(**_brief_kwargs())
    editor_claims = [c for c in brief["claim_inventory"] if c["class"] == "editor"]
    assert editor_claims[0]["reference_evidence_ids"] == ["evidence_1"]


def test_money_flow_section_conditional():
    brief = assemble_brief(
        **_brief_kwargs(
            money_flow_section=[{"event_id": "evt_1", "status": "confirmed", "text": "ETF 净流入"}]
        )
    )
    assert brief["money_flow_section"][0]["status"] == "confirmed"


def test_zero_to_six_watchlist():
    brief = assemble_brief(
        **_brief_kwargs(
            watchlist=[
                {
                    "calendar_id": "c1",
                    "priority": "critical",
                    "scheduled_at": "2026-08-11T12:00:00Z",
                    "label": "FOMC",
                    "explanation": "关注",
                }
            ]
        )
    )
    assert len(brief["watchlist"]) == 1
    with pytest.raises(SchemaError):
        assemble_brief(
            **_brief_kwargs(
                watchlist=[
                    {
                        "calendar_id": f"c{i}",
                        "priority": "critical",
                        "scheduled_at": "2026-08-11T12:00:00Z",
                        "label": "x",
                        "explanation": "y",
                    }
                    for i in range(7)
                ]
            )
        )


def test_zero_event_no_bottom_line_and_bottom_line_bounds():
    # Zero events => no Bottom Line slots (schema maxItems 3; empty allowed).
    brief = assemble_brief(**_brief_kwargs(full_events=[], compact_events=[], bottom_line=[]))
    assert brief["bottom_line"] == []
    # Four points rejected by schema.
    bl = [{"event_id": f"evt_{i}", "text": "点"} for i in range(4)]
    with pytest.raises(SchemaError):
        assemble_brief(**_brief_kwargs(bottom_line=bl))


# ---------------------------------------------------------------------------
# Ownership and bounds
# ---------------------------------------------------------------------------


def test_editor_authoritative_field_rejected():
    editor = _editor()
    editor["headings"] = ["自定义"]
    with pytest.raises(BriefError, match="must not supply"):
        assemble_brief(**_brief_kwargs(editor_output=editor))


def test_editor_unknown_ref_rejected():
    editor = _editor()
    editor["filled_slots"][0]["reference_aliases"] = ["ghost"]
    with pytest.raises(BriefError, match="unknown reference alias"):
        assemble_brief(**_brief_kwargs(editor_output=editor))


def test_editor_61_slot_max():
    slots = [
        {
            "slot_alias": f"s{i:02d}",
            "wording_fragment": "内容",
            "reference_aliases": [],
        }
        for i in range(61)
    ]
    meta = {
        f"s{i:02d}": {"slot_kind": "event_fact_summary", "is_factual": True, "is_causal": False}
        for i in range(61)
    }
    brief = assemble_brief(**_brief_kwargs(editor_output=_editor(slots), slot_meta=meta))
    assert len(brief["claim_inventory"]) == 61 + DASHBOARD_CLAIM_COUNT
    assert len(brief["claim_inventory"]) <= MAX_CLAIMS
    slots.append({"slot_alias": "s61", "wording_fragment": "内容", "reference_aliases": []})
    # 62 slots exceed both schema maxItems(61) and the semantic bound.
    with pytest.raises((BriefError, SchemaError)):
        assemble_brief(**_brief_kwargs(editor_output=_editor(slots), slot_meta=meta))


def test_claim_inventory_bound_74():
    # 74 - 13 dashboard = 61 editor slots is the exact maximum.
    assert EDITOR_MAX_SLOTS + DASHBOARD_CLAIM_COUNT == MAX_CLAIMS == 74


def test_editor_one_fragment_per_slot():
    editor = _editor()
    editor["filled_slots"][0]["extra_fragment"] = "第二个片段"
    with pytest.raises(SchemaError, match="Additional properties"):
        assemble_brief(**_brief_kwargs(editor_output=editor))


def test_lone_surrogate_in_fragment_rejected():
    editor = _editor()
    editor["filled_slots"][0]["wording_fragment"] = "bad\ud800"
    with pytest.raises(SchemaError, match="surrogate"):
        assemble_brief(**_brief_kwargs(editor_output=editor))


def test_brief_heading_order_fixed():
    brief = assemble_brief(**_brief_kwargs())
    assert brief["headings"] == [
        "市场仪表盘",
        "市场状态",
        "重点事件",
        "其他重要事件",
        "资金流与持仓",
        "未来 24 小时关注",
        "结论",
    ]


def test_forbidden_url_injection_rejected():
    # The editor cannot supply URLs; they are renderer-owned.
    editor = _editor()
    editor["filled_slots"][0]["url"] = "https://evil.example.com"
    with pytest.raises(SchemaError, match="Additional properties"):
        assemble_brief(**_brief_kwargs(editor_output=editor))


# ---------------------------------------------------------------------------
# Degraded report
# ---------------------------------------------------------------------------


def test_degraded_report_valid():
    report = build_degraded_report(
        report_id="degraded_1",
        brief_generated_at="2026-08-11T00:25:00Z",
        evidence_cutoff_at="2026-08-11T00:20:00Z",
        feed_run_id="feed_run_1",
        feed_health={"status": "degraded", "warnings": ["某来源不可用"]},
        dashboard=_dashboard(),
        analytics={"volatility": {"sp500": "0.123456"}},
        unresolved_counts={"candidate_blocks": 3, "unresolved_groups": 1, "unresolved_events": 0},
        warnings=["提示"],
    )
    validate_against("degraded-report.schema.json", report)
    assert report["mode"] == "degraded"
    assert "bottom_line" not in report  # no LLM-owned conclusions


def test_degraded_report_rejects_llm_fields():
    report = build_degraded_report(
        report_id="d1",
        brief_generated_at="2026-08-11T00:25:00Z",
        evidence_cutoff_at="2026-08-11T00:20:00Z",
        feed_run_id="r1",
        feed_health={"status": "healthy", "warnings": []},
        dashboard=[],
        analytics={},
        unresolved_counts={"candidate_blocks": 0, "unresolved_groups": 0, "unresolved_events": 0},
    )
    with pytest.raises(SchemaError):
        report["price_in"] = "不应存在"
        validate_against("degraded-report.schema.json", report)


def test_full_and_degraded_obey_distinct_schemas():
    brief = assemble_brief(**_brief_kwargs())
    report = build_degraded_report(
        report_id="d2",
        brief_generated_at="2026-08-11T00:25:00Z",
        evidence_cutoff_at="2026-08-11T00:20:00Z",
        feed_run_id="r1",
        feed_health={"status": "healthy", "warnings": []},
        dashboard=[],
        analytics={},
        unresolved_counts={"candidate_blocks": 0, "unresolved_groups": 0, "unresolved_events": 0},
    )
    # A normal Brief cannot validate as a degraded report and vice versa.
    with pytest.raises(SchemaError):
        validate_against("degraded-report.schema.json", brief)
    with pytest.raises(SchemaError):
        validate_against("brief.schema.json", report)
