## Why

`scripts/deliver.js` reads `~/config.json` instead of `~/.follow-the-money/config.json` (it should match `scripts/check-alerts.js:13`). Because of this path bug, Telegram/Email delivery has **never actually worked** in the agent runtime — every run silently falls back to `{ delivery: { method: 'stdout' } }`. We are paying full maintenance cost (Telegram Bot API + Resend integration, `dotenv` dep, `.env` secret management, two outbound HTTP paths, extensive docs, markdown-injection mitigation, integration tests) for a feature that is dead code. Removing it eliminates the H1 config-path bug, the only outbound PII surface, and ~40 lines of code; the user-facing behavior does not change because stdout has been the only effective path since release.

## What Changes

- **BREAKING**: Rename `scripts/deliver.js` → `scripts/print.js` and reduce its scope to a stdout printer. The script reads `--text` or `--file` and writes content to stdout; nothing else.
- **BREAKING**: Drop the `delivery.method` config field. `~/.follow-the-money/config.json` no longer needs a `delivery` block. `print.js` does not read config.
- **BREAKING**: Drop all Telegram / Email / Resend user-facing docs and onboarding steps. Telegram Bot setup, Resend account setup, `~/.follow-the-money/.env` management, and the `delivery-setup.md` reference are removed.
- **BREAKING**: Remove `dotenv` from `package.json` dependencies and regenerate `package-lock.json`. No remaining user.
- Remove the `delivery-setup.md` reference file entirely.
- Update `README.md`, `SKILL.md`, `references/onboarding.md`, `references/architecture.md`, `references/alert-rules.md`, `references/cron-setup.md` to describe stdout-only flow.
- Trim `tests/scripts/print.test.js` (renamed from `deliver.test.js`) to stdout behavior assertions only.
- Clean up `.claude/settings.local.json` bash permission entries that referenced `TELEGRAM_BOT_TOKEN` or the old `deliver.js` test invocations.
- Update `docs/code-quality-review-2026-07-08.md` H1 entry to mark resolved-by-removal.
- **Optional** (recommended): update `course/index.html` and `course/modules/*.html` to match the simplified system, so teaching material does not describe a feature that no longer exists.

## Capabilities

### New Capabilities

- `delivery`: The delivery contract for the local skill. Read by agents to know what to expect from `scripts/print.js` and how to consume its output. Single method: stdout.

### Modified Capabilities

_None — no existing spec defines delivery requirements today._

## Impact

- `scripts/deliver.js` — removed (replaced by `scripts/print.js`)
- `scripts/print.js` — new, ~10 lines
- `tests/scripts/deliver.test.js` — removed
- `tests/scripts/print.test.js` — new, ~3 cases
- `references/delivery-setup.md` — removed
- `package.json` / `package-lock.json` — drop `dotenv`
- `README.md`, `SKILL.md`, `references/onboarding.md`, `references/architecture.md`, `references/alert-rules.md`, `references/cron-setup.md` — text revisions
- `.claude/settings.local.json` — remove ~5 telegram-related bash permission entries
- `docs/code-quality-review-2026-07-08.md` — mark H1 resolved by removal
- `course/index.html`, `course/modules/*.html` — optional teaching-material sync
- No data file is touched: `state-*.json`, `feed-*.json`, `*.ndjson` are unaffected.
- `scripts/check-alerts.js`, `scripts/aggregate.js`, `scripts/prepare-digest.js`, `scripts/fetch-feed.js`, `scripts/verify-edgar.js`, `scripts/eval.js` are not in the delivery path and are unaffected.