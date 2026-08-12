## 1. Lock the regression contract

- [x] 1.1 Add failing resolver-schema tests requiring `component_alias` on every proposal and unresolved group and rejecting the former top-level-only, mixed, missing, and unknown-shape variants.
- [x] 1.2 Add failing block-resolution tests for two disconnected components in one packed block: two valid proposals produce two Events, proposal-plus-unresolved retains both outcomes, and all-unresolved produces no Events without losing audit data.
- [x] 1.3 Add failing semantic tests for unknown aliases; missing, duplicate, non-seed, invented, out-of-block, and cross-component seed/fact/evidence/entity references; and atomic zero-result behavior when a later component is invalid.
- [x] 1.4 Add failing family/coexistence tests proving global proposal-position aliases remain canonical while same-label families stay separate across components and cross-component relations reject the complete block.
- [x] 1.5 Add a failing full-pipeline regression using a real multi-item Feed that deterministically forms at least two components in one block and asserts complete Event/unresolved results rather than `ResolutionError` or omission.
- [x] 1.6 Add failing Bundle tests for the dedicated normalized unresolved member, exact replay comparison, missing/unindexed/tampered member rejection, and zero provider/LLM calls during replay.

## 2. Replace the resolver response contract

- [x] 2.1 Update `resolver-output.schema.json` to remove the top-level `component_alias` and require it on each proposal and unresolved group while retaining the existing block-wide array and field bounds.
- [x] 2.2 Update `resolve-events.md` to describe one packed block with explicit component boundaries, item-level ownership, complete block seed partitioning, and component-local reference/family rules.
- [x] 2.3 Update schema fingerprints and repository-owned unit fixtures to the new closed shape, with no dual-schema fallback or implicit `c0` assignment.

## 3. Implement atomic block resolution

- [x] 3.1 Add a block-level semantic validator that resolves aliases and validates every proposal/unresolved seed, supporting fact, evidence, entity, position, family, and coexistence reference against the named component before construction.
- [x] 3.2 Preserve block-wide exactly-once seed coverage while making ownership checks component-local and fail the complete response before returning any partial Event or unresolved result.
- [x] 3.3 Add the block-level merge operation that constructs Events for all valid proposals in canonical component order, preserves proposal-array order within each component, and normalizes unresolved groups to canonical identifiers.
- [x] 3.4 Remove the pipeline's `block.components[0]` resolution path and consume the block-level Events and unresolved groups exactly once per resolver block.

## 4. Persist and replay unresolved audit data

- [x] 4.1 Add ordered normalized unresolved groups to `PipelineResult` without feeding them into analyst packets, selection, or Brief Event rendering.
- [x] 4.2 Persist normalized unresolved groups as a dedicated indexed normal-run Bundle member and include it in member-closure and integrity expectations.
- [x] 4.3 Load, reconstruct, and compare the unresolved artifact during deterministic replay, failing closed on schema, ownership, content, or member drift.

## 5. Migrate recordings and prove end-to-end behavior

- [x] 5.1 Regenerate or explicitly migrate every repository-owned saved resolver output and golden fixture to item-level aliases; verify no top-level-only resolver output remains.
- [x] 5.2 Run the focused schema, resolver, pipeline, Bundle, replay, and golden-evaluation tests and repair only failures attributable to this Change.
- [x] 5.3 Run offline evaluation and confirm all dataset/provenance metrics remain valid with zero provider and zero LLM calls.
- [x] 5.4 Run the complete repository quality gate after the final stable revision and record the fresh command outputs in `docs/validation-evidence.md`.
- [x] 5.5 Run `openspec validate fix-multi-component-resolver-blocks --strict` and `openspec validate --all --strict`, then perform a fresh requirement-to-code-to-test review confirming no first-component shortcut, alias inference, partial merge, or unresolved audit loss remains.
