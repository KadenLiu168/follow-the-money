"""Private one-shot Agent invocation for deterministic Audit and Events."""

from __future__ import annotations

import json
import sys
from datetime import date, datetime
from typing import Any

from .audit import AuditClaim, AuditFlow, AuditResult, ClaimAuditor
from .events import build_event, canonical_event_id
from .ledger import SEED_ORIGINS, Ledger, build_ledger_entry, canonical_fact_key
from .schema import SchemaError, validate_against

_SCHEMA = "agent-invocation.schema.json"
_SUPPORTED_OPERATIONS = ("audit.text", "audit.claims", "event.structure")
_ERROR_STATUS = 1


class _RequestError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code


def _error(code: str, message: str) -> dict[str, Any]:
    return {"contract_version": 1, "error": {"code": code, "message": message}}


def _reject_json_constant(value: str) -> None:
    raise ValueError(value)


def _read_request() -> dict[str, Any]:
    try:
        raw = sys.stdin.buffer.read()
        value = json.loads(
            raw.decode("utf-8"),
            parse_constant=_reject_json_constant,
        )
    except (UnicodeDecodeError, ValueError) as exc:
        raise _RequestError("invalid_json") from exc

    if not isinstance(value, dict):
        raise _RequestError("invalid_request")

    version = value.get("contract_version")
    if type(version) is int and version != 1:
        raise _RequestError("unsupported_contract_version")

    operation = value.get("operation")
    if isinstance(operation, str) and operation not in _SUPPORTED_OPERATIONS:
        raise _RequestError("unsupported_operation")

    if set(value) != {"contract_version", "operation", "input"}:
        raise _RequestError("invalid_request")
    try:
        validate_against(_SCHEMA, value)
    except SchemaError as exc:
        raise _RequestError("invalid_request") from exc
    return value


def _map_result(result: AuditResult) -> dict[str, Any]:
    findings = [
        {
            "claim_id": finding.claim_id,
            "category": finding.category,
            "detail": finding.detail,
            "severity": finding.severity,
        }
        for finding in result.findings
    ]
    return {"passed": result.passed, "findings": findings}


def _success(operation: str, result: AuditResult) -> dict[str, Any]:
    response = {
        "contract_version": 1,
        "operation": operation,
        "result": _map_result(result),
    }
    validate_against(_SCHEMA, response)
    return response


def _parse_timestamp(value: str) -> None:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise _RequestError("invalid_request") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise _RequestError("invalid_request")


def _validate_effective_time(value: str | None, precision: str) -> None:
    if value is None:
        return
    try:
        if precision == "instant":
            _parse_timestamp(value)
        elif precision == "date":
            date.fromisoformat(value)
        elif precision == "month":
            year, month = value.split("-")
            if not 1 <= int(year) <= 9999 or not 1 <= int(month) <= 12:
                raise ValueError
        elif precision == "year" and not 1 <= int(value) <= 9999:
            raise ValueError
    except (ValueError, TypeError) as exc:
        raise _RequestError("invalid_request") from exc


def _event_entries(input_value: dict[str, Any]) -> list[Any]:
    evidence_ids = input_value["evidence_ids"]
    for fact in input_value["key_facts"]:
        if (
            fact["entry_type"] not in {"FACT", "CLAIM"}
            or fact["evidence_id"] not in evidence_ids
            or fact["origin_payload"] not in SEED_ORIGINS
        ):
            raise _RequestError("invalid_request")
        _parse_timestamp(fact["knowledge_available_at"])
        _validate_effective_time(fact["effective_time"], fact["effective_precision"])

    entries = []
    seen_fact_ids: set[str] = set()
    for fact in input_value["key_facts"]:
        entry = build_ledger_entry(
            entry_type=fact["entry_type"],
            origin_payload=fact["origin_payload"],
            evidence_id=fact["evidence_id"],
            subject=fact["subject"],
            predicate=fact["predicate"],
            effective_time=fact["effective_time"],
            effective_precision=fact["effective_precision"],
            value=fact["value"],
            unit=fact["unit"],
            knowledge_available_at=fact["knowledge_available_at"],
        )
        if entry.fact_id in seen_fact_ids:
            raise _RequestError("invalid_request")
        seen_fact_ids.add(entry.fact_id)
        entries.append(entry)
    return entries


