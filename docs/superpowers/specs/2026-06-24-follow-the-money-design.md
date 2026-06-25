# follow-the-money Design Spec

**Date:** 2026-06-25
**Status:** Validated (post-brainstorming)
**Implementation plan:** `docs/superpowers/plans/2026-06-24-follow-the-money.md`

---

## Overview

### Purpose

A skill that tracks the SEC EDGAR filings of legendary US fund managers (13F) and full-market activist/blockholder moves (13D/G), then delivers periodic digests plus immediate alerts on new SC 13D filings.

### Why

Most stock news comes from commentators summarizing what the smart money is doing. This skill flips it: track the filings directly. Eight legendary US fund managers whose quarterly 13F filings reveal exactly where they're putting their capital, plus every activist/blockholder 13D/G move on the entire US market.

**No opinions, no predictions, no commentary. Just the facts, in plain English.**

### Non-goals (v1)

- Form 4 tracking (insider trades — too high volume)
- A-share / HK market support
- User-customizable source lists (8 funds centrally curated)
- Real-time prices
- LLM-based stock recommendations

---

## Architecture

### Four-layer data flow

```
[SEC EDGAR]  →  [Center Aggregator (GitHub Actions)]
                          ↓
                    [JSON/NDJSON in this repo]
                          ↓
              [Local Skill on user's machine]
                          ↓
                    [Delivery: stdout / Telegram / Email]
```

**Layer 1 — SEC EDGAR:**
- 13F data: submissions JSON API + form13fData.xml
- 13D/G data: EDGAR full-text search API + daily filing index

**Layer 2 — Center aggregator (GitHub Actions):**
- Triggered by cron (08:00 ET + 20:00 ET daily) + manual dispatch
- Single secret: `SEC_EDGAR_USER_AGENT` (format: `"AppName email@example.com"`)
- Two parallel pipelines: A (13F by CIK list) / B (13D/G by form list)
- Incrementally writes feed files + updates state files; commits to repo

**Layer 3 — Local skill:**
- `prepare-digest.js`: pull feed + read config + filter by lookback
- `check-alerts.js`: read feed + filter new 13D/13D/A → alert list
- `deliver.js`: dispatch (stdout/Telegram/email)

**Layer 4 — Output:**
- **Digest**: periodic push (daily/weekly)
- **Alert**: triggered on each 13D/13D/A new filing

### Why this architecture

- **Centralized aggregation:** EDGAR rate limit + full-market 13D/G scanning cannot be done locally
- **No user secrets for content:** center holds User-Agent via GitHub Actions secret
- **Stateless local:** all "seen/unseen" state derived from feed files

### Agent-agnostic principle

The skill MUST work across any AI agent runtime (Claude Code, OpenClaw, Cursor, etc.). No agent-specific names, commands, or platforms referenced anywhere in code, prompts, or SKILL.md. Platform detection happens via generic tool probing (`which <tool>` for known utilities), never via agent brand names.

---

## Tracked Sources

### 13F Filers (8 funds)

| Fund | CIK | Style |
|---|---|---|
| Berkshire Hathaway | 0001067983 | value |
| Pershing Square | 0001336528 | activist-value |
| Scion Asset Management | 0001641562 | deep-value |
| Baupost Group | 0001061768 | value |
| Oaktree Capital | 0000945323 | distressed-value |
| ARK Invest | 0001601072 | thematic-growth |
| Tiger Global Management | 0001167483 | growth |
| Coatue Management | 0001532173 | growth |

**Note:** CIKs must be verified against EDGAR before launch. Verification step in `scripts/verify-edgar.js`.

### 13D/G Scope

Full US market. Any filer, any company. Forms tracked:
- SC 13D, SC 13D/A
- SC 13G, SC 13G/A

---

## Data Formats

### Directory layout (data files in repo)

```
follow-the-money/
├── feed-13f.json                          # 13F aggregated feed (single file)
├── feed-13dg/                             # 13D/G aggregated feed (by year)
│   ├── manifest.json
│   ├── 2024.ndjson
│   ├── 2025.ndjson
│   └── 2026.ndjson
├── state-13f.json                         # aggregator's 13F dedup state
├── state-13dg.ndjson                      # aggregator's 13D/G dedup state
├── state-13dg-alerts.log                  # (optional) audit log of alerts pushed
├── config/
│   └── default-sources.json               # 8 CIKs + 13D/G config
└── ...
```

### `feed-13f.json` (single JSON file)

