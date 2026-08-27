"""ECO-51 — private one-shot Agent invocation boundary."""

from __future__ import annotations

import inspect
import io
import json
import os
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from follow_the_money.schema import validate_against

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "agent-invocation.schema.json"


def _event_input(
    *,
    event_type: str = "macro_release",
    origin_payload: str = "macro_release",
    evidence_id: str = "ev-1",
    subject: str = "ent_fed",
    subject_zh: str = "美联储",
    predicate: str = "policy_rate",
    effective_time: str | None = "2026-08-11T01:00:00Z",
    effective_precision: str = "instant",
    value: str | None = "5.0",
    unit: str | None = "percent",
    knowledge_available_at: str = "2026-08-11T01:00:00Z",
) -> dict:
    return {
        "event_type": event_type,
        "evidence_ids": [evidence_id],
        "entity_ids": [subject],
        "key_facts": [
            {
                "entry_type": "FACT",
                "origin_payload": origin_payload,
                "evidence_id": evidence_id,
                "subject": subject,
                "predicate": predicate,
                "effective_time": effective_time,
                "effective_precision": effective_precision,
                "value": value,
                "unit": unit,
                "knowledge_available_at": knowledge_available_at,
            }
        ],
        "subject_zh": subject_zh,
    }


EXPECTED_EVENT_RESULT = {
    "event_id": "evt_794cc9b6674d8b29cd7cdcdbe5b08bfcbc5ff03a",
    "event_type": "macro_release",
    "evidence_ids": ["ev-1"],
    "key_fact_ids": ["fact_61f788f2068268ab4bf7c2095d7d2a0b"],
    "fully_known_at": "2026-08-11T01:00:00Z",
    "story_family_id": "fam_single_evt_794cc9b6674d8b29cd7cdcdbe5b08bfcbc5ff03a",
    "coexistence_pair_ids": [],
    "display_label": "美联储发布宏观数据：5.0percent",
    "economic_effective_time": {"value": "2026-08-11T01:00:00Z", "precision": "instant"},
    "common_effective_time": {"value": "2026-08-11T01:00:00Z", "precision": "instant"},
    "multiple_effective_times": False,
    "key_fact_effective_times": [
        {
            "fact_id": "fact_61f788f2068268ab4bf7c2095d7d2a0b",
            "value": "2026-08-11T01:00:00Z",
            "precision": "instant",
        }
    ],
    "key_fact_references": [
        {"fact_id": "fact_61f788f2068268ab4bf7c2095d7d2a0b", "evidence_id": "ev-1"}
    ],
}


def _run(raw: bytes | str | dict) -> tuple[subprocess.CompletedProcess[bytes], dict]:
    if isinstance(raw, dict):
        raw = json.dumps(raw, ensure_ascii=False).encode("utf-8")
    elif isinstance(raw, str):
        raw = raw.encode("utf-8")
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        (str(REPO_ROOT / "src"), str(REPO_ROOT), env.get("PYTHONPATH", ""))
    )
    proc = subprocess.run(
        [sys.executable, "-m", "follow_the_money.agent_invocation"],
        cwd=REPO_ROOT,
        env=env,
        input=raw,
        capture_output=True,
        check=False,
    )
    lines = proc.stdout.decode("utf-8").splitlines()
    assert len(lines) == 1, (proc.stdout, proc.stderr)
    response = json.loads(lines[0])
    validate_against(SCHEMA, response)
    return proc, response


def _request(operation: str, input_value: dict) -> dict:
    return {"contract_version": 1, "operation": operation, "input": input_value}


def _finding(claim_id: str | None, category: str, detail: str) -> dict:
    return {
        "claim_id": claim_id,
        "category": category,
        "detail": detail,
        "severity": "critical",
    }


def _keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {key for item in value.values() for key in _keys(item)}
    if isinstance(value, list):
        return {key for item in value for key in _keys(item)}
    return set()


def test_process_success_responses_cover_text_critical_and_claims():
    cases = (
        (_request("audit.text", {"text": "A descriptive statement."}), True, []),
        (
            _request("audit.text", {"text": "Buy the stock now."}),
            False,
            [_finding(None, "trading_instruction", "prohibited trading instruction detected")],
        ),
        (
            _request(
                "audit.claims",
                {
                    "claims": [
                        {
                            "claim_id": "c1",
                            "text": "A descriptive statement.",
                            "requires_direct_evidence": False,
                            "evidence_ids": [],
                        }
                    ],
                    "submitted_claim_ids": ["c1"],
                },
            ),
            True,
            [],
        ),
    )

    for request, passed, findings in cases:
        proc, response = _run(request)
        assert proc.returncode == 0
        assert response["operation"] == request["operation"]
        assert response["result"] == {"passed": passed, "findings": findings}


