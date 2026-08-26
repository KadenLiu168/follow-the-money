## Context

See `proposal.md` for motivation. The repository has one live serialized Feed contract and mature internal Audit semantics, but no Host-Agent invocation entry, envelope, or Agent-facing Audit representation. ECO-49 is contract-only: its schema must make ECO-50 mechanically unambiguous without creating a runtime or pre-designing ECO-51 Event payloads.

## Goals / Non-Goals

**Goals:**

- Express the complete version-1 request, success, error, `audit.text`, and `audit.claims` boundary in one closed Draft 2020-12 JSON Schema.
- Preserve the existing Audit domain result—including critical findings—as successful operation output distinct from invocation failure.
- Make ownership and bounded authority visible in the contract while keeping non-machine-verifiable semantic rules in living specs and focused architecture tests.
- Leave one narrow extension point: a later approved Change may add another static operation to the same versioned envelope when compatible.

**Non-Goals:**

- No executable, dispatcher, adapter, caller, registry, discovery operation, remote transport, session protocol, or runtime configuration.
- No Event operation or payload, Feed wrapper, internal dataclass serialization, policy override, grounding-proof field, workflow DTO, or automatic orchestration.

## Decisions

### 1. Use one schema with closed concrete message variants

Apply will add `schemas/agent-invocation.schema.json` using JSON Schema Draft 2020-12, matching the repository's existing schema toolchain. Its root `oneOf` will reference closed concrete variants for:

- version-1 `audit.text` request;
- version-1 `audit.claims` request;
- version-1 successful Audit response;
- version-1 invocation-error response.

Each object level uses `additionalProperties: false`. Concrete request variants bind `operation` with `const`, so operation and input cannot mismatch and unsupported operations fail schema validation. This is smaller and stricter than a generic registry-driven envelope or a second operation-metadata document.

Alternative considered: separate common, Audit input, Audit result, and error schema files. Rejected because ECO-49 has one boundary and two operations with one result shape; multiple external files create compatibility surfaces without current value.

### 2. Keep the envelope minimal and asymmetric where malformed requests require it

Request:

```json
{"contract_version": 1, "operation": "audit.text", "input": {"text": "..."}}
```

Successful result:

```json
{"contract_version": 1, "operation": "audit.text", "result": {"passed": false, "findings": [{"claim_id": null, "category": "trading_instruction", "detail": "...", "severity": "critical"}]}}
```

Invocation error:

```json
{"contract_version": 1, "error": {"code": "invalid_json", "message": "..."}}
```

Success echoes the operation because it identifies the result semantics. Error omits it because malformed JSON, a missing operation, or an unsupported operation may provide no trustworthy supported identifier. The response version is always the supported response-envelope version `1`, including when rejecting an unsupported request version.

No correlation ID is added: one process handles one request and produces one response. No generic `status`, timestamp, metadata, diagnostics, or retry field is needed because the mutually exclusive `result`/`error` shapes and process status already carry the stable distinction.

### 3. Map Agent-facing Audit values instead of serializing Python structures

The schema names only values the existing Audit rules consume. `audit.text` carries `text` and optional `claim_id`. `audit.claims` carries claim inventory, independently submitted claim IDs, and optional confirmed-flow ownership values. ECO-50 will own the explicit mapping to internal `AuditClaim`, `AuditFlow`, and `AuditResult`; those Python names and layouts are not schema definitions.

String identities are non-empty and contain at least one non-whitespace character. Structurally invalid identities are invocation errors. Empty claim arrays, duplicate claim IDs, submitted IDs outside the inventory, missing required evidence references, and confirmed flows without owners remain validly submitted domain states so the deterministic Audit can return its existing findings.

Skill-owned `SafetyLexicon` configuration is intentionally absent. An Agent cannot redefine the policy being audited.

Alternative considered: accept an arbitrary JSON object and let `ClaimAuditor` validate everything. Rejected because type/shape validation belongs at the external trust boundary, while only valid domain inputs should reach the retained capability.

### 4. Encode result/error separation and bounded Audit consistency

The success and error variants are mutually exclusive. The Audit result schema enumerates the categories currently produced by the governing internal contract and closes finding objects. It will enforce:

- `passed: true` cannot contain a critical finding;
- `passed: false` contains at least one critical finding;
- a critical Audit outcome remains a successful response shape.

Process status is specified only as zero for successful capability execution and non-zero for invocation failure. ECO-49 does not allocate numeric non-zero exit codes.

Grounding, factuality, entailment, complete correctness, and final admissibility are intentionally not serialized. Tests will reject those proof-like fields and assert that evidence IDs remain only caller-supplied references. Semantic ownership and authority remain normative in the living specs rather than being misrepresented as JSON booleans.

### 5. Treat version 1 as the single compatibility boundary

The version covers the common envelope and all version-1 operations. Internal refactoring is invisible if serialized behavior is preserved. A breaking change to an existing message or operation meaning requires a new major version. A later compatible static operation may be added under version 1 only through an approved Change; ECO-51 decides whether its concrete Event operation meets that rule.

No per-operation or field versions are added. Version negotiation is unnecessary for a private local one-shot boundary: unsupported majors fail closed.

### 6. Make activation a documentation/contract decision, never runtime data

The Phase 5 matrix belongs in OpenSpec and truthful current-facing documentation. It is not included in schema, configuration, or discovery output. ECO-49 changes no caller status. ECO-50 and ECO-51 must each establish real wiring before changing their capability from `retained-no-production-caller`.

## Risks / Trade-offs

- [Closed category enums require deliberate evolution when Audit adds a finding category] → Require an approved contract Change and compatibility assessment instead of silently emitting unknown external values.
- [JSON Schema cannot prove ownership, provenance, or semantic support] → Keep those rules normative in the responsibility/grounding/invocation specs and add focused architecture assertions against forbidden authority-upgrade fields and caller/config wiring.
- [Contract fixtures can be mistaken for runtime integration tests] → Name and document them as schema/architecture checks; completion reporting must state that ECO-50 runtime behavior is unimplemented and untested.
- [One schema grows when ECO-51 adds Event operations] → Accept that bounded growth for a single protocol; split only if a concrete size or ownership problem appears.

## Migration Plan

1. Add the closed schema and focused valid/invalid fixtures/tests without changing `feed.schema.json`.
2. Update current-facing documentation and existing architecture assertions that incorrectly claim no Agent serialized contract exists.
3. Verify that no runtime entry, caller, Event operation, registry, remote/session framework, or Feed wiring was introduced.
4. Roll back by removing only the ECO-49 schema/tests/docs changes; the existing Feed and retained libraries are unaffected because no production path changes.
