## Why

The resolver emits `story_family_label` and `distinct_material_development` relations, but the production pipeline discards both before canonical Event construction. Every Event therefore reaches selection as an Event-specific singleton and `distinct_first_member` remains false, so the specified 15-point redundancy penalty and its exact-pair exemption are unreachable despite passing isolated unit tests.

## What Changes

- Add one script-owned semantic materialization stage that validates resolver family labels and coexistence relations after canonical Event IDs exist, then derives canonical family IDs and unordered Event-ID pairs.
- Treat `unknown` and every one-member family as Event-specific singletons; scope every non-singleton family to one resolver component and response.
- Reject the complete resolver response on incorrect position aliases or dangling, self, duplicate, asymmetric, cross-family, cross-component, cross-block, or over-limit relations instead of silently discarding invalid semantics.
- Replace the precomputed `distinct_first_member` production input with validated canonical pair data; let selection determine the frozen first member after base-priority ordering and test the exact first-to-later pair itself.
- Wire the materialized family and pair data through `run_pipeline`, replay, Event output, and deterministic selection.
- Remove or consolidate the unused/no-op family helpers so there is one authoritative production path.
- Add resolver-to-selection regression fixtures, including routine-family penalty, threshold crossing, exact-pair exemption, non-transitivity, singleton handling, invalid-relation rejection, order stability, and recorded replay coverage.

## Capabilities

### New Capabilities

- `production-story-family-resolution`: Defines fail-closed resolver family materialization, canonical family/pair derivation, production pipeline propagation, and frozen-order redundancy selection behavior.

### Modified Capabilities

None. The related `semantic-event-resolution`, `event-analysis-and-ranking`, and `regression-evaluation` capabilities currently exist only in the completed but unarchived `implement-follow-the-money-repository` Change, not under `openspec/specs/`; this corrective Change therefore records its narrow contract as a new capability.

## Impact

- Deterministic resolver merge: `src/follow_the_money/engine/resolution.py` and canonical Event construction.
- Pipeline orchestration: `src/follow_the_money/pipeline.py` must consume validated family/pair materialization before packet creation and selection.
- Selection contract: `src/follow_the_money/selection.py` consumes canonical pair data and computes the exemption only after freezing base order.
- Tests and fixtures: resolver semantics, selection, full pipeline, saved replay, and at least one non-singleton/non-empty coexistence fixture.
- Compatibility: no provider, Feed, scoring-weight, threshold, LLM-pass, editor, audit, or publication contract changes. Invalid resolver family semantics that were previously ignored will become typed fail-closed failures.
- Coordination: `fix-multi-component-resolver-blocks` overlaps `pipeline.py`, `resolution.py`, resolver schema, and fixtures. Its block/component ownership contract should be applied first or rebased explicitly; this Change remains responsible only for component-local family/pair materialization and selection consumption.
