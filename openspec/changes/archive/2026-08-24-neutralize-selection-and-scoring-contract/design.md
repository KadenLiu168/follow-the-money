## Context

See `proposal.md` for motivation and the delta spec for normative behavior. Current repository tracing shows that `scoring.py` and `selection.py` are retained deterministic libraries used by tests but not imported by Feed or another production orchestration path. The scoring layer already exposes `base_priority` in `EventScores`, but its callable and intermediate vocabulary still says Morning Relevance and Brief Priority. The selection layer mixes independent ranking behavior with removed workflow gates and Brief rendering/count policy.

The change crosses the scoring API, ranking data model, closed YAML/config-model/loader contract, focused tests, two living capabilities, and `docs/scoring.md`. The second capability change is limited to removing a directly contradictory retained-library summary; it does not perform the broader ECO-31 baseline cleanup. There is no persisted or external serialized scoring/ranking boundary to migrate, and no repository caller that requires compatibility aliases.

## Goals / Non-Goals

**Goals:**

- Make the two retained Python layers legible as deterministic scoring followed by deterministic ranking.
- Preserve exact Decimal results and the existing family algorithm while deleting workflow and presentation policy rather than renaming it.
- Keep configuration closed and atomic across YAML, model, loader, tests, and documentation.
- Make the absence of a production scoring/ranking caller an explicit verified boundary.

**Non-Goals:**

- Defining the origin of caller-supplied scoring values or the consumer of ranked results.
- Redesigning confidence, canonical Event identity, story-family identity, coexistence-pair creation, or pair validation.
- Adding compatibility, migration, serialization, orchestration, batching, limiting, or presentation layers.
- Touching Feed/providers/market formulas, `ClaimAuditor` (ECO-30), or general pre-Agent baseline wording (ECO-31).

## Decisions

### 1. Use direct neutral names and no compatibility aliases

Rename the Morning-specific operation and result field to an event-relevance concept, rename `morning_weights` to `relevance_weights`, and rename `brief_priority(...)` to `base_priority(...)`. Keep `base_priority_weights`, all relevance inputs, configured values, bins, mapping lookups, Decimal context, and operation order unchanged. The implementation should use one neutral name at each layer rather than retaining deprecated wrappers, dual config keys, or duplicated model fields.

This is preferred over retaining Morning terminology because the calculation is no longer owned by a morning Brief, and over Agent-oriented names because no Agent Contract exists. A compatibility period was rejected because repository tracing found no non-test caller and aliases would preserve two truth sources.

### 2. Replace selection shapes with one ranking-only typed boundary

Use ranking-neutral Python names such as `RankingInput`, `RankedEvent`, `RankingResult`, and `rank_events`. The input contains only `event_id`, `fully_known_at`, `base_priority`, `confidence`, `component_coverage`, `story_family_id`, and the existing canonical `coexistence_pairs` projection. The result contains the complete ordered ranked events and deterministic ineligibility reasons. Each ranked event carries `event_id`, `base_priority`, and `final_priority`; it carries no presentation field.

Delete `analysis_present`, `packet_passed`, `conflict_free`, and `breaking_label` instead of making them optional or ignored. Delete the capability helpers that translate those fields into full/compact behavior. Delete `format`, `breaking_unconfirmed`, and `sparse_warning` instead of introducing neutral-looking tiers. This direct replacement is smaller and makes construction/signature tests capable of proving that legacy state is absent.

No new wrapper or request model is added: callers directly supply the existing deterministic domain values. The existing per-input canonical pair information may continue to be normalized into one immutable pair set inside ranking; pair generation and validation remain upstream and unchanged.

### 3. Separate eligibility, base ordering, penalty application, and final ordering without changing their algorithms

Eligibility has exactly two fail-closed outcomes: `unresolved` confidence and coverage below `min_component_coverage`. All resolved confidence levels pass this boundary. A value outside the closed confidence set is an invalid typed input and fails before eligibility rather than becoming a third eligibility reason. Eligible inputs are frozen in the existing base order: base priority descending, parsed `fully_known_at` descending, then Event ID ascending.

Walk that frozen order exactly once to establish each family's first member. A later member receives `family_penalty` unless the canonical unordered pair between that member and the frozen first member exists. A pair between later members does not affect comparison with the first member. Compute `max(0, base_priority - penalty)` inside the normative Decimal context, then apply the existing deterministic final sort. Return all ranked events; do not apply a threshold or slice.

