## Context

`scripts/prepare-digest.js` produces the daily digest by filtering 13F and 13DG feeds through a `--lookback N` day window. Today it reads the wall clock in three places with no way to override:

- Line 28: `manifest.currentYear = new Date().getUTCFullYear()` (fallback when no manifest)
- Line 37: `const cutoff = new Date(Date.now() - lookbackDays * 86400000)...` (13F filter)
- Line 55: `generatedAt: new Date().toISOString()`

13F and 13DG are filtered by **two different code paths**:

```
13F:  normalizedFeed.filter(e => e.latestFilingDate >= cutoff)   // hand-rolled, field = latestFilingDate
13DG: filterByLookback(dgRaw, { lookbackDays })                  // lib function, field = filingDate, now = new Date()
```

`filterByLookback` already accepts a `now` parameter, but the caller never passes it, and the 13F path doesn't use the function at all. The result: the integration test (which uses fixed fixture dates `2026-06-25` / `2026-06-29` and `--lookback 7`) fails whenever the real "today" drifts past the cutoff — it is currently failing (`1 failed / 118 passed`).

A constraint that shapes the design: **13F feed entries have no top-level `filingDate` field**. They expose `latestFilingDate` (set in `lib/aggregate/pipeline-a.js:29`, and reliably kept current by `upsert13FFiling` in `lib/store/feed-json.js:45-46`). 13DG entries use `filingDate`. Any unification must respect this field difference.

## Goals / Non-Goals

**Goals:**
- Make `prepare-digest.js` fully deterministic given a fixed reference time and fixed input feeds.
- Make the integration test permanently green without weakening what it asserts.
- Unify 13F/13DG lookback filtering through one function with one `now`.
- Enable as-of backfill ("rebuild the digest as if today were D") with no further code changes.
- Zero behavior change for existing callers when no reference time is supplied.

**Non-Goals:**
- Changing the stored feed schema (no new fields on `feed-13f.json` entries).
- Adding a time seam to `scripts/check-alerts.js` (its alert filter uses `config.lastAlertTimestamp`, not the wall clock; its only wall-clock use is the manifest year fallback, which is safe in practice and out of scope here).
- Modifying `lib/aggregate/pipeline-a.js` or the ingestion pipeline.
- Adding `--now` to every script (scoped to `prepare-digest.js`, where the bug lives).

## Decisions

### Decision 1: Resolve `now` from `--now` flag, then `FTM_NOW` env, then `new Date()`

`prepare-digest.js` computes a single `now` at startup:

```js
const nowIdx = args.indexOf('--now');
const now = nowIdx >= 0
  ? new Date(args[nowIdx + 1])
  : (process.env.FTM_NOW ? new Date(process.env.FTM_NOW) : new Date());
if (Number.isNaN(now.getTime())) { console.error('[prepare-digest] invalid --now/FTM_NOW'); process.exit(1); }
```

All three current wall-clock reads (`cutoff`, manifest year fallback, `generatedAt`) use this `now`.

**Why both flag and env:** A `--now` flag is discoverable for manual backfill (`node scripts/prepare-digest.js --lookback 7 --now 2026-03-31`). An env var is the only ergonomic way to inject time into a child process spawned by `execSync` in the integration test (the test already builds an `env` object for `SEC_EDGAR_USER_AGENT`/`FIXTURES_JSON`). Supporting both costs one ternary and covers every caller.

**Alternatives considered:**
- *Mock `Date`/`Date.now` in the child via the `--import` stub.* Rejected: global monkey-patching of `Date` in a child process is fragile (it also shifts `generatedAt`, manifest year, and any future date use), and it's invisible to operators who want to backfill. A real seam is more honest and more useful.
- *Use relative fixture dates (`daysAgo(3)`).* Rejected as the primary fix: it makes the test pass but leaves the production code un-testable and backfill impossible. Kept as a *possible* defense-in-depth later, but not needed once the seam exists.
- *`vi.setSystemTime` in vitest.* Rejected: the digest runs in a child process (`execSync`), so vitest's time control doesn't reach it.