```json
{
  "schemaVersion": 1,
  "generatedAt": "2026-05-15T08:00:00.000Z",
  "lookbackDays": 90,
  "thirteenF": [
    {
      "filerCik": "0001067983",
      "filerName": "Berkshire Hathaway Inc",
      "latestFilingDate": "2026-06-10",
      "latestFormType": "13F-HR/A",
      "latestAccessionNumber": "0001067983-26-000456",
      "periodOfReport": "2026-03-31",
      "history": [
        { "filingDate": "2026-05-15", "formType": "13F-HR",  "accessionNumber": "0001067983-26-000123" },
        { "filingDate": "2026-06-10", "formType": "13F-HR/A", "accessionNumber": "0001067983-26-000456" }
      ],
      "holdings": [
        {
          "cusip": "037833100",
          "issuerName": "APPLE INC",
          "shares": 300000000,
          "valueUsd": 58200000000,
          "votingAuthority": { "sole": 300000000, "shared": 0, "none": 0 }
        }
      ],
      "summary": {
        "totalHoldingsCount": 1,
        "totalValueUsd": 58200000000,
        "newPositions": ["037833100"],
        "closedPositions": [],
        "increasedPositions": 0,
        "decreasedPositions": 0
      }
    }
  ],
  "stats": { "thirteenFFilings": 1, "thirteenFHoldings": 1 }
}
```

**13F-HR/A handling:** When a new 13F-HR/A arrives with the same `(filerCik, periodOfReport)` as an existing entry, **overwrite** the existing entry's holdings + summary, append to `history`, and update `latestFilingDate` / `latestFormType` / `latestAccessionNumber`. delta is always computed against the most recent entry with a **different** `periodOfReport`.

### `feed-13dg/manifest.json`

```json
{
  "schemaVersion": 1,
  "currentYear": 2026,
  "years": {
    "2026": { "file": "feed-13dg/2026.ndjson", "count": 8934, "firstDate": "2026-01-01", "lastDate": "2026-06-25" },
    "2025": { "file": "feed-13dg/2025.ndjson", "count": 42103, "firstDate": "2025-01-02", "lastDate": "2025-12-31" }
  }
}
```

### `feed-13dg/<year>.ndjson` (NDJSON, one filing per line)

```ndjson
{"filerCik":"0000932470","filerName":"ICAHN CARL C","issuerCik":"0001717393","issuerName":"Jet.AI Inc","issuerTicker":"JTAI","formType":"SC 13D","filingDate":"2026-06-20","ownershipPercent":6.8,"sharesOwned":4500000,"intent":"active","accessionNumber":"0000932470-26-000045","primaryDocUrl":"https://www.sec.gov/Archives/edgar/data/932470/000093247026000045/primary_doc.html"}
{"filerCik":"0000893855","filerName":"ELLIOTT INVESTMENT MANAGEMENT L.P.","issuerCik":"0001315098","issuerName":"Activision Blizzard Inc","issuerTicker":"ATVI","formType":"SC 13G","filingDate":"2026-06-18","ownershipPercent":5.1,"sharesOwned":4900000,"intent":"passive","accessionNumber":"0000893855-26-000078","primaryDocUrl":"https://www.sec.gov/Archives/edgar/data/893855/000089385526000078/primary_doc.html"}
```

**Why per-year split:** Feed files grow append-only forever. Year-split keeps each file ~50MB/year; git diff stays small and mergeable. Digest logic reads current year + previous year to handle cross-year boundaries.

### `state-13f.json`

```json
{
  "lastUpdated": "2026-05-15T08:00:00.000Z",
  "seenFilings": {
    "0001067983-26-000123": 1715740800000
  }
}
```

### `state-13dg.ndjson`

```ndjson
{"accession":"0000932470-26-000045","seenAt":1719250000000}
{"accession":"0000893855-26-000078","seenAt":1719100000000}
```

### Local state — none (derived)

**Decision:** Local skill has **no independent alert state file**. Alert deduplication is purely derived from `feed-13dg/manifest.json` + the user's `config.lastAlertTimestamp` (stored in `~/.follow-the-money/config.json`).

Rationale:
- Single source of truth: center feed is authoritative
- Zero-cost reinstall: deleting `~/.follow-the-money/` doesn't lose "seen" information
- Multi-device sync: every device reads the same feed
- Atomic write: temp file + rename to avoid half-written lines

### Naming conventions

- Times: ISO 8601 strings
- Money: USD + units (B/M)
- CIK: 10-digit zero-padded string
- Accession number: 18 chars with dashes
- Ticker: uppercase

### NDJSON robustness

All NDJSON writers MUST use atomic write (temp file + rename) to prevent half-line corruption. All NDJSON readers MUST validate line numbers on startup; if gaps detected, log a warning and backfill from `feed-13dg/manifest.json` count vs. on-disk line count.

---

## Alert Strategy

### Three-level classification

| Form | Treatment | Rationale |
|---|---|---|
| SC 13D | Always alert (full details) | Active investor, 5% threshold cross, rare & important |
| SC 13D/A | Alert but merged per (filer + issuer + day) | Amendment, usually position/intent tweak, can be noisy |
| SC 13G | Digest only | Passive, high volume |
| SC 13G/A | Digest only | Same as 13G |

### Merging rule (13D/A)

When multiple 13D/A filings have the same `(filerCik, issuerCik, filingDate)`:
- Combine into one alert: `🚨 [filer] 修订了 [issuer] 的 13D（N 次修订，[position change summary]）`
- position change summary derived from comparing last vs. current ownershipPercent

### Soft cap (anti-spam)

- Single cron run produces ≤ 8 alerts → push all
- Single cron run produces > 8 alerts → push first 8 in detail, append one summary: `📊 另 N 条 13D/G 详见 digest`

### intent field — by form type only

**Decision:** intent is derived purely from form type. No Item 4 text regex.

| Form | intent |
|---|---|
| SC 13D / 13D/A | `active` |
| SC 13G / 13G/A | `passive` |

Rationale: SEC legal framework already separates 13D (active) from 13G (passive). Item 4 text is mostly legal boilerplate, unreliable signal. Alert wording uses "举牌" (active) vs "披露" (passive) for clarity.

### Alert deduplication (derived state)

check-alerts.js logic:

```js
const lastAlert = config.lastAlertTimestamp || "1970-01-01";
const newCritical = feed.filter(f =>
  ALERT_FORMS.has(f.formType) && f.filingDate > lastAlert
);
if (newCritical.length === 0) exit(0);
deliver(newCritical);
config.lastAlertTimestamp = newCritical.at(-1).filingDate;
atomicWriteConfig(config);
```

`atomicWriteConfig` uses temp+rename. If push crashes between delivery and timestamp update, the next run re-delivers the last item — acceptable for v1.

---

## Components

### File structure

```
follow-the-money/
├── package.json
├── .gitignore                                # .env, node_modules, *.log
├── LICENSE                                   # MIT
├── README.md
├── SKILL.md                                  # agent behavior spec (concise)
├── config/
│   └── default-sources.json                  # 8 CIKs + 13D/G config
├── scripts/
│   ├── aggregate.js                          # center aggregator (GitHub Action entry)
│   ├── prepare-digest.js                     # local digest preparation
│   ├── check-alerts.js                       # local alert detection
│   ├── deliver.js                            # delivery (stdout/Telegram/email)
│   ├── verify-edgar.js                       # pre-launch real-EDGAR validation
│   └── eval.js                               # evals runner
├── lib/
│   ├── token-bucket.js
│   ├── http-client.js
│   ├── parsers/
│   │   ├── thirteen-f.js
│   │   └── thirteen-dg.js                    # intent-by-form-type only
│   ├── compute/
│   │   └── thirteen-f-summary.js
│   ├── aggregate/
│   │   ├── pipeline-a.js                     # 13F (CIK-driven)
│   │   └── pipeline-b.js                     # 13D/G (search-driven)
│   ├── store/
│   │   ├── feed-json.js                      # read/write feed-13f.json
│   │   ├── feed-ndjson.js                    # read/append feed-13dg/*.ndjson
│   │   ├── manifest.js                       # read/write feed-13dg/manifest.json
│   │   ├── state-json.js                     # aggregator's 13F dedup state
│   │   └── state-ndjson.js                   # aggregator's 13D/G dedup state
│   ├── feed/
│   │   ├── filter-by-lookback.js
│   │   └── merge-by-issuer.js                # 13D/A merge helper for alerts
│   ├── alert/
│   │   ├── classify.js                       # 13D → alert, 13G → digest
│   │   └── merge-amendments.js
│   └── edgar/
│       ├── fetch-submissions.js
│       ├── fetch-thirteen-f-xml.js
│       └── fetch-thirteen-dg-search.js
├── prompts/
│   ├── digest-intro.md
│   ├── format-13f.md
│   ├── format-13dg.md
│   ├── format-alert.md
│   └── translate.md
├── references/                                # agent-loaded on demand
│   ├── architecture.md
│   ├── data-formats.md
│   ├── edgar-fetching.md
│   ├── alert-rules.md
│   ├── onboarding.md                          # 8-step detailed flow
│   ├── cron-setup.md                          # crontab examples
│   ├── prompt-customization.md                # how to override prompts
│   └── delivery-setup.md                      # Telegram/Email detailed steps
├── .github/
│   └── workflows/
│       └── aggregate.yml                      # cron + dispatch
├── evals/
│   └── evals.json                             # 8 prompts with checks[]
└── tests/                                     # mirror lib/ structure
    ├── parsers/
    ├── compute/
    ├── aggregate/
    ├── store/
    ├── alert/
    ├── feed/
    ├── edgar/
    ├── scripts/
    └── fixtures/
```

