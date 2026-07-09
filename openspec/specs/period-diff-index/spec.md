# period-diff-index Specification

## Purpose
TBD - created by archiving change low-priority-cleanup. Update Purpose after archive.
## Requirements
### Requirement: periodDiff uses a CIK index for prior lookup
The `periodDiff` function SHALL accept an optional prebuilt CIK index and, when provided, locate the prior period entry via that index instead of scanning the full filing list.

#### Scenario: index provided
- **WHEN** `periodDiff(entry, allFilings, config, cikIndex)` is called with a prebuilt index
- **THEN** the prior entry returned is identical to the one found by the prior full-scan implementation

#### Scenario: index omitted (backward compatible)
- **WHEN** `periodDiff(entry, allFilings, config)` is called without an index
- **THEN** the function builds the index internally and still returns the correct prior entry

### Requirement: digest run builds the index once
The `prepare-digest.js` digest step SHALL build the CIK index a single time and pass it to every `periodDiff` call in its `.map`.

#### Scenario: many filers
- **WHEN** the feed contains multiple filers across multiple periods
- **THEN** the computed summaries (new/closed/increased/decreased positions, priorTotalValueUsd, deltaPct) are byte-for-byte identical to the pre-index implementation

