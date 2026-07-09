# ci-test-gate Specification

## Purpose
TBD - created by archiving change medium-followups. Update Purpose after archive.
## Requirements
### Requirement: aggregate workflow runs test gate before aggregation
The GitHub Actions aggregator workflow (`.github/workflows/aggregate.yml`) MUST, after dependency installation and BEFORE running `node scripts/aggregate.js`, execute (in order) the project test suite (`npm test`, i.e. `vitest run`), the lint check (`npm run lint`), and the format check (`npm run format:check`). If any of these steps exits non-zero, the workflow MUST NOT proceed to aggregate or commit feed data for that run.

#### Scenario: all checks pass then aggregate
- **WHEN** `npm test`, `npm run lint`, and `npm run format:check` all exit 0 in the aggregator workflow
- **THEN** the workflow proceeds to run `node scripts/aggregate.js` and (if feed data changed) commits

#### Scenario: test failure blocks aggregation
- **WHEN** `npm test` exits non-zero in the aggregator workflow
- **THEN** the workflow MUST stop before `node scripts/aggregate.js` (no feed aggregation or commit for that run)

#### Scenario: lint failure blocks aggregation
- **WHEN** `npm run lint` exits non-zero in the aggregator workflow
- **THEN** the workflow MUST stop before `node scripts/aggregate.js` (no feed aggregation or commit for that run)

#### Scenario: format violation blocks aggregation
- **WHEN** `npm run format:check` exits non-zero in the aggregator workflow
- **THEN** the workflow MUST stop before `node scripts/aggregate.js` (no feed aggregation or commit for that run)

