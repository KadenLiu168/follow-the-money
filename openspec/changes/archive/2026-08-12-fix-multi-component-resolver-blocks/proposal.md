## Why

Resolver blocks may contain multiple disconnected candidate components, but the current output contract identifies only one top-level component and the pipeline constructs Events only from `block.components[0]`. A valid block-wide seed partition can therefore fail with `ResolutionError` or leave later components represented only as discarded unresolved output, so normal multi-event Feeds are not handled completely or auditably.

## What Changes

- **BREAKING** Replace the resolver output's single top-level `component_alias` with a required `component_alias` on every proposal and unresolved group.
- Validate the complete resolver response atomically at block scope: every alias must exist, every reference must remain inside the named component projection, and every block seed must be assigned exactly once.
- Resolve and merge proposals for every component in a packed block while preserving component-local story-family and coexistence boundaries.
- Retain structured unresolved groups in pipeline audit output instead of silently discarding them.
- Align the resolver prompt, structured-output schema, recorded LLM fixtures, replay bundles, and golden evaluation artifacts with the block-level contract.
- Add regression coverage for multi-component success, cross-component rejection, alias validation, complete seed partitioning, unresolved retention, and deterministic replay.

## Capabilities

### New Capabilities

- `multi-component-resolver-block-processing`: Defines the packed-block resolver response, per-item component ownership, atomic semantic validation, complete Event construction, unresolved audit retention, and replay behavior for blocks containing one or more candidate components.

### Modified Capabilities

None. The related `semantic-event-resolution` and `deterministic-evidence-engine` capabilities currently exist only in the completed but unarchived `implement-follow-the-money-repository` Change, not in `openspec/specs/`; this Change adds the corrective contract as a narrow capability rather than claiming to modify an absent main spec.

## Impact

- Resolver contract: `schemas/resolver-output.schema.json` and `prompts/resolve-events.md`.
- Deterministic merge and validation: `src/follow_the_money/pipeline.py` and `src/follow_the_money/engine/resolution.py`.
- Audit/replay persistence: pipeline result serialization, Bundle members, and saved LLM output loading.
- Tests and fixtures: resolver/schema tests, full pipeline gate tests, golden recorded outputs, offline evaluation, and Bundle replay.
- Compatibility: previously recorded resolver outputs using the top-level alias are incompatible and must be regenerated or explicitly migrated; runtime must not heuristically accept both shapes.
- No provider, Feed ingestion, graph connectivity, block-packing limits, analyst/editor/language-audit contract, ranking, or publication behavior changes beyond consuming the complete resolved/unresolved block result.