### Decision 2: Add a `field` option to `filterByLookback` (default `'filingDate'`)

```js
export function filterByLookback(items, { lookbackDays, now = new Date(), field = 'filingDate' }) {
  ...
  return items.filter(it => it[field] >= cutoffStr);
}
```

**Why a `field` option instead of aliasing `filingDate` onto 13F entries:** Adding `filingDate: latestFilingDate` to 13F entries would change the stored `feed-13f.json` schema, requiring a migration of existing feed files and edits to `pipeline-a.js` + `feed-json.js`. A `field` option achieves the same unification with a one-line, backward-compatible change to a pure function. Default `'filingDate'` preserves the existing 13DG behavior and all current callers/tests untouched.

**Why not a `computeCutoff(now, lookbackDays)` helper shared by two inline filters:** That would unify the *cutoff math* but leave two filter implementations (and two field references) in `prepare-digest.js`. The DRY violation and the "forgot to pass `now`" risk would remain. Routing both through `filterByLookback` removes the duplication entirely.

### Decision 3: Route 13F filtering through `filterByLookback` with `field: 'latestFilingDate'`

```js
const now = /* resolved per Decision 1 */;
const f13Filtered = filterByLookback(normalizedFeed, { lookbackDays, now, field: 'latestFilingDate' });
const dgFiltered  = filterByLookback(dgRaw, { lookbackDays, now });
```

This deletes the hand-rolled `cutoff`/`>=` block (current lines 37, 43) and makes 13F and 13DG share one filter function and one `now`. `latestFilingDate` is guaranteed to be the most recent filing date per filer (see `feed-json.js` upsert: the incoming `entry` spreads first, overwriting the prior `latestFilingDate`), so it is the correct field to window 13F entries by.

### Decision 4: Derive the manifest year fallback from `now`

Current line 28: `currentYear: new Date().getUTCFullYear()`. Change to `currentYear: now.getUTCFullYear()`. This keeps the "no manifest → guess current year" path consistent with the rest of the digest's notion of "today", which matters for as-of backfill across a year boundary.

## Risks / Trade-offs

- **[Invalid `--now`/`FTM_NOW` value silently misbehaves]** → Mitigation: validate with `Number.isNaN(now.getTime())` and exit non-zero with a clear error before any filtering runs.
- **[13F entries missing `latestFilingDate` get dropped by the filter]** → Mitigation: `latestFilingDate` is always set by `pipeline-a.js:29` for every entry; `upsert13FFiling` preserves it. Add a unit test asserting an entry with `latestFilingDate` inside the window is retained. No migration needed for existing feeds (all have the field).
- **[`filterByLookback` `field` option silently returns empty if field is misspelled]** → Mitigation: default `'filingDate'` keeps 13DG unchanged; 13F's `field: 'latestFilingDate'` is covered by a unit test. Low risk since the option is only used in two call sites, both in the same file.
- **[Behavior change for `generatedAt` when `FTM_NOW` is set]** → Trade-off, accepted: if an operator backfills with `FTM_NOW`, the digest's `generatedAt` will reflect the injected time, not real-now. This is desirable for reproducibility (a backfilled digest should look as if it were generated then) and is documented in the spec.
- **[Test still depends on `FTM_NOW` being passed]** → Mitigation: the integration test explicitly sets `FTM_NOW=2026-06-26` in the child env; if omitted, the test would fail loudly rather than silently. No hidden coupling.

## Open Questions

- Should `scripts/check-alerts.js` eventually accept the same `--now`/`FTM_NOW` seam for its manifest year fallback? Out of scope here (its alert filter is already wall-clock-independent), but worth a follow-up change if cross-year backfill of alerts becomes a need.
- Should `generatedAt` use real-now even when `FTM_NOW` is set (so consumers know "this was backfilled on date X")? Current decision: use `now` for full reproducibility. Revisit if downstream consumers need to distinguish backfilled from live digests.
