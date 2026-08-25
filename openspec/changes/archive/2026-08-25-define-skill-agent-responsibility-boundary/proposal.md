## Why

ECO-33 defines what deterministic behavior the Skill owns, but it deliberately leaves operational responsibility, mutation/derivation ownership, and cross-boundary trust semantics undefined. ECO-34 must close that narrower gap before ECO-35 can define Agent-output grounding and validation policy, without turning a responsibility contract into a runtime design.

## What Changes

- Add a semantic Skill-Agent responsibility boundary that assigns non-deterministic research intent, interpretation, reasoning, Agent working analysis, conclusions, and user-facing narrative to the Host Agent.
- Assign the accepted semantics, deterministic invariants, capability-local validation, and truthful live-versus-retained status of the six ECO-33 capability families to the Skill.
- Define the deterministic engine as an internal Skill responsibility layer that executes accepted typed/domain invariants, transformations, calculations, canonicalization, ordering, and capability-local validation—not as a third participant, service, facade, endpoint, or runtime boundary.
- Define semantic ownership after mutation or derivation: a consumer-modified or supplemented value becomes consumer/Agent-owned and cannot remain represented as the unchanged original Skill-produced deterministic result.
- Require provenance and authority to be preserved across the boundary: crossing the boundary or processing Agent-supplied information deterministically cannot silently upgrade the originating assertion into verified evidence.
- Narrowly modify `skill-capability-surface` so responsibility, mutation, and trust reference this new capability while Agent objects/schemas, transport, invocation, orchestration, runtime implementation, and ECO-35 grounding/output-validation policy remain deferred.
- Align only stale current-facing documentation during Apply. Production code, schemas, configuration, Providers, financial formulas, caller topology, and deterministic behavior remain unchanged.

## Capabilities

### New Capabilities

- `skill-agent-responsibility-boundary`: Defines Host Agent, Skill, and internal deterministic-engine responsibilities; semantic information/result ownership; mutation/derivation ownership; and preservation of provenance and authority across the boundary.

### Modified Capabilities

- `skill-capability-surface`: Replaces the ECO-34 deferral for responsibility, mutation, and trust with a reference to the accepted responsibility-boundary capability while preserving the six-family taxonomy, execution-status truth, runtime-integration deferrals, and ECO-35 scope.

## Impact

- Affected contracts: one new living capability plus one narrow delta to `skill-capability-surface`; detailed Feed and deterministic-domain behavior remains authoritative in `feed-evidence-pipeline`, `deterministic-research-engine`, and `deterministic-core-retention`.
- Expected documentation alignment during Apply: `SKILL.md`, `docs/architecture.md`, `README.md`, and `README.zh-CN.md` only where existing ECO-34 deferral language becomes stale.
- No production code, tests, schema, configuration, Provider, dependency, LLM/model surface, Agent DTO/facade/adapter/protocol/runtime, state store, production caller, or Feed-to-retained wiring is introduced. `schemas/feed.schema.json` remains the only current serialized external contract, the Evidence Feed remains the only `live-production` family, and all five post-Feed families remain `retained-no-production-caller`.
