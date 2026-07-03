---
name: follow-the-money
description: |
  Tracks SEC EDGAR filings of 8 legendary US fund managers (13F) and full-market
  activist/blockholder moves (13D/G). Triggers on `/money`, on cron, or when the
  user asks for "smart money" / "fund moves" / "activist filings" updates.
  Delivers periodic digests and immediate alerts on new SC 13D filings via
  stdout (default), Telegram, or email. Works across any AI agent runtime —
  no agent-specific commands or platforms referenced.
---

# Follow the Money, Not the News

Track what legendary US fund managers and major activists are actually doing — directly from SEC filings, in plain English.

This skill covers the periodic digest and the immediate SC 13D alert path. It is intentionally pipeline-focused: it orchestrates the local scripts, prompts, and config under `~/.follow-the-money/`, and delegates every network call to `node scripts/*` so the runtime stays a thin coordinator.

The eight managers tracked are: Berkshire Hathaway, Pershing Square Capital, Scion Asset Management, Baupost Group, Oaktree Capital Management, ARK Invest, Tiger Global Management, and Coatue Management. Filings are pulled from EDGAR's public dataset; secrets (Telegram bot token, Resend API key) live in `~/.follow-the-money/.env`, with non-secret config in `config.json`.

If a step in this skill fails, surface the exact stderr from the failing script to the user and stop. Do not silently fall back to a partial digest. Partial output is worse than no output because the user may act on an incomplete view of recent activity.

## Daily path (cron or `/money`)

1. **Load config** from `~/.follow-the-money/config.json`. If missing or `onboardingComplete: false`, run onboarding (see `references/onboarding.md`).
2. **Fetch fresh feed** (skill mode only):
   ```bash
   node scripts/fetch-feed.js
   ```
   Resolves `$FOLLOW_THE_MONEY_FEED_DIR` (default: `$XDG_CACHE_HOME/follow-the-money/feed/` on Linux, `~/Library/Caches/follow-the-money/feed/` on macOS). Downloads `feed-13f.json`, `state-13f.json`, `feed-13dg/`, `state-13dg.ndjson` from `raw.githubusercontent.com/KadenLiu168/follow-the-money/main/`.
   
   On failure: log warning to stderr, fall through to local mode (step 3 reads from `cwd`). Suitable when the user has already run `node scripts/aggregate.js` locally.
   
3. **Prepare digest**:
   ```bash
   FOLLOW_THE_MONEY_FEED_DIR=$FOLLOW_THE_MONEY_FEED_DIR node scripts/prepare-digest.js
   ```
   Default lookback is 90 days (one quarter) — 13F is quarterly, so a 1-day lookback returns nothing on non-filing days. Use `--lookback 1` if the user explicitly asks for "today only".
   Reads `feed-13f.json` + `feed-13dg/manifest.json` + current year NDJSON from `$FOLLOW_THE_MONEY_FEED_DIR`, filters by lookback, emits unified JSON to stdout.
4. **Render**: apply `prompts/digest-intro` + `prompts/format-13f` + `prompts/format-13dg` + `prompts/translate` (if `config.language != 'en'`) to the JSON. Output is a Markdown digest.
5. **Deliver**:
   ```bash
   node scripts/deliver.js --text "<digest>"
   ```
6. **Check alerts** (uses `$FOLLOW_THE_MONEY_FEED_DIR` via env var):
   ```bash
   FOLLOW_THE_MONEY_FEED_DIR=$FOLLOW_THE_MONEY_FEED_DIR node scripts/check-alerts.js
   ```
   For each alert, apply `prompts/format-alert` and deliver individually.
7. **Update state** (after successful delivery): atomically write the latest alert's `filingDate` back to `config.lastAlertTimestamp`.

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

| Phrase (examples) | Field |
|---|---|
| "switch to weekly" / "send me weekly" | `frequency: "weekly"` |
| "change time to 9am" / "send at 9:00" | `deliveryTime: "09:00"` |
| "in Chinese" / "translate to Chinese" | `language: "zh"` |
| "send to Telegram" / "via Telegram" | `delivery.method: "telegram"` (then onboarding step 6) |
| "show my settings" / "what's my config" | read + display config.json |

All other changes → confirm with user before writing.

## Onboarding (first run)

Triggers when `~/.follow-the-money/config.json` is missing or `onboardingComplete: false`. See `references/onboarding.md` for the 8-step flow.

## Error handling

- `prepare-digest.js` exits non-zero → surface the error verbatim, do not run `deliver.js` or `check-alerts.js`, do not update `lastAlertTimestamp`.
- `check-alerts.js` exits non-zero → continue the digest delivery path, but log the alert-check failure into the digest footer so the user knows one channel is stale.
- `deliver.js` exits non-zero → retry up to 2 times with 30s backoff for transient errors (network, 5xx). For 4xx errors (bad token, missing config), stop and surface the error.
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
- `references/delivery-setup.md` — Telegram/email setup
