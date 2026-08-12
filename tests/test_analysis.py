"""Task 2.7/2.8 — analyst-output ownership and authoritative Analysis assembly."""

from __future__ import annotations

import pytest

from follow_the_money.analysis import AnalysisError, merge_analysis
from follow_the_money.ledger import Ledger, build_ledger_entry
from follow_the_money.schema import validate_against

ALIASES = {"ev_1": "evidence_1", "ev_2": "evidence_2", "ev_3": "evidence_3"}


def _analyst(**overrides) -> dict:
    out = {
        "packet_alias": "e0",
        "mechanisms": ["机制一"],
        "implications": ["含义一"],
        "reaction_attributions": [],
        "price_in": {
            "status": "unclear",
            "explanation": "无预期证据",
            "reference_aliases": ["ev_1"],
        },
        "indirect_indication": {"indicated": False, "reference_aliases": []},
        "asset_mappings": [],
        "alternatives": [],
        "watch_points": [],
        "scope": "single_entity",
        "fundamental_depth": "headline",
        "reversibility": "medium",
        "structural_horizon": "weeks",
        "cn_hk_exposure": "direct",
        "us_next_session_exposure": "indirect",
        "catalyst_calendar_ids": [],
        "audit_reasons": [],
    }
    out.update(overrides)
    return out


@pytest.fixture
def ledger() -> Ledger:
    l = Ledger()
    for ev in ("evidence_1", "evidence_2"):
        l.add(
            build_ledger_entry(
                entry_type="FACT",
                origin_payload="news",
                evidence_id=ev,
                subject="ent_a",
                predicate="p",
                effective_time=None,
                effective_precision="instant",
                value="1",
                unit="u",
                knowledge_available_at="2026-08-11T01:00:00Z",
            )
        )
    return l


def test_merge_basic(ledger):
    analysis = merge_analysis(
        event_id="evt_1",
        analyst_output=_analyst(),
        alias_to_evidence=ALIASES,
        ledger=ledger,
    )
    validate_against("analysis.schema.json", analysis)
    assert analysis["event_id"] == "evt_1"
    assert analysis["money_flow"]["status"] == "no_evidence"
    assert analysis["mechanisms"] == ["机制一"]


def test_unknown_reference_alias_rejected(ledger):
    out = _analyst()
    out["price_in"]["reference_aliases"] = ["ghost"]
    with pytest.raises(AnalysisError, match="unknown reference alias"):
        merge_analysis(event_id="e", analyst_output=out, alias_to_evidence=ALIASES, ledger=ledger)


def test_duplicate_asset_group_rejected(ledger):
    mapping = {
        "asset_group": "us_equities",
        "direction": "positive",
        "confidence": "high",
        "horizon": "days",
        "mechanism": "机制",
        "reference_aliases": ["ev_1"],
        "audit_reason": None,
    }
    out = _analyst(asset_mappings=[mapping, dict(mapping)])
    with pytest.raises(AnalysisError, match="duplicate asset group"):
        merge_analysis(event_id="e", analyst_output=out, alias_to_evidence=ALIASES, ledger=ledger)


def test_one_mapping_per_group_ok(ledger):
    out = _analyst(
        asset_mappings=[
            {
                "asset_group": "us_equities",
                "direction": "positive",
                "confidence": "high",
                "horizon": "days",
                "mechanism": "机制",
                "reference_aliases": ["ev_1"],
                "audit_reason": None,
            },
            {
                "asset_group": "cn_hk_equities",
                "direction": "negative",
                "confidence": "medium",
                "horizon": "weeks",
                "mechanism": "机制二",
                "reference_aliases": ["ev_2"],
                "audit_reason": None,
            },
        ]
    )
    analysis = merge_analysis(
        event_id="e", analyst_output=out, alias_to_evidence=ALIASES, ledger=ledger
    )
    assert len(analysis["asset_mappings"]) == 2


def test_audit_reason_required_for_unclear(ledger):
    out = _analyst(
        asset_mappings=[
            {
                "asset_group": "us_equities",
                "direction": "unclear",
                "confidence": "high",
                "horizon": "days",
                "mechanism": "机制",
                "reference_aliases": ["ev_1"],
                "audit_reason": None,
            }
        ]
    )
    with pytest.raises(AnalysisError, match="audit_reason required"):
        merge_analysis(event_id="e", analyst_output=out, alias_to_evidence=ALIASES, ledger=ledger)