This preserves the current family implementation rather than moving penalty calculation into scoring or redesigning family data. It also avoids a replacement selection-policy abstraction after the old Brief policy is removed.

### 4. Change the closed configuration as one contract

Atomically rename `morning_weights` to `relevance_weights` in `config/config.yaml`, `Scoring`, the strict key allowlist/loader, validation, tests, and documentation. Remove `full_priority_threshold`, `compact_priority_threshold`, `target_count`, `hard_max_count`, and `max_full_events` from all three configuration layers. Retain `significance_weights`, `relevance_weights`, `base_priority_weights`, `min_component_coverage`, `family_penalty`, categorical maps, freshness bins, surprise bins/scales, exposure/catalyst maps, and asset-group mappings.

The strict loader must reject every removed or renamed legacy key. Supporting old and new names, silently dropping legacy keys, or adding a migration framework was rejected because it would weaken the existing closed contract and there is no deployed external configuration migration requirement.

### 5. Prove numerical parity before deleting legacy behavior

Before implementation changes, freeze representative current outputs for all-known, partially unknown, boundary-bin, exposure, and hostile-Decimal-context vectors. Convert these tests to call the neutral names and require exact Decimal equality, not rounded or approximate equality. This guards a semantic rename from accidentally altering weights, missing-data treatment, mapping behavior, or operation order.

In a separate RED group, assert the neutral dataclass/function signatures and outputs omit legacy workflow/presentation fields, all three resolved confidence levels rank, all eligible events beyond 12 are returned, and strict configuration rejects old keys. Preserve or strengthen permutation, zero-floor, configured-penalty, first-to-later pair, later-to-later, and non-transitive tests. Delete only tests whose asserted behavior is intentionally removed.

### 6. Keep the library unwired and documentation focused

Update the two detailed affected living requirements, the directly contradictory retained-library summary, and `docs/scoring.md` during Apply. Add a focused source/import-boundary regression or equivalent deterministic repository check proving Feed and production entry paths do not acquire a scoring/ranking caller. Do not add an external schema merely to test the Python dataclasses. Recheck README files and `SKILL.md`, but leave broader baseline wording to ECO-31 unless an ECO-29 edit makes a specific current statement directly false.

## Risks / Trade-offs

- [Risk] A terminology-only scoring change alters a Decimal result through reordered arithmetic or changed coercion. → Freeze exact pre-change vectors first and require equality under both normal and hostile ambient Decimal contexts.
- [Risk] Legacy Brief policy survives under generic thresholds, tiers, limits, aliases, or ignored fields. → Assert public dataclass/config shapes, reject old config keys, return more than 12 eligible events, and search the scoped implementation/docs for all removed symbols and semantics.
- [Risk] Removing packet/editor gates accidentally removes deterministic evidence-quality protection. → Keep confidence computation out of scope and retain explicit unresolved-confidence and minimum-coverage tests.
- [Risk] Simplifying ranking changes which family member is first or broadens pair exemption transitively. → Preserve a separately frozen base order and mutation-oriented first/later/non-transitive permutation fixtures.
- [Risk] Direct Python renames break an unobserved caller. → Re-run non-archive import/call tracing before Apply; if a production caller exists, stop and report the contract conflict rather than add aliases or widen scope.
- [Risk] Closed configuration becomes inconsistent across YAML, model, loader, and tests. → Make the rename/removal atomic and cover both shipped defaults and strict rejection of every legacy key.
- [Risk] Documentation cleanup absorbs ECO-30 or ECO-31. → Modify only `docs/scoring.md` and directly contradictory ECO-29 statements confirmed by search; report broader stale language without editing it.

## Migration Plan

1. Reconfirm active Changes, callers, and scoped references; capture exact pre-change scoring outputs and RED neutral-contract tests before implementation edits.
2. Rename the scoring vocabulary and configuration atomically while preserving every arithmetic operation and exact output.
3. Replace the selection types/function with the ranking-only boundary, remove legacy gates and presentation/count policy, and keep ordering/family logic unchanged.
4. Synchronize the two living requirements and focused scoring documentation only after implementation and focused tests agree with the delta.
5. Run focused regressions, the canonical repository quality gate, OpenSpec doctor/strict validation, and a final scope/reference audit.

Rollback is a normal code/config/spec/docs revert before archive. No persisted data, deployed service, or external serialized contract requires a staged migration. Archived Changes remain unchanged.
