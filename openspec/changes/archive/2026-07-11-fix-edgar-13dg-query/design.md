# Design Decisions

## D1 — Switch `forms=SC 13D` → `q="SC 13D"` (not a forms variant)

Spike result: `forms=SC+13D & dateRange=custom & startdt/enddt` returns **0 hits for 2025+ windows** (reproducible), while `q=SC+13D` with the same dates returns 287 for a 2026 window. The `forms=` facet in `search-index` lags recent filings; the `q=` full-text index does not.

- Rejected alternative "keep `forms=` and only fix date params": would make recent windows return 0 → silent 漏报. Explicitly ruled out by the spike.
- Rejected "add `q=*` to force `forms=` to match": spike showed `forms=SC+13D & q=*` still returns 0 for recent windows. The `forms=` field itself is the broken variable.

## D2 — Date params are `startdt`/`enddt`, format `YYYY-MM-DD`

Spike: `startdt=2026-06-01` (dash) is accepted; `startdt=20260601` (nodash) returns `hits.total=undefined` (invalid). Wire format must use the dashed ISO date. JS variable names `startDate`/`endDate` (function signature + `pipeline-b.js` call site) are unchanged — only the URL interpolation uses `startdt`/`enddt`.

## D3 — `root_forms` filter lives in `fetchThirteenDGSearch` (single exit)

Both `pipeline-b.js` and `verify-edgar.js` go through `fetchThirteenDGSearch`, so filtering there covers both call sites. Predicate: keep a hit when `_source.root_forms` contains `formType` **or** `SCHEDULE <suffix>` (e.g. `SC 13D` ↔ `SCHEDULE 13D` are the same form under EDGAR's alternate label). This drops `SC TO-T` and other `q=` noise while keeping legitimate aliases.

Implementation: `(root_forms ?? []).some(rf => rf === formType || rf === 'SCHEDULE ' + formType.slice(3))`. `formType.slice(3)` drops the leading `'SC '` (e.g. `'SC 13D'` → `'13D'`).

## D4 — Caller surface unchanged

`pipeline-b.js` and `verify-edgar.js` keep passing `{ startDate, endDate, formType }`. Only `fetch-thirteen-dg-search.js` changes its URL construction and post-filtering. Blast radius is one module plus test fixtures.
