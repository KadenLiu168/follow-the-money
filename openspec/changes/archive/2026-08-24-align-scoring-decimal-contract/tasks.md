## 1. Reconfirm the Scoped Baseline

- [x] 1.1 Re-read the active Change list, current `Versioned deterministic scoring` requirement, `docs/scoring.md`, scoring implementation, and focused tests; stop and report if another active Change overlaps or the owned Systemic Breadth context no longer matches this design.
- [x] 1.2 Confirm the Change delta preserves all existing formulas, weights, maps, bins, missing-data and coverage semantics, operation order, caller-supplied typed boundary, retained-library status, and no-schema/no-production-caller boundaries while removing unconditional historical Decimal-tail parity.

## 2. Add the Fractional Decimal Regression First

- [x] 2.1 Add a focused scoring test using `affected_groups = 1` or `3` that exercises `significance_components(...)` and `event_significance(...)` and asserts exact normative Systemic Breadth, Event Significance, and unchanged component coverage.
- [x] 2.2 Evaluate the same semantic vector under at least two materially different ambient Decimal precision and rounding combinations, assert identical normative Systemic Breadth and downstream Event Significance, and guarantee restoration of the surrounding Decimal context.
- [x] 2.3 Run the new focused regression against the unchanged implementation; retain the existing hostile-context, fractional-oracle, formula/configuration, missing-component, and coverage tests without encoding a historical ambient-context Decimal tail.
- [x] 2.4 Do not modify `src/follow_the_money/scoring.py` or `normative_decimal_context` when the regression passes; if it exposes a direct scoped violation, stop and report the contract conflict before proposing any production repair.

## 3. Correct Focused Documentation

- [x] 3.1 Change only the final Market State statement in `docs/scoring.md` from `selection` to `ranking`, leaving the existing Decimal contract and all other scoring documentation unchanged.
- [x] 3.2 Review the scoped diff to confirm no scoring configuration, formula, ranking behavior, production caller, schema, Agent contract, orchestration, or unrelated documentation cleanup was introduced.

## 4. Verify the Change

- [x] 4.1 Run the focused scoring and ECO-29 neutral scoring/ranking test modules and confirm existing scoring and ranking behavior remains green.
- [x] 4.2 Run `.venv/bin/python scripts/quality_gate.py` and record the actual result without substituting a weaker custom gate.
- [x] 4.3 Run `openspec doctor`, `openspec validate align-scoring-decimal-contract --strict`, and `openspec validate --all --strict` and resolve only findings attributable to this Change.
- [x] 4.4 Perform the final architecture, scope, and truthfulness audit: current code, tests, delta, and focused documentation can be simultaneously true; archived ECO-29 material and the living spec remain untouched pending separately authorized sync/archive; no Linear, commit, or push action occurred.
