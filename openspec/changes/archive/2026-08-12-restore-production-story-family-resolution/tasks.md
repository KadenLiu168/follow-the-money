## 1. Establish the implementation baseline

- [x] 1.1 Complete or explicitly rebase onto `fix-multi-component-resolver-blocks`, then record the settled component-local resolver input/output boundary before editing overlapping pipeline, resolution, schema, or fixture files.
- [x] 1.2 Inventory live and recorded resolver outputs for non-`unknown` family labels, non-empty coexistence relations, and invalid legacy relations; record which fixtures remain valid and which must be regenerated.
- [x] 1.3 Run and record the focused resolver, Event, selection, full-pipeline, replay, and evaluation tests as the pre-change baseline.

## 2. Add failing vertical and semantic tests

- [x] 2.1 Add failing component-local materialization tests for exact `p00..pNN` aliases, canonical family IDs from sorted Event IDs, independent `unknown` families, non-unknown singleton families, and stable output under equivalent proposal ordering.
- [x] 2.2 Add failing relation-validation tests for valid symmetric pair conversion and rejection of missing reciprocal, self, duplicate, dangling, cross-family, cross-component, cross-response/block, relation-on-singleton, and over-eight relations without partial output.
- [x] 2.3 Replace selection tests that inject `distinct_first_member` with failing canonical-pair tests covering one-time routine penalty, exact first-to-later exemption, later-to-later non-effect, A-B/B-C non-transitivity, and post-penalty threshold crossing.
- [x] 2.4 Add failing `run_pipeline` tests whose resolver output contains multiple proposals in one family and assert the finalized Event family IDs/pairs plus observable penalized, exempted, and excluded selection results.
- [x] 2.5 Add failing saved-replay and equivalent-order fixtures that exercise at least one non-singleton family, one ordinary later-member penalty, and one non-empty exact coexistence pair through the production pipeline.

## 3. Implement authoritative resolver-family materialization

- [x] 3.1 Introduce one component-local materialization result and entry point that builds all canonical Events before deriving any family ID or coexistence pair.
- [x] 3.2 Validate exact response-position aliases and partition non-`unknown` labels only within the supplied component/response while keeping `unknown` and all one-member groups Event-specific singletons.
- [x] 3.3 Validate the complete directed relation graph atomically, require exactly one symmetric declaration per side, and convert valid relations into stable unique unordered Event-ID pairs with exact incident pairs on finalized Events.
- [x] 3.4 Surface semantic violations through the existing typed resolver/pipeline failure path with no fallback or partial publication.
- [x] 3.5 Remove or consolidate `finalize_story_families`, `assign_family_ids`, and any temporary family-label plumbing so production has one authoritative path and no unused/no-op alternative.

## 4. Wire canonical semantics into deterministic selection

- [x] 4.1 Replace the caller-supplied `distinct_first_member` boundary with normalized immutable canonical pair data in `SelectionInput` or the equivalent single selection input contract.
- [x] 4.2 After eligibility filtering and base-order freeze, derive each family's first member inside selection and check only the exact unordered first-to-later pair before applying the 15-point penalty once.
- [x] 4.3 Wire finalized family IDs and canonical pairs from resolver materialization through normal `run_pipeline`, saved replay, Event/packet projection, and selection without changing weights, thresholds, tie-breaks, or other LLM passes.
- [x] 4.4 Verify singleton events, empty pair sets, pairwise non-transitivity, and input-order determinism remain stable in both live-adapter and saved-replay paths.

## 5. Repair regression evidence

- [x] 5.1 Regenerate only resolver/pass outputs and expected artifacts invalidated by the corrected family semantics; preserve provenance and reject rather than normalize invalid legacy relations.
- [x] 5.2 Add a provenance-backed recorded story-family case that asserts canonical members, exact unordered pairs, hand-calculated base/final priorities, the 15-point penalty, exact-pair exemption, and final selected order.
- [x] 5.3 Update validation evidence to explain the previously unreachable production branches and show that the new fixtures traverse resolver output through `run_pipeline` rather than injecting derived selection state.

## 6. Validate and independently review

- [x] 6.1 Run focused resolver, Event, selection, pipeline, Bundle/replay, and offline-evaluation tests after the final implementation revision.
- [x] 6.2 Run the complete project quality gate and confirm zero provider or LLM network calls in offline replay/evaluation.
- [x] 6.3 Run `openspec validate restore-production-story-family-resolution --strict`, global strict validation, and `openspec doctor`; resolve every failure attributable to this Change and record unrelated baseline failures without modifying their artifacts.
- [x] 6.4 Perform a fresh independent requirement-to-design-to-code-to-test review, repair any proven Blocker/High or necessary Medium findings, and rerun every invalidated gate.
