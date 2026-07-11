## Why

`lib/edgar/fetch-thirteen-dg-search.js` builds the EDGAR `search-index` URL with `startDate`/`endDate` and `forms=SC 13D`. A live spike on 2026-07-11 (recorded in `.workbuddy/memory/2026-07-11.md`) proved two defects, not one:

1. **`startDate`/`endDate` are silently ignored by EDGAR.** The response is byte-identical to sending no date param at all — it returns the full 13D/G history (capped at `hits.total=10000`). Correct params are `startdt`/`enddt` with the `YYYY-MM-DD` format (the nodash `YYYYMMDD` form returns `total=undefined` / invalid).
2. **`forms=SC 13D` + `dateRange=custom` returns 0 hits for 2025+ filings** (reproducible across 2025 and 2026 windows; 2024 works). Only the `q=` full-text query (`q="SC 13D"`) returns recent filings (287 for a 2026 window).

The dangerous interaction: **today the code only "works" because the ignored date window makes it fetch the full history and dedupe via `seen`** — so 2025/2026 new filings are still ingested (wasteful but functional). Fixing *only* the date params while keeping `forms=SC 13D` would make recent windows return 0 → **silent 漏报** (13F keeps working, so it goes unnoticed). Therefore the fix must switch to `q=` *and* correct the date params.

A third issue: `q=` text matching is noisy (the spike showed `SC TO-T` slipping into `q="SC 13D"` results), and `pipeline-b.js` does **not** filter by `_source.root_forms`, so noise would flow straight into the feed. Add a `root_forms` filter at the single search exit.

## What Changes

- `lib/edgar/fetch-thirteen-dg-search.js`: build the URL as `q="<formType>"&dateRange=custom&startdt=<startDate>&enddt=<endDate>`; filter returned hits by `_source.root_forms` (keep only the target form or its `SCHEDULE` alias). JS variable names `startDate`/`endDate` stay the same — only the wire format changes.
- `scripts/verify-edgar.js`: drop the `&forms=SC+13D` segment and fix `startDate`/`endDate` → `startdt`/`enddt` so the dev/CI check mirrors the production query.
- Tests: update `fetch-thirteen-dg-search.test.js`, `pipeline-b.test.js`, `verify-edgar.test.js` + fixtures to assert `q=`/`startdt`/`enddt` and `root_forms` filtering; add a noise-rejection test.

## Capabilities

### New Capabilities
- `edgar-13dg-query`: the contract that 13D/G EDGAR search uses EDGAR's `startdt`/`enddt` date params (not `startDate`/`endDate`) and the `q=` full-text query (not `forms=`), and filters results by `root_forms` to drop non-13D noise.

### Modified Capabilities
<!-- None. No existing spec's REQUIREMENTS change. -->

## Impact

- **Code**: `lib/edgar/fetch-thirteen-dg-search.js`, `scripts/verify-edgar.js`.
- **Behavior**: 13D-G search returns recent (2025+) filings inside the date window; stops over-fetching the entire history every run; drops `SC TO-T`-style noise before it reaches the feed.
- **Tests**: assertions updated; one new noise-rejection test.
- **No new runtime deps / no API contract change** beyond the EDGAR query shape.
