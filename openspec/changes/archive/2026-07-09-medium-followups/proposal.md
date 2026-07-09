## Why

The 2026-07-08 code-quality review left three 🟡 medium findings open that no later change resolved: M4 (README 🅱️ mode promises a markdown summary the code never produces), M5 (the CI aggregator has no test gate, so regressions ship silently), and M6 (`pipeline-a` rewrites the entire feed file on every new filing inside its loop). They are low-to-moderate risk, pure-reward, and behavior-preserving — good candidates to close together in one main-branch change.

## What Changes

- **M4 (doc)**: `README.md` 🅱️ step 4 is corrected. `scripts/prepare-digest.js` emits a digest **JSON** and `scripts/print.js` only echoes that JSON to stdout — it does NOT render markdown. The README currently claims "你会看到一份 markdown 摘要", which is false. The README will state the 🅱️ flow outputs JSON and that markdown rendering is 🅰️ agent-mode only. No render script is added (scope kept minimal).
- **M5 (CI)**: `.github/workflows/aggregate.yml` gains an `npm test` step between `npm ci` and `node scripts/aggregate.js`. A failing test suite blocks aggregation/commit for that run.
- **M6 (code, behavior-preserving)**: extract a pure in-memory function `merge13FFiling(feed, entry)` from `upsert13FFiling` in `lib/store/feed-json.js` that stamps `valueUnit: 'thousands'`, applies the history-dedupe-by-accession merge, and recomputes feed stats. `upsert13FFiling(path, entry)` becomes a thin disk wrapper (`writeFeedJson(path, merge13FFiling(readFeedJson(path), entry))`) for backward compatibility. `lib/aggregate/pipeline-a.js` accumulates entries via `merge13FFiling` in memory and writes `feed-13f.json` **once** at the end of the run instead of once per filing.

## Capabilities

### New Capabilities
- `ci-test-gate`: the aggregator GitHub Actions workflow MUST run the project test suite before aggregating/committing feed data.

### Modified Capabilities
- `value-units-normalization`: the single 13F stamping locus becomes the pure `merge13FFiling` function; `pipeline-a` MUST write the feed once per run (not per filing). Existing requirement "pipeline stamps valueUnit marker on write" is updated.
- `documentation-accuracy`: a new requirement that the README 🅱️ instructions accurately describe JSON output (not a markdown summary).

## Impact

- Files: `README.md`, `.github/workflows/aggregate.yml`, `lib/store/feed-json.js`, `lib/aggregate/pipeline-a.js`, and tests (`tests/store/feed-json.test.js`, `tests/aggregate/pipeline-a.test.js`).
- Behavior: unchanged for consumers. Feed content, value-unit marker, history merge, and stats are byte-for-byte equivalent; only the number of disk writes per `pipeline-a` run drops from O(N) to O(1).
- Risk: low. M4 is doc-only; M5 is YAML-only; M6 is a refactor with existing tests covering the stamp + history-merge semantics.
