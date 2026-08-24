## Context

See `proposal.md` for motivation and the delta spec for the normative contract. Repository inspection found no active OpenSpec Changes and no production caller for the retained scoring library. `significance_components(...)` already evaluates Systemic Breadth inside `normative_decimal_context()`, and `event_significance(...)` independently owns its Decimal context. `docs/scoring.md` already defines precision 50, `ROUND_HALF_EVEN`, and ambient-context independence.

The coverage gap is narrower than the implementation: an existing fractional breadth oracle uses `affected_groups = 3`, while the existing hostile-context scoring test uses `affected_groups = 9`. The latter produces an exact integer breadth and therefore cannot detect ambient precision leakage on the Systemic Breadth division.

## Goals / Non-Goals

**Goals:**

- Make the normative formula, versioned configuration, defined operation order, and repository-owned Decimal context the complete authority for deterministic scoring results.
- Preserve semantic parity across the neutral scoring terminology without preserving numeric artifacts from an ambient-context calculation path.
- Add one focused regression that exercises fractional Systemic Breadth and downstream Event Significance across materially different ambient Decimal contexts.
- Keep the eventual implementation delta limited to tests and the single focused documentation correction unless fresh Apply-time evidence reveals a direct in-scope defect.

**Non-Goals:**

- Changing scoring formulas, weights, maps, bins, configuration, coverage, relevance, confidence, family penalties, or ranking behavior.
- Reworking `normative_decimal_context`, adding a second Decimal helper, or restoring ambient-context arithmetic.
- Adding schemas, compatibility aliases, production callers, Agent-facing types, Agent orchestration, or broader documentation cleanup.
- Editing the archived ECO-29 Change or treating historical output as a second contract.

## Decisions

### 1. The normative deterministic contract wins over historical implementation parity

ECO-29 exposed a conflict between historical implementation parity and the repository's normative Decimal invariant. The normative deterministic contract wins for current behavior.

The living requirement will preserve formulas, configured weights, categorical mappings, surprise bins, missing-data semantics, and operation order, then state that the owned high-precision Decimal context determines numerical results independently of ambient process settings. A historical result produced outside that context is an implementation artifact, not an independent source of truth.

Reverting Systemic Breadth to ambient arithmetic was rejected because it would weaken determinism. Editing the archived ECO-29 Change was rejected because archived artifacts record history; the current delta corrects the accepted contract without rewriting that history.

### 2. Preserve the current production implementation

The current Systemic Breadth path already has the required shape:

```text
with normative_decimal_context():
    breadth = affected_groups / 9 * 100
```

No production-code change is planned. Apply-time inspection must reconfirm this exact ownership before tests are changed. If a separate in-scope violation is found, implementation work must stop and report the conflict instead of silently broadening this Change.

### 3. Close the fractional hostile-context gap through existing scoring boundaries

Add a focused test in the existing scoring test surface using `affected_groups = 1` or `3`. Evaluate equivalent inputs through `significance_components(...)` and `event_significance(...)` under at least two materially different ambient precision/rounding combinations. Capture Systemic Breadth and Event Significance from each run and require exact equality to the normative contract oracle and to each other.

The test will exercise the scoring functions rather than reproduce a separate scoring implementation. It will preserve the existing hostile-context coverage for relevance and base priority and the existing fractional literal oracle. A divisible `9 / 9 * 100` input is specifically unsuitable for this regression because it cannot expose precision leakage.

### 4. Keep contract and documentation edits surgical

The delta modifies the complete existing `Versioned deterministic scoring` requirement and rewrites its equivalent-vector scenario. During a separately authorized sync or archive, that delta becomes the living requirement; Apply itself does not rewrite archived history.

The only planned documentation edit is the final Market State sentence in `docs/scoring.md`, replacing `selection` with `ranking`. The existing Decimal-contract section remains unchanged. Ranking implementation and configuration are verified as unchanged through focused existing tests and the canonical quality gate, not rewritten.

## Risks / Trade-offs

- [Risk] A regression compares only two equally wrong values. → Keep an exact normative fractional oracle in addition to cross-context equality, and exercise both component and downstream significance outputs.
- [Risk] Test setup leaks a hostile Decimal context into later tests. → Use scoped context management or guaranteed restoration of every ambient setting changed by the test.
- [Risk] A contract correction expands into scoring or Decimal refactoring. → Treat the current production path as expected-correct and stop on evidence that would require broader production work.
- [Risk] Documentation cleanup absorbs unrelated terminology residue. → Change only the identified final Market State sentence and report any other residue without editing it.
- [Risk] The living spec is changed before lifecycle authorization. → Keep the normative edit in this delta until a separately authorized sync/archive step.

## Migration Plan

1. During Apply, reconfirm the owned-context call chain and that no active Change now overlaps this scope.
2. Add the focused fractional hostile-context regression first and run it against the unchanged implementation.
3. Make the one-line `docs/scoring.md` terminology correction; modify production code only if the new regression exposes a direct scoped defect, which is not currently expected.
4. Run focused scoring/ranking tests, the canonical repository quality gate, and OpenSpec strict validation.
5. Leave delta-to-living-spec synchronization, archive, commit, push, and Linear work to separately authorized lifecycle steps.

Rollback before sync/archive is removal of the focused test and documentation line change. There is no data, API, configuration, or dependency migration.
