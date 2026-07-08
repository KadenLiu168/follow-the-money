## 1. Extend `filterByLookback` with a `field` option

- [x] 1.1 Add `field = 'filingDate'` parameter to `filterByLookback(items, { lookbackDays, now = new Date(), field = 'filingDate' })` in `lib/feed/filter-by-lookback.js`; change the filter to compare `it[field]` instead of `it.filingDate`
- [x] 1.2 Add unit tests in `tests/feed/filter-by-lookback.test.js`: filter on a custom `field` (e.g. `latestFilingDate`) with an injected `now`; assert default `field` behavior is unchanged
- [x] 1.3 Run `filterByLookback` unit tests; confirm green

## 2. Add the time seam to `prepare-digest.js`

- [x] 2.1 Resolve `now` at startup: `--now <ISO>` flag (parse `args.indexOf('--now')`) → `FTM_NOW` env → `new Date()`; validate with `Number.isNaN(now.getTime())` and exit non-zero with an error on invalid input
- [x] 2.2 Replace the manifest year fallback (`new Date().getUTCFullYear()` on line 28) with `now.getUTCFullYear()`
- [x] 2.3 Replace the hand-rolled 13F cutoff (lines 37, 43) with `filterByLookback(normalizedFeed, { lookbackDays, now, field: 'latestFilingDate' })`
- [x] 2.4 Pass the shared `now` into the 13DG filter: `filterByLookback(dgRaw, { lookbackDays, now })`
- [x] 2.5 Change `generatedAt: new Date().toISOString()` (line 55) to `generatedAt: now.toISOString()`
- [x] 2.6 Confirm no remaining direct `Date.now()` / `new Date()` calls in `prepare-digest.js` (grep-verify)
- [x] 2.7 When `--now` flag is present without a following value, error and exit non-zero (do NOT silently fall back to env/wall-clock); consistent with `--lookback` missing-value behavior

## 3. Fix the integration test

- [x] 3.1 In `tests/integration.test.js`, add `FTM_NOW: '2026-06-26T00:00:00Z'` to the `env` object passed to the `prepare-digest.js` `execSync` call (line 75) so the fixed fixture dates (`2026-06-25`, `2026-06-29`) always fall inside `--lookback 7`
- [x] 3.2 Leave fixture dates and `--lookback 7` unchanged
- [x] 3.3 Run `tests/integration.test.js`; confirm both `digest.thirteenF.length > 0` and `digest.thirteenDG.length > 0` pass

## 4. Regression coverage for the seam

- [x] 4.1 Add a unit test asserting `prepare-digest.js` (or a thin extracted helper) produces identical output for two runs with the same `FTM_NOW` and same input feed
- [x] 4.2 Add a unit test asserting `--now` takes precedence over `FTM_NOW` (Decision 1, Scenario: Flag takes precedence over environment)
- [x] 4.3 Add a unit test asserting an invalid `FTM_NOW` causes non-zero exit with an error message (Decision 1, Scenario: Invalid reference time is rejected)
- [x] 4.4 Add a unit test asserting `--now` present without a value causes non-zero exit with a "--now requires a value" message (Scenario: --now flag present without a value is rejected)

## 5. Validation

- [x] 5.1 Run `npm test`; confirm all 119+ tests pass (the previously failing integration test must be green)
- [x] 5.2 Manually verify default behavior unchanged: `node scripts/prepare-digest.js --lookback 7` (no `--now`/`FTM_NOW`) produces a digest with a real-now `generatedAt`
- [x] 5.3 Manually verify backfill: `FTM_NOW=2026-06-26T00:00:00Z node scripts/prepare-digest.js --lookback 7` produces `generatedAt: 2026-06-26T00:00:00.000Z` and includes the fixture-dated filings
- [x] 5.4 Grep-confirm no `dotenv`/delivery-related regressions introduced
