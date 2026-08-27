"""ECO-30 — workflow-neutral deterministic safety audit boundary."""

from __future__ import annotations

import inspect
from pathlib import Path

import follow_the_money.audit as audit_module
from follow_the_money.audit import ClaimAuditor
from follow_the_money.config.model import SafetyLexicon

REPO_ROOT = Path(__file__).resolve().parents[1]


def _claim(
    claim_id: object = "c1",
    text: str = "A descriptive factual statement.",
    requires_direct_evidence: bool = False,
    evidence_ids: tuple[str, ...] = (),
):
    claim_type = getattr(audit_module, "AuditClaim", None)
    assert claim_type is not None, "ECO-30 requires an audit-owned AuditClaim input"
    return claim_type(claim_id, text, requires_direct_evidence, evidence_ids)


def _flow(confirmed: bool, owning_event_id: str | None = None):
    flow_type = getattr(audit_module, "AuditFlow", None)
    assert flow_type is not None, "ECO-30 requires an audit-owned AuditFlow input"
    return flow_type(confirmed, owning_event_id)


def _findings(result):
    return [(finding.claim_id, finding.category, finding.detail) for finding in result.findings]


# ---------------------------------------------------------------------------
# Standalone text safety
# ---------------------------------------------------------------------------


def test_text_audit_rejects_chinese_trading_instruction_without_brief_input():
    result = ClaimAuditor().audit_text("今天买入腾讯。")

    assert not result.passed
    assert _findings(result) == [
        (None, "trading_instruction", "prohibited trading instruction detected")
    ]


def test_text_audit_rejects_english_trading_instruction():
    result = ClaimAuditor().audit_text("Buy the stock now.")

    assert not result.passed
    assert any(f.category == "trading_instruction" for f in result.findings)


def test_text_audit_preserves_configured_descriptive_exception():
    lexicon = SafetyLexicon(
        zh_terms=(),
        en_terms=("buy",),
        descriptive_exceptions=("policy memo",),
    )

    result = ClaimAuditor(lexicon).audit_text("This policy memo describes a buy signal.")

    assert result.passed
    assert result.findings == []


def test_text_audit_attaches_optional_claim_identity_to_finding():
    result = ClaimAuditor().audit_text("卖出该资产。", claim_id="claim-7")

    assert result.findings[0].claim_id == "claim-7"


def test_text_audit_repeated_inputs_have_identical_results_and_no_runtime_model_surface():
    auditor = ClaimAuditor(SafetyLexicon())
    text = "\u200bPlease sell this position."

    first = auditor.audit_text(text, claim_id="c1")
    second = auditor.audit_text(text, claim_id="c1")

    assert first == second
    audit_source = inspect.getsource(audit_module).lower()
    assert "openai" not in audit_source
    assert "llm" not in audit_source
    assert "credential" not in audit_source


# ---------------------------------------------------------------------------
# Structured claim boundary
# ---------------------------------------------------------------------------


def test_structured_audit_rejects_empty_inventory():
    result = ClaimAuditor().audit_claims((), ())

    assert not result.passed
    assert any(f.category == "empty_inventory" for f in result.findings)


def test_structured_audit_rejects_duplicate_claim_id():
    result = ClaimAuditor().audit_claims((_claim(), _claim()), ("c1",))

    assert not result.passed
    assert any(f.category == "duplicate_claim_id" for f in result.findings)


def test_structured_audit_rejects_invalid_inventory_id_without_incidental_exception():
    for invalid_id in (None, 7, "", "   "):
        result = ClaimAuditor().audit_claims((_claim(claim_id=invalid_id),), ())

        assert not result.passed
        assert any(f.category == "invalid_claim_id" for f in result.findings)


def test_structured_audit_rejects_invalid_submitted_id_without_incidental_exception():
    for invalid_id in (None, 7, "", "   "):
        result = ClaimAuditor().audit_claims((_claim(),), (invalid_id,))

        assert not result.passed
        assert any(f.category == "invalid_claim_id" for f in result.findings)


def test_structured_audit_observes_submitted_identity_outside_inventory():
    result = ClaimAuditor().audit_claims((_claim("c1"),), ("c2",))

    assert not result.passed
    assert _findings(result) == [
        ("c2", "outside_inventory", "rendered assertion outside inventory")
    ]


