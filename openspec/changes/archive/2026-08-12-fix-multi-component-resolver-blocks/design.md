## Context

Candidate components are stable, boundary-preserving graph partitions. `pack_blocks()` intentionally places multiple whole components into one bounded resolver request, and the request projection carries an ordered component array with request-local aliases. The current resolver schema instead exposes one top-level `component_alias`, while the pipeline validates seed coverage across the entire block and constructs Events only against the first component. This makes the request unit, response ownership unit, validation unit, and construction unit inconsistent.

The original architecture remains frozen: one logical resolver invocation per packed block, at most 24 seeds and 24 proposals per block, deterministic script-owned Event identity, strict structured output, fail-closed semantic validation, and replay from recorded LLM outputs. The corrective design must preserve those properties rather than bypass packing or add heuristic recovery.

## Goals / Non-Goals

**Goals:**

- Make every resolver proposal and unresolved group explicitly owned by exactly one component in the current block.
- Validate the complete block response before constructing any Event.
- Construct Events for every valid proposal in every packed component without crossing component boundaries.
- Preserve block-wide exactly-once seed coverage and component-local family/coexistence semantics.
- Preserve normalized unresolved results as deterministic audit data and verify them during Bundle replay.
- Fail closed on old, mixed, unknown-alias, cross-component, incomplete, duplicate, or invented-reference output.

**Non-Goals:**

- Changing candidate graph connectivity, component identity, next-fit packing, block limits, or resolver invocation count.
- Adding compatibility fallback for the old top-level alias schema.
- Changing Event identity, scoring, ranking, analyst/editor/language-audit behavior, or provider/Feed contracts.
- Reclassifying unresolved groups as Events or allowing unresolved seeds into downstream ranking.
- General refactoring of the pipeline outside the resolver block boundary.

## Decisions

### 1. Put `component_alias` on every proposal and unresolved group

The resolver output remains one closed object with flat `proposals` and `unresolved_groups` arrays. Each array item SHALL contain a required request-local `component_alias`; the existing top-level alias SHALL be removed. Proposal position aliases remain global to the complete proposal array, while story-family labels and coexistence relations remain scoped to proposals with the same component alias.

This shape matches the existing packed request and block-wide array limits without adding a second nesting/cardinality layer. It also follows the original design language that every proposal/group names one component.

Alternatives considered:

- **One resolver call per component:** simpler local construction, but discards the purpose of block packing and changes invocation, concurrency, deadline, and 40-block capacity semantics.
- **One nested result object per component:** expressible, but adds redundant per-component arrays and new cardinality rules while the existing global proposal positions and caps already operate at response scope.
- **Keep the top-level alias and filter proposals:** cannot represent more than one component and would necessarily omit or misattribute later components.

### 2. Introduce one block-level semantic validation and merge boundary

Resolution code SHALL expose a block-level operation that accepts the `CandidateBlock`, its alias table, the complete resolver output, the immutable Ledger, and the entity resolver. It SHALL first validate the entire output and only then construct Events. Validation SHALL establish:

1. every item has an alias present in the current block;
2. defining seeds, supporting facts, evidence references, and entity references are allowed by the named component projection;
3. every block seed appears exactly once across proposals and unresolved groups;
4. no proposal, unresolved group, family label, or coexistence relation crosses a component boundary;
5. position aliases, family partitions, and coexistence pairs satisfy their existing complete-response rules.

Only after all checks pass SHALL proposals be grouped in canonical block-component order, preserving proposal-array order within each component, and passed to script-owned Event construction. The pipeline SHALL append the returned block Events once; it SHALL no longer select `block.components[0]`.

Alternatives considered:

- **Validate and construct component-by-component:** may construct partial results before discovering an invalid later component and makes atomic failure harder to reason about.
- **Reuse only block-wide seed coverage plus `resolve_component_events`:** catches some cross-component seed references late but does not validate ownership of unresolved, evidence, supporting-fact, entity, or family references.

### 3. Preserve unresolved groups as canonical pipeline audit data

After successful validation, unresolved groups SHALL be normalized from aliases to canonical component/fact/evidence identifiers in canonical block order and exposed separately from Events on `PipelineResult`. Normal runs SHALL persist them as a dedicated indexed Bundle member, and replay SHALL compare the reconstructed unresolved artifact exactly like Events, packets, and analyses. They SHALL not enter analyst packets, selection, or Brief event rendering.

The raw structured resolver response remains in `pipeline/llm.json` for replay input. The normalized unresolved artifact exists so audit consumers do not need to reinterpret model output or alias tables.

Alternative considered:

- **Rely only on raw `llm.json`:** preserves bytes but leaves aliases unresolved and allows the main pipeline result to appear complete while unresolved components are invisible to deterministic audit consumers.

### 4. Treat the schema transition as fail-closed and version-bound

The runtime SHALL accept only the new schema after this Change. Recorded outputs and golden fixtures SHALL be migrated or regenerated before the final gate. No permissive union schema, missing-alias inference, or automatic assignment to `c0` is allowed. Existing Bundle schema/build fingerprints provide the replay boundary: incompatible historical bundles fail verification rather than being silently reinterpreted.

## Risks / Trade-offs

- **[Breaking recorded-output change]** Existing resolver fixtures and run bundles use the top-level alias → update all repository-owned recordings together and assert that old/mixed shapes fail schema validation.
- **[More semantic checks can reveal latent invalid fixtures]** Evidence/support/entity ownership was not consistently enforced at the pipeline boundary → repair fixtures to match their component projections; do not weaken validation.
- **[Partial construction could leak if validation order regresses]** A later invalid component might be discovered after earlier Events are built → keep semantic validation pure and complete before invoking Event construction, with a regression proving zero returned results on failure.
- **[Audit artifact changes Bundle closure]** Adding an unresolved member changes manifests and replay comparisons → update writer, reader, manifest expectations, and tamper/drift tests in the same revision.
- **[Canonical order ambiguity]** Interleaved proposals can otherwise yield inconsistent output order → use block component order, then original proposal-array order within each component; unresolved groups use the same rule.

## Migration Plan

1. Add failing schema and semantic tests for the new item-level alias contract and multi-component block behavior.
2. Change the resolver schema and prompt; update unit fixtures to the new shape.
3. Add the atomic block-level validator/merger and route pipeline resolution through it.
4. Add normalized unresolved data to `PipelineResult`, Bundle persistence, and replay comparison.
5. Regenerate or explicitly migrate every repository-owned saved resolver output; reject the prior top-level-only shape.
6. Run focused resolver/pipeline/replay tests, offline golden evaluation, the complete quality gate, and strict OpenSpec validation.

Rollback requires reverting code, schema, prompt, fixtures, and Bundle expectations as one unit. Mixing old and new artifacts is unsupported.

## Open Questions

None. The governing choices are fixed by the existing packed-block and fail-closed architecture.
