# Design: low-priority-cleanup

## D1 — periodDiff CIK index (L2)

`findPriorEntry` currently scans the full `allFilings` array for every call and sorts it. `prepare-digest.js` calls `periodDiff` once per filer over the same `normalizedFeed`, giving O(n² log n).

Add `buildCikIndex(allFilings)`:
- Returns `Map<cik, entry[]>`, each group sorted descending by `periodOfReport` then `latestFilingDate`.
- `findPriorEntry(filerEntry, cikIndex)` reads `cikIndex.get(filerEntry.filerCik)` and returns the first entry whose `periodOfReport < filerEntry.periodOfReport` (the most recent prior, since the group is sorted desc).

`periodDiff(filerEntry, allFilings, configSources = [], cikIndex)`:
- If `cikIndex` is not supplied, build it from `allFilings` (backward-compatible for direct unit-test calls `periodDiff(f, all)`).
- `prepare-digest.js` builds the index **once** before the `.map` and passes it, so the whole run is O(n).

`findPriorEntry` is module-private, so changing its signature is safe.

## D2 — seenFilings TTL (L3)

`state.seenFilings` is a `{ [accessionNumber]: epochMs }` map with no eviction. Add:
- `SEEN_FILINGS_TTL_DAYS = 90` (named constant, easy to tune).
- `pruneSeenFilings(state, now = Date.now())` that deletes entries older than the TTL.
- `readStateJson` prunes on load (so the persisted file is cleaned on next write).

Trade-off: a pruned accession may be re-fetched, but `upsert13FFiling` dedups by `filerCik`+`periodOfReport`, so no duplicate feed data is produced — only a redundant fetch. Acceptable for a dedup *cache*.

## D3 — unified config loader (L7)

Create `lib/config/load-default-sources.js`:
```js
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

export function loadDefaultSources() {
  const url = new URL('../config/default-sources.json', import.meta.url);
  return JSON.parse(readFileSync(fileURLToPath(url), 'utf8'));
}
```
Update `aggregate.js`, `verify-edgar.js`, and `prepare-digest.js` to call it. `prepare-digest.js` drops the static `import ... with { type: 'json' }` form. Returns the identical object.

## D4 — print.js path safety (L8)

`scripts/print.js` reads `--file` with `readFileSync` and no validation (arbitrary path read). Add `resolveSafePath(filePath)`:
- Resolve against the repo root derived from the script location (`fileURLToPath(new URL('..', import.meta.url))`).
- Reject if the resolved absolute path does not start with the repo root (blocks `../../etc/passwd` and absolute escapes).
- On violation: `console.error` + `process.exit(1)`.

Common case (`node scripts/print.js --file digest.txt` in repo root) still works because `digest.txt` resolves inside the repo root.

## D5 — compute13FSummary side-effect (L10)

Current code pushes into `newPositions` from inside a `.filter()` callback — a hidden side effect. Replace with an explicit loop (or a separate `.filter().map()`) so `newPositions` is computed without mutating during iteration. Output shape is unchanged (`string[]` of CUSIPs).
