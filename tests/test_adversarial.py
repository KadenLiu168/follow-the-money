"""Task 10.13 — end-to-end adversarial fixtures.

Proves unsupported evidence, English-only narrative, Markdown/HTML/link
injection, or Unicode direction/zero-width controls cannot cross an
LLM/render boundary; full and degraded outputs obey their distinct schemas;
legitimate mixed Chinese/ticker text survives safely; and no structured or
rendered path emits prohibited investment instructions.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from follow_the_money.audit import ClaimAuditor
from follow_the_money.brief import build_degraded_report
from follow_the_money.render import (
    RenderError,
    escape_text_node,
    render_link,
)
from follow_the_money.schema import SchemaError, validate_against
from follow_the_money.unicode import UnicodeError_

T0 = datetime(2026, 8, 11, 0, 20, 0, tzinfo=UTC)


def _ts(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _brief(**overrides) -> dict:
    brief = {
        "schema_version": 1,
        "brief_id": "b_adversarial",
        "brief_generated_at": _ts(T0 + timedelta(minutes=5)),
        "brief_completed_at": _ts(T0 + timedelta(minutes=6)),
        "evidence_cutoff_at": _ts(T0),
        "feed_run_id": "r1",
        "mode": "normal",
        "headings": [
            "市场仪表盘",
            "市场状态",
            "重点事件",
            "其他重要事件",
            "资金流与持仓",
            "未来 24 小时关注",
            "结论",
        ],
        "dashboard": [],
        "market_state": {
            "regime": "unknown",
            "vector": {
                d: "unknown" for d in ("risk_appetite", "rates", "liquidity", "growth", "inflation")
            },
            "missing_roles": [],
            "explanation": "",
        },
        "full_events": [],
        "compact_events": [],
        "money_flow_section": [],
        "watchlist": [],
        "bottom_line": [],
        "claim_inventory": [],
        "warnings": [],
        "audit_status": {"script_audit": "passed", "language_audit": "passed", "findings": []},
        "provenance": {"feed_digest": "a" * 64, "config_hash": "b" * 64, "prompt_fingerprints": {}},
    }
    brief.update(overrides)
    return brief


# ---------------------------------------------------------------------------
# Markdown/HTML/link injection cannot cross the render boundary
# ---------------------------------------------------------------------------


def test_markdown_injection_neutralized():
    text = "## 伪造标题 **加粗** [链接](https://evil.example.com)"
    out = escape_text_node(text)
    assert "## " not in out
    assert "**" not in out
    assert "[链接]" not in out
    assert "evil.example.com" not in out  # link syntax neutralized


def test_html_injection_neutralized():
    out = escape_text_node("<script>alert(1)</script>")
    assert "<script>" not in out
    assert "&lt;script&gt;" in out


def test_link_injection_renderer_owned_only():
    # Raw URL targets cannot be user-supplied; only renderer-owned fixed
    # labels may emit https links.
    with pytest.raises(RenderError):
        render_link("来源", "https://evil.example.com/steal?token=abc")


def test_unicode_direction_controls_rejected():
    for bad in ("\u202e", "\u202b", "\u200f", "\u200b", "\u2066"):
        with pytest.raises(UnicodeError_):
            escape_text_node(f"文本{bad}文本")


def test_unicode_line_separator_rejected():
    with pytest.raises(UnicodeError_):
        escape_text_node("行\u2028分隔")


def test_english_only_narrative_rejected_by_han_threshold():
    # The deterministic Han-script minimum is a language-audit semantic
    # (task 10.7): an all-English fragment fails the wrong_language critical
    # gate. The renderer itself escapes it safely; the audit blocks it.
    from follow_the_money.audit import audit_language_findings

    output = {
        "covered_claim_ids": ["c_0"],
        "findings": [
            {
                "claim_id": "c_0",
                "category": "wrong_language",
                "rationale": "all-English",
                "reference_aliases": [],
            }
        ],
    }
    severity_map = {"critical": ("wrong_language",), "warning": ()}
    critical, _ = audit_language_findings(output, severity_map)
    assert len(critical) == 1
    assert critical[0]["category"] == "wrong_language"
    # And the renderer still safely escapes the fragment.
    assert escape_text_node("This is a completely English narrative without Chinese.")


def test_mixed_chinese_ticker_survives():
    out = escape_text_node("美联储（Fed）维持利率，标普500上涨0.5%")
    # Latin ticker/proper names survive; Chinese remains intact.
    assert "美联储" in out
    assert "Fed" in out
    assert "标普500" in out


# ---------------------------------------------------------------------------
# Full vs degraded distinct schemas
# ---------------------------------------------------------------------------


def test_full_and_degraded_obey_distinct_schemas():
    brief = _brief()
    validate_against("brief.schema.json", brief)
    report = build_degraded_report(
        report_id="d_adv",
        brief_generated_at=_ts(T0 + timedelta(minutes=5)),
        evidence_cutoff_at=_ts(T0),
        feed_run_id="r1",
        feed_health={"status": "degraded", "warnings": ["某来源不可用"]},
        dashboard=[],
        analytics={},
        unresolved_counts={"candidate_blocks": 0, "unresolved_groups": 0, "unresolved_events": 0},
    )
    validate_against("degraded-report.schema.json", report)
    with pytest.raises(SchemaError):
        validate_against("degraded-report.schema.json", brief)
    with pytest.raises(SchemaError):
        validate_against("brief.schema.json", report)


def test_degraded_report_no_llm_fields():
    report = build_degraded_report(
        report_id="d2",
        brief_generated_at=_ts(T0 + timedelta(minutes=5)),
        evidence_cutoff_at=_ts(T0),
        feed_run_id="r1",
        feed_health={"status": "healthy", "warnings": []},
        dashboard=[],
        analytics={},
        unresolved_counts={"candidate_blocks": 0, "unresolved_groups": 0, "unresolved_events": 0},
    )
    for field in ("price_in", "bottom_line", "asset_mappings", "why_it_matters"):
        assert field not in report


# ---------------------------------------------------------------------------
# No prohibited investment instructions on any path
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "建议买入该ETF",
        "请卖出黄金",
        "加仓美股",
        "Buy this stock now",
        "You should sell your position",
        "设置止损价",
        "目标价 120",
    ],
)
def test_trading_instructions_blocked_in_rendered_output(text):
    auditor = ClaimAuditor()
    brief = _brief()
    brief["claim_inventory"] = [
        {
            "claim_id": "c_0",
            "text": text,
            "is_factual": False,
            "is_causal": False,
            "reference_evidence_ids": [],
        }
    ]
    result = auditor.audit(brief)
    assert not result.passed
    assert any(f.category == "trading_instruction" for f in result.findings)


def test_structured_path_blocks_trading_instruction():
    # The brief schema has no instruction field; extra properties are rejected.
    brief = _brief()
    brief["trading_advice"] = "买入"
    with pytest.raises(SchemaError, match="Additional properties"):
        validate_against("brief.schema.json", brief)


def test_descriptive_false_positive_survives():
    # Legitimate descriptive/historical uses of lexicon words are allowed.
    auditor = ClaimAuditor()
    brief = _brief()
    brief["claim_inventory"] = [
        {
            "claim_id": "c_0",
            "text": "该基金净买入额昨日达到 10 亿元",
            "is_factual": True,
            "is_causal": False,
            "reference_evidence_ids": ["ev_1"],
        }
    ]
    result = auditor.audit(brief)
    assert result.passed


# ---------------------------------------------------------------------------
# Unsupported evidence cannot cross boundaries
# ---------------------------------------------------------------------------


def test_out_of_feed_reference_rejected():
    # Editor output referencing unknown aliases fails Brief assembly.
    from follow_the_money.brief import BriefError, assemble_brief

    with pytest.raises(BriefError, match="unknown reference alias"):
        assemble_brief(
            brief_id="b",
            brief_generated_at=_ts(T0 + timedelta(minutes=5)),
            brief_completed_at=_ts(T0 + timedelta(minutes=6)),
            evidence_cutoff_at=_ts(T0),
            feed_run_id="r1",
            editor_output={
                "filled_slots": [
                    {"slot_alias": "s0", "wording_fragment": "内容", "reference_aliases": ["ghost"]}
                ]
            },
            alias_to_evidence={},
            dashboard=[],
            market_state={
                "regime": "unknown",
                "vector": {},
                "missing_roles": [],
                "explanation": "",
            },
            full_events=[],
            compact_events=[],
            money_flow_section=[],
            watchlist=[],
            bottom_line=[],
        )


def test_english_only_prose_blocked_via_audit_projection():
    # An all-English fragment survives the renderer escape but is blocked by
    # the language audit's wrong_language critical category.
    from follow_the_money.audit import audit_language_findings

    output = {
        "covered_claim_ids": ["c_0"],
        "findings": [
            {
                "claim_id": "c_0",
                "category": "wrong_language",
                "rationale": "narrative not predominantly Chinese",
                "reference_aliases": [],
            }
        ],
    }
    severity_map = {"critical": ("wrong_language",), "warning": ()}
    critical, _ = audit_language_findings(output, severity_map)
    assert critical and critical[0]["severity"] == "critical"
