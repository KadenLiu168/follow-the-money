## 1. Contract Tests First

- [x] 1.1 Add focused RED schema tests for valid `audit.text` and `audit.claims` requests, a valid pass result, and a valid successful result containing a deterministic critical finding.
- [x] 1.2 Add RED rejection cases for unsupported major versions, unsupported operations, missing fields, unknown/forbidden fields, invalid operation inputs, result/error mixing, and inconsistent `passed`/critical-finding combinations.
- [x] 1.3 Add RED boundary assertions that the external contract exposes no Agent-controlled Audit policy, grounding/factuality/entailment/admissibility proof fields, Event operation, discovery/registry data, session/workflow/model fields, or internal Python type/module names.

## 2. Serialized Agent Invocation Contract

- [x] 2.1 Add `schemas/agent-invocation.schema.json` as one closed Draft 2020-12 schema with version-1 concrete request, successful Audit result, and typed invocation-error variants.
- [x] 2.2 Define only `audit.text` and `audit.claims` inputs, preserving valid deterministic-negative states while rejecting structurally invalid trust-boundary input and excluding Skill-owned safety configuration.
- [x] 2.3 Define the closed Audit finding/result representation and enforce that critical findings remain in the successful result channel while invocation errors remain mutually exclusive and typed.
- [x] 2.4 Run the focused contract tests and make the minimum schema/test corrections until they pass; do not add a runtime adapter, executable, dispatcher, or production caller.

## 3. Architecture and Documentation Alignment

- [x] 3.1 Update only stale current-facing assertions in `tests/test_audit.py` and related architecture tests so internal Audit structures remain internal while the separate contract-only Agent invocation schema is accepted.
- [x] 3.2 Update `SKILL.md`, `README.md`, `README.zh-CN.md`, and `docs/architecture.md` to distinguish the accepted invocation contract from unimplemented runtime wiring and actual capability caller status.
- [x] 3.3 Record the Phase 5 activation matrix in current-facing architecture documentation as planning approval only: Feed remains live; Audit targets ECO-50; Event Structuring targets ECO-51 after Audit; Market, Confidence/Watchlist, and Scoring/Ranking remain deferred.
- [x] 3.4 Verify by static caller/import/config/schema inspection that Feed remains unchanged and evidence-only; Audit and Event Structuring remain `retained-no-production-caller`; and no Event payload, Feed-to-retained wiring, registry/discovery layer, HTTP/MCP/RPC/session framework, LLM runtime, or automatic grounding/pipeline behavior was added.

## 4. Verification

- [x] 4.1 Run focused schema and architecture regressions covering the new contract, Audit semantics, no-LLM boundary, and unchanged Feed boundary; report them as contract checks rather than ECO-50 runtime integration tests.
- [x] 4.2 Run `git diff --check` and review the complete diff against the ECO-49 allowlist, confirming no production implementation, dependency, configuration, internal Audit algorithm, or `schemas/feed.schema.json` change.
- [x] 4.3 Run `openspec doctor`, `openspec validate define-agent-runtime-invocation-contract --strict`, and `openspec validate --all --strict`.
- [x] 4.4 Run `.venv/bin/python scripts/quality_gate.py` and record the exact result without substituting a weaker gate or running the side-effecting Feed dry run.
