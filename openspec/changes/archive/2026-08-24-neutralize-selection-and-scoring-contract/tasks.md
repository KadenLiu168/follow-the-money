## 1. Apply Preflight and Contract Trace

- [x] 1.1 Re-read ECO-29 scope, the proposal/design/delta, the two affected living requirements, active Changes, `scoring.py`, `selection.py`, all three configuration layers, focused tests, and `docs/scoring.md`; stop and report any conflict rather than expanding into ECO-30, ECO-31, or future Agent work.
- [x] 1.2 Re-run non-archive import/call and symbol tracing for scoring/ranking, every legacy workflow/presentation field, all Brief-only config keys, Morning/Brief names, thresholds/counts, and sparse behavior; confirm there is no production caller and preserve any independently owned behavior discovered by the trace.
- [x] 1.3 Prepare the frozen environment with `uv sync --frozen --all-groups`, record the initial worktree state, and preserve unrelated user changes.

## 2. RED Numerical and Neutral-Contract Tests

- [x] 2.1 Freeze literal exact Decimal oracles from the current implementation for all-known and partially unknown significance vectors, surprise/freshness boundaries, maximum absolute surprise, systemic breadth, exposure/catalyst combinations, the relevance formula, base-priority formula, and hostile ambient Decimal contexts; retain existing fail-closed unmapped-category coverage.
- [x] 2.2 Add RED scoring API/config tests requiring neutral `event_relevance`, `relevance_weights`, and `base_priority` names, exact equality with the frozen numerical oracles, and absence of Morning/Brief aliases.
- [x] 2.3 Add RED closed-configuration tests proving shipped YAML/model/loader agreement and strict rejection of `morning_weights`, `full_priority_threshold`, `compact_priority_threshold`, `target_count`, `hard_max_count`, and `max_full_events` without fallback or dual-name acceptance.
- [x] 2.4 Add RED ranking-shape tests requiring `RankingInput`, `RankedEvent`, `RankingResult`, and `rank_events`; assert the input omits `analysis_present`, `packet_passed`, `conflict_free`, and `breaking_label`, and the output omits `format`, `breaking_unconfirmed`, and `sparse_warning`.
- [x] 2.5 Add RED eligibility/completeness tests proving resolved high, medium, and low confidence Events rank without legacy workflow state, unresolved and below-minimum-coverage Events remain ineligible for their exact reasons, and more than 12 eligible Events are all returned without a replacement tier or limit.
- [x] 2.6 Preserve or strengthen RED ranking regressions for base and final tie-breaks, input-permutation equivalence, configured family penalty, priority zero floor, exact frozen-first-to-later exemption, later-to-later non-exemption, and pairwise non-transitivity.
- [x] 2.7 Add a focused RED repository-boundary regression proving Feed and production entry modules do not import or invoke the retained scoring/ranking library and no external scoring/ranking schema exists; run the focused test selection and record the expected pre-implementation failures.

## 3. Neutral Scoring and Closed Configuration

- [x] 3.1 Rename Morning Relevance to the neutral event-relevance operation/result vocabulary and `brief_priority(...)` to `base_priority(...)`, removing old aliases while leaving inputs, weights, bins, maps, missing-data behavior, Decimal context, coercions, and operation order unchanged.
- [x] 3.2 Atomically rename YAML/model/loader `morning_weights` to `relevance_weights`; retain its exact 40/25/20/15 value and update closed-key and length validation without accepting the old key.
- [x] 3.3 Remove the five Brief-only threshold/count fields from `config/config.yaml`, `Scoring`, and strict loading, preserving significance/base-priority weights, minimum coverage, family penalty, categorical maps, bins/scales, exposure/catalyst maps, and asset-group configuration.
- [x] 3.4 Update scoring/config/no-LLM tests to the single neutral API and run the focused numerical and configuration suite until every literal Decimal, fail-closed, and closed-key regression passes.

## 4. Deterministic Ranking Boundary

- [x] 4.1 Replace selection input/output/result types and entry point with the ranking-neutral names and exact fields from the design, deleting legacy workflow fields, capability helpers, presentation state, and compatibility aliases.
- [x] 4.2 Fail closed on values outside the closed confidence set, then implement eligibility with only unresolved confidence and below-minimum component coverage as rejection conditions, preserving deterministic reason reporting and allowing otherwise valid high, medium, and low confidence inputs.
- [x] 4.3 Preserve the frozen base sort, existing canonical pair normalization, first-family-member tracking, configured penalty, normative Decimal subtraction, zero floor, first-to-later pair exemption, and non-transitive behavior exactly.
- [x] 4.4 Remove full/compact threshold reapplication, format reassignment, hard/target/full counts, truncation, and sparse-warning behavior; return every eligible ranked Event in the preserved final sort with base and final priorities.
- [x] 4.5 Delete or rewrite only tests that enforce removed Analyst/packet/Editor/Breaking/Brief behavior, then run the complete focused scoring/ranking suite until neutral shape, eligibility, completeness, ordering, penalty, pair, and permutation regressions pass.

## 5. Contract and Focused Documentation Alignment

- [x] 5.1 Apply the `Versioned deterministic scoring` delta to the living spec with exact arithmetic preservation, neutral names, closed configuration, typed caller inputs, and honest no-caller/no-schema status.
- [x] 5.2 Rename and apply the `Deterministic ranking and family penalty` living requirement, removing workflow/presentation/count policy while preserving quality gates, complete ordering, family penalty, and pair semantics.
- [x] 5.3 Update `docs/scoring.md` to describe neutral event relevance, base priority, and complete deterministic ranking; remove full/compact, Breaking/Unconfirmed, Brief thresholds/counts, and sparse-output claims without introducing replacement tiers or Agent ownership.
- [x] 5.4 Recheck current README files, `SKILL.md`, architecture docs, external schemas, and archived Changes; modify no additional file unless an ECO-29 change makes one specific current statement directly false, and leave broader baseline cleanup to ECO-31.
- [x] 5.5 Align the directly contradictory `deterministic-core-retention` summary so it no longer requires Morning/Brief terminology, selection formats, or unchanged removed behavior; leave unrelated baseline wording to ECO-31.

## 6. Verification and Scope Audit

- [x] 6.1 Run focused scoring, ranking, configuration, retained-library, and no-production-caller tests and confirm they pass with exact Decimal assertions.
- [x] 6.2 Run `.venv/bin/python scripts/quality_gate.py` and confirm the canonical repository gate passes without substituting a weaker command set.
- [x] 6.3 Run `openspec doctor`, `openspec validate neutralize-selection-and-scoring-contract --strict`, and `openspec validate --all --strict`, and confirm all checks pass.
- [x] 6.4 Review the final diff and reference trace against every acceptance criterion: exact arithmetic/Decimal parity, only two eligibility gates, complete deterministic ranking, unchanged family/pair semantics, closed legacy-key rejection, no aliases/tiers/limits/schema/caller/Agent contract, no ECO-30/ECO-31 scope absorption, and unchanged archived history.