---

## Workflows

### Digest flow (periodic, on cron or `/money`)

1. Load `~/.follow-the-money/config.json`
2. Run `scripts/prepare-digest.js`:
   - Pull `feed-13f.json` from repo
   - Pull `feed-13dg/manifest.json` + current + previous year NDJSON
   - Filter by lookback (1 day daily / 7 days weekly)
   - Load prompts (user override → repo default)
   - Emit unified JSON to stdout
3. Agent receives JSON, applies `prompts.intro` + per-section prompts to remix into readable digest
4. Apply language (`en` / `zh` / `bilingual`) per `prompts.translate`
5. Run `scripts/deliver.js --file <digest>` to push

### Alert flow (every cron run)

1. Run `scripts/check-alerts.js`:
   - Read `feed-13dg/manifest.json` + current year NDJSON
   - Filter: `formType in {SC 13D, SC 13D/A}` AND `filingDate > config.lastAlertTimestamp`
   - Classify by form type: SC 13D → individual, SC 13D/A → merge per (filer+issuer+day)
   - Apply soft cap (≤ 8 detail; > 8 add summary)
2. For each critical event, agent applies `prompts.format-alert`
3. Run `scripts/deliver.js --text "<alert>"` per event
4. After successful delivery: update `config.lastAlertTimestamp` to latest `filingDate` (atomic write)

### Onboarding (first run, 8 steps)

Detailed flow in `references/onboarding.md`. Summary:

1. Introduction (what skill does, sources)
2. Frequency (daily/weekly)
3. Time + timezone (e.g., 08:00 America/New_York)
4. Delivery method (stdout default; offer Telegram/Email)
5. Language (en / zh / bilingual)
6. API keys (only if Telegram/Email)
7. Show sources (8 funds + full 13D/G market)
8. Reminder: settings mutable via conversation
9. Set up cron (per OS, see `references/cron-setup.md`)
10. Run welcome digest, ask for feedback

**Onboarding triggers only when `~/.follow-the-money/config.json` missing or `onboardingComplete: false`.**

### Manual trigger

`/money` (or whatever slash command the agent maps): skip cron check, run digest immediately.

### Config changes via conversation

Recognize phrases:
- "Switch to weekly" → `frequency: "weekly"`
- "Change time to X" → `deliveryTime: "X"`
- "Translate to Chinese" → `language: "zh"`
- "Send to Telegram" → `delivery.method: "telegram"` + onboarding for setup
- "Show my settings" → read config.json, display human-readable

---

## Configuration

### `~/.follow-the-money/config.json`

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

### `~/.follow-the-money/.env`

```bash
# Only required if delivery.method is telegram or email
TELEGRAM_BOT_TOKEN=your-bot-token
RESEND_API_KEY=re_your-api-key
```

`platform: "any"` because we don't detect specific agent names; this field is informational only.

---

## Error Handling

### Aggregator layer (GitHub Actions)

- Single CIK failure → log + continue
- Single filing parse failure → skip + log
- EDGAR total outage → do not commit feed; let cron retry next run
- Partial success → exit 0 with non-zero changes (so feed gets committed); only exit non-zero for total failure
- Bug fix: aggregator's exit code logic — `if (a.errors.length || (b && b.errors.length))` (not `a.errors` twice)

### Network layer

- Global token bucket: 10 req/sec
- Failure retry: 3x exponential backoff
- 429 response: respect `Retry-After` header
- `HttpClient` wraps fetch with bucket + retry + UA

### NDJSON robustness

- All NDJSON writes use atomic write (temp file + rename)
- All NDJSON readers validate line count vs. manifest count on startup; warn on mismatch
- Don't crash on a single bad line — skip + log, but count vs. manifest

### Local layer

- Missing config.json → trigger onboarding
- Missing feed files → empty digest with "no data" message
- Delivery failure → log, fall back to stdout (alert still shown in agent session)

---

## Testing

### Unit tests

Vitest + nock. Mirror `lib/` structure. Run: `npm test`.

### Integration tests

End-to-end via fixtures (no real network). `tests/scripts/*.test.js` exercises each script via `execSync`.

