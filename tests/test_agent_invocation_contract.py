"""ECO-49 — closed Agent invocation contract checks."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from follow_the_money.schema import SchemaError, validate_against

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "agent-invocation.schema.json"


def _valid(payload: object) -> None:
    validate_against(SCHEMA, payload)


def _invalid(payload: object) -> None:
    with pytest.raises(SchemaError):
        validate_against(SCHEMA, payload)


def test_agent_invocation_schema_accepts_supported_requests_and_audit_results():
    _valid({"contract_version": 1, "operation": "audit.text", "input": {"text": "Buy now."}})
    _valid(
        {
            "contract_version": 1,
            "operation": "audit.claims",
            "input": {
                "claims": [
                    {
                        "claim_id": "c1",
                        "text": "A claim.",
                        "requires_direct_evidence": True,
                        "evidence_ids": ["e1"],
                    }
                ],
                "submitted_claim_ids": ["c1"],
                "flows": [{"confirmed": True, "owning_event_id": "event-1"}],
            },
        }
    )
    _valid(
        {
            "contract_version": 1,
            "operation": "audit.text",
            "result": {"passed": True, "findings": []},
        }
    )
    _valid(
        {
            "contract_version": 1,
            "operation": "audit.claims",
            "result": {
                "passed": False,
                "findings": [
                    {
                        "claim_id": "c1",
                        "category": "trading_instruction",
                        "detail": "prohibited trading instruction detected",
                        "severity": "critical",
                    }
                ],
            },
        }
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"contract_version": 2, "operation": "audit.text", "input": {"text": "ok"}},
        {"contract_version": 1, "operation": "event.create", "input": {"text": "ok"}},
        {"contract_version": 1, "operation": "audit.text"},
        {"contract_version": 1, "input": {"text": "ok"}},
        {
            "contract_version": 1,
            "operation": "audit.text",
            "input": {"text": "ok"},
            "metadata": {},
        },
        {
            "contract_version": 1,
            "operation": "audit.text",
            "input": {"text": "ok", "policy": {"prohibited_terms": []}},
        },
        {"contract_version": 1, "operation": "audit.text", "input": {"text": ""}},
        {
            "contract_version": 1,
            "operation": "audit.text",
            "input": {"text": "ok", "claim_id": "   "},
        },
        {
            "contract_version": 1,
            "operation": "audit.claims",
            "input": {
                "claims": [
                    {
                        "claim_id": "   ",
                        "text": "ok",
                        "requires_direct_evidence": False,
                        "evidence_ids": [],
                    }
                ],
                "submitted_claim_ids": [],
            },
        },
        {
            "contract_version": 1,
            "operation": "audit.claims",
            "input": {
                "claims": [],
                "submitted_claim_ids": [""],
            },
        },
        {
            "contract_version": 1,
            "operation": "audit.claims",
            "input": {
                "claims": [],
                "submitted_claim_ids": [],
                "flows": [{"confirmed": True, "owning_event_id": "   "}],
            },
        },
        {
            "contract_version": 1,
            "operation": "audit.text",
            "result": {"passed": True, "findings": []},
            "error": {"code": "execution_failure", "message": "failed"},
        },
        {
            "contract_version": 1,
            "error": {"code": "execution_failure", "message": "failed"},
            "result": {"passed": True, "findings": []},
        },
        {
            "contract_version": 1,
            "operation": "audit.text",
            "result": {
                "passed": True,
                "findings": [
                    {
                        "claim_id": None,
                        "category": "trading_instruction",
                        "detail": "finding",
                        "severity": "critical",
                    }
                ],
            },
        },
        {
            "contract_version": 1,
            "operation": "audit.text",
            "result": {"passed": False, "findings": []},
        },
        {
            "contract_version": 1,
            "operation": "audit.text",
            "result": {
                "passed": False,
                "findings": [
                    {
                        "claim_id": None,
                        "category": "trading_instruction",
                        "detail": "finding",
                        "severity": "warning",
                    }
                ],
            },
        },
    ],
)
def test_agent_invocation_schema_rejects_invalid_requests_and_results(payload):
    _invalid(payload)


@pytest.mark.parametrize(
    "code",
    [
        "invalid_json",
        "unsupported_contract_version",
        "unsupported_operation",
        "invalid_request",
        "execution_failure",
    ],
)
def test_agent_invocation_schema_accepts_typed_invocation_errors(code):
    _valid({"contract_version": 1, "error": {"code": code, "message": "failure"}})


def test_agent_invocation_schema_exposes_only_bounded_external_names():
    schema_path = REPO_ROOT / "schemas" / SCHEMA
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    operations = {
        schema["$defs"][name]["properties"]["operation"]["const"]
        for name in ("request_audit_text", "request_audit_claims")
    }
    assert operations == {"audit.text", "audit.claims"}

    raw = schema_path.read_text(encoding="utf-8").lower()
    for forbidden in (
        "auditclaim",
        "auditflow",
        "auditresult",
        "claimauditor",
        "follow_the_money.audit",
        "grounded",
        "factually_correct",
        "entailed",
        "answer_valid",
        "admissib",
        "list_capabilities",
        "registry",
        "session",
        "workflow",
        "model",
    ):
        assert forbidden not in raw
