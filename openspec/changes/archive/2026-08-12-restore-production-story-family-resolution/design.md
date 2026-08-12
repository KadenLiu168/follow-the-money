## Context

The resolver schema and prompt already expose response-position aliases, `story_family_label`, and symmetric `distinct_material_development` relations. The current production merge calls `resolve_component_events()`, which builds each Event without those fields; `build_event()` therefore assigns an Event-specific singleton family. The pipeline then creates `SelectionInput` without `distinct_first_member`, leaving its default false. Isolated Event and selection unit tests pass because they inject family IDs, member lists, pairs, or the boolean directly, while normal pipeline and recorded replay fixtures use only singleton/unknown cases.

The frozen product contract remains script-first/LLM-last: the LLM may propose bounded response-local family labels and pairwise relations, but scripts exclusively validate them, derive canonical IDs, decide the frozen first member, apply penalties, and determine publication eligibility. No new model call or heuristic clustering is permitted.

The active `fix-multi-component-resolver-blocks` Change overlaps resolver ownership and pipeline orchestration. This design deliberately operates on one explicit component-local proposal set so it can sit beneath either the current orchestration or the planned multi-component loop. Applying the multi-component Change first minimizes merge and fixture churn.

## Goals / Non-Goals

**Goals:**

- Restore the specified family penalty and exact-pair exemption in live and replay production paths.
- Establish one authoritative, fail-closed semantic materialization path after canonical Event IDs exist.
- Keep unknown and singleton families Event-specific and prevent cross-boundary family construction.
- Make selection compute pair exemption from canonical evidence after freezing base order.
- Add end-to-end regression evidence that cannot pass by injecting already-derived selection flags.

**Non-Goals:**

- Change the resolver JSON shape, family-label grammar, relation enum, scoring weights, 15-point penalty, thresholds, or tie-break order.
- Add semantic similarity, embeddings, transitive family inference, category quotas, or another LLM pass.
- Rework candidate graph construction, block packing, provider ingestion, editor allocation, claim audit, or publication mechanics.
- Own block-to-component routing or unresolved-group persistence; those remain in `fix-multi-component-resolver-blocks`.

## Decisions

### 1. Use one component-local semantic materializer

Create one authoritative resolution operation that receives an explicit component and its ordered resolver proposals, constructs all canonical Events, validates family/relation semantics, and returns finalized Events plus the canonical pair set. The operation proceeds in this order:

1. Validate that proposal aliases are exactly `p00..pNN` for array positions and that referenced facts/evidence/entities remain valid for the supplied component.
2. Build all canonical Events without trusting response-local family labels as IDs.
3. Build the alias-to-Event-ID table from the completed Event array.
4. Partition non-`unknown` labels within this invocation only; derive a multi-member family ID from sorted member Event IDs and use Event-specific singleton IDs for `unknown` or one-member groups.
5. Validate every directed coexistence declaration against the closed component-local graph, require exactly one reciprocal declaration, and canonicalize each valid undirected edge to a sorted Event-ID pair.
6. Return immutable/stably ordered family and pair data; each Event records its incident canonical pairs for audit and downstream projection.

This ordering is required because family IDs and coexistence pairs depend on canonical Event IDs, while Event identity must remain independent of model-provided family labels.

**Alternative considered:** call the existing `assign_family_ids()` after `resolve_component_events()`. Rejected because proposal labels are never preserved, all `unknown` labels are currently grouped together, coexistence relations are not validated or converted, and the separate no-op finalizer leaves multiple competing paths.

### 2. Reject invalid family semantics atomically

Position aliases, labels, and relations form one semantic graph. Any incorrect alias, dangling/self/duplicate/asymmetric edge, invalid family scope, relation on an unknown/singleton family, or bound violation raises `ResolutionError` for the complete resolver response. The pipeline surfaces this as its existing typed normal-path failure and does not publish a partially materialized result.

Schema validation remains responsible for shape, grammar, enum, and array bounds; the semantic materializer owns relationships that JSON Schema cannot prove. Saved replay executes the same validation rather than trusting previously recorded structured output.

