## Why

Phase-3 Pre-Agent Baseline Acceptance has passed, but the living contract still does not identify which already accepted deterministic behaviors the Skill intentionally owns for future Host-Agent integration. ECO-33 must establish that semantic capability surface now so later Changes can define responsibility and grounding boundaries without prematurely freezing Agent objects, schemas, invocation, orchestration, or runtime architecture.

## What Changes

- Add one closed semantic catalog covering Evidence Feed; evidence and Event structuring; market analytics and state; confidence and watchlist; scoring and ranking; and deterministic audit.
- Define capability ownership as repository/Skill ownership of deterministic behavior and invariants, without allocating future operational responsibility between the Skill and Host Agent.
- Record the Evidence Feed as `live-production` and every post-Feed capability family as `retained-no-production-caller`; treat these labels as architecture descriptions rather than runtime metadata or configuration.
- Distinguish stable semantic capabilities from Provider/configuration/network/publication machinery, serialization/digest helpers, similarity primitives, dataclass layouts, and other internal implementation details.
- Narrowly evolve the Phase-3 living-baseline requirement so a semantic Skill capability surface is permitted while Agent-facing objects and schemas, invocation protocols, adapters, orchestration, ECO-34 responsibility/trust decisions, ECO-35 grounding/validation decisions, and Phase-5 implementation remain deferred.
- Align only current-facing documentation made stale by the accepted Phase-4 semantic surface; do not change production behavior, financial formulas, Provider/Feed behavior, schemas, dependencies, or caller wiring.

## Capabilities

### New Capabilities

- `skill-capability-surface`: Defines the closed semantic catalog, repository-owned deterministic invariants, live-versus-retained status, internal-infrastructure exclusions, and decisions intentionally deferred beyond ECO-33.

### Modified Capabilities

- `deterministic-core-retention`: Modifies only `OpenSpec living baseline matches the active architecture` so the living baseline may define the semantic Skill capability surface while concrete Agent contracts and runtime integration remain undefined.

## Impact

- Affected contracts: one new living capability and one narrow delta to `deterministic-core-retention`; detailed Feed and deterministic-domain behavior remains authoritative in the existing living specs.
- Expected documentation alignment during Apply: `SKILL.md`, `README.md`, `README.zh-CN.md`, and `docs/architecture.md`.
- Production code, tests, configuration, Providers, financial formulas, Feed collection/publication, and `schemas/feed.schema.json` are unchanged. No new serialized contract, Agent facade/adapter, invocation protocol, orchestration layer, model/LLM surface, or production caller is introduced.
