## Why

`remove-standalone-runtime` established the correct Agent-only, deterministic architecture, but its cleanup left three local contract inconsistencies: the internal Feed entry infers exit categories from exception messages, repository documentation still describes a pre-Git bootstrap state, and the retained-core specification claims standalone JSON Schema validation for internal structures that have no such schemas. These mismatches should be corrected now so implementation, OpenSpec, and long-lived documentation describe the same post-Change-1 system.

## What Changes

- Replace message-based Feed CLI exit classification with two explicit, minimal exception categories: input/configuration/startup-capability failures exit `2`, while execution/runtime/publication/integrity failures exit `1`; healthy and degraded success remain `0`, and `argparse` keeps its native usage exit `2`.
- Add focused CLI tests proving exit codes depend on exception type rather than wording, including healthy, degraded, and `argparse` behavior.
- Remove obsolete claims from `README.md`, `README.zh-CN.md`, and `SKILL.md` that the repository is not a Git checkout or lacks history/remotes, while preserving durable deployment and evidence-cutoff boundaries.
- Correct the retained-core contract and architecture documentation: the Feed is the current serialized external artifact validated against `feed.schema.json`; internal deterministic structures are protected by Python types, domain invariants, validation, and deterministic tests rather than one standalone JSON Schema per object.
- Keep the Agent-only architecture unchanged. Do not restore or redesign the removed LLM runtime, prompts, pipeline, public CLI, old schemas, bundle/replay, evaluation runtime, or any future Agent delivery contract.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `deterministic-core-retention`: Make the internal Feed entry's `0/1/2` exit-category contract explicit and align retained validation requirements with the actual Feed JSON Schema boundary and typed/domain-tested internal structures.

## Impact

- Affected implementation: `src/follow_the_money/feed/cli.py` and focused Feed CLI tests.
- Affected documentation: `README.md`, `README.zh-CN.md`, `SKILL.md`, and `docs/architecture.md`.
- Affected specification: `openspec/specs/deterministic-core-retention/spec.md` through this Change's delta spec.
- No new dependency, public command, serialized artifact, JSON Schema, provider behavior, financial calculation, LLM integration, Agent contract, or deployment action is introduced.
