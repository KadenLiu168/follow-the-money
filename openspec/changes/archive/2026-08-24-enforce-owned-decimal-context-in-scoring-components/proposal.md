## Why

The accepted deterministic scoring contract already requires every normative financial arithmetic result to be governed by the repository-owned high-precision Decimal context, but three reachable significance-component operations still inherit ambient process precision and rounding. Under a hostile context, the Fundamental Magnitude and Persistence means can be rounded before aggregation, while absolute-value preprocessing can move Repricing Magnitude across a configured bin boundary and change downstream Event Significance.

## What Changes

- Evaluate the existing Fundamental Magnitude arithmetic mean inside `normative_decimal_context()` without changing its categorical maps, formula, weight, or unknown semantics.
- Evaluate the existing Persistence arithmetic mean inside the same owned context without changing its maps, formula, weight, or semantic policy.
- Evaluate the absolute observable repricing magnitude used by the existing bins inside the owned context without changing proxy selection, bin boundaries, scores, quantization, or comparison policy.
- Add a hostile-context regression with exact component oracles for fractional Fundamental Magnitude, Persistence, Systemic Breadth, and boundary-adjacent Repricing Magnitude, plus invariant Event Significance and component coverage.
- Perform a bounded audit of currently reachable arithmetic in `src/follow_the_money/scoring.py`, classifying normative arithmetic, exact construction/comparison/validation, and unused or unrelated helpers; report unrelated findings instead of expanding this Change.
- Preserve all scoring configuration, formulas, weights, missing-data and coverage semantics, Event Relevance, Base Priority, ranking, family penalties, and the retained-library/no-production-caller boundary.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `deterministic-research-engine`: Clarify the existing Versioned deterministic scoring invariant with a focused scenario requiring every significance component and downstream aggregation to remain identical under materially different ambient Decimal contexts.

## Impact

- Expected implementation surface: `src/follow_the_money/scoring.py` only.
- Expected regression surface: `tests/test_neutralize_selection_and_scoring_contract.py` and, only if useful for a focused bin boundary assertion, `tests/test_scoring.py`.
- Contract delta: `openspec/specs/deterministic-research-engine/spec.md` through this Change's delta spec.
- No configuration, dependency, serialized schema, Feed, provider, market, selection, Agent-facing contract, production orchestration, or general documentation change is expected.
