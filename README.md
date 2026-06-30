# follow-the-money

Track legendary US fund managers and activist investors — straight from SEC filings. No opinions, no predictions, just the facts.

## Why

Most stock news is commentary. This skill skips the commentary: it pulls 13F (quarterly holdings) from 8 legendary US fund managers, and 13D/G (5% activist/passive moves) from the entire US market, then delivers plain-English digests and immediate alerts on new SC 13D filings.

## What you get

- **Daily/weekly digest** of every new 13F and 13D/G filing in your lookback window.
- **Immediate alert** on every new SC 13D or merged 13D/A — pushed to stdout, Telegram, or email.
- **8 funds tracked:** Berkshire Hathaway, Pershing Square, Scion, Baupost, Oaktree, ARK Invest, Tiger Global, Coatue.
- **Full US market** coverage for 13D/G — every filer, every company.

## Quick Start

### Install
```bash
git clone https://github.com/KadenLiu168/follow-the-money
cd follow-the-money
npm install
```

### Verify EDGAR (one-time, before first run)
```bash
export SEC_EDGAR_USER_AGENT="follow-the-money your@email.com"
npm run verify-edgar
```

### First digest
```bash
node scripts/prepare-digest.js --lookback 7 > digest.txt
node scripts/deliver.js --file digest.txt
```

### Manual trigger
With the skill installed, say `/money` in your agent to get today's digest.

## How it works

SEC EDGAR → center aggregator (GitHub Actions, twice-daily cron) → feed files in this repo → local skill → delivery.

See `references/architecture.md` for the full 4-layer diagram.

## Alert rules

| Form | Treatment |
|---|---|
| SC 13D | Always alert (full details) |
| SC 13D/A | Alert, merged per (filer + issuer + day) |
| SC 13G / 13G/A | Digest only |

Soft cap: if a single cron run produces > 8 alerts, push the first 8 in detail and append `📊 另 N 条 13D/G 详见 digest`.

## Configuration

Stored in `~/.follow-the-money/config.json`:
```json
{
  "schemaVersion": 1,
  "platform": "any",
  "language": "en",
  "timezone": "America/New_York",
  "frequency": "daily",
  "deliveryTime": "08:00",
  "delivery": { "method": "stdout" },
  "lastAlertTimestamp": "2026-06-25T08:00:00.000Z",
  "onboardingComplete": true
}
```

API keys live in `~/.follow-the-money/.env`:
```bash
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHAT_ID=your-chat-id
RESEND_API_KEY=re_your-api-key
EMAIL_TO=you@example.com
```

## Customizing prompts

See `references/prompt-customization.md`.

## Limitations (v1)

- 8 funds centrally curated; user-customizable source lists deferred to v2
- US market only (A-share / HK support deferred)
- No real-time prices
- No Form 4 (insider trades)
- No LLM-based stock recommendations

## Architecture

See `references/architecture.md` and `docs/superpowers/specs/2026-06-24-follow-the-money-design.md`.

## License

MIT