def test_structured_audit_requires_evidence_only_when_explicitly_obligated():
    required = ClaimAuditor().audit_claims((_claim(requires_direct_evidence=True),), ("c1",))
    optional = ClaimAuditor().audit_claims((_claim(requires_direct_evidence=False),), ("c1",))

    assert not required.passed
    assert any(f.category == "missing_evidence" for f in required.findings)
    assert optional.passed


def test_structured_audit_accepts_required_claim_with_direct_evidence():
    result = ClaimAuditor().audit_claims(
        (_claim(requires_direct_evidence=True, evidence_ids=("evidence-1",)),),
        ("c1",),
    )

    assert result.passed
    assert result.findings == []


def test_structured_audit_requires_owner_for_confirmed_flow():
    result = ClaimAuditor().audit_claims((_claim(),), ("c1",), (_flow(True),))

    assert not result.passed
    assert any(f.category == "flow_ownership" for f in result.findings)


def test_structured_audit_accepts_confirmed_flow_with_owner():
    result = ClaimAuditor().audit_claims(
        (_claim(),),
        ("c1",),
        (_flow(True, "event-1"),),
    )

    assert result.passed
    assert result.findings == []


def test_structured_audit_does_not_promote_unconfirmed_flow_without_owner():
    result = ClaimAuditor().audit_claims((_claim(),), ("c1",), (_flow(False),))

    assert result.passed


def test_structured_audit_reuses_text_safety_and_claim_identity():
    result = ClaimAuditor().audit_claims(
        (_claim(text="今天加仓。"),),
        ("c1",),
    )

    assert not result.passed
    assert _findings(result) == [
        ("c1", "trading_instruction", "prohibited trading instruction detected")
    ]


def test_structured_audit_is_stable_under_reordered_repeated_and_malformed_inputs():
    auditor = ClaimAuditor()
    claims = (
        _claim("b", text="卖出该资产。"),
        _claim("a", text="Buy now.", requires_direct_evidence=True),
    )

    first = auditor.audit_claims(claims, ("outside-2", "outside-1"), (_flow(True),))
    reordered = auditor.audit_claims(
        tuple(reversed(claims)),
        ("outside-1", "outside-2"),
        (_flow(True),),
    )
    malformed = auditor.audit_claims((_claim(None), _claim("   ")), (None, ""))
    repeated_malformed = auditor.audit_claims((_claim("   "), _claim(None)), ("", None))

    assert first == reordered
    assert not malformed.passed
    assert malformed == repeated_malformed


# ---------------------------------------------------------------------------
# Architecture regressions
# ---------------------------------------------------------------------------


def test_audit_boundary_has_no_legacy_brief_or_internal_serialized_audit_contract():
    audit_source = inspect.getsource(audit_module).lower()
    for removed_term in (
        "brief",
        "editor",
        "dashboard",
        "money_flow_section",
        "claim_inventory",
    ):
        assert removed_term not in audit_source
    assert (REPO_ROOT / "schemas" / "agent-invocation.schema.json").exists()
    assert not list((REPO_ROOT / "schemas").glob("*audit*.json"))
    assert not list((REPO_ROOT / "schemas").glob("*claim*.json"))


def test_normal_tests_and_production_entry_paths_do_not_retain_legacy_auditor_wiring():
    test_source = "\n".join(
        path.read_text()
        for path in (REPO_ROOT / "tests").rglob("*.py")
        if path.name != "test_audit.py"
    )
    assert "auditor.audit({" not in test_source

    source_root = REPO_ROOT / "src" / "follow_the_money"
    for path in source_root.rglob("*.py"):
        if path in (source_root / "audit.py", source_root / "agent_invocation.py"):
            continue
        assert "ClaimAuditor" not in path.read_text(), path

    invocation_source = (source_root / "agent_invocation.py").read_text()
    assert "ClaimAuditor" in invocation_source

    event_callers = []
    for source_path in source_root.rglob("*.py"):
        source = source_path.read_text()
        if "build_event(" in source and source_path.name != "events.py":
            event_callers.append(source_path.relative_to(source_root))
    assert event_callers == [Path("agent_invocation.py")]


def test_audit_module_does_not_define_removed_or_future_workflow_objects():
    audit_source = inspect.getsource(audit_module)
    for forbidden in ("Brief", "Editor", "Agent", "ResearchContext", "BriefContext"):
        assert forbidden not in audit_source
