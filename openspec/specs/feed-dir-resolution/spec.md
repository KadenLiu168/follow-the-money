# feed-dir-resolution Specification

## Purpose
TBD - created by archiving change fix-d1-feed-dir-propagation. Update Purpose after archive.
## Requirements
### Requirement: Feed dir resolution has one source of truth

The resolved feed directory MUST be computed by a single function that returns `FOLLOW_THE_MONEY_FEED_DIR` when the env var is set, otherwise a platform cache default (`$XDG_CACHE_HOME/follow-the-money/feed` on Linux, `~/Library/Caches/follow-the-money/feed` on macOS, `%LOCALAPPDATA%/follow-the-money/feed` on Windows).

#### Scenario: Env override wins
- **WHEN** `FOLLOW_THE_MONEY_FEED_DIR=/custom` is set
- **THEN** the resolved dir MUST equal `/custom`

#### Scenario: Platform default when unset
- **WHEN** the env var is unset on macOS
- **THEN** the resolved dir MUST equal `~/Library/Caches/follow-the-money/feed`

### Requirement: Skill mode fetch and consumers share one dir

When `FOLLOW_THE_MONEY_FEED_DIR` is provided (skill mode), `fetch-feed.js` MUST write to that dir AND `prepare-digest.js` / `check-alerts.js` MUST read from that same dir — no `cwd` divergence at the write/read boundary.

#### Scenario: Fresh fetch is actually consumed
- **WHEN** `fetch-feed.js` writes `feed-13f.json` to the resolved dir
- **AND** `prepare-digest.js` runs with `FOLLOW_THE_MONEY_FEED_DIR` set to that same dir
- **THEN** `prepare-digest.js` MUST read the freshly written file (not a `cwd` copy)

### Requirement: Local mode fallback to cwd is preserved

When `FOLLOW_THE_MONEY_FEED_DIR` is unset, `prepare-digest.js` and `check-alerts.js` MUST fall back to `process.cwd()` so a locally-aggregated feed is read.

#### Scenario: Unset env reads cwd
- **WHEN** the env var is unset
- **THEN** consumers MUST read from `process.cwd()`

