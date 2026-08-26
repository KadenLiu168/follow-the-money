## Why

Phase 5 cannot add a production caller for any retained deterministic capability until the Host-Agent invocation mechanism, serialized compatibility boundary, failure semantics, and authority preservation rules are accepted. ECO-49 establishes that gate now so ECO-50 can prove the boundary with Deterministic Audit and ECO-51 can later extend the same protocol for the minimum Event Structuring use case without reopening common architecture decisions.

## What Changes

- Add a private local one-shot process contract: one UTF-8 JSON request on stdin, one machine-readable JSON response on stdout, diagnostics on stderr, no session/streaming/multiplexing/shared state, and no hidden capability chaining.
- Define one closed major-versioned request/result/error envelope and static namespaced operations `audit.text` and `audit.claims`; unsupported versions, operations, fields, or operation inputs fail closed.
- Define the minimum Agent-facing Audit JSON contract required by ECO-50 without exposing internal Python dataclass/module layout or caller-controlled deterministic policy.
- Distinguish invocation failure from a successful deterministic Audit result containing critical findings; process status communicates invocation success or failure, not Audit pass or grounding status.
- Preserve Agent ownership of Agent-originated values and limit Skill authority to the deterministic transformation or finding guaranteed by the governing living spec, with no provenance, verification, factuality, grounding, entailment, or admissibility upgrade.
- Accept the Phase 5 activation plan: Feed remains live and unchanged; Audit is approved for ECO-50; Evidence/Event Structuring is approved after Audit for ECO-51; Market, Confidence/Watchlist, and Scoring/Ranking remain deferred.
- Keep Audit and Event Structuring `retained-no-production-caller` after ECO-49. Do not add an executable, adapter, production caller, Event payload, registry/discovery layer, fixed pipeline, remote/session framework, LLM runtime, or automatic grounding/recovery behavior.

## Capabilities

### New Capabilities

- `agent-runtime-invocation-contract`: Defines the local one-shot JSON invocation protocol, closed envelopes and Audit operations, compatibility and failure semantics, authority preservation, no-hidden-orchestration rules, and the Phase 5 activation plan.

### Modified Capabilities

- `skill-capability-surface`: Records the accepted invocation contract and activation plan while keeping execution status tied to the real caller graph and keeping activation decisions out of runtime state or configuration.
- `skill-agent-responsibility-boundary`: Replaces obsolete fully-undefined future-invocation wording with a reference to the separate invocation contract while preserving semantic ownership and authority boundaries.
- `agent-grounding-validation-contract`: Removes only stale no-Agent-schema wording while preserving semantic support, admissibility, unsupported-assertion, and recovery ownership.
- `deterministic-research-engine`: Distinguishes internal deterministic Audit structures from the separate Agent-facing serialized representation without changing Audit algorithms or authority.

## Impact

- Apply will add one focused Agent invocation JSON Schema, contract fixtures/checks, and the minimum truthful updates to the four living capabilities and current-facing documentation.
- `schemas/feed.schema.json`, Feed behavior, existing deterministic algorithms, internal Audit Python structures, dependencies, and the production caller graph remain unchanged.
- ECO-50 owns the executable/adapter and Audit production caller. ECO-51 owns Event-specific operations and its production caller. No runtime or integration behavior is implemented or claimed by ECO-49.