**Alternative considered:** ignore invalid relations while retaining events. Rejected because silently dropping the only exemption evidence changes ranking and violates the established fail-closed contract.

### 3. Pass canonical pairs, not a caller-owned exemption boolean

Replace the production use of `SelectionInput.distinct_first_member` with canonical coexistence-pair data, represented as normalized immutable Event-ID pairs. After eligibility filtering and base-order freeze, selection records the first member for each family and checks membership of `sorted(first_event_id, current_event_id)` in the validated pair set.

The selection layer therefore owns the only point where `first member` exists. It applies the penalty once per later member and does not infer transitive pairs. A per-Event incident pair collection may be used at the input boundary, but selection normalizes it to one set and rejects or ignores no semantic errors; all semantic validation must already have succeeded upstream.

**Alternative considered:** compute `distinct_first_member` in `run_pipeline`. Rejected because the first member depends on post-analysis base priority and tie-breaks, so an upstream boolean duplicates order-sensitive selection logic and can become stale or inconsistent.

### 4. Preserve current external schemas while improving Event provenance

No resolver-output shape change is needed. Finalized Events continue using `story_family_id` and `coexistence_pair_ids`; the latter contains stable sorted incident pairs. Pipeline selection consumes those canonical values, and any aggregate pair set is a deterministic union rather than new model output. Response-local family labels and proposal aliases remain runtime/audit inputs and are never authoritative Event identity.

This keeps normal output compatibility for singleton cases. Valid previously recorded non-singleton outputs begin affecting ranking as originally specified; invalid recorded relations now fail replay and must be regenerated.

### 5. Require vertical regression coverage

Unit tests remain useful for validation matrices, but acceptance requires fixtures that enter through resolver structured output and pass through canonical Event construction, scoring, and `run_pipeline` selection. Tests SHALL assert canonical family IDs/pairs and observable final priorities or exclusion, not only schema validity.

At least one recorded replay fixture must contain three related Events so the suite can distinguish: ordinary penalty, exact first-to-later exemption, and non-transitive later-to-later behavior. Equivalent-order fixtures must update position aliases consistently and prove stable canonical results.

## Risks / Trade-offs

- **[Overlap with multi-component resolver work]** Both Changes touch `pipeline.py`, `resolution.py`, schemas/fixtures, and pipeline tests. → Apply `fix-multi-component-resolver-blocks` first, then rebase this Change and keep the materializer API component-local.
- **[Previously accepted saved outputs may fail]** Replay will begin enforcing semantic relations that were previously ignored. → Inventory recorded non-unknown labels/relations, regenerate invalid fixtures, and do not add a permissive compatibility path.
- **[Pair representation may drift between Event and selection]** Duplicate directional declarations or list ordering could produce inconsistent checks. → Canonicalize once to sorted tuples, store stable incident lists, and derive one immutable union for selection.
- **[Unit tests can again bypass production wiring]** Direct `SelectionInput` construction could mask a future disconnect. → Require `run_pipeline` assertions for both penalty and exemption branches in the quality gate.
- **[Ranking changes are intentional but user-visible]** Restoring the penalty may remove duplicated events or reorder Top 3. → Pin hand-calculated priorities and threshold-crossing expectations in replay fixtures and document the correction in validation evidence.

## Migration Plan

1. Complete or explicitly rebase onto `fix-multi-component-resolver-blocks` so component ownership has one settled contract.
2. Add failing semantic-materialization tests and failing `run_pipeline` penalty/exemption tests before changing production behavior.
3. Implement the single component-local materializer and remove/consolidate the no-op or unused family helpers.
4. Replace the selection boolean boundary with canonical pair consumption and wire live/replay paths.
5. Add or regenerate recorded non-singleton family fixtures and run focused resolver, selection, pipeline, replay, and evaluation gates.
6. Run the complete project quality gate and independently review requirement-to-code-to-test traceability.

Rollback is a normal code revert because there is no persistent database or external API migration. Recorded fixtures updated to the corrected semantics should be reverted with the code if rollback is required.

## Open Questions

None. The family scope, pair validation, penalty amount, frozen-order rule, non-transitivity, failure policy, and Change sequencing are already determined by the existing product contract and this proposal.