@pytest.mark.parametrize(
    ("input_value", "expected"),
    [
        (
            {"claims": [], "submitted_claim_ids": []},
            _finding(None, "empty_inventory", "claim inventory is empty"),
        ),
        (
            {
                "claims": [
                    {
                        "claim_id": "c1",
                        "text": "A.",
                        "requires_direct_evidence": False,
                        "evidence_ids": [],
                    },
                    {
                        "claim_id": "c1",
                        "text": "B.",
                        "requires_direct_evidence": False,
                        "evidence_ids": [],
                    },
                ],
                "submitted_claim_ids": ["c1"],
            },
            _finding(None, "duplicate_claim_id", "duplicate claim IDs in inventory"),
        ),
        (
            {
                "claims": [
                    {
                        "claim_id": "c1",
                        "text": "A.",
                        "requires_direct_evidence": False,
                        "evidence_ids": [],
                    }
                ],
                "submitted_claim_ids": ["outside"],
            },
            _finding("outside", "outside_inventory", "rendered assertion outside inventory"),
        ),
        (
            {
                "claims": [
                    {
                        "claim_id": "c1",
                        "text": "A.",
                        "requires_direct_evidence": True,
                        "evidence_ids": [],
                    }
                ],
                "submitted_claim_ids": ["c1"],
            },
            _finding("c1", "missing_evidence", "factual claim lacks evidence refs"),
        ),
        (
            {
                "claims": [
                    {
                        "claim_id": "c1",
                        "text": "A.",
                        "requires_direct_evidence": False,
                        "evidence_ids": [],
                    }
                ],
                "submitted_claim_ids": ["c1"],
                "flows": [{"confirmed": True, "owning_event_id": None}],
            },
            _finding(None, "flow_ownership", "confirmed flow lacks owning event"),
        ),
        (
            {
                "claims": [
                    {
                        "claim_id": "c1",
                        "text": "今天加仓。",
                        "requires_direct_evidence": False,
                        "evidence_ids": [],
                    }
                ],
                "submitted_claim_ids": ["c1"],
            },
            _finding("c1", "trading_instruction", "prohibited trading instruction detected"),
        ),
    ],
)
def test_valid_domain_negative_claims_are_successful_invocations(input_value, expected):
    proc, response = _run(_request("audit.claims", input_value))

    assert proc.returncode == 0
    assert response["result"] == {"passed": False, "findings": [expected]}


def test_process_event_structure_returns_exact_closed_event_projection():
    proc, response = _run(_request("event.structure", _event_input()))

    assert proc.returncode == 0
    assert proc.stderr == b""
    assert response == {
        "contract_version": 1,
        "operation": "event.structure",
        "result": EXPECTED_EVENT_RESULT,
    }


def test_process_event_structure_supports_default_and_filing_labels():
    default_input = _event_input(
        event_type="default",
        origin_payload="news",
        evidence_id="ev-default",
        subject="raw-subject",
        subject_zh="主体",
    )
    filing_input = _event_input(
        event_type="filing",
        origin_payload="filing",
        evidence_id="ev-filing",
        subject="ent_company",
        subject_zh="公司",
        predicate="filed",
        value="13F",
        unit="form",
    )
    filing_input.update({"company": "Acme", "form": "13F"})
    filing_fallback_input = {key: value for key, value in filing_input.items() if key != "company"}

    for input_value, label in (
        (default_input, "主体 policy_rate 5.0percent"),
        (filing_input, "Acme提交13F申报"),
        (filing_fallback_input, "公司提交13F申报"),
    ):
        proc, response = _run(_request("event.structure", input_value))
        assert proc.returncode == 0
        assert response["result"]["display_label"] == label
        assert set(response["result"]) == {
            "event_id",
            "event_type",
            "evidence_ids",
            "key_fact_ids",
            "fully_known_at",
            "story_family_id",
            "coexistence_pair_ids",
            "display_label",
            "economic_effective_time",
            "common_effective_time",
            "multiple_effective_times",
            "key_fact_effective_times",
            "key_fact_references",
        }


