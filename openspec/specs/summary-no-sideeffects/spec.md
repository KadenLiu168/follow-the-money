# summary-no-sideeffects Specification

## Purpose
TBD - created by archiving change low-priority-cleanup. Update Purpose after archive.
## Requirements
### Requirement: compute13FSummary has no iteration side effects
The `compute13FSummary` function SHALL produce `newPositions` without mutating external state inside a `.filter()` (or similar) callback.

#### Scenario: identical output
- **WHEN** `compute13FSummary(currentHoldings, priorHoldings)` is called
- **THEN** the returned object (including `newPositions` as a `string[]` of CUSIPs, plus `closedPositions`, `increasedPositions`, `decreasedPositions`, `totalValueUsd`, `totalHoldingsCount`) is identical to the pre-change implementation for the same inputs

