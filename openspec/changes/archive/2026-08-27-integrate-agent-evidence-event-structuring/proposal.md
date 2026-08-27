## Why

ECO-49 and ECO-50 established and implemented the private one-shot Host-Agent invocation boundary, but accepted deterministic Evidence/Event Structuring still has no production caller. ECO-51 is now unblocked and can expose the smallest justified Event vertical slice without redesigning the retained Ledger/Event algorithms or creating a stateful Ledger API.

## What Changes

- Add one additive version-1 operation, `event.structure`, to the existing closed `contract_version` / `operation` / `input` envelope and shared success/error model.
- Define a closed Agent-facing request for already-selected evidence, entity identities, Event-defining facts, optional family/coexistence inputs, and only the structured display inputs required by existing deterministic templates.
- Explicitly map the request through an invocation-local `Ledger` and the existing canonical fact/Event constructors, then return a closed minimal Event result plus ordered `fact_id` / `evidence_id` references.
- Fail closed on malformed, unknown, contradictory, or untraceable trust-boundary inputs; do not silently repair provenance or identity conflicts.
- Preserve Host-Agent ownership of classifications, selections, hypotheses, and display inputs, with no grounding, factuality, entailment, verification, admissibility, or narrative claim.
- Change Evidence and Event Structuring to on-demand `live-production` only after the real caller and tests exist; leave Feed independent and leave Market, Confidence/Watchlist, and Scoring/Ranking unwired.
- Add contract, process-integration, deterministic-preservation, authority, caller-graph, and no-hidden-orchestration tests, then reconcile current-facing architecture and Skill documentation.

## Capabilities

### New Capabilities

None. This Change exposes a bounded operation for already accepted Event semantics through the existing invocation capability.

### Modified Capabilities

- `agent-runtime-invocation-contract`: Add the closed `event.structure` request/result variants, static dispatch semantics, Event-specific trust-boundary consistency rules, and the post-ECO-51 caller graph.
- `skill-capability-surface`: Change Evidence and Event Structuring from `retained-no-production-caller` to on-demand `live-production` while keeping every other deferred family unchanged.
- `skill-agent-responsibility-boundary`: Define ownership and bounded authority for Agent-selected Event inputs and the deterministic Event result.
- `deterministic-research-engine`: Permit exactly the approved invocation adapter to construct invocation-local facts/Ledger state and call existing canonical Event behavior without changing its algorithms or internal Python contracts.

## Impact

- Expected Apply scope: `schemas/agent-invocation.schema.json`, the existing private invocation runtime plus at most one small Event mapping helper, focused contract/runtime/domain/caller-graph tests, the four listed living-spec deltas, truthful updates to `SKILL.md`, both READMEs, and `docs/architecture.md`, and only the minimum deterministic-core correction if RED permutation/cross-process tests prove an existing accepted Event invariant is violated.
- No new dependency, provider/configuration change, Feed behavior/schema change, standalone Event/Ledger schema, public CLI, persistent state, capability registry, second transport, automatic capability chaining, LLM/model/credential runtime, or unrelated retained-capability caller is introduced.
- `contract_version: 1`, existing Audit messages, shared invocation errors, and the accepted deterministic Ledger/Event implementations remain authoritative and backward compatible.