def test_process_event_structure_canonicalizes_family_pairs_and_input_order():
    from follow_the_money.events import story_family_id

    base = _event_input()
    second_fact = {
        **base["key_facts"][0],
        "evidence_id": "ev-2",
        "predicate": "rate_hike",
        "value": "0.5",
    }
    base["evidence_ids"] = ["ev-1", "ev-2"]
    base["entity_ids"] = ["ent_treasury", "ent_fed", "ent_fed"]
    base["key_facts"] = [base["key_facts"][0], second_fact]
    peer_a = "evt_" + "a" * 40
    peer_b = "evt_" + "b" * 40
    coexist = "evt_" + "c" * 40
    base["story_family_peer_event_ids"] = [peer_b, peer_a, peer_a]
    base["coexisting_event_ids"] = [coexist, peer_a, coexist]
    permuted = deepcopy(base)
    permuted["evidence_ids"].reverse()
    permuted["entity_ids"] = ["ent_fed", "ent_treasury"]
    permuted["key_facts"].reverse()
    permuted["story_family_peer_event_ids"] = [peer_a, peer_b]
    permuted["coexisting_event_ids"] = [peer_a, coexist]

    first_proc, first = _run(_request("event.structure", base))
    second_proc, second = _run(_request("event.structure", permuted))

    assert first_proc.returncode == second_proc.returncode == 0
    assert first_proc.stdout == second_proc.stdout
    assert first == second
    event_id = first["result"]["event_id"]
    assert first["result"]["story_family_id"] == story_family_id([event_id, peer_a, peer_b])
    assert first["result"]["coexistence_pair_ids"] == [
        sorted([event_id, peer_a]),
        sorted([event_id, coexist]),
    ]


def test_event_invalid_requests_fail_closed_before_execution():
    missing_evidence = _event_input()
    missing_evidence["key_facts"][0]["evidence_id"] = "ev-missing"
    duplicate_fact = _event_input()
    duplicate_fact["key_facts"] = [
        duplicate_fact["key_facts"][0],
        deepcopy(duplicate_fact["key_facts"][0]),
    ]
    duplicate_fact["key_facts"][1]["knowledge_available_at"] = "2026-08-11T02:00:00Z"
    non_filing_display = _event_input()
    non_filing_display["form"] = "13F"
    filing_without_form = _event_input(event_type="filing", origin_payload="filing")
    cases = (missing_evidence, duplicate_fact, non_filing_display, filing_without_form)

    for input_value in cases:
        proc, response = _run(_request("event.structure", input_value))
        assert proc.returncode != 0
        assert response == {
            "contract_version": 1,
            "error": {"code": "invalid_request", "message": "invalid request"},
        }


def test_invalid_event_never_constructs_ledger_or_event(monkeypatch, capsys):
    import follow_the_money.agent_invocation as module

    calls = []

    class ExplodingLedger:
        def __init__(self):
            calls.append("ledger")

    def exploding_event(**kwargs):
        calls.append("event")
        raise AssertionError("invalid input reached Event construction")

    monkeypatch.setattr(module, "Ledger", ExplodingLedger, raising=False)
    monkeypatch.setattr(module, "build_event", exploding_event, raising=False)
    invalid = _event_input()
    invalid["key_facts"][0]["evidence_id"] = "ev-missing"

    code = _call_main(monkeypatch, _request("event.structure", invalid), module)
    response = json.loads(capsys.readouterr().out)

    assert code != 0
    assert response["error"]["code"] == "invalid_request"
    assert calls == []


def test_invalid_event_prevalidates_every_fact_before_fact_construction(monkeypatch, capsys):
    import follow_the_money.agent_invocation as module

    invalid = _event_input()
    invalid["key_facts"].append(
        {**invalid["key_facts"][0], "evidence_id": "ev-missing", "predicate": "later_fact"}
    )

    def exploding_entry(**kwargs):
        raise AssertionError("invalid input reached fact construction")

    monkeypatch.setattr(module, "build_ledger_entry", exploding_entry)
    code = _call_main(monkeypatch, _request("event.structure", invalid), module)
    response = json.loads(capsys.readouterr().out)

    assert code != 0
    assert response["error"]["code"] == "invalid_request"


