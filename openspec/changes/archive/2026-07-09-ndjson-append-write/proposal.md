## Why

`append13DFiling` and `appendStateNdjson` rewrite the entire year file on every append (`readFileSync` whole file → `writeFileSync` whole file). `pipeline-b` calls `append13DFiling` once per new filing, so a 3-day full-market window appending hundreds of 13D/G filings performs O(hundreds × filesize) read+write. At ~50MB/year (per `references/data-formats.md`), this degrades throughput and memory and risks CI timeouts as data grows. Two related defects live in the same file: corrupt lines are silently skipped without counting (violates the spec's "count skipped lines" rule), and an invalid `filingDate` produces a `NaN` year file that is dropped from the manifest (silent data loss).

## What Changes

- `lib/store/feed-ndjson.js`: switch `append13DFiling` to true append mode (no full rewrite). Surface corrupt-line count. Reject/quarantine entries with an invalid `filingDate` instead of writing a `NaN` year file.
- `lib/store/state-ndjson.js`: apply the same append-mode + corrupt-count + validation treatment to `appendStateNdjson` / `readStateNdjson`.
- `lib/store/manifest.js`: update per-year `count`/`firstDate`/`lastDate` incrementally (already incremental for feed; ensure state manifest parity).

## Capabilities

### New Capabilities
- `feed-storage`: the contract for NDJSON append semantics — O(1) append writes, corrupt-line accounting, and valid `filingDate` enforcement for both the 13D/G feed and the state file.

### Modified Capabilities
<!-- none -->

## Impact

- **Code**: `lib/store/feed-ndjson.js`, `lib/store/state-ndjson.js`, `lib/store/manifest.js`, `lib/aggregate/pipeline-b.js` (call sites unchanged but benefit).
- **Behavior**: appends no longer rewrite the whole file; silent data loss and uncounted corruption are eliminated.
- **Performance**: removes the O(n²) read+write growth; memory peak drops from O(filesize) per append to O(line).
- **Tests**: add append-mode tests (N appends == N lines, no rewrite), corrupt-line count test, invalid-`filingDate` rejection test.
- **No API / dependency / network changes.**
