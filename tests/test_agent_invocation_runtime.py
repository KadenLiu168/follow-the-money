"""ECO-50 — private one-shot Agent Audit invocation boundary."""

from __future__ import annotations

import inspect
import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from follow_the_money.schema import validate_against

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "agent-invocation.schema.json"


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


def test_only_audit_is_live_and_no_event_operation_or_activation_registry_exists():
    architecture = (REPO_ROOT / "docs" / "architecture.md").read_text()
    assert "| Evidence Feed | `live-production`" in architecture
    assert "| Deterministic Audit | Implemented by ECO-50 | `live-production`" in architecture
    for family in (
        "Evidence and Event Structuring",
        "Market Analytics and State",
        "Confidence and Watchlist",
        "Scoring and Ranking",
    ):
        assert f"| {family} | `retained-no-production-caller`" in architecture

    source = inspect.getsource(__import__("follow_the_money.agent_invocation", fromlist=["main"]))
    assert "event.create" not in source
    assert "live-production" not in source
    assert "retained-no-production-caller" not in source
    schema = json.loads((REPO_ROOT / "schemas" / SCHEMA).read_text(encoding="utf-8"))
    assert schema["$defs"]["request_audit_text"]["properties"]["operation"]["const"] == "audit.text"
    assert (
        schema["$defs"]["request_audit_claims"]["properties"]["operation"]["const"]
        == "audit.claims"
    )