def test_audit_reason_forbidden_when_certain(ledger):
    out = _analyst(
        asset_mappings=[
            {
                "asset_group": "us_equities",
                "direction": "positive",
                "confidence": "high",
                "horizon": "days",
                "mechanism": "机制",
                "reference_aliases": ["ev_1"],
                "audit_reason": "不应有",
            }
        ]
    )
    with pytest.raises(AnalysisError, match="must be null"):
        merge_analysis(event_id="e", analyst_output=out, alias_to_evidence=ALIASES, ledger=ledger)


def test_audit_reason_ok_for_unknown_horizon(ledger):
    out = _analyst(
        asset_mappings=[
            {
                "asset_group": "us_equities",
                "direction": "positive",
                "confidence": "unknown",
                "horizon": "days",
                "mechanism": "机制",
                "reference_aliases": ["ev_1"],
                "audit_reason": "信心不足",
            }
        ]
    )
    analysis = merge_analysis(
        event_id="e", analyst_output=out, alias_to_evidence=ALIASES, ledger=ledger
    )
    assert analysis["asset_mappings"][0]["audit_reason"] == "信心不足"


def test_direct_flow_confirms_money_flow(ledger):
    out = _analyst(indirect_indication={"indicated": True, "reference_aliases": ["ev_1"]})
    analysis = merge_analysis(
        event_id="e",
        analyst_output=out,
        alias_to_evidence=ALIASES,
        ledger=ledger,
        direct_flow_evidence_ids=["evidence_3"],
    )
    assert analysis["money_flow"]["status"] == "confirmed"
    assert analysis["money_flow"]["direct_evidence_ids"] == ["evidence_3"]


def test_indirect_indication_maps_to_indicated(ledger):
    out = _analyst(indirect_indication={"indicated": True, "reference_aliases": ["ev_1"]})
    analysis = merge_analysis(
        event_id="e", analyst_output=out, alias_to_evidence=ALIASES, ledger=ledger
    )
    assert analysis["money_flow"]["status"] == "indicated"


def test_price_movement_alone_is_no_evidence(ledger):
    out = _analyst(indirect_indication={"indicated": True, "reference_aliases": []})
    analysis = merge_analysis(
        event_id="e", analyst_output=out, alias_to_evidence=ALIASES, ledger=ledger
    )
    # An indirect indication with no referenced non-price evidence cannot
    # produce "indicated"; price movement alone yields no_evidence.
    assert analysis["money_flow"]["status"] == "no_evidence"


def test_attempted_confirmed_flow_assignment_rejected(ledger):
    out = _analyst()
    out["money_flow"] = {"status": "confirmed", "direct_evidence_ids": []}
    with pytest.raises(AnalysisError, match="must not supply 'money_flow'"):
        merge_analysis(event_id="e", analyst_output=out, alias_to_evidence=ALIASES, ledger=ledger)


def test_attempted_score_injection_rejected(ledger):
    out = _analyst(score=99)
    with pytest.raises(AnalysisError, match="must not supply 'score'"):
        merge_analysis(event_id="e", analyst_output=out, alias_to_evidence=ALIASES, ledger=ledger)


def test_mapping_horizon_has_no_third_free_standing_field(ledger):
    out = _analyst(
        asset_mappings=[
            {
                "asset_group": "us_equities",
                "direction": "positive",
                "confidence": "high",
                "horizon": "days",
                "mechanism": "机制",
                "reference_aliases": ["ev_1"],
                "audit_reason": None,
            }
        ]
    )
    # analyst-output has no free-standing time-horizon field beyond the
    # per-mapping horizon and the categorical structural_horizon feature.
    analysis = merge_analysis(
        event_id="e", analyst_output=out, alias_to_evidence=ALIASES, ledger=ledger
    )
    assert set(analysis) >= {"structural_horizon"}
    assert "time_horizon" not in analysis


def test_trading_instruction_in_mechanism_rejected(ledger):
    # Trading-instruction detection is a semantic audit (task 10.5), not a
    # JSON Schema rule. The strict schema still bounds the field.
    out = _analyst(mechanisms=["建议买入并持有"])
    validate_against("analyst-output.schema.json", out)
    # Semantic safety lexicon rejection is exercised in the audit suite.
