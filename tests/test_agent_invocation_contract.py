"""ECO-51 — closed Agent invocation contract checks."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from follow_the_money.schema import SchemaError, validate_against

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "agent-invocation.schema.json"

EVENT_INPUT = {
    "event_type": "macro_release",
    "evidence_ids": ["ev-1"],
    "entity_ids": ["ent_fed"],
    "key_facts": [
        {
            "entry_type": "FACT",
            "origin_payload": "macro_release",
            "evidence_id": "ev-1",
            "subject": "ent_fed",
            "predicate": "policy_rate",
            "effective_time": "2026-08-11T01:00:00Z",
            "effective_precision": "instant",
            "value": "5.0",
            "unit": "percent",
            "knowledge_available_at": "2026-08-11T01:00:00Z",
        }
    ],
    "subject_zh": "美联储",
}

EVENT_RESULT = {
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
    _valid({"contract_version": 1, "operation": "event.structure", "input": EVENT_INPUT})
    _valid({"contract_version": 1, "operation": "event.structure", "result": EVENT_RESULT})
    nullable_claim = deepcopy(EVENT_INPUT)
    nullable_claim["event_type"] = "default"
    nullable_claim["evidence_ids"] = ["ev-flow"]
    nullable_claim["entity_ids"] = ["raw-subject"]
    nullable_claim["key_facts"][0].update(
        {
            "entry_type": "CLAIM",
            "origin_payload": "flow",
            "evidence_id": "ev-flow",
            "subject": "raw-subject",
            "effective_time": None,
            "effective_precision": "year",
            "value": None,
            "unit": None,
        }
    )
    nullable_claim["story_family_peer_event_ids"] = ["evt_" + "a" * 40]
    nullable_claim["coexisting_event_ids"] = ["evt_" + "b" * 40]
    _valid({"contract_version": 1, "operation": "event.structure", "input": nullable_claim})
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
        {
            "contract_version": 1,
            "operation": "event.structure",
            "input": {**deepcopy(EVENT_INPUT), "key_facts": []},
        },
        {
            "contract_version": 1,
            "operation": "event.structure",
            "input": {
                key: value for key, value in deepcopy(EVENT_INPUT).items() if key != "event_type"
            },
        },
        {
            "contract_version": 1,
            "operation": "event.structure",
            "input": {**deepcopy(EVENT_INPUT), "metadata": {}},
        },
        {
            "contract_version": 1,
            "operation": "event.structure",
            "input": {**deepcopy(EVENT_INPUT), "evidence_ids": "ev-1"},
        },
        {
            "contract_version": 1,
            "operation": "event.structure",
            "input": {**deepcopy(EVENT_INPUT), "evidence_ids": ["   "]},
        },
        {
            "contract_version": 1,
            "operation": "event.structure",
            "input": {**deepcopy(EVENT_INPUT), "event_type": "   "},
        },
        {
            "contract_version": 1,
            "operation": "event.structure",
            "input": {
                **deepcopy(EVENT_INPUT),
                "story_family_peer_event_ids": ["evt_not_canonical"],
            },
        },
        {
            "contract_version": 1,
            "operation": "event.structure",
            "input": {
                **deepcopy(EVENT_INPUT),
                "key_facts": [{**EVENT_INPUT["key_facts"][0], "entry_type": "OBSERVATION"}],
            },
        },
        {
            "contract_version": 1,
            "operation": "event.structure",
            "input": {
                **deepcopy(EVENT_INPUT),
                "key_facts": [{**EVENT_INPUT["key_facts"][0], "origin_payload": "market_data"}],
            },
        },
        {
            "contract_version": 1,
            "operation": "event.structure",
            "input": {
                **deepcopy(EVENT_INPUT),
                "key_facts": [
                    {
                        **EVENT_INPUT["key_facts"][0],
                        "effective_time": "2026-08-11",
                        "effective_precision": "instant",
                    }
                ],
            },
        },
        {
            "contract_version": 1,
            "operation": "event.structure",
            "input": {
                **deepcopy(EVENT_INPUT),
                "key_facts": [
                    {
                        **EVENT_INPUT["key_facts"][0],
                        "knowledge_available_at": "not-a-timestamp",
                    }
                ],
            },
        },
        {
            "contract_version": 1,
            "operation": "event.structure",
            "input": {**deepcopy(EVENT_INPUT), "company": "Acme"},
        },
        {
            "contract_version": 1,
            "operation": "event.structure",
            "input": {**deepcopy(EVENT_INPUT), "form": "13F"},
        },
        {
            "contract_version": 1,
            "operation": "event.structure",
            "input": {
                **deepcopy(EVENT_INPUT),
                "key_facts": [{**EVENT_INPUT["key_facts"][0], "fact_id": "fact_external"}],
            },
        },
        {
            "contract_version": 1,
            "operation": "event.structure",
            "input": {**deepcopy(EVENT_INPUT), "event_id": "evt_external"},
        },
        {
            "contract_version": 1,
            "operation": "event.structure",
            "input": {**deepcopy(EVENT_INPUT), "ledger": {}},
        },
        {
            "contract_version": 1,
            "operation": "event.structure",
            "input": {**deepcopy(EVENT_INPUT), "story_family_id": "fam_external"},
        },
        {
            "contract_version": 1,
            "operation": "event.structure",
            "input": {**deepcopy(EVENT_INPUT), "display_label": "agent label"},
        },
        {
            "contract_version": 1,
            "operation": "event.structure",
            "input": {
                **deepcopy(EVENT_INPUT),
                "key_facts": [{**EVENT_INPUT["key_facts"][0], "parent_ids": []}],
            },
        },
        {
            "contract_version": 1,
            "operation": "event.structure",
            "input": {**deepcopy(EVENT_INPUT), "verified": True},
        },
        {
            "contract_version": 1,
            "operation": "event.structure",
            "input": {
                **deepcopy(EVENT_INPUT),
                "key_facts": [{**EVENT_INPUT["key_facts"][0], "grounded": True}],
            },
        },
        {
            "contract_version": 1,
            "operation": "event.structure",
            "input": {
                **deepcopy(EVENT_INPUT),
                "event_type": "filing",
                "key_facts": [{**EVENT_INPUT["key_facts"][0], "origin_payload": "filing"}],
            },
        },
        {
            "contract_version": 1,
            "operation": "event.structure",
            "input": {
                **deepcopy(EVENT_INPUT),
                "event_type": "filing",
                "form": "   ",
                "key_facts": [{**EVENT_INPUT["key_facts"][0], "origin_payload": "filing"}],
            },
        },
        {
            "contract_version": 1,
            "operation": "event.structure",
            "result": {**deepcopy(EVENT_RESULT), "schema_version": 1},
        },
        {
            "contract_version": 1,
            "operation": "event.structure",
            "result": {**deepcopy(EVENT_RESULT), "verified": True},
        },
        {
            "contract_version": 1,
            "operation": "event.structure",
            "result": {**deepcopy(EVENT_RESULT), "narrative": "agent narrative"},
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
        for name in (
            "request_audit_text",
            "request_audit_claims",
            "request_event_structure",
        )
    }
    assert operations == {"audit.text", "audit.claims", "event.structure"}

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
