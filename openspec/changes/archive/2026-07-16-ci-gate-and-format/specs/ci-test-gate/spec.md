# ci-test-gate Specification

## REMOVED Requirements

### Requirement: aggregate workflow runs test gate before aggregation
**Reason**: The format/lint/test gate lived inside `aggregate.yml` (the daily SEC-filing cron). Because it ran before `node scripts/aggregate.js` with no `continue-on-error`, any unformatted file made the job exit 1 and silently halted feed updates. The gate belongs at merge time (pre-commit to `main`), not inside the data-fetch cron — the cron is the worst place to discover a formatting slip because it also blocks the product's core pipeline.
**Migration**: Code-quality gates (`npm test`, `npm run lint`, `npm run format:check`) move to a new dedicated workflow `.github/workflows/ci.yml` that runs on `push` to `main` and `pull_request` targeting `main`. `aggregate.yml` no longer runs these gates; it only fetches and commits feed data.

## ADDED Requirements

### Requirement: dedicated CI workflow gates code quality on push and pull request
The repository SHALL include a dedicated CI workflow `.github/workflows/ci.yml` that, on `push` to `main` and on `pull_request` targeting `main`, executes (in order) `npm ci`, `npm test` (i.e. `vitest run`), `npm run lint`, and `npm run format:check`. If any step exits non-zero, the workflow MUST fail so the change cannot be merged/kept green on `main`.

#### Scenario: push to main runs all gates
- **WHEN** a commit is pushed to `main`
- **THEN** `ci.yml` runs `npm ci` → `npm test` → `npm run lint` → `npm run format:check` in order and fails if any exits non-zero

#### Scenario: pull request to main is gated before merge
- **WHEN** a pull request targeting `main` is opened or updated
- **THEN** `ci.yml` runs the same gate sequence and the PR status reflects failure on any non-zero step

#### Scenario: format violation fails CI before merge
- **WHEN** `npm run format:check` exits non-zero in `ci.yml`
- **THEN** the workflow fails and the offending commit/PR is not green (caught pre-merge, not by the cron)

### Requirement: aggregate workflow focuses on data fetch without code-quality gates
The GitHub Actions aggregator workflow `.github/workflows/aggregate.yml` MUST NOT run `npm test`, `npm run lint`, or `npm run format:check` as blocking steps before `node scripts/aggregate.js`. Its responsibility is to install dependencies, fetch SEC filings, and commit feed data; code quality is enforced by `ci.yml` before changes reach `main`.

#### Scenario: aggregate runs without pre-checks
- **WHEN** `aggregate.yml` is triggered (schedule or `workflow_dispatch`)
- **THEN** it runs `checkout` → `setup-node` → `npm ci` → `node scripts/aggregate.js` → `git commit/push` without executing the test/lint/format gates

#### Scenario: a formatting slip on main does not block feeding
- **WHEN** `main` somehow contains an unformatted file that `ci.yml` missed
- **THEN** `aggregate.yml` still fetches and commits feed data (code quality is `ci.yml`'s concern, not the cron's)