def _map_event_result(event: dict[str, Any], ledger: Ledger) -> dict[str, Any]:
    key_fact_ids = list(event["key_fact_ids"])
    return {
        "event_id": event["event_id"],
        "event_type": event["event_type"],
        "evidence_ids": list(event["evidence_ids"]),
        "key_fact_ids": key_fact_ids,
        "fully_known_at": event["fully_known_at"],
        "story_family_id": event["story_family_id"],
        "coexistence_pair_ids": [list(pair) for pair in event["coexistence_pair_ids"]],
        "display_label": event["display_label"],
        "economic_effective_time": dict(event["economic_effective_time"]),
        "common_effective_time": (
            None if event["common_effective_time"] is None else dict(event["common_effective_time"])
        ),
        "multiple_effective_times": event["multiple_effective_times"],
        "key_fact_effective_times": [
            {
                "fact_id": item["fact_id"],
                "value": item["value"],
                "precision": item["precision"],
            }
            for item in event["key_fact_effective_times"]
        ],
        "key_fact_references": [
            {"fact_id": fact_id, "evidence_id": ledger.get(fact_id).evidence_id}
            for fact_id in key_fact_ids
        ],
    }


def _success_event(result: dict[str, Any]) -> dict[str, Any]:
    response = {
        "contract_version": 1,
        "operation": "event.structure",
        "result": result,
    }
    validate_against(_SCHEMA, response)
    return response


def _structure_event(input_value: dict[str, Any]) -> dict[str, Any]:
    entries = _event_entries(input_value)
    ledger = Ledger()
    for entry in entries:
        ledger.add(entry)

    event_id = canonical_event_id(
        evidence_ids=input_value["evidence_ids"],
        event_type=input_value["event_type"],
        entity_ids=input_value["entity_ids"],
        defining_fact_keys=[canonical_fact_key(entry) for entry in entries],
    )
    event = build_event(
        event_type=input_value["event_type"],
        evidence_ids=input_value["evidence_ids"],
        entity_ids=input_value["entity_ids"],
        event_defining_fact_ids=[entry.fact_id for entry in entries],
        ledger=ledger,
        subject_zh=input_value["subject_zh"],
        company=input_value.get("company"),
        form=input_value.get("form"),
        member_events=(event_id, *input_value.get("story_family_peer_event_ids", ())),
        coexistence_pairs=[
            (event_id, peer) for peer in sorted(set(input_value.get("coexisting_event_ids", ())))
        ],
    )
    return _map_event_result(event, ledger)


def _emit(response: dict[str, Any]) -> None:
    validate_against(_SCHEMA, response)
    sys.stdout.write(json.dumps(response, ensure_ascii=False, separators=(",", ":")) + "\n")


def main() -> int:
    try:
        request = _read_request()
    except _RequestError as exc:
        _emit(_error(exc.code, exc.code.replace("_", " ")))
        return _ERROR_STATUS

    operation = request["operation"]
    try:
        if operation == "audit.text":
            auditor = ClaimAuditor()
            input_value = request["input"]
            result = auditor.audit_text(input_value["text"], claim_id=input_value.get("claim_id"))
        elif operation == "audit.claims":
            auditor = ClaimAuditor()
            input_value = request["input"]
            claims = tuple(
                AuditClaim(
                    claim["claim_id"],
                    claim["text"],
                    claim["requires_direct_evidence"],
                    tuple(claim["evidence_ids"]),
                )
                for claim in input_value["claims"]
            )
            flows = tuple(
                AuditFlow(flow["confirmed"], flow["owning_event_id"])
                for flow in input_value.get("flows", ())
            )
            result = auditor.audit_claims(claims, tuple(input_value["submitted_claim_ids"]), flows)
        elif operation == "event.structure":
            _emit(_success_event(_structure_event(request["input"])))
            return 0
        else:
            raise AssertionError("validated operation was not dispatched")
        _emit(_success(operation, result))
        return 0
    except _RequestError as exc:
        _emit(_error(exc.code, exc.code.replace("_", " ")))
        return _ERROR_STATUS
    except Exception:  # noqa: BLE001 - invocation boundary must fail closed
        _emit(_error("execution_failure", "execution failure"))
        return _ERROR_STATUS


if __name__ == "__main__":
    raise SystemExit(main())
