# Tasks

## L2 — periodDiff CIK index
- [x] 1.1 Add `buildCikIndex(allFilings)` in `lib/enrich/period-diff.js` (Map<cik, entries[]> sorted desc).
- [x] 1.2 Change `findPriorEntry` to take the index and pick the most-recent prior within the CIK group.
- [x] 1.3 Make `periodDiff` accept an optional `cikIndex` (build internally if absent).
- [x] 1.4 In `prepare-digest.js` build the index once and pass it into the `.map` periodDiff calls.

## L3 — seenFilings TTL
- [x] 2.1 Add `SEEN_FILINGS_TTL_DAYS` constant + `pruneSeenFilings(state, now)` in `lib/store/state-json.js`.
- [x] 2.2 Apply prune in `readStateJson`.

## L7 — unified config loader
- [x] 3.1 Create `lib/config/load-default-sources.js` exporting `loadDefaultSources()`.
- [x] 3.2 Switch `aggregate.js`, `verify-edgar.js`, `prepare-digest.js` to use it (drop the JSON import attribute in prepare-digest).

## L8 — print.js path safety
- [x] 4.1 Add `resolveSafePath(filePath)` (rejects escapes outside repo root) in `scripts/print.js`.
- [x] 4.2 Use it for the `--file` argument; error + exit(1) on violation.

## L10 — compute13FSummary side-effect
- [x] 5.1 Compute `newPositions` without mutating inside `.filter()` in `lib/compute/thirteen-f-summary.js`.

## Tests
- [x] 6.1 `tests/enrich/period-diff.test.js`: index path returns identical prior; prepare-digest-style run identical.
- [x] 6.2 `tests/store/state-json.test.js`: TTL prune drops stale, keeps fresh.
- [x] 6.3 `tests/config/load-default-sources.test.js`: returns parsed default-sources.
- [x] 6.4 `tests/scripts/print.test.js`: in-repo allowed; `../../etc/passwd` and `/etc/passwd` rejected.
- [x] 6.5 `tests/compute/thirteen-f-summary.test.js`: output unchanged (assert newPositions content).

## Validation
- [x] 7.1 `node --check` all changed JS.
- [x] 7.2 `npm test` (full vitest) green.
- [x] 7.3 `openspec validate low-priority-cleanup` and `--all` green.
