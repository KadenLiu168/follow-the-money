## WHY

`compute13FSummary` builds `newPositions` by pushing into an array from inside a `.filter()` callback. This hidden side effect makes the code harder to reason about and is flagged by the code-quality review (L10).

## WHAT

Compute `newPositions` without mutating state during iteration; keep the exact same return shape and values.

## ADDED Requirements

### Requirement: compute13FSummary has no iteration side effects
The `compute13FSummary` function SHALL produce `newPositions` without mutating external state inside a `.filter()` (or similar) callback.

#### Scenario: identical output
- **WHEN** `compute13FSummary(currentHoldings, priorHoldings)` is called
- **THEN** the returned object (including `newPositions` as a `string[]` of CUSIPs, plus `closedPositions`, `increasedPositions`, `decreasedPositions`, `totalValueUsd`, `totalHoldingsCount`) is identical to the pre-change implementation for the same inputs
