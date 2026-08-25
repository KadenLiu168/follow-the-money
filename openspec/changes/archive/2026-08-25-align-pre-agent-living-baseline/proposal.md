## Why

The implementation and all three living OpenSpec specifications already describe an Agent-only repository whose only live production path is the credential-free evidence Feed, but several current-facing documents still blur that boundary or pre-design a future Agent topology. ECO-31 must align those claims now so ECO-32 can strengthen acceptance gates against a truthful Pre-Agent baseline rather than encode stale architecture.

## What Changes

- Record the audit result that `deterministic-core-retention`, `feed-evidence-pipeline`, and `deterministic-research-engine` already distinguish the live Feed path, retained no-caller deterministic libraries, and an undefined future Skill-Agent Contract; preserve those living requirements unchanged.
- Replace the concrete future pipeline in `docs/architecture.md` with the current `Provider -> deterministic Feed -> Host Agent` topology, a non-sequential inventory of retained deterministic libraries, and an explicitly undefined future boundary.
- Correct `SKILL.md` so the minimal Feed entry owns Feed collection and Feed processing only; the Host Agent owns interpretation and narrative, and retained post-Feed libraries are not claimed as entry-orchestrated.
- Clarify ambiguous English and Chinese README wording so only the Feed production path is described as live, while retained libraries are described as tested and intentionally not production-orchestrated.
- Narrow the `pyproject.toml` package description so it does not present retained libraries as parts of the evidence-only Feed; keep dependency and build configuration unchanged.
- Audit other current-facing documentation and existing architectural tests, changing only confirmed stale claims. Preserve archived Changes and dated historical evidence unchanged.
- Keep runtime behavior, tests, configuration, Provider contracts, schemas, formulas, scoring, ranking, audit behavior, deployment, and production wiring unchanged. Do not implement ECO-32 acceptance-gate work.

## Capabilities

### New Capabilities

None. ECO-31 introduces no new system capability.

### Modified Capabilities

None. The three living capabilities already state the required architecture, so this documentation-only Change declares `skip_specs: true` rather than inventing a spec delta.

## Impact

- Current-facing documentation and package metadata: `docs/architecture.md`, `SKILL.md`, `README.md`, `README.zh-CN.md`, and the descriptive `pyproject.toml` metadata only.
- OpenSpec planning evidence: this Change records the living-spec audit and the implementation/caller/test trace used to justify zero delta specs.
- Runtime and compatibility: no code, API, serialized Feed, configuration, Provider, schema, financial rule, test behavior, deployment, dependency, or caller-graph change.
- Historical evidence: no file under `openspec/changes/archive/` and no dated validation record is modified.
