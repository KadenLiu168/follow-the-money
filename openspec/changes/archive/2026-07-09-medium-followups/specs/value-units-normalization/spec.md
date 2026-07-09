## MODIFIED Requirements

### Requirement: pipeline stamps valueUnit marker on write (prevent recurrence)

The 13F feed-generation path MUST stamp `valueUnit: 'thousands'` on each filer entry it writes to `feed-13f.json`, reflecting the SEC 13F `<value>` official thousands semantics. The stamping MUST happen in the single pure merge function `merge13FFiling(feed, entry)` in `lib/store/feed-json.js`, which stamps the marker, applies the history-dedupe-by-accession merge, and recomputes feed stats. `upsert13FFiling(path, entry)` is a thin wrapper that writes `merge13FFiling(readFeedJson(path), entry)` to disk for backward compatibility and single-shot callers. The aggregator `lib/aggregate/pipeline-a.js` MUST accumulate entries in memory via `merge13FFiling` and write the feed exactly once per run via `writeFeedJson` (NOT once per filing). This keeps future snapshots self-describing, introduces no new mixed-unit debt, and makes per-run disk writes O(1) instead of O(N).

#### Scenario: pipeline write includes marker
- **WHEN** `merge13FFiling` (via `upsert13FFiling` or `pipeline-a`) appends/updates a filer entry in the feed (`feed-13f.json`)
- **THEN** the written entry MUST include `valueUnit: 'thousands'`

#### Scenario: pipeline-a writes feed once per run
- **WHEN** `runPipelineA` processes N new filings in a single run
- **THEN** `feed-13f.json` MUST be written to disk exactly once at the end of the run (after in-memory accumulation via `merge13FFiling`), not once per filing
