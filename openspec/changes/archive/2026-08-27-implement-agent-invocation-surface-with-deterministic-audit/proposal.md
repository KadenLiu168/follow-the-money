## Why

ECO-49 accepted the private Host-Agent invocation contract but deliberately left it without an executable or production caller. ECO-50 must now prove that boundary with the smallest approved vertical slice—existing Deterministic Audit—while reconciling living requirements that still describe Audit and all Agent runtime integration as unwired.

## What Changes

- Implement one private local one-shot stdin/stdout JSON entry that explicitly classifies requests, validates the accepted version-1 request variants, statically dispatches only `audit.text` and `audit.claims`, and returns one accepted success or typed error response.
- Explicitly map accepted external Audit values to existing `AuditClaim` and `AuditFlow` inputs and map the existing ordered `AuditResult` back to the accepted external result without exposing internal Python layouts or changing Audit semantics.
- Treat valid deterministic negative Audit outcomes as successful capability execution with process exit `0`; reserve non-zero status for invocation failures classified as `invalid_json`, `unsupported_contract_version`, `unsupported_operation`, `invalid_request`, or `execution_failure` without defining stable numeric non-zero meanings.
- Activate Deterministic Audit as an on-demand `live-production` capability with exactly one approved Host-Agent caller while keeping Feed independent and evidence-only and every other retained capability unwired.
- Narrow caller-graph regressions to permit only the new invocation boundary to call `ClaimAuditor`, and add focused process integration, result-fidelity, authority, failure-classification, and no-hidden-orchestration tests.
- Reconcile stale caller/runtime statements in existing living specs and current-facing documentation. Do not rewrite archived Changes or alter `schemas/agent-invocation.schema.json` unless Apply discovers a concrete accepted-contract contradiction that runtime adaptation cannot satisfy.

## Capabilities

### New Capabilities

None. The runtime implements the already accepted `agent-runtime-invocation-contract`, and Audit behavior remains owned by existing capabilities.

### Modified Capabilities

- `agent-runtime-invocation-contract`: Change the accepted contract from contract-only to an implemented private one-shot boundary, define fail-closed request classification precedence, and record the post-ECO-50 caller graph.
- `skill-capability-surface`: Change Deterministic Audit from `retained-no-production-caller` to the existing `live-production` status while leaving the other four post-Feed families retained and unwired.
- `skill-agent-responsibility-boundary`: Recognize on-demand Audit invocation without changing Host-Agent ownership, bounded Skill authority, or recovery and final-emission responsibility.
- `agent-grounding-validation-contract`: Permit the bounded Audit production caller while preserving that evidence references and Audit success do not prove semantic support, factuality, entailment, overall correctness, or admissibility.
- `deterministic-research-engine`: Replace the Audit no-caller requirement with exactly one approved invocation adapter and preserve all existing deterministic Audit inputs, findings, ordering, and policy semantics.
- `deterministic-core-retention`: Reconcile the former Feed-only invocation and all-retained-no-wiring baseline with the accepted Agent schema and the single approved Audit caller, without weakening no-LLM, Feed, or unrelated retained-library invariants.

## Impact

- Expected Apply scope: one small private invocation module/entry, focused runtime and architecture tests, the six listed living-spec deltas, and truthful updates to `SKILL.md`, `README.md`, `README.zh-CN.md`, and `docs/architecture.md`.
- `schemas/agent-invocation.schema.json` remains the version-1 serialized authority; `schemas/feed.schema.json`, Feed behavior, Audit domain rules, SafetyLexicon policy, dependencies, configuration authority, and archived Changes remain unchanged.
- No public `[project.scripts]` CLI, Event operation, registry/discovery mechanism, workflow engine, remote/session/streaming transport, retry/rewrite loop, mandatory capability sequence, LLM/model/credential runtime, or caller for Market, Confidence/Watchlist, Scoring/Ranking, or Evidence/Event Structuring is introduced.
