# digest-lookback Specification

## Purpose
TBD - created by archiving change add-digest-time-seam. Update Purpose after archive.
## Requirements
### Requirement: Digest reference time SHALL be injectable

The digest pipeline (`scripts/prepare-digest.js`) SHALL resolve a single reference time ("now") from, in order of precedence: a `--now <ISO 8601>` command-line flag, an `FTM_NOW` environment variable, or the current wall-clock time. Every date-derived value the script computes — the lookback cutoff, the manifest year fallback, and the output `generatedAt` timestamp — SHALL be derived from this single resolved `now` and SHALL NOT call `Date.now()` or `new Date()` directly after startup.

#### Scenario: Default behavior with no injection
- **WHEN** `prepare-digest.js` is invoked with `--lookback 7` and neither `--now` nor `FTM_NOW` is provided
- **THEN** the reference time SHALL equal the current wall-clock time at process startup
- **AND** the digest output SHALL be identical to the behavior before this change

#### Scenario: Injection via environment variable
- **WHEN** `FTM_NOW=2026-06-26T00:00:00Z` is set in the environment and `--now` is not passed
- **THEN** the reference time SHALL be `2026-06-26T00:00:00.000Z`
- **AND** the lookback cutoff for `--lookback 7` SHALL be `2026-06-19`
- **AND** the output `generatedAt` SHALL be `2026-06-26T00:00:00.000Z`

#### Scenario: Flag takes precedence over environment
- **WHEN** both `--now 2026-03-31` and `FTM_NOW=2026-06-26` are provided
- **THEN** the reference time SHALL be derived from the `--now` value (`2026-03-31`)
- **AND** `FTM_NOW` SHALL be ignored

#### Scenario: Invalid reference time is rejected
- **WHEN** `--now` or `FTM_NOW` is set to a value that `new Date()` cannot parse
- **THEN** the process SHALL print an error message naming the invalid value
- **AND** the process SHALL exit with a non-zero status code
- **AND** no digest output SHALL be written to stdout

#### Scenario: --now flag present without a value is rejected
- **WHEN** `prepare-digest.js` is invoked with `--now` as the last argument (no following value)
- **THEN** the process SHALL print an error message stating `--now` requires a value
- **AND** the process SHALL exit with a non-zero status code
- **AND** no digest output SHALL be written to stdout

### Requirement: Lookback filtering SHALL be unified through a single function

Both 13F and 13DG feeds SHALL be filtered through `filterByLookback` using the same resolved reference time. `filterByLookback` SHALL accept an optional `field` parameter (default `'filingDate'`) selecting which date field to compare against the cutoff. The 13F path SHALL filter on `latestFilingDate`; the 13DG path SHALL filter on `filingDate`.

#### Scenario: 13F entries filtered by latestFilingDate within window
- **WHEN** `filterByLookback` is called with `{ lookbackDays: 7, now: new Date('2026-06-26'), field: 'latestFilingDate' }` on items `[{ latestFilingDate: '2026-06-25' }, { latestFilingDate: '2026-06-10' }]`
- **THEN** it SHALL return only the item with `latestFilingDate: '2026-06-25'`

#### Scenario: 13DG entries filtered by filingDate (default field)
- **WHEN** `filterByLookback` is called with `{ lookbackDays: 7, now: new Date('2026-06-26') }` on items `[{ filingDate: '2026-06-29' }, { filingDate: '2026-05-01' }]`
- **THEN** it SHALL return only the item with `filingDate: '2026-06-29'`

#### Scenario: Default field preserves existing behavior
- **WHEN** `filterByLookback` is called without a `field` option
- **THEN** it SHALL filter on the `filingDate` field
- **AND** existing callers and tests that do not pass `field` SHALL behave unchanged

### Requirement: Digest output SHALL be deterministic for a fixed reference time and fixed input

Given identical input feeds and an identical resolved reference time, `prepare-digest.js` SHALL produce byte-identical output (modulo any non-deterministic content introduced solely by external sources).

#### Scenario: Integration test with fixed reference time
- **WHEN** the integration test runs `prepare-digest.js --lookback 7` with `FTM_NOW=2026-06-26` and fixtures dated `2026-06-25` (13F) and `2026-06-29` (13DG)
- **THEN** `digest.thirteenF.length` SHALL be greater than 0
- **AND** `digest.thirteenDG.length` SHALL be greater than 0
- **AND** the test SHALL pass regardless of the real wall-clock date on which it runs

#### Scenario: Backfill a digest as-of a past date
- **WHEN** an operator runs `prepare-digest.js --lookback 7 --now 2026-03-31` against a feed containing filings dated through `2026-03-30`
- **THEN** the digest SHALL include filings within the window ending `2026-03-31`
- **AND** the output `generatedAt` SHALL be `2026-03-31T00:00:00.000Z`

