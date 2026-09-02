"""ECO-52 — cross-surface Phase 5 acceptance evidence."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from follow_the_money.feed.cli import run_feed as _run_feed
from follow_the_money.feed.validate import assert_feed_identity, validate_feed
from follow_the_money.schema import validate_against
from tests.test_gate_13_1 import CUTOFF, _fixture_registry

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "agent-invocation.schema.json"


def run_feed(**kwargs):
    if "runtime_state_root" not in kwargs and kwargs.get("output_root") is not None:
        output = Path(kwargs["output_root"])
        kwargs["runtime_state_root"] = str(output.parent / f".{output.name}-state")
    return _run_feed(**kwargs)


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


def _request(operation: str, input_value: dict[str, Any]) -> dict[str, Any]:
    return {"contract_version": 1, "operation": operation, "input": input_value}


def _audit_input() -> dict[str, Any]:
    return {
        "claims": [
            {
                "claim_id": "agent-claim",
                "text": "A descriptive statement.",
                "requires_direct_evidence": True,
                "evidence_ids": ["agent-evidence"],
            }
        ],
        "submitted_claim_ids": ["agent-claim"],
    }


def _event_input(
    *,
    event_type: str = "macro_release",
    origin_payload: str = "macro_release",
    evidence_id: str = "ev-1",
    subject: str = "ent_fed",
    subject_zh: str = "美联储",
    predicate: str = "policy_rate",
    value: str | None = "5.0",
    unit: str | None = "percent",
) -> dict[str, Any]:
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
                "effective_time": "2026-08-11T01:00:00Z",
                "effective_precision": "instant",
                "value": value,
                "unit": unit,
                "knowledge_available_at": "2026-08-11T01:00:00Z",
            }
        ],
        "subject_zh": subject_zh,
    }


def _invoke(request: dict[str, Any]) -> tuple[subprocess.CompletedProcess[bytes], dict[str, Any]]:
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        (str(REPO_ROOT / "src"), str(REPO_ROOT), env.get("PYTHONPATH", ""))
    )
    proc = subprocess.run(
        [sys.executable, "-m", "follow_the_money.agent_invocation"],
        cwd=REPO_ROOT,
        env=env,
        input=json.dumps(request, ensure_ascii=False).encode("utf-8"),
        capture_output=True,
        check=False,
    )
    lines = proc.stdout.decode("utf-8").splitlines()
    assert len(lines) == 1, (proc.stdout, proc.stderr)
    response = json.loads(lines[0])
    validate_against(SCHEMA, response)
    return proc, response


def _run_sequence(
    requests: tuple[dict[str, Any], ...],
) -> list[tuple[subprocess.CompletedProcess[bytes], dict[str, Any]]]:
    return [_invoke(request) for request in requests]


def _keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {key for item in value.values() for key in _keys(item)}
    if isinstance(value, list):
        return {key for item in value for key in _keys(item)}
    return set()


def test_feed_only_acceptance_does_not_invoke_agent_boundary(tmp_path, monkeypatch):
    def unexpected_agent_boundary(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("Feed-only acceptance invoked the Agent boundary")

    monkeypatch.setattr(subprocess, "run", unexpected_agent_boundary)
    result = run_feed(
        output_root=str(tmp_path / "out"),
        cutoff=CUTOFF,
        providers_fn=_fixture_registry,
    )

    assert result.exit_code == 0
    assert result.feed is not None
    validate_feed(result.feed)
    assert_feed_identity(result.feed)
    validate_against("feed.schema.json", result.feed)
    assert result.feed["items"]


def test_audit_only_acceptance_returns_a_complete_deterministic_result():
    proc, response = _invoke(_request("audit.claims", _audit_input()))

    assert proc.returncode == 0
    assert proc.stderr == b""
    assert response == {
        "contract_version": 1,
        "operation": "audit.claims",
        "result": {"passed": True, "findings": []},
    }


def test_event_only_acceptance_returns_a_complete_deterministic_result():
    proc, response = _invoke(_request("event.structure", _event_input()))

    assert proc.returncode == 0
    assert proc.stderr == b""
    assert response == {
        "contract_version": 1,
        "operation": "event.structure",
        "result": EXPECTED_EVENT_RESULT,
    }


def test_explicit_audit_event_orders_are_independent_and_result_local():
    audit_request = _request("audit.claims", _audit_input())
    event_request = _request("event.structure", _event_input())

    event_then_audit = _run_sequence((event_request, audit_request))
    audit_then_event = _run_sequence((audit_request, event_request))

    assert [proc.returncode for proc, _ in event_then_audit] == [0, 0]
    assert [proc.returncode for proc, _ in audit_then_event] == [0, 0]
    assert event_then_audit[0][1] == audit_then_event[1][1]
    assert event_then_audit[1][1] == audit_then_event[0][1]


def test_operation_closure_rejects_deferred_capability_at_process_boundary():
    schema = json.loads((REPO_ROOT / "schemas" / SCHEMA).read_text(encoding="utf-8"))
    root_defs = (item["$ref"].rsplit("/", 1)[-1] for item in schema["oneOf"])
    operations = {
        definition["properties"]["operation"]["const"]
        for name in root_defs
        if "input" in (definition := schema["$defs"][name])["properties"]
    }
    assert operations == {"audit.text", "audit.claims", "event.structure"}

    proc, response = _invoke(_request("market.state", {}))

    assert proc.returncode != 0
    assert response == {
        "contract_version": 1,
        "error": {"code": "unsupported_operation", "message": "unsupported operation"},
    }
    assert "result" not in response


def test_successful_results_preserve_agent_evidence_without_authority_upgrades():
    event_request = _request(
        "event.structure",
        _event_input(
            event_type="news",
            origin_payload="news",
            evidence_id="agent-evidence",
            subject="agent-entity",
            subject_zh="Agent 选择的主体",
            predicate="agent_selected_fact",
        ),
    )
    audit_proc, audit_response = _invoke(_request("audit.claims", _audit_input()))
    event_proc, event_response = _invoke(event_request)

    assert audit_proc.returncode == event_proc.returncode == 0
    assert event_response["result"]["key_fact_references"][0]["evidence_id"] == "agent-evidence"
    forbidden = {
        "grounded",
        "verified",
        "entailed",
        "factually_correct",
        "answer_valid",
        "admissible",
        "semantic_support",
        "proof",
        "authority",
    }
    assert not forbidden & (_keys(audit_response) | _keys(event_response))


def test_critical_audit_failure_is_successful_and_unchanged():
    request = _request(
        "audit.claims",
        {
            "claims": [
                {
                    "claim_id": "critical-claim",
                    "text": "今天买入腾讯。",
                    "requires_direct_evidence": True,
                    "evidence_ids": ["evidence-1"],
                }
            ],
            "submitted_claim_ids": ["critical-claim"],
        },
    )

    proc, response = _invoke(request)

    assert proc.returncode == 0
    assert response["result"] == {
        "passed": False,
        "findings": [
            {
                "claim_id": "critical-claim",
                "category": "trading_instruction",
                "detail": "prohibited trading instruction detected",
                "severity": "critical",
            }
        ],
    }
