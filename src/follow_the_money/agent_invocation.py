"""Private one-shot Agent invocation for deterministic Audit."""

from __future__ import annotations

import json
import sys
from typing import Any

from .audit import AuditClaim, AuditFlow, AuditResult, ClaimAuditor
from .schema import SchemaError, validate_against

_SCHEMA = "agent-invocation.schema.json"
_SUPPORTED_OPERATIONS = ("audit.text", "audit.claims")
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
    passed = result.passed and all(finding["severity"] != "critical" for finding in findings)
    return {"passed": passed, "findings": findings}


def _success(operation: str, result: AuditResult) -> dict[str, Any]:
    response = {
        "contract_version": 1,
        "operation": operation,
        "result": _map_result(result),
    }
    validate_against(_SCHEMA, response)
    return response


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
        auditor = ClaimAuditor()
        if operation == "audit.text":
            input_value = request["input"]
            result = auditor.audit_text(input_value["text"], claim_id=input_value.get("claim_id"))
        elif operation == "audit.claims":
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
        else:
            raise AssertionError("validated operation was not dispatched")
        _emit(_success(operation, result))
        return 0
    except Exception:  # noqa: BLE001 - invocation boundary must fail closed
        _emit(_error("execution_failure", "execution failure"))
        return _ERROR_STATUS


if __name__ == "__main__":
    raise SystemExit(main())
