## Why

Phase 4 now defines the Skill capability surface and Skill-Agent responsibility boundary, but it still defers the semantic rules for representing Host-Agent factual assertions as grounded and for deciding whether Agent-owned output is admissible. ECO-35 closes that gap now that ECO-34 is accepted, without choosing or implying a runtime integration mechanism.

## What Changes

- Add a runtime-neutral grounding contract that distinguishes an evidence reference from semantic support and bounds grounded assertions by the authority of their supporting Evidence Feed evidence and Skill-produced deterministic results.
- Assign semantic support assessment and the operational decision to emit Agent-owned narrative to the Host Agent, while preserving the Skill's ownership of accepted deterministic findings within each governing capability.
- Define fail-closed output admissibility for known unsupported grounded factual assertions and unresolved applicable critical deterministic findings.
- Define semantic recovery: a later candidate may be emitted only after the relevant grounding or deterministic-validation violation no longer applies, without prescribing retries, rewrites, invocation order, or recovery topology.
- Replace the Phase-4 living baseline's ECO-35 deferrals with references to the new contract and minimally align current-facing documentation.
- Keep production implementation, `feed.schema.json`, retained-capability caller status, and the evidence-only Feed boundary unchanged.

## Capabilities

### New Capabilities

- `agent-grounding-validation-contract`: Defines grounding, semantic-support ownership, deterministic-validation authority, output admissibility, unsupported-assertion handling, and semantic recovery at the Skill-Agent boundary.

### Modified Capabilities

- `skill-agent-responsibility-boundary`: Replaces the ECO-35 grounding and output-policy deferral with an explicit reference to `agent-grounding-validation-contract` while retaining the existing responsibility and runtime-neutrality boundary.
- `skill-capability-surface`: Replaces unresolved ECO-35 grounding, validation, unsupported-claim, and recovery deferrals with the new governing capability while preserving the closed six-family catalog and execution-status classifications.

## Impact

- Adds one living semantic capability and updates two existing Phase-4 living capabilities through OpenSpec deltas.
- Requires minimal alignment in `docs/architecture.md`, `SKILL.md`, `README.md`, and `README.zh-CN.md` so current-facing claims refer to the accepted contract rather than ECO-35 as future work.
- Requires architecture and focused regression verification, including the retained deterministic audit behavior and the absence of Agent schemas, adapters, facades, production wiring, and new serialized external contracts.
- Does not require production-code, dependency, API, schema, provider, configuration, or runtime changes.