def test_accepted_event_execution_failure_is_one_schema_valid_error(monkeypatch, capsys):
    import follow_the_money.agent_invocation as module

    def exploding_event(**kwargs):
        raise RuntimeError("unexpected Event failure")

    monkeypatch.setattr(module, "build_event", exploding_event, raising=False)
    code = _call_main(monkeypatch, _request("event.structure", _event_input()), module)
    captured = capsys.readouterr()

    assert code != 0
    assert captured.err == ""
    assert "Traceback" not in captured.out
    lines = captured.out.splitlines()
    assert len(lines) == 1
    response = json.loads(lines[0])
    validate_against(SCHEMA, response)
    assert response == {
        "contract_version": 1,
        "error": {"code": "execution_failure", "message": "execution failure"},
    }


def test_event_mapping_matches_direct_canonical_construction():
    from follow_the_money.events import build_event
    from follow_the_money.ledger import Ledger, build_ledger_entry

    input_value = _event_input()
    fact = input_value["key_facts"][0]
    ledger = Ledger()
    entry = ledger.add(build_ledger_entry(**fact))
    direct = build_event(
        event_type=input_value["event_type"],
        evidence_ids=input_value["evidence_ids"],
        entity_ids=input_value["entity_ids"],
        event_defining_fact_ids=[entry.fact_id],
        ledger=ledger,
        subject_zh=input_value["subject_zh"],
    )
    expected = {key: value for key, value in direct.items() if key != "schema_version"}
    expected["key_fact_references"] = [{"fact_id": entry.fact_id, "evidence_id": entry.evidence_id}]

    proc, response = _run(_request("event.structure", input_value))

    assert proc.returncode == 0
    assert response["result"] == expected


def test_one_event_request_calls_only_event_structuring_once(monkeypatch, capsys):
    import follow_the_money.agent_invocation as module
    from follow_the_money.events import build_event

    calls = []
    build = build_event

    def recording_event(**kwargs):
        calls.append(kwargs)
        return build(**kwargs)

    class ExplodingAuditor:
        def __init__(self):
            raise AssertionError("Audit was called for event.structure")

    monkeypatch.setattr(module, "build_event", recording_event, raising=False)
    monkeypatch.setattr(module, "ClaimAuditor", ExplodingAuditor)
    code = _call_main(monkeypatch, _request("event.structure", _event_input()), module)
    response = json.loads(capsys.readouterr().out)

    assert code == 0
    assert response["operation"] == "event.structure"
    assert len(calls) == 1


def test_event_has_one_private_canonical_caller_and_no_feed_edge():
    source_root = REPO_ROOT / "src" / "follow_the_money"
    callers = []
    for source_path in source_root.rglob("*.py"):
        source = source_path.read_text()
        if "build_event(" in source and source_path.name != "events.py":
            callers.append(source_path.relative_to(source_root))

    assert callers == [Path("agent_invocation.py")]
    invocation_source = (source_root / "agent_invocation.py").read_text()
    assert "run_feed" not in invocation_source
    assert "build_event(" in invocation_source


def test_event_inputs_remain_agent_owned_without_authority_claims():
    input_value = _event_input(
        event_type="news",
        origin_payload="news",
        evidence_id="agent-evidence",
        subject="agent-entity",
        subject_zh="Agent 选择的主体",
        predicate="agent_selected_fact",
    )
    input_value["story_family_peer_event_ids"] = ["evt_" + "a" * 40]
    input_value["coexisting_event_ids"] = ["evt_" + "b" * 40]

    proc, response = _run(_request("event.structure", input_value))

    assert proc.returncode == 0
    result = response["result"]
    assert result["event_type"] == "news"
    assert result["evidence_ids"] == ["agent-evidence"]
    assert result["key_fact_references"][0]["evidence_id"] == "agent-evidence"
    assert not {
        "verified",
        "grounded",
        "factually_correct",
        "entailed",
        "answer_valid",
        "admissible",
        "classification",
        "hypothesis",
        "narrative",
    } & (_keys(input_value) | _keys(response))


