## Why

`FOLLOW_THE_MONEY_FEED_DIR` is the **mode discriminator** (architecture.md L46-55): **set** → skill mode (fetch writes the cache dir, consumers read it); **unset** → local mode (consumers read `process.cwd()`). The intent is correct, but **skill mode never sets the var.** `fetch-feed.js` resolves its target via `defaultTargetDir()` (cache dir) and writes fresh data there, yet exports nothing; `SKILL.md` Step 3/6 pass `FOLLOW_THE_MONEY_FEED_DIR=$FOLLOW_THE_MONEY_FEED_DIR` — an empty shell variable because Step 2 never assigned it. So `prepare-digest.js` falls back to `process.cwd()` and reads the **stale CI-committed feed** in the repo. Result: the fetch step is dead in default config and the digest silently uses stale data, violating SKILL.md's own rule *"Do not silently fall back to a partial digest."*

## What Changes

- **`scripts/fetch-feed.js`**: add a `--print-dir` flag. When present, `main()` prints `defaultTargetDir()` and exits 0 **without doing any network I/O**. `defaultTargetDir()` stays exported (existing tests unchanged). This makes the resolved dir queryable from the shell with a single source of truth.
- **`SKILL.md` (Daily path, Step 2/3/6)**: inline-resolve the dir on every skill-mode data command instead of relying on an unset shell var:
  ```bash
  # Step 2: fetch (writes to cache dir via defaultTargetDir())
  node scripts/fetch-feed.js

  # Steps 3 & 6: only point consumers at the cache dir when fetch succeeded
  if node scripts/fetch-feed.js --print-dir >/dev/null 2>&1; then
    FEED_DIR="$(node scripts/fetch-feed.js --print-dir)"
    FOLLOW_THE_MONEY_FEED_DIR="$FEED_DIR" node scripts/prepare-digest.js
    FOLLOW_THE_MONEY_FEED_DIR="$FEED_DIR" node scripts/check-alerts.js
  else
    # fetch unavailable → documented local-mode fallback to cwd
    node scripts/prepare-digest.js
    node scripts/check-alerts.js
  fi
  ```
  Inlining (rather than `export`) keeps each command **self-contained**, so it is robust even when the agent runtime runs every step in a fresh shell where `export` does not persist.

## Non-Goals (explicitly NOT in this change)

- **D3 (empty/ missing feed silently treated as a normal result)** is out of scope for this change and remains deferred. This change fixes the *directory mismatch* only; it does not add the empty-feed warning guard. Until D3 lands, a fetch failure that falls back to stale/empty cwd data is still silent.
- **We do NOT delete the `|| REPO` cwd fallback** in `prepare-digest.js` / `check-alerts.js`. The variant proposed in `docs/analysis-vs-follow-builders.md` (unify to cache dir + drop `|| REPO`) would break the documented local mode *and* the existing `falls back to cwd when FOLLOW_THE_MONEY_FEED_DIR is unset` tests. Rejected.

## Capabilities

### New Capabilities
- `feed-dir-resolution`: the contract that (a) feed-dir resolution has a single source of truth returning `FOLLOW_THE_MONEY_FEED_DIR` when set else a platform cache default, and (b) in skill mode fetch and the consumers resolve to the **same** directory so fresh data is actually read.

### Modified Capabilities
<!-- None. -->

## Impact

- **Code**: `scripts/fetch-feed.js` (add `--print-dir` branch), `SKILL.md` (daily-path shell block).
- **Behavior**: default-config skill runs now read the freshly fetched cache dir; local mode (`|| REPO` fallback, cwd) is preserved unchanged.
- **Tests**: existing `defaultTargetDir` / `reads from FOLLOW_THE_MONEY_FEED_DIR when set` / `falls back to cwd` tests stay green. New: a flow test asserting `fetch` writes → `prepare` (env = resolved dir) reads the same content; and a `--print-dir` test.
- **No API / dependency / network changes.** Pure local path resolution; no new runtime deps.
