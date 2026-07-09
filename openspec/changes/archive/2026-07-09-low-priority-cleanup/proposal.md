# Proposal: low-priority-cleanup

## Summary

Address the remaining **low-priority** findings from `docs/code-quality-review-2026-07-08.md` that are still open and safe to bundle. This change covers **L2, L3, L7, L8, L10**.

### Scope corrections (already resolved, excluded)

- **L1** (NDJSON append) — resolved by change `ndjson-append-write` (P1-2).
- **L5** (`engines.node >=20.19.0`) — `package.json:7` already reads `">=20.19.0"`.
- **L6** (`course/` gitignore) — `.gitignore:51` already contains `course/` and `git ls-files course/` returns 0 (untracked).

### Deferred (out of scope, noted for later)

- **L4** (ESLint/Prettier/`.nvmrc`) — config-heavy; making `lint` pass across the whole repo would breach the "minimal change / touch only this change" rule. Handle as its own change later.
- **L9** (centralize magic numbers) — broad, would touch many files unrelated to this change. Handle separately.

## Goals

1. **L2** — `periodDiff` builds a per-CIK index once so prior-period lookup is O(n) instead of O(n²) across the digest run.
2. **L3** — `state.seenFilings` gains a TTL prune so the map does not grow unbounded.
3. **L7** — all three readers of `config/default-sources.json` use one shared `loadDefaultSources()` loader.
4. **L8** — `scripts/print.js --file` rejects paths that escape the repo root.
5. **L10** — `compute13FSummary` no longer mutates external state inside a `.filter()` callback.

## Non-Goals

- No new runtime behavior beyond the TTL prune (L3), which is a cache-eviction safety net; the feed itself remains the source of truth (upsert dedups by `filerCik`+`periodOfReport`).
- No lint/format infrastructure (L4) and no magic-number hunt (L9).

## Impact

- Files touched: `lib/enrich/period-diff.js`, `lib/store/state-json.js`, `lib/config/load-default-sources.js` (NEW), `scripts/print.js`, `lib/compute/thirteen-f-summary.js`, `scripts/aggregate.js`, `scripts/verify-edgar.js`, `scripts/prepare-digest.js`.
- All changes are behavior-preserving except L3 (intentional cache eviction, no data loss).