@pytest.mark.parametrize(
    ("raw", "expected_code"),
    [
        (b"", "invalid_json"),
        (b"not json", "invalid_json"),
        (b"{", "invalid_json"),
        (b"\xff", "invalid_json"),
        (b'{"contract_version": 1} {"contract_version": 1}', "invalid_json"),
        ({"contract_version": 2, "operation": "unknown"}, "unsupported_contract_version"),
        ({"contract_version": 1, "operation": "event.create"}, "unsupported_operation"),
        ({"contract_version": 1, "operation": "audit.text"}, "invalid_request"),
        (
            {"contract_version": 1, "operation": "audit.text", "input": {}, "extra": 1},
            "invalid_request",
        ),
        (
            {"contract_version": True, "operation": "audit.text", "input": {"text": "ok"}},
            "invalid_request",
        ),
        ({"contract_version": 1, "operation": 7, "input": {"text": "ok"}}, "invalid_request"),
        ({"contract_version": 1, "operation": "audit.text", "input": []}, "invalid_request"),
        (
            {"contract_version": 1, "operation": "audit.text", "input": {"claims": []}},
            "invalid_request",
        ),
        (
            {
                "contract_version": 1,
                "operation": "audit.text",
                "input": {"text": "ok", "unknown": True},
            },
            "invalid_request",
        ),
        (
            {
                "contract_version": 1,
                "operation": "audit.text",
                "input": {"text": "ok", "claim_id": ""},
            },
            "invalid_request",
        ),
        (
            {
                "contract_version": 1,
                "operation": "audit.claims",
                "input": {
                    "claims": [
                        {
                            "claim_id": "",
                            "text": "ok",
                            "requires_direct_evidence": False,
                            "evidence_ids": [],
                        }
                    ],
                    "submitted_claim_ids": [],
                },
            },
            "invalid_request",
        ),
        (
            {
                "contract_version": 1,
                "operation": "audit.text",
                "result": {"passed": True, "findings": []},
            },
            "invalid_request",
        ),
        (
            {
                "contract_version": 1,
                "error": {"code": "execution_failure", "message": "failed"},
            },
            "invalid_request",
        ),
    ],
)
def test_invalid_input_precedence_is_fail_closed(raw, expected_code):
    proc, response = _run(raw)

    assert proc.returncode != 0
    assert response["error"]["code"] == expected_code


def _call_main(monkeypatch, payload: dict, module):
    stdin = io.TextIOWrapper(io.BytesIO(json.dumps(payload).encode("utf-8")), encoding="utf-8")
    monkeypatch.setattr(sys, "stdin", stdin)
    return module.main()


def test_unexpected_supported_execution_is_one_schema_valid_error(monkeypatch, capsys):
    import follow_the_money.agent_invocation as module

    class ExplodingAuditor:
        def audit_text(self, text, *, claim_id=None):
            raise RuntimeError("boom")

    monkeypatch.setattr(module, "ClaimAuditor", ExplodingAuditor)
    code = _call_main(monkeypatch, _request("audit.text", {"text": "ok"}), module)
    captured = capsys.readouterr()

    assert code != 0
    assert "Traceback" not in captured.out
    assert captured.err == ""
    response = json.loads(captured.out)
    validate_against(SCHEMA, response)
    assert response["error"]["code"] == "execution_failure"
    assert "result" not in response


def test_result_mapping_preserves_fields_order_and_pass_state(monkeypatch, capsys):
    import follow_the_money.agent_invocation as module
    from follow_the_money.audit import AuditFinding, AuditResult

    findings = [
        AuditFinding("c1", "missing_evidence", "warning detail", "warning"),
        AuditFinding("c2", "trading_instruction", "critical detail", "critical"),
    ]
    expected_findings = [
        {
            "claim_id": "c1",
            "category": "missing_evidence",
            "detail": "warning detail",
            "severity": "warning",
        },
        {
            "claim_id": "c2",
            "category": "trading_instruction",
            "detail": "critical detail",
            "severity": "critical",
        },
    ]

    class SyntheticAuditor:
        def audit_text(self, text, *, claim_id=None):
            return AuditResult(False, findings)

    monkeypatch.setattr(module, "ClaimAuditor", SyntheticAuditor)
    code = _call_main(monkeypatch, _request("audit.text", {"text": "ok"}), module)
    response = json.loads(capsys.readouterr().out)

    assert code == 0
    assert response["result"] == {"passed": False, "findings": expected_findings}
    assert module._map_result(AuditResult(True, findings)) == {
        "passed": True,
        "findings": expected_findings,
    }


