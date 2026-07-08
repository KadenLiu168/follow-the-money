## Why

`scripts/prepare-digest.js` reads the wall clock directly (`Date.now()`, `new Date()`) with no injection point, so the integration test (`tests/integration.test.js`) that uses fixed fixture dates is non-deterministic and is currently failing: `npm test` reports 1 failed / 118 passed. The same gap makes "rebuild a digest as-of a past date" impossible. A secondary issue: 13F and 13DG are filtered by two inconsistent code paths (13F hand-rolls a cutoff against `latestFilingDate`; 13DG calls `filterByLookback` against `filingDate`), a DRY violation that is the direct cause of the wall-clock coupling.

## What Changes

- Add a **time seam** to `scripts/prepare-digest.js`: a single `now` reference resolved from `--now <ISO>` flag, then `FTM_NOW` env, then `new Date()`. All date-derived logic (lookback cutoff, manifest year fallback, `generatedAt`) uses this value instead of calling `Date.now()`/`new Date()` directly.
- Extend `lib/feed/filter-by-lookback.js` with an optional `field` parameter (default `'filingDate'`) so it can filter on any date field — enabling 13F entries (which expose `latestFilingDate`, not `filingDate`) to reuse the same function.
- Unify `prepare-digest.js` so **both** 13F and 13DG are filtered through `filterByLookback` with the shared `now`, removing the hand-rolled 13F cutoff. 13F passes `field: 'latestFilingDate'`; 13DG uses the default `'filingDate'`.
- Fix `tests/integration.test.js` to pass `FTM_NOW=2026-06-26` (via env on the `prepare-digest` exec) so the fixed fixture dates (`2026-06-25`, `2026-06-29`) always fall inside `--lookback 7`, making the test deterministic and permanently green.
- Add a regression unit test asserting `filterByLookback` honors the `field` option and an injected `now`.

## Capabilities

### New Capabilities
- `digest-lookback`: How the digest pipeline selects filings within a lookback window and how the reference time ("now") is determined, injected, and applied uniformly across 13F and 13DG feeds.

### Modified Capabilities
<!-- None. The existing `delivery` and `value-units-normalization` specs are unaffected; this change does not alter their requirements. -->

## Impact

- `lib/feed/filter-by-lookback.js` — add `field` option (backward-compatible default).
- `scripts/prepare-digest.js` — replace direct `Date.now()`/`new Date()` calls with a single resolved `now`; route 13F filtering through `filterByLookback({ field: 'latestFilingDate' })`; derive manifest year fallback from `now`.
- `tests/integration.test.js` — inject `FTM_NOW` env into the `prepare-digest` child process; no change to fixture dates or `--lookback 7`.
- `tests/feed/filter-by-lookback.test.js` — add cases for `field` option and injected `now`.
- No changes to stored feed schema (`feed-13f.json`, `feed-13dg/*.ndjson`), `lib/aggregate/pipeline-a.js`, `lib/store/feed-json.js`, or `scripts/check-alerts.js` (out of scope; its `lastAlertTimestamp` filter is already wall-clock-independent).
- No dependency changes.
- No breaking changes to CLI behavior: when `--now`/`FTM_NOW` are absent, behavior is identical to today.
