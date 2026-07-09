# Architecture

Four-layer data flow, layer responsibilities, and key design decisions. Load this when you need to understand *why* the system is shaped the way it is.

## Data Flow

```
[SEC EDGAR]  →  [Center Aggregator (GitHub Actions)]
                          ↓
                  [JSON/NDJSON in this repo]
                          ↓
              [Local Skill on user's machine]
                          ↓
                [Delivery: stdout]
```

| Layer | Runs where | Job |
|---|---|---|
| 1. SEC EDGAR | SEC servers | Source of truth for 13F + 13D/G filings |
| 2. Center aggregator | GitHub Actions cron (`0 12 * * *` + `0 0 * * *` UTC, ≈08:00 ET DST-naive) | Pull from EDGAR, write feed + state files, commit |
| 3. Local skill | User's machine (on cron) | Read feed, prepare digest, detect alerts, dispatch |
| 4. Output | stdout | Periodic digest + immediate 13D alerts |

## Layer Responsibilities

### Layer 1 — SEC EDGAR
- 13F data: `submissions` JSON API + `form13fData.xml`
- 13D/G data: EDGAR full-text search API + daily filing index

### Layer 2 — Center aggregator (`scripts/aggregate.js`)
- Triggered by cron (`0 12 * * *` + `0 0 * * *` UTC, ≈08:00 ET DST-naive) + `workflow_dispatch`
- Single secret: `SEC_EDGAR_USER_AGENT` (format `"AppName email@example.com"`)
- Two parallel pipelines:
  - **A** (13F): CIK-driven, one entry per fund
  - **B** (13D/G): search-driven, append per filing
- Incremental writes: feed files updated, state files updated, commit to repo

### Layer 3 — Local skill
- `scripts/prepare-digest.js` — pull feed + read config + filter by lookback
- `scripts/check-alerts.js` — read feed + filter new 13D/13D/A → alert list
- `scripts/print.js` — emit digest/alert text to stdout

### Skill-mode data freshness

As of 2026-07-03, the skill no longer reads `feed-13f.json` from `cwd`. Instead:

1. `scripts/fetch-feed.js` downloads 4 static data files plus per-year NDJSON discovered from the manifest, from `raw.githubusercontent.com` into `$FOLLOW_THE_MONEY_FEED_DIR` (default: `$XDG_CACHE_HOME/follow-the-money/feed/` on Linux, `~/Library/Caches/follow-the-money/feed/` on macOS).
2. `prepare-digest.js` and `check-alerts.js` read from that env var (fallback to `cwd` for local mode).
3. CI's `aggregate.yml` uses `git add -f` to publish data files to `main` despite `.gitignore` excluding them for local development.
4. The repo is public, so raw URLs need no authentication.

Local deployments are unaffected: `node scripts/aggregate.js` still writes to `cwd`, which the scripts read when `FOLLOW_THE_MONEY_FEED_DIR` is unset.

### Layer 4 — Output
- **Digest**: periodic push (daily / weekly)
- **Alert**: triggered on each SC 13D / SC 13D/A new filing

## Key Design Decisions

### Centralized aggregation
EDGAR's rate limit (10 req/sec) and full-market 13D/G scanning cannot be done locally on every user's machine. The center does the heavy work once and publishes the result.

### No user secrets
The center holds `SEC_EDGAR_USER_AGENT` via a GitHub Actions secret. Users do not need any secrets for delivery — stdout is the only output channel.

### Stateless local skill
All "seen/unseen" state is derived from the feed files plus `config.lastAlertTimestamp`. Deleting `~/.follow-the-money/` does not lose seen information — reinstalling picks up the same state.

### Single source of truth
The center feed is authoritative. Multiple devices reading the same feed get the same digests and same alert history.

### Agent-agnostic
The skill works across any AI agent runtime. No agent brand names anywhere in code, prompts, or SKILL.md. Platform detection uses generic `which <tool>` probing when needed.

## File Layout (data files)

```
follow-the-money/
├── feed-13f.json                  # 13F aggregated feed
├── feed-13dg/
│   ├── manifest.json
│   └── <year>.ndjson              # one filing per line, per year
├── state-13f.json                 # aggregator's 13F dedup state
├── state-13dg.ndjson              # aggregator's 13D/G dedup state
└── config/default-sources.json    # 8 CIKs + 13D/G config
```

See `data-formats.md` for full schemas. See `edgar-fetching.md` for API details.
