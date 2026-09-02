## Why

ECO-74 made runtime continuity authoritative in checkpoint state, so durable dated Feed artifacts now duplicate responsibilities already owned by checkpoint state and Git history. The product publication contract should expose only the current Feed at `feeds/latest.json` before further Agent-driven enablement work builds on the baseline.

## What Changes

- **BREAKING**: Replace successful dual-output publication with latest-only publication at `feeds/latest.json`.
- Stop creating or staging new `feeds/daily/**` artifacts.
- Remove deployment finalization, generated-state validation, and recovery assumptions that require a dated artifact, while preserving checkpoint-based continuity.
- Preserve canonical serialization, candidate validation, deterministic ownership ordering, atomic replacement, crash safety, durability, idempotence, and fail-closed behavior.
- Treat Git history only as repository-level history, not as a runtime API, archive service, or historical query capability.
- Update affected tests and documentation without changing the Feed schema, evidence, provenance, or Host Agent boundary.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `feed-evidence-pipeline`: Change durable Feed publication, hosted finalization, generated-state paths, and checkpoint advancement from dated-plus-latest to latest-only.

## Impact

- Publication and orchestration code under `src/follow_the_money/feed/`.
- Hosted deployment workflow validation/finalization and generated-state path checks.
- Publication, CLI, deployment, checkpoint, determinism, and workflow tests.
- Feed contract, architecture, runbook, README, and Skill documentation that describes dated Feed output.
- No dependency, Feed schema, provider, evidence, provenance, Agent runtime, or LLM/model changes.
