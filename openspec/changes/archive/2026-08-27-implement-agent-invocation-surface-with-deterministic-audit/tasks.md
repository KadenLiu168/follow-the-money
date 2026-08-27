## 1. Focused RED Runtime Contract Tests

- [x] 1.1 Add process-level RED tests for a passing `audit.text`, an `audit.text` critical `trading_instruction`, and a passing `audit.claims`, asserting one valid stdout response and process status `0`.
- [x] 1.2 Add RED tests for valid domain-negative `audit.claims` inputs: empty inventory, duplicate claim ID, submitted ID outside inventory, required evidence with an empty reference list, confirmed flow without owner, and structured prohibited trading text; assert execution status `0`, `passed: false`, and the exact critical finding.
- [x] 1.3 Add RED parsing/classification tests for malformed, empty, non-JSON, invalid-UTF-8, and multiple-value stdin; unsupported integer contract major; unsupported string operation; missing/unknown/wrong-typed fields; operation/input mismatch; unknown input fields; invalid external identities; and both success- and error-response-shaped stdin, asserting the accepted error-code precedence and only a non-zero status.
- [x] 1.4 Add a RED execution-boundary test that forces an otherwise valid supported request to raise unexpectedly and asserts one schema-valid `execution_failure` response, no result, non-zero status, and no stdout traceback.
- [x] 1.5 Add RED result-mapping tests that compare internal and external `passed`, finding count/order, `claim_id`, category, detail, and severity; use a synthetic internal warning only at the mapper boundary and prove a critical result cannot be downgraded or converted to pass.

## 2. Minimum Private Audit Invocation Boundary

- [x] 2.1 Add one private importable `python -m` module with `main() -> int`; read stdin once as strict UTF-8, parse exactly one JSON document with the standard library, emit stdout exactly once, keep diagnostics on stderr, and add no `[project.scripts]` entry or dependency.
- [x] 2.2 Implement structural request classification before root-schema validation with the specified `invalid_json` → unsupported major → unsupported operation → `invalid_request` precedence, using exact types and keys rather than exception-message matching so response shapes cannot dispatch.
- [x] 2.3 Reuse `validate_against("agent-invocation.schema.json", ...)` for closed supported request and emitted response validation, keeping the accepted ECO-49 schema unchanged because no contradiction has been found.
- [x] 2.4 Implement literal `if`/`elif` dispatch for only `audit.text` and `audit.claims`; explicitly map contracted fields to existing internal Audit inputs, map absent `flows` to the existing empty sequence, and introduce no registry, reflection, discovery, or future operation placeholder.
- [x] 2.5 Construct the existing auditor under its current Skill-owned default `SafetyLexicon` semantics with no caller policy/config input, YAML parser, Feed/provider startup, credential, model, or second policy source.
- [x] 2.6 Map the existing result field by field and in existing order, validate the complete success envelope before emission, return `0` for every completed Audit including `passed: false`, and return one implementation-chosen non-zero value for every invocation error without allocating a numeric taxonomy.
- [x] 2.7 Run the focused invocation and existing Audit/schema tests and make only the minimum boundary/test corrections until they pass.

## 3. Authority, Orchestration, Caller, and Feed Regressions

- [x] 3.1 Add focused assertions that Agent-originated text, claims, classifications, and identifiers remain Agent-owned; evidence IDs remain references; and neither request nor result contains grounding, factuality, entailment, answer-validity, admissibility, policy, model, or credential fields.
- [x] 3.2 Add call-count/negative-path tests proving exactly one explicitly addressed Audit method executes once, with no automatic retry, rewrite, sibling Audit operation, Event, Market, Watchlist, Confidence, Scoring, Ranking, or Feed call.
- [x] 3.3 Narrow the existing blanket no-`ClaimAuditor`-caller regression to an exact allowlist for the new invocation module, while continuing to reject Feed, legacy workflow, Event, Market, Watchlist, Confidence, Scoring, Ranking, and every unrelated source caller.
- [x] 3.4 Verify through focused architecture tests that Deterministic Audit alone changes to `live-production`; Evidence/Event Structuring, Market, Confidence/Watchlist, and Scoring/Ranking remain `retained-no-production-caller`; no Event operation or external Event payload exists; and no dynamic activation state or registry exists.
- [x] 3.5 Run existing deterministic Feed contract, schema, generation/publication, workflow-entry, and evidence-only regressions with fixtures; confirm `schemas/feed.schema.json` and Feed production behavior are unchanged without running the side-effecting real Feed dry run.

## 4. Living Specs and Current-Facing Documentation

- [x] 4.1 Apply the six Change deltas to `agent-runtime-invocation-contract`, `skill-capability-surface`, `skill-agent-responsibility-boundary`, `agent-grounding-validation-contract`, `deterministic-research-engine`, and `deterministic-core-retention`; reconcile any stale current Purpose wording those deltas make false, while preserving unrelated retained-capability and historical requirements.
- [x] 4.2 Update only stale caller/runtime statements in `SKILL.md`, `README.md`, `README.zh-CN.md`, and `docs/architecture.md`: describe Feed and on-demand Audit as independent `live-production` capabilities and keep the other four families unwired.
- [x] 4.3 Review the complete caller graph and current-facing text for forbidden implications: no mandatory Feed-to-Audit/Event pipeline, hidden chaining, retry/rewrite loop, semantic-proof authority, public CLI, remote/session/streaming framework, LLM/model/credential runtime, or early ECO-51 implementation.
- [x] 4.4 Confirm no archived Change, dependency, Audit domain rule, SafetyLexicon policy, `schemas/agent-invocation.schema.json`, or `schemas/feed.schema.json` changed; if Apply reveals an actual accepted-schema contradiction, stop and report it instead of silently redesigning the contract.

## 5. Final Verification

- [x] 5.1 Run `git diff --check` and review the complete diff against the ECO-50 allowlist, preserving unrelated worktree content.
- [x] 5.2 Run the focused runtime, Audit, Agent schema, caller-graph, no-LLM, grounding/authority, and Feed regression tests and record exact results.
- [x] 5.3 Run `openspec doctor`, `openspec validate implement-agent-invocation-surface-with-deterministic-audit --strict`, and `openspec validate --all --strict`.
- [x] 5.4 Run `.venv/bin/python scripts/quality_gate.py` and report the exact canonical result without substituting a weaker gate or running a real Feed dry run.