### Pre-launch verification: `scripts/verify-edgar.js`

**Critical step before launch.** Validates:

1. All 8 CIKs return 200 from EDGAR submissions API
2. Sample 13F XML from each CIK parses correctly
3. 13D/G full-text search returns ≥ 1 result for last 3 days
4. At least 3 sample 13D primary docs parse correctly
5. Rate limit handling works (10 req/s sustained)
6. No 429s during normal flow

Run manually before enabling the GitHub Action. Outputs `VERIFICATION PASSED` or `VERIFICATION FAILED` with detail.

### Evals: `evals/evals.json` + `scripts/eval.js`

Each eval entry has:
- `prompt`: input text (e.g., `/money`)
- `description`: human-readable intent
- `checks[]`: machine-verifiable assertions

```json
{
  "id": 1,
  "prompt": "/money",
  "description": "Triggers skill and runs digest immediately",
  "checks": [
    { "type": "contains", "value": "📋", "description": "13F section emoji present" },
    { "type": "regex", "pattern": "https://www\\.sec\\.gov/.*primaryDoc.*", "description": "contains source URL" },
    { "type": "min_length", "value": 200, "description": "digest is non-trivial" }
  ]
}
```

**Supported check types:**
- `contains` / `not_contains` — string contains
- `regex` — pattern match
- `min_length` / `max_length` — output length
- `json_field_exists` / `json_field_equals` — JSON structure
- `contains_url_from` — URL must come from feed's source list

Eval runner (`scripts/eval.js`):
- Reads evals.json
- For each entry: invoke agent with prompt, capture output, run checks
- Report pass/fail per check, exit non-zero if any fail
- Suitable for CI integration (manual trigger initially)

### LLM prompt output quality

Beyond mechanical checks, prompt output quality is judged by:
- Manual review during development
- User feedback after first digest
- Future: golden-output diff (deferred to v2)

---

## Deployment

### GitHub Action: `.github/workflows/aggregate.yml`

```yaml
name: Aggregate SEC Filings
on:
  schedule:
    - cron: '0 12 * * *'   # 08:00 ET
    - cron: '0 0 * * *'    # 20:00 ET
  workflow_dispatch:
jobs:
  aggregate:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - name: Run aggregator
        env:
          SEC_EDGAR_USER_AGENT: ${{ secrets.SEC_EDGAR_USER_AGENT }}
        run: node scripts/aggregate.js
      - name: Commit if changed
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add feed-13f.json feed-13dg/ state-13f.json state-13dg.ndjson
          if git diff --staged --quiet; then
            echo "No changes"
          else
            git commit -m "chore: update feed ($(date -u +%Y-%m-%dT%H:%M:%SZ))"
            git push
          fi
```

**Cron schedule:** Twice daily (08:00 ET + 20:00 ET). Acceptable latency for "smart money digest" use case.

**Required secrets:**
- `SEC_EDGAR_USER_AGENT`: format `"AppName email@example.com"`, required by SEC
- `GITHUB_TOKEN`: built-in, for commits

---

## SKILL.md Architecture

### Concise, focused on execution

SKILL.md (~100 lines) contains only what the agent needs **every time it runs**:
- frontmatter (description for triggering)
- Digest flow (core path)
- Alert flow (core path)
- Config-change pattern recognition
- Manual trigger handling

### References (agent loads on demand)

- `references/onboarding.md` — detailed 8-step onboarding
- `references/cron-setup.md` — OS-specific crontab examples
- `references/prompt-customization.md` — overriding prompts
- `references/delivery-setup.md` — Telegram/Email setup
- `references/architecture.md` — 4-layer overview
- `references/data-formats.md` — schema deep dive
- `references/edgar-fetching.md` — API endpoints and rate limits
- `references/alert-rules.md` — alert policy rationale

### No agent-specific content

SKILL.md and references contain zero agent brand names (no "openclaw", "Claude Code", "Cursor", etc.). Platform detection uses generic utility probing if needed.

---

## Out of Scope (v2+)

- Form 4 tracking (insider trades)
- A-share / HK market support
- User-customizable source lists
- Real-time price integration
- LLM-based stock recommendations
- Watchlist (ticker → related 13D/G highlights)
- Golden-output evals (LLM quality diff)
- NDJSON archive rotation beyond per-year

---

## Open Items

None at time of writing. All 13 discussion points resolved.

## Revision History

| Date | Author | Change |
|---|---|---|
| 2026-06-24 | initial brainstorm | design discussion |
| 2026-06-25 | post-discussion | spec rewritten based on 13 resolved decisions |