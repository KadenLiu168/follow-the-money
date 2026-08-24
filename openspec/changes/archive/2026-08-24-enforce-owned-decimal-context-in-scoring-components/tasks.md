## 1. Baseline Audit and RED Regression

- [x] 1.1 Re-read this Change, the living `deterministic-research-engine` scoring requirement, current active Changes, and `src/follow_the_money/scoring.py`; confirm there is no overlapping Change or production scoring caller and prepare the environment with `uv sync --frozen --all-groups`.
- [x] 1.2 Complete the bounded `scoring.py` audit by classifying every arithmetic operation as normative arithmetic, exact construction/comparison/validation, or unused/unrelated; confirm the three known leaks are Fundamental Magnitude mean, Persistence mean, and observable-repricing absolute value, and report rather than absorb any unrelated finding.
- [x] 1.3 Add a regression using scoped `localcontext()` settings that include `prec=1` with `ROUND_UP` and a high-precision different rounding mode; use `sector`/`headline`, `medium`/`months`, three affected groups, a known surprise, and repricing z `-0.4999`.
- [x] 1.4 Assert literal component oracles `37.5`, `62.5`, `33.333333333333333333333333333333333333333333333333`, and Repricing score `0`, exact equality for all component values, Event Significance, and coverage across contexts, and guaranteed restoration of the surrounding Decimal context; explicitly retain the existing `0.5 -> 25` bin side in this or a focused boundary test.
- [x] 1.5 Run the new regression against the unchanged implementation and record a RED failure caused by the intended mean and repricing preprocessing leaks, not by fixture, configuration, or restoration errors.

## 2. Minimal Owned-Context Repair

- [x] 2.1 Evaluate the existing Fundamental Magnitude mean inside `normative_decimal_context()` without changing operands, categorical maps, weights, unknown handling, or operation order.
- [x] 2.2 Evaluate the existing Persistence mean inside `normative_decimal_context()` with the same formula and semantic constraints.
- [x] 2.3 Evaluate only the existing observable-repricing absolute-value preprocessing inside `normative_decimal_context()`, then use the unchanged configured bins and comparisons without quantization or tolerance.
- [x] 2.4 Run the new hostile-context and repricing-boundary regression to GREEN and inspect the diff to confirm no new Decimal authority, scoring abstraction, configuration change, schema, production caller, or unrelated cleanup was introduced.

## 3. Regression and Contract Verification

- [x] 3.1 Run `tests/test_scoring.py` and `tests/test_neutralize_selection_and_scoring_contract.py`, retaining coverage for Surprise bins, Systemic Breadth, missing components, component coverage, unmapped categorical failure, Event Relevance, Base Priority, ranking, and family penalties.
- [x] 3.2 Run the canonical repository quality gate with `.venv/bin/python scripts/quality_gate.py` and record the actual result.
- [x] 3.3 Run `openspec doctor`, `openspec validate enforce-owned-decimal-context-in-scoring-components --strict`, and `openspec validate --all --strict`, and record the actual results.
- [x] 3.4 Perform final architecture, scope, and completeness checks: the accepted Decimal invariant remains the sole contract and `normative_decimal_context()` the sole authority; all three confirmed leaks are covered; formulas, maps, bins, weights, missing/coverage semantics, relevance, priority, ranking, configuration, Feed, and Agent boundaries remain unchanged; report any unresolved conflict or follow-up separately.