def test_inconsistent_internal_result_fails_closed(monkeypatch, capsys):
    import follow_the_money.agent_invocation as module
    from follow_the_money.audit import AuditFinding, AuditResult

    class InconsistentAuditor:
        def audit_text(self, text, *, claim_id=None):
            return AuditResult(
                True,
                [
                    AuditFinding(
                        "c1",
                        "trading_instruction",
                        "critical detail",
                        "critical",
                    )
                ],
            )

    monkeypatch.setattr(module, "ClaimAuditor", InconsistentAuditor)
    code = _call_main(monkeypatch, _request("audit.text", {"text": "ok"}), module)
    captured = capsys.readouterr()

    assert code != 0
    assert "Traceback" not in captured.out
    assert captured.err == ""
    lines = captured.out.splitlines()
    assert len(lines) == 1
    response = json.loads(lines[0])
    validate_against(SCHEMA, response)
    assert response == {
        "contract_version": 1,
        "error": {"code": "execution_failure", "message": "execution failure"},
    }


def test_agent_values_remain_agent_owned_and_one_addressed_method_runs_once(monkeypatch, capsys):
    import follow_the_money.agent_invocation as module
    from follow_the_money.audit import AuditResult

    calls = []

    class RecordingAuditor:
        def audit_claims(self, claims, submitted_claim_ids, flows=()):
            calls.append((tuple(claims), tuple(submitted_claim_ids), tuple(flows)))
            return AuditResult(True)

        def audit_text(self, text, *, claim_id=None):
            raise AssertionError("sibling audit operation was called")

    monkeypatch.setattr(module, "ClaimAuditor", RecordingAuditor)
    request = _request(
        "audit.claims",
        {
            "claims": [
                {
                    "claim_id": "agent-claim",
                    "text": "Agent supplied text",
                    "requires_direct_evidence": True,
                    "evidence_ids": ["agent-evidence"],
                }
            ],
            "submitted_claim_ids": ["agent-claim"],
            "flows": [{"confirmed": True, "owning_event_id": "agent-event"}],
        },
    )
    assert _call_main(monkeypatch, request, module) == 0
    response = json.loads(capsys.readouterr().out)

    assert len(calls) == 1
    claims, submitted, flows = calls[0]
    claim = claims[0]
    assert (claim.claim_id, claim.text, claim.requires_direct_evidence, claim.evidence_ids) == (
        "agent-claim",
        "Agent supplied text",
        True,
        ("agent-evidence",),
    )
    assert submitted == ("agent-claim",)
    assert (flows[0].confirmed, flows[0].owning_event_id) == (True, "agent-event")
    assert not {
        "classification",
        "grounded",
        "factually_correct",
        "entailed",
        "answer_valid",
        "admissible",
        "policy",
        "model",
        "credential",
    } & (_keys(request) | _keys(response))


def test_invocation_boundary_has_no_grounding_policy_or_runtime_orchestration():
    import follow_the_money.agent_invocation as module

    source = inspect.getsource(module).lower()
    for forbidden in (
        "ground",
        "entail",
        "admissib",
        "policy",
        "credential",
        "model",
        "feed",
        "event.create",
        "feed.",
        ".feed",
        "market.",
        ".market",
        "watchlist",
        "scoring",
        "ranking",
        "registry",
        "retry",
        "rewrite",
    ):
        assert forbidden not in source


def test_event_is_live_without_activation_registry_or_unrelated_callers():
    architecture = (REPO_ROOT / "docs" / "architecture.md").read_text()
    assert "| Evidence Feed | `live-production`" in architecture
    assert "| Deterministic Audit | Implemented by ECO-50 | `live-production`" in architecture
    assert "| Evidence and Event Structuring | `live-production`" in architecture
    for family in (
        "Market Analytics and State",
        "Confidence and Watchlist",
        "Scoring and Ranking",
    ):
        assert f"| {family} | `retained-no-production-caller`" in architecture

    source = inspect.getsource(__import__("follow_the_money.agent_invocation", fromlist=["main"]))
    assert "event.create" not in source
    assert "event.structure" in source
    assert "live-production" not in source
    assert "retained-no-production-caller" not in source
    schema = json.loads((REPO_ROOT / "schemas" / SCHEMA).read_text(encoding="utf-8"))
    assert schema["$defs"]["request_audit_text"]["properties"]["operation"]["const"] == "audit.text"
    assert (
        schema["$defs"]["request_audit_claims"]["properties"]["operation"]["const"]
        == "audit.claims"
    )
    assert (
        schema["$defs"]["request_event_structure"]["properties"]["operation"]["const"]
        == "event.structure"
    )
