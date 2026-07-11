---
name: follow-the-money
description: |
  Tracks SEC EDGAR filings of 8 legendary US fund managers (13F) and full-market
  activist/blockholder moves (13D/G). Triggers on `/money`, on cron, or when the
  user asks for "smart money" / "fund moves" / "activist filings" updates.
  Delivers periodic digests and immediate alerts on new SC 13D filings to
  stdout. Works across any AI agent runtime —
  no agent-specific commands or platforms referenced.
---

# Follow the Money, Not the News

Track what legendary US fund managers and major activists are actually doing — directly from SEC filings, in plain English.

This skill covers the periodic digest and the immediate SC 13D alert path. It is intentionally pipeline-focused: it orchestrates the local scripts, prompts, and config under `~/.follow-the-money/`, and delegates every network call to `node scripts/*` so the runtime stays a thin coordinator.

The eight managers tracked are: Berkshire Hathaway, Pershing Square Capital, Scion Asset Management, Baupost Group, Oaktree Capital Management, ARK Invest, Tiger Global Management, and Coatue Management. Filings are pulled from EDGAR's public dataset. Non-secret config lives in `~/.follow-the-money/config.json`. No API keys are required.

If a step in this skill fails, surface the exact stderr from the failing script to the user and stop. Do not silently fall back to a partial digest. Partial output is worse than no output because the user may act on an incomplete view of recent activity.

## Daily path (cron or `/money`)

1. **Load config** from `~/.follow-the-money/config.json`. If missing or `onboardingComplete: false`, run onboarding (see `references/onboarding.md`).
2. **Fetch fresh feed** (skill mode only):

   ```bash
   node scripts/fetch-feed.js
   ```

   Resolves `$FOLLOW_THE_MONEY_FEED_DIR` (default: `$XDG_CACHE_HOME/follow-the-money/feed/` on Linux, `~/Library/Caches/follow-the-money/feed/` on macOS). Downloads `feed-13f.json`, `state-13f.json`, `feed-13dg/`, `state-13dg.ndjson` from `raw.githubusercontent.com/KadenLiu168/follow-the-money/main/`.

   On failure: log the warning to stderr. If `fetch-feed.js` itself is unavailable, steps 3/6 fall back to `cwd` (local mode). A fetch that runs but leaves a stale cache is handled separately (empty-feed guard, out of scope for D1).

3. **Prepare digest**:
   ```bash
   # Resolve the exact cache dir Step 2 wrote to (single source of truth), then
   # run prepare in skill mode. If fetch-feed.js is unavailable, fall back to
   # cwd (local mode). Inlining keeps each step self-contained across shells.
   if FEED_DIR="$(node scripts/fetch-feed.js --print-dir)" && [ -n "$FEED_DIR" ]; then
     FOLLOW_THE_MONEY_FEED_DIR="$FEED_DIR" node scripts/prepare-digest.js
   else
     node scripts/prepare-digest.js
   fi
   ```
   Default lookback is 90 days (one quarter) — 13F is quarterly, so a 1-day lookback returns nothing on non-filing days. Use `--lookback 1` if the user explicitly asks for "today only".
   Reads `feed-13f.json` + `feed-13dg/manifest.json` + current year NDJSON from `$FOLLOW_THE_MONEY_FEED_DIR`, filters by lookback, emits unified JSON to stdout.
4. **Render**: apply `prompts/digest-intro` + `prompts/format-13f` + `prompts/format-13dg` + `prompts/translate` (if `config.language != 'en'`) to the JSON. Output is a Markdown digest.
5. **Print**:
   ```bash
   node scripts/print.js --text "<digest>"
   ```
6. **Check alerts** (resolves the same cache dir as Step 2/3):
   ```bash
   if FEED_DIR="$(node scripts/fetch-feed.js --print-dir)" && [ -n "$FEED_DIR" ]; then
     FOLLOW_THE_MONEY_FEED_DIR="$FEED_DIR" node scripts/check-alerts.js
   else
     node scripts/check-alerts.js
   fi
   ```
   For each alert, apply `prompts/format-alert` and deliver individually.
   (The script atomically persists `config.lastAlertTimestamp` itself — do NOT write it here; the script is the single owner.)

### Feed freshness model

The skill uses a **fetch-then-digest** pattern:

- Step 2 fetches fresh data from `raw.githubusercontent.com/KadenLiu168/follow-the-money/main/*`
  into a per-user cache directory. Override with `FOLLOW_THE_MONEY_FEED_DIR` env var.
- On fetch failure, the skill falls back to local files in `cwd` (suitable when the user has
  run `node scripts/aggregate.js` locally).
- The repo's `.gitignore` excludes the data files for local development, but the CI workflow
  uses `git add -f` to keep publishing them to `main`.

**Local deployment:** `git clone` gets code only (no data). Run `node scripts/aggregate.js`
once to populate `cwd` with data; optionally schedule via cron for freshness.

## Manual trigger

- `/money` (or any user phrase like "show me today's smart money moves") → run digest immediately, skip cron.

## Config change recognition

When the user says one of the following, update `~/.follow-the-money/config.json` and confirm:

| Phrase (examples)                       | Field                      |
| --------------------------------------- | -------------------------- |
| "switch to weekly" / "send me weekly"   | `frequency: "weekly"`      |
| "change time to 9am" / "send at 9:00"   | `deliveryTime: "09:00"`    |
| "in Chinese" / "translate to Chinese"   | `language: "zh"`           |
| "show my settings" / "what's my config" | read + display config.json |

All other changes → confirm with user before writing.

## Onboarding (first run)

Triggers when `~/.follow-the-money/config.json` is missing or `onboardingComplete: false`. See `references/onboarding.md` for the 8-step flow.

## Error handling

- `prepare-digest.js` exits non-zero → surface the error verbatim, do not run `print.js` or `check-alerts.js`, do not update `lastAlertTimestamp`.
- `check-alerts.js` exits non-zero → continue the digest print path, but log the alert-check failure into the digest footer so the user knows alert data may be stale.
- `print.js` exits non-zero → surface the error verbatim. There are no transient failure modes (no network calls); retry is not appropriate.
- Missing references file → do not crash. Skip the section that depends on it and note "reference not loaded" in the digest footer.

## Platform detection

This skill MUST work in any agent runtime. If a shell command is needed, use generic `which <tool>` probing (e.g., `which crontab`, `which launchctl`) — never reference agent names.

## References (load on demand)

- `references/architecture.md` — 4-layer data flow
- `references/data-formats.md` — feed/state schemas
- `references/edgar-fetching.md` — API endpoints, rate limits
- `references/alert-rules.md` — three-level alert policy rationale
- `references/onboarding.md` — 8-step first-run flow
- `references/cron-setup.md` — crontab examples per OS
- `references/prompt-customization.md` — how to override prompts
