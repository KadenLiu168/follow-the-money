# ci-test-gate Specification

## Purpose
TBD - created by archiving change medium-followups. Update Purpose after archive.
## Requirements
### Requirement: aggregate workflow runs test gate before aggregation

The GitHub Actions aggregator workflow (`.github/workflows/aggregate.yml`) MUST execute the project test suite (`npm test`, i.e. `vitest run`) after dependency installation and BEFORE running `node scripts/aggregate.js`. If the test suite fails, the workflow MUST NOT proceed to aggregate or commit feed data for that run.

#### Scenario: tests pass then aggregate
- **WHEN** `npm test` exits 0 in the aggregator workflow
- **THEN** the workflow proceeds to run `node scripts/aggregate.js` and (if feed data changed) commits

#### Scenario: tests fail blocks aggregation
- **WHEN** `npm test` exits non-zero in the aggregator workflow
- **THEN** the workflow MUST stop before `node scripts/aggregate.js` (no feed aggregation or commit for that run)

