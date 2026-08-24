## Context

See `proposal.md` for motivation and the delta spec for the normative behavior. Repository inspection found no active OpenSpec Change and no production caller for the retained scoring library. In `src/follow_the_money/scoring.py`, Surprise absolute-value processing, Systemic Breadth, Event Significance, Event Relevance, and Base Priority already execute their normative arithmetic inside `normative_decimal_context()`.

Three currently reachable significance-component operations remain outside that context: the Fundamental Magnitude mean, the Persistence mean, and absolute observable repricing magnitude before bin comparison. A proposal-time probe using the same semantic vector showed `prec=1` with `ROUND_UP` producing `40`, `100`, and Repricing score `25`, while a high-precision context produced the normative `37.5`, `62.5`, and `0`; downstream Event Significance also differed. The configured maps, bins, weights, and operation order are not the defect.

The bounded module audit classifies the two means, Surprise absolute value, Systemic Breadth formula, Repricing absolute value, weighted Event Significance, Event Relevance aggregation, and Base Priority as normative arithmetic. Decimal construction from closed configuration, bin and freshness comparisons, category validation, and integer weight counting are exact construction/comparison/validation. `_pct` and `EventScores.coverage_pct` have no current call sites and are outside the significance-component repair; they remain untouched unless Apply-time inspection establishes a direct dependency on this invariant.

## Goals / Non-Goals

**Goals:**

- Close all three confirmed ambient-context leaks with the existing Decimal authority and preserve the current arithmetic sequence.
- Make the accepted invariant mutation-resistant through exact component oracles and downstream invariance assertions under contexts that demonstrably fail before the repair.
- Repeat the bounded `scoring.py` classification during Apply so newly discovered direct dependencies are handled or reported before implementation expands.

**Non-Goals:**

- Centralizing component computation behind a new abstraction or redesigning `normative_decimal_context()`.
- Changing configuration, formulas, mappings, bins, weights, missing-data or coverage semantics, relevance, priority, ranking, or family penalties.
- Auditing market, selection, Feed, providers, or other modules; adding a schema, production caller, Agent contract, or orchestration path.
- Removing unused helpers or performing adjacent cleanup.

## Decisions

### 1. Use narrow owned-context blocks at each confirmed leak

Evaluate each arithmetic mean and the observable-repricing absolute value within the existing `normative_decimal_context()`. Keep bin evaluation immediately after absolute-value preprocessing and leave comparisons unchanged.

This is preferred over wrapping the whole component function because it produces a smaller, easier-to-review diff and makes each normative arithmetic boundary explicit. It is preferred over a new helper, duplicate context, precision constant, or rounding policy because the repository already has one authoritative Decimal mechanism. No quantization or tolerance is introduced.

### 2. Prove the repair with one semantic hostile-context vector

Use a vector whose mapped means are fractional, whose breadth is repeating, and whose repricing magnitude sits immediately below a configured boundary: `sector` plus `headline`, `medium` plus `months`, three affected groups, and `-0.4999` observable repricing z. Include a normal known surprise so all five components are known.

Evaluate it inside scoped ambient contexts including `prec=1` with `ROUND_UP` and a high precision with a different rounding mode. The low-precision setting is intentional: precision 6 would not expose the two fractional-mean leaks. Assert the literal normative component values before asserting cross-context equality, then assert exact downstream Event Significance and unchanged coverage. Capture and compare the surrounding context representation, or use equivalent guaranteed scoped restoration, to prevent test pollution.

This is preferred over equality-only testing because two contexts could agree on the same wrong value. A focused `0.4999 -> 0` and `0.5 -> 25` Repricing boundary assertion may be added if the combined regression does not make both sides of the existing boundary sufficiently explicit.

### 3. Keep the audit bounded and evidence-driven

During Apply, inspect arithmetic and call sites inside `scoring.py` only and record the three classifications in the implementation review. Any additional currently reachable normative arithmetic that can inherit ambient precision is in scope only when directly required by this scoring invariant. Unused helpers, exact comparisons/construction, and unrelated findings remain unchanged and are reported rather than absorbed.

This avoids turning a verified component defect into a repository-wide Decimal redesign while still preventing an obvious fourth leak from being ignored.

## Risks / Trade-offs

- [Risk] A broad context block or reordered expression changes accepted operation order. → Use local blocks around the existing expressions and retain their operands, ordering, maps, and comparisons exactly.
- [Risk] The regression passes through shared wrong rounding rather than the normative result. → Assert exact literal values for each exposed component before cross-context equality and assert downstream Event Significance and coverage.
- [Risk] Hostile Decimal settings leak into later tests. → Use `localcontext()` or guaranteed restoration and explicitly verify the surrounding context is restored.
- [Risk] A bounded audit becomes unrelated cleanup. → Require a direct current call path and ambient-sensitive normative arithmetic before changing anything beyond the three confirmed sites; otherwise report the finding.

## Migration Plan

1. Add and run the focused regression against the unchanged implementation, retaining the failure evidence for the three intended component paths.
2. Apply the three local owned-context changes without modifying configuration or public contracts.
3. Run focused scoring and neutral scoring/ranking tests, then the canonical repository and OpenSpec gates.
4. Roll back by reverting the three local context changes and their regression/spec delta; no data, configuration, schema, or deployment migration is required.
