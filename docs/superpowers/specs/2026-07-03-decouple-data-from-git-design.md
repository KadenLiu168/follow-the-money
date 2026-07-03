# Decouple Data Files from Git — Design Spec

**Date:** 2026-07-03
**Status:** Draft (post-brainstorming, pre-implementation)
**Scope:** Single change; not a sub-project split
**Implementation plan:** TBD (will be created via writing-plans skill)

---

## Overview

### Purpose

Make `feed-13f.json`, `state-13f.json`, `feed-13dg/`, and `state-13dg.ndjson` **gitignored for local development** while **continuing to be committed to `main` by the GitHub Action** via `git add -f`. Concurrently, make the repo public so the skill can fetch the data via `raw.githubusercontent.com` without authentication.

The net effect:
- Local clones no longer pull 11MB of JSON over the wire.
- Local `aggregate.js` runs stay local (don't leak into the user's `git status`).
- The CI keeps publishing fresh data to `main` so the skill always sees the latest run.
- The skill fetches from `raw.githubusercontent.com` (public, no auth) instead of reading local files.

### Why

Three forces converged:

1. **Freshness gap.** Today, the skill reads `feed-13f.json` from `cwd`. Local files are frozen at the last `git pull`; the GitHub copy is updated every ~12h by `aggregate.yml`. As of 2026-07-03, the local file is `2026-07-01 03:04 UTC`; the GitHub latest is `2026-07-02 13:41 UTC` — ~34 hours stale.
2. **Skill portability.** For the skill to fetch from GitHub reliably, the repo needs to be public (it's currently private; `raw.githubusercontent.com` returns 404 for unauthenticated requests).
3. **Local hygiene.** Once the data is also published on the server side, there's no reason a local clone should carry it — the local copy is unnecessary weight, and any local `aggregate.js` run produces 11MB of files that show up in `git status`.

### Non-goals

- **Changing CI's publishing destination** (gh-pages, Releases, sister repo). The user explicitly chose "keep pushing to main, same as now" — `git add -f` is the smallest change that achieves the local/remote split.
- **Removing 11MB JSON from git history.** Existing history is not retroactively purged (`git filter-repo` etc.). New clones still pay the history cost once; that cost is bounded by pack compression and is out of scope.
- **Re-architecting the digest pipeline** (compute, enrich, deliver). The pipeline already reads JSON correctly; this spec only changes *where the JSON comes from*.
- **Adding authentication to the skill fetch.** The repo will be public, so the fetch URL needs no token. No `GITHUB_TOKEN` secret is introduced.
- **Backporting data fetches for non-skill consumers** (e.g. the README's `git clone` flow). Local users continue to rely on running `node scripts/aggregate.js` themselves; the README is updated to reflect this.

### Out of scope (will be brainstormed separately)

- Per-filer secret / private-repo data isolation — not relevant; data is public SEC filings.
- Cache layer with TTL (the raw URL already serves CDN-cached content; explicit caching adds complexity for no observed benefit).
- Migrating aggregate.js to a non-Node runtime.

---

## Background — current state

### Data files produced by `scripts/aggregate.js`

```
feed-13f.json              11 MB    JSON   (463988 lines)
state-13f.json            18 KB    JSON
feed-13dg/manifest.json   208 B    JSON
feed-13dg/2024.ndjson     171 KB    NDJSON (400 lines)
state-13dg.ndjson         23 KB    NDJSON
```

All five are currently git-tracked and committed by `.github/workflows/aggregate.yml` to `main` (via `git add feed-13f.json ... && git commit && git push`).

### Today's CI flow (`.github/workflows/aggregate.yml`, lines 29-43)

```yaml
- name: Commit if changed
  run: |
    git config user.name "github-actions[bot]"
    git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
    [ -f feed-13f.json ] && git add feed-13f.json
    [ -d feed-13dg ] && git add feed-13dg/
    [ -f state-13f.json ] && git add state-13f.json
    [ -f state-13dg.ndjson ] && git add state-13dg.ndjson
    if git diff --staged --quiet; then
      echo "No changes"
    else
      git commit -m "chore: update feed ($(date -u +%Y-%m-%dT%H:%M:%SZ))"
      git push
    fi
```

After this spec, the four `git add` lines each gain a `-f` flag.

### Today's skill flow (`SKILL.md` daily path, lines 25-30)

```
2. Prepare digest:
   node scripts/prepare-digest.js
   Reads feed-13f.json + feed-13dg/manifest.json + current year NDJSON,
   filters by lookback, emits unified JSON to stdout.
```

`scripts/prepare-digest.js:11-13` reads `feed-13f.json` and `feed-13dg/` from `cwd`. After this spec, those paths become configurable via an env var, and a new SKILL.md step fetches them via `curl` first.

---

## Architecture

### High-level flow

```
┌──────────────────────────────────────────────────────────────┐
│ GitHub (public repo)                                          │
│                                                              │
│  main branch:                                                 │
│    ├── SKILL.md                                               │
│    ├── scripts/, lib/, prompts/, config/, tests/              │
│    ├── .github/workflows/aggregate.yml                        │
│    ├── .gitignore     ← NEW: data files ignored              │
│    └── (no data files TRACKED, but they exist after CI push)  │
│                                                              │
│  aggregate.yml CI:                                            │
│    1. run aggregate.js                                        │
│    2. git add -f feed-13f.json state-*.json feed-13dg/        │
│    3. git commit -m "chore: update feed"                     │
│    4. git push                                                │
│    → main 分支出现/更新 4 个文件                              │
└──────────────────────────────────────────────────────────────┘
                                │
                                │ curl (no auth, repo public)
                                ▼
┌──────────────────────────────────────────────────────────────┐
│ Skill (agent /money)                                          │
│   1. mkdir -p $FOLLOW_THE_MONEY_FEED_DIR                     │
│   2. curl raw.githubusercontent.com/.../main/feed-13f.json   │
│      → $FOLLOW_THE_MONEY_FEED_DIR/feed-13f.json               │
│   3. ... (4 more files)                                       │
│   4. FOLLOW_THE_MONEY_FEED_DIR=$XDG_CACHE_HOME/...            │
│      node scripts/prepare-digest.js                          │
│   5. (existing) render + deliver + check-alerts               │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ Local deployment (git clone)                                  │
│   1. git clone → code only (data gitignored)                  │
│   2. First run: node scripts/aggregate.js                     │
│      → local $REPO/feed-13f.json                              │
│   3. (optional) cron: aggregate.js keeps it fresh            │
│   4. agent reads $REPO/feed-13f.json (fallback path)          │
└──────────────────────────────────────────────────────────────┘
```

### Layer placement

```
scripts/                  ← entry points (existing)
  ├── aggregate.js        ← unchanged
  ├── prepare-digest.js   ← path resolution refactored
  ├── check-alerts.js     ← path resolution refactored
  ├── deliver.js          ← unchanged
  └── verify-edgar.js     ← unchanged

lib/                      ← all unchanged

.github/workflows/
  └── aggregate.yml       ← 4-line change (`-f` flag)

.gitignore                ← 4 lines added

SKILL.md                  ← daily path step 2 split into 2a (fetch) + 2b (digest)

scripts/lib/fetch/        ← NEW directory
  └── fetch-feed.js       ← new; curl wrapper + path resolver
```

### Why a new `lib/fetch/fetch-feed.js` (vs inlining `curl` in SKILL.md)

- Tests need a Node-callable API (not a shell-out) to assert retry / fallback behavior.
- Future consumers (e.g. a `scripts/check-updates.js` cron helper) can reuse the same code path.
- Keeps SKILL.md a thin coordinator, consistent with the project's existing principle.

---

## Component 1: `scripts/lib/fetch/fetch-feed.js` (NEW)

### Public API

```js
export async function fetchFeed({
  repoOwner,        // string, e.g. 'KadenLiu168'
  repoName,         // string, e.g. 'follow-the-money'
  branch,           // string, default 'main'
  targetDir,        // string, e.g. $XDG_CACHE_HOME/follow-the-money/feed
  files,            // string[] — see File list below
  // optional:
  httpTimeoutMs,    // number, default 15000
  retries,          // number, default 2 (matches SKILL.md deliver.js retry policy)
}) → { ok: true, filesWritten: string[] } | { ok: false, reason: string }
```

### File list (hard-coded inside the module)

```js
const FEED_FILES = [
  { urlPath: 'feed-13f.json',            localName: 'feed-13f.json' },
  { urlPath: 'state-13f.json',           localName: 'state-13f.json' },
  { urlPath: 'feed-13dg/manifest.json',  localName: 'feed-13dg/manifest.json' },
  { urlPath: 'feed-13dg/2024.ndjson',    localName: 'feed-13dg/2024.ndjson' },
  { urlPath: 'state-13dg.ndjson',        localName: 'state-13dg.ndjson' },
];
```

The `feed-13dg/` directory needs at minimum `manifest.json` + the current-year NDJSON. `2024.ndjson` is the only NDJSON in the current feed; this list will be regenerated each fetch by reading `feed-13dg/manifest.json` first and then downloading every year listed under `years.*.file`.

**Implementation note:** Two-phase fetch is required:
1. Fetch `manifest.json` first → discover `years` map.
2. Fetch each `years.*.file` NDJSON.
3. Fetch `state-*.json` and `feed-13f.json` (no dependency).

The module exposes this as one call; callers don't see the two phases.

### Behavior

- Uses Node's built-in `fetch` (Node 20+, no new deps).
- Per file: GET `https://raw.githubusercontent.com/<owner>/<name>/<branch>/<urlPath>` → write atomically (`write to .tmp, rename`) to `<targetDir>/<localName>`.
- On HTTP failure: retry up to `retries` times with exponential backoff (500ms, 1500ms).
- On all retries exhausted: return `{ ok: false, reason: 'http_error:<filename>:<status>' }`.
- Creates `targetDir` and any subdirectories with `mkdir -p` semantics.

### Edge cases

| Case | Behavior |
|---|---|
| `feed-13dg/manifest.json` 404 | Return `ok: false` immediately; manifest is required to discover NDJSON files |
| `feed-13dg/<year>.ndjson` 404 (year listed in manifest but missing) | Log warning, continue with other years, mark manifest-stale in result |
| `feed-13f.json` 404 | Return `ok: false` |
| Network timeout | Retry; eventually return `ok: false` with reason |
| Target dir on a read-only filesystem | Catch EACCES, return `ok: false` with reason |
| Existing files in targetDir | Overwrite (the fetch represents the latest authoritative state) |
| Concurrent fetches (parallel `node scripts/fetch-feed.js` calls) | No locking — last write wins; this matches the "always latest" semantic |

### Error handling

- The function returns a result object; it does **not throw**. The caller (SKILL.md agent) decides whether to fall back to local files.
- On any failure, the function does **not delete** existing files in `targetDir`. Stale data is safer than no data.

---

## Component 2: `scripts/prepare-digest.js` — path resolution refactor

### Current behavior (lines 11-13)

```js
const REPO = process.cwd();
const FEED_13F = join(REPO, 'feed-13f.json');
const FEED_13DG_DIR = join(REPO, 'feed-13dg');
```

### New behavior

```js
const REPO = process.cwd();
const FEED_DIR = process.env.FOLLOW_THE_MONEY_FEED_DIR
  || REPO;  // backward-compat: local mode still works
const FEED_13F = join(FEED_DIR, 'feed-13f.json');
const FEED_13DG_DIR = join(FEED_DIR, 'feed-13dg');
```

The script otherwise unchanged. The env var resolution is the only delta.

### Why env var (not CLI flag)

- `prepare-digest.js` is invoked by SKILL.md daily path step 2. The fetch step (step 1.5) sets the env var. CLI flags would force every caller to pass the same path.
- Backward compat: callers that don't set the env var get the previous behavior.

---

## Component 3: `scripts/check-alerts.js` — same refactor

Identical pattern to Component 2: replace `REPO` with `FEED_DIR` (env var → REPO fallback). No other changes.

---

## Component 4: `.gitignore` — 4 lines added

```gitignore
# Locally generated feed/state data (skill mode fetches from GitHub; CI uses git add -f)
feed-13f.json
state-13f.json
feed-13dg/
state-13dg.ndjson
```

The trailing slash on `feed-13dg/` is significant: it matches the directory only (so `feed-13dg-manifest.txt` would not match — defensive against future files).

`feed-13dg/manifest.json` is gitignored by virtue of being inside `feed-13dg/`.

---

## Component 5: `.github/workflows/aggregate.yml` — 4 `-f` flags added

```diff
   - name: Commit if changed
     run: |
       git config user.name "github-actions[bot]"
       git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
-      [ -f feed-13f.json ] && git add feed-13f.json
-      [ -d feed-13dg ] && git add feed-13dg/
-      [ -f state-13f.json ] && git add state-13f.json
-      [ -f state-13dg.ndjson ] && git add state-13dg.ndjson
+      [ -f feed-13f.json ]     && git add -f feed-13f.json
+      [ -d feed-13dg ]         && git add -f feed-13dg/
+      [ -f state-13f.json ]    && git add -f state-13f.json
+      [ -f state-13dg.ndjson ] && git add -f state-13dg.ndjson
       if git diff --staged --quiet; then
         echo "No changes"
       else
         git commit -m "chore: update feed ($(date -u +%Y-%m-%dT%H:%M:%SZ))"
         git push
       fi
```

`git add -f` forces the add even when the path is `.gitignore`d. This is the standard Git pattern for "files that should be tracked by CI but not by humans".

---

## Component 6: `SKILL.md` — daily path split into fetch + digest

### Current daily path (lines 22-41)

```
1. Load config
2. Prepare digest
3. Render
4. Deliver
5. Check alerts
6. Update state
```

### New daily path

```
1. Load config
2. Fetch fresh feed (NEW, replaces local-only assumption)
   2a. Set FEED_DIR = ${XDG_CACHE_HOME:-$HOME/.cache}/follow-the-money/feed
       (mkdir -p $FEED_DIR)
   2b. Run: node scripts/fetch-feed.js
       On failure → log warning, fall back to cwd (local mode)
3. Prepare digest
       env FOLLOW_THE_MONEY_FEED_DIR=$FEED_DIR \
         node scripts/prepare-digest.js
4. Render
5. Deliver
6. Check alerts (uses $FEED_DIR via env var)
7. Update state
```

The "fall back to cwd" path preserves backward compatibility for users who already have data in their working directory (e.g. they ran `aggregate.js` locally).

### New SKILL.md section under "Daily path"

```markdown
### Feed freshness model

The skill uses a **fetch-then-digest** pattern:
- Step 2 fetches fresh data from `raw.githubusercontent.com/KadenLiu168/follow-the-money/main/*`
  into a per-user cache directory (`$XDG_CACHE_HOME/follow-the-money/feed/` on Linux,
  `~/Library/Caches/follow-the-money/feed/` on macOS, `%LOCALAPPDATA%\follow-the-money\feed\`
  on Windows). Override with `FOLLOW_THE_MONEY_FEED_DIR` env var.
- On fetch failure, the skill falls back to local files in the working directory
  (suitable when the user has run `node scripts/aggregate.js` locally).
- The repo's `.gitignore` excludes the data files for local development, but the
  CI workflow uses `git add -f` to keep publishing them to `main`.
```

---

## Component 7: GitHub repo visibility — public

Manual one-time change in GitHub UI: Settings → General → Danger Zone → Change repository visibility → Public.

After change, `https://raw.githubusercontent.com/KadenLiu168/follow-the-money/main/feed-13f.json` is reachable without authentication (verified today: returns HTTP 404 for private repo; expected to return HTTP 200 after visibility change).

---

## Data flow summary

### URLs the skill fetches

```
https://raw.githubusercontent.com/KadenLiu168/follow-the-money/main/feed-13f.json
https://raw.githubusercontent.com/KadenLiu168/follow-the-money/main/state-13f.json
https://raw.githubusercontent.com/KadenLiu168/follow-the-money/main/feed-13dg/manifest.json
https://raw.githubusercontent.com/KadenLiu168/follow-the-money/main/feed-13dg/2024.ndjson
https://raw.githubusercontent.com/KadenLiu168/follow-the-money/main/state-13dg.ndjson
```

(One NDJSON per year listed in `feed-13dg/manifest.json#years`. Today: `2024.ndjson` only.)

### Local cache directory

Resolved by `scripts/lib/fetch/fetch-feed.js`:

| Platform | Default path |
|---|---|
| Linux | `$XDG_CACHE_HOME/follow-the-money/feed/` (default `$HOME/.cache/follow-the-money/feed/`) |
| macOS | `$HOME/Library/Caches/follow-the-money/feed/` |
| Windows | `%LOCALAPPDATA%\follow-the-money\feed\` |

Override: `FOLLOW_THE_MONEY_FEED_DIR` env var.

### What each consumer reads

| Consumer | Reads from | Source |
|---|---|---|
| Skill mode (`/money`) | `$FOLLOW_THE_MONEY_FEED_DIR` (fetched in step 2) | Network → GitHub raw URL |
| Local mode (user runs `aggregate.js`) | `cwd` | Local disk |
| Local mode fallback (skill fetch failed) | `cwd` | Local disk |
| CI workflow `aggregate.yml` | `cwd` (written by `aggregate.js`, committed with `-f`) | Disk → git push to main |

---

## Error handling

| Failure | Behavior | Impact |
|---|---|---|
| Skill fetch: `feed-13f.json` 404 | Return `ok: false`; SKILL.md step 2 logs warning, falls through to local mode (cwd) | If local has stale data → user sees stale digest; if local has no data → prepare-digest.js exits with stderr (existing behavior) |
| Skill fetch: manifest.json 404 (CI just started) | Return `ok: false`; same fallback | Same as above |
| Skill fetch: per-year NDJSON 404 | Log warning, continue with other years | One year of 13D/G data missing from digest; digest still renders with reduced coverage |
| Network offline | All fetches fail with timeout | Fall through to local mode |
| Local mode + no local data | `prepare-digest.js` exits non-zero (existing) | Skill halts per SKILL.md error handling section |
| CI push fails (permissions, branch protection) | Workflow step exits non-zero | Feed stays at last successful push; all consumers see this state |
| `git add -f` accidentally adds a non-data file | Not possible: CI script uses explicit file paths, no globs | None |
| Repo public → exposure of data files | The data is **already public** (SEC EDGAR); only difference is now it's also at a stable raw URL | None (intentional outcome) |

---

## Testing strategy

### Existing tests

`tests/fixtures/feed-13dg/manifest.json` and similar fixtures are **not** affected. The new path resolution honors the env var but defaults to `cwd`, so existing tests that don't set `FOLLOW_THE_MONEY_FEED_DIR` continue to work.

### New tests (TDD order)

**`tests/lib/fetch/fetch-feed.test.js`** (new file)

| Test | Setup | Expected |
|---|---|---|
| All files 200, fresh fetch | Mock fetch returns 200 for all 5 files | `ok: true`, all 5 files written, atomic via .tmp rename |
| `feed-13f.json` 404 | Mock returns 404 for feed-13f.json | `ok: false`, reason contains 'http_error', `feed-13f.json` not written, other files also not written (manifest discovery happens first) |
| Manifest 200, NDJSON 404 | Mock returns 404 for one NDJSON | `ok: true`, warning logged, other files written |
| Network timeout | Mock fetch rejects with AbortError | Retries up to `retries` times, then `ok: false` |
| Concurrent calls | Two simultaneous fetchFeed calls | Both succeed (no lock; last-write-wins) |
| Existing files in targetDir | Pre-populate `feed-13f.json` with stale content | New fetch overwrites stale content atomically |

**`tests/scripts/prepare-digest.test.js`** (existing file, add tests)

| Test | Setup | Expected |
|---|---|---|
| `FOLLOW_THE_MONEY_FEED_DIR` set, files exist there | Set env var, write data to env var dir | Reads from env var dir (not cwd) |
| `FOLLOW_THE_MONEY_FEED_DIR` unset | Unset env var | Reads from cwd (backward compat) |
| `FOLLOW_THE_MONEY_FEED_DIR` set, files don't exist there | Set env var, no files | Exits non-zero with stderr (existing behavior) |

**`tests/scripts/check-alerts.test.js`** (existing file, add test)

| Test | Setup | Expected |
|---|---|---|
| `FOLLOW_THE_MONEY_FEED_DIR` set | Set env var, write manifest + ndjson | Reads from env var dir |
| Unset | Default | Reads from cwd |

**CI workflow validation** (manual)

- After merge, trigger `workflow_dispatch` once → confirm `git add -f` succeeds, files appear on `main`, raw URLs return 200.
- Wait one cron tick (next `0 12 * * *` or `0 0 * * *` UTC) → confirm files updated as expected.

**End-to-end skill test** (manual, post-merge)

- Trigger `/money` from a fresh clone (no local data).
- Confirm fetch step succeeds, prepare-digest reads from cache dir, digest renders with latest EDGAR data.

### Out of scope for tests

- Live HTTP testing against `raw.githubusercontent.com` (flaky; covered by manual smoke test).
- GitHub repo visibility change (manual UI step; out of code scope).

---

## Migration / rollout

### Pre-merge checklist

1. ✅ Spec reviewed and approved.
2. Implementation plan written via writing-plans skill.
3. All new tests written and passing locally.
4. `npm test` passes (existing 92 tests + new fetch-feed tests + new env-var tests).

### Merge order (single PR)

The change is one logical unit and ships as one PR:
1. `.gitignore` updated (new tracked lines)
2. `scripts/lib/fetch/fetch-feed.js` added (new file)
3. `scripts/prepare-digest.js`, `scripts/check-alerts.js` updated (env var resolution)
4. `.github/workflows/aggregate.yml` updated (`-f` flags)
5. `SKILL.md` updated (new step 2 + Feed freshness model section)
6. `README.md` updated (local mode note)
7. `references/architecture.md` updated (data flow diagram)
8. `tests/lib/fetch/fetch-feed.test.js` added
9. `tests/scripts/prepare-digest.test.js`, `tests/scripts/check-alerts.test.js` augmented

### Post-merge steps (manual)

1. **Change repo visibility to public** (Settings → General → Danger Zone).
2. Verify `curl https://raw.githubusercontent.com/KadenLiu168/follow-the-money/main/feed-13f.json` returns 200.
3. Trigger `workflow_dispatch` on `aggregate.yml` to confirm CI still publishes successfully.
4. Trigger `/money` from a fresh clone (with no local data) to confirm fetch works.

### Rollback plan

Single revert PR restores all components. The data files will still be on `main` from prior CI runs; no data loss. The `.gitignore` change is additive; reverting it just means the files become tracked again (no behavioral regression).

---

## References

- **Brainstorming context:** conversation 2026-07-03
- **Current CI:** `.github/workflows/aggregate.yml`
- **Current skill:** `SKILL.md`
- **Data readers:** `scripts/prepare-digest.js`, `scripts/check-alerts.js`
- **Data writer:** `scripts/aggregate.js` (unchanged by this spec)
- **Existing related spec:** `docs/superpowers/specs/2026-07-01-digest-data-correctness-design.md` (style reference)
- **Repo URL pattern:** `https://github.com/KadenLiu168/follow-the-money`