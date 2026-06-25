# follow-the-money Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an agent-agnostic skill that tracks 8 legendary US fund managers' 13F filings and full-market 13D/G activist moves, delivering periodic digests plus immediate alerts on new SC 13D filings.

**Architecture:** 4-layer data flow. Layer 1 = SEC EDGAR (data source). Layer 2 = center aggregator on GitHub Actions (twice-daily cron, writes feed-13f.json + feed-13dg/<year>.ndjson + manifest + state files into this repo). Layer 3 = local skill on user's machine (reads feed, runs digest/alert logic, applies prompts, emits text). Layer 4 = delivery (stdout default, optional Telegram/email). Local alert state is **derived** from `feed-13dg/manifest.json` + `config.lastAlertTimestamp` — no separate local state file.

**Tech Stack:** Node.js 20+ (ESM, native fetch), vitest (tests), nock (HTTP mocking, dev-only). Zero runtime dependencies.

**Spec:** `docs/superpowers/specs/2026-06-24-follow-the-money-design.md`

---

## Global Constraints

- **Node:** `>=20.0.0`, ESM (`"type": "module"` in package.json)
- **Test runner:** vitest, nock for HTTP mocking (devDependency only)
- **8 tracked CIKs** (must be verified against EDGAR by Task 1.3 before launch):
  - `0001067983` (Berkshire Hathaway), `0001336528` (Pershing Square), `0001641562` (Scion), `0001061768` (Baupost), `0000945323` (Oaktree), `0001601072` (ARK Invest), `0001167483` (Tiger Global), `0001532173` (Coatue)
- **Agent-agnostic:** zero agent brand names (no "openclaw", "Claude Code", "Cursor", "Codex", "Copilot", "Gemini") in any code, prompt, SKILL.md, or reference. Platform detection uses generic `which <tool>` probing only.
- **13D/G intent:** derived purely from form type. `SC 13D` / `SC 13D/A` → `"active"`. `SC 13G` / `SC 13G/A` → `"passive"`. **No Item 4 regex.**
- **13F-HR/A handling:** when a new 13F-HR/A arrives with same `(filerCik, periodOfReport)` as an existing feed entry, **overwrite** the existing entry's holdings + summary, **append** the old entry's snapshot to `history[]`, and update `latestFilingDate` / `latestFormType` / `latestAccessionNumber`. Delta is always computed against the most recent entry with a different `periodOfReport`.
- **Alert strategy (three-level):** `SC 13D` always alert (full details). `SC 13D/A` alert but merged by `(filerCik + issuerCik + filingDate)`. `SC 13G` and `SC 13G/A` digest-only, never alert.
- **Soft cap:** if a single cron run produces > 8 alerts, push the first 8 in detail and append one summary line: `📊 另 N 条 13D/G 详见 digest`.
- **NDJSON atomic writes:** every NDJSON writer uses temp file + rename to prevent half-line corruption. Every NDJSON reader validates line count vs. manifest count on startup; warn on mismatch.
- **Aggregator state location:** `state-13f.json` and `state-13dg.ndjson` live in the repo and are **only** read/written by the GitHub Action. Local skill MUST NOT read or write these files.
- **Local alert state:** stored in `~/.follow-the-money/config.json` field `lastAlertTimestamp`. Updated atomically (temp + rename) after each successful alert push.
- **Frequent commits:** every task ends with a `git commit`. Use conventional-commits prefixes: `feat`, `fix`, `test`, `chore`, `docs`.

---

## File Structure

```
follow-the-money/
├── package.json                              # Node 20+, ESM, type: module
├── .gitignore                                # .env, node_modules, *.log, coverage/
├── README.md
├── LICENSE                                   # MIT
├── SKILL.md                                  # Agent behavior spec (~100 lines, concise)
├── config/
│   └── default-sources.json                  # 8 CIKs + 13D/G config
├── scripts/
│   ├── aggregate.js                          # Center aggregator (GitHub Action entry)
│   ├── prepare-digest.js                     # Local digest preparation
│   ├── check-alerts.js                       # Local alert detection
│   ├── deliver.js                            # Delivery (stdout/Telegram/email)
│   ├── verify-edgar.js                       # Pre-launch real-EDGAR validation
│   └── eval.js                               # Evals runner
├── lib/
│   ├── token-bucket.js
│   ├── http-client.js
│   ├── parsers/
│   │   ├── thirteen-f.js                     # 13F XML parser
│   │   └── thirteen-dg.js                    # 13D/G primary doc parser (intent by form type)
│   ├── compute/
│   │   └── thirteen-f-summary.js             # new/inc/dec/closed deltas vs prior period
│   ├── store/
│   │   ├── feed-json.js                      # Read/write feed-13f.json (handles 13F-HR/A overwrite)
│   │   ├── feed-ndjson.js                    # Append feed-13dg/<year>.ndjson (atomic write)
│   │   ├── manifest.js                       # Read/write feed-13dg/manifest.json
│   │   ├── state-json.js                     # Read/write state-13f.json
│   │   └── state-ndjson.js                   # Append state-13dg.ndjson (atomic write)
│   ├── feed/
│   │   ├── filter-by-lookback.js             # Filter feed by date range
│   │   └── merge-by-issuer.js                # 13D/A merge helper (filer+issuer+day)
│   ├── alert/
│   │   ├── classify.js                       # 13D → alert, 13G → digest
│   │   └── merge-amendments.js               # 13D/A merge into single alert
│   └── edgar/
│       ├── fetch-submissions.js              # EDGAR submissions JSON
│       ├── fetch-thirteen-f-xml.js           # EDGAR 13F XML
│       └── fetch-thirteen-dg-search.js       # EDGAR 13D/G search
├── prompts/
│   ├── digest-intro.md
│   ├── format-13f.md
│   ├── format-13dg.md
│   ├── format-alert.md
│   └── translate.md
├── references/                                # Agent-loaded on demand
│   ├── architecture.md
│   ├── data-formats.md
│   ├── edgar-fetching.md
│   ├── alert-rules.md
│   ├── onboarding.md                          # 8-step detailed onboarding
│   ├── cron-setup.md                          # crontab examples per OS
│   ├── prompt-customization.md                # How to override prompts
│   └── delivery-setup.md                      # Telegram/Email detailed steps
├── .github/
│   └── workflows/
│       └── aggregate.yml
├── evals/
│   └── evals.json                             # Prompts with machine-checkable checks[]
└── tests/                                     # Mirror lib/ + scripts/
    ├── token-bucket.test.js
    ├── http-client.test.js
    ├── parsers/
    ├── compute/
    ├── store/
    ├── feed/
    ├── alert/
    ├── edgar/
    ├── scripts/
    └── fixtures/
        ├── submissions-cik-0001067983.json
        ├── form13fData.xml
        ├── search-13dg.json
        ├── 13d-primary-doc.html
        ├── 13g-primary-doc.html
        ├── feed-13f.json
        ├── feed-13dg/                         # Sample year-split feed
        │   ├── manifest.json
        │   ├── 2025.ndjson
        │   └── 2026.ndjson
        ├── state-13f.json
        ├── state-13dg.ndjson
        └── config.json
```

**Decomposition rationale:** `lib/` modules are extracted so each can be unit-tested with nock (no network). Scripts under `scripts/` are thin orchestrators that wire lib modules together. `prompts/` and `references/` are content (markdown), loaded by the agent. SKILL.md stays concise (~100 lines) so the agent loads only the daily path; deep details sink to `references/`.

---

## Phase 0: Project Scaffold

### Task 0.1: Initialize package.json and directory layout

**Files:**
- Create: `package.json`
- Create: `.gitignore`

**Interfaces:**
- Produces: Node ESM project with `npm test` script that runs vitest.

- [ ] **Step 1: Initialize git repo and create directory structure**

```bash
cd /Users/kaden/follow-the-money
git init
mkdir -p config scripts lib/parsers lib/compute lib/store lib/feed lib/alert lib/edgar \
  prompts references .github/workflows evals tests/parsers tests/compute tests/store \
  tests/feed tests/alert tests/edgar tests/scripts tests/fixtures tests/fixtures/feed-13dg
```

- [ ] **Step 2: Write package.json**

```json
{
  "name": "follow-the-money",
  "version": "0.1.0",
  "description": "Track legendary US fund managers via SEC 13F and 13D/G activist moves",
  "type": "module",
  "engines": { "node": ">=20.0.0" },
  "scripts": {
    "test": "vitest run",
    "test:watch": "vitest",
    "aggregate": "node scripts/aggregate.js",
    "digest": "node scripts/prepare-digest.js",
    "verify-edgar": "node scripts/verify-edgar.js",
    "evals": "node scripts/eval.js"
  },
  "devDependencies": {
    "vitest": "^2.0.0",
    "nock": "^14.0.0"
  }
}
```

- [ ] **Step 3: Write .gitignore**

```
node_modules/
.env
.env.local
*.log
coverage/
.DS_Store
```

- [ ] **Step 4: Install dependencies**

Run: `npm install`
Expected: `node_modules/` created, `package-lock.json` written. No errors.

- [ ] **Step 5: Commit**

```bash
git add package.json package-lock.json .gitignore
git commit -m "chore: initialize Node 20+ ESM project with vitest + nock"
```

---

### Task 0.2: Configure vitest

**Files:**
- Create: `vitest.config.js`

**Interfaces:**
- Produces: vitest config that runs tests under `tests/`, supports ESM, sets 10s timeout.

- [ ] **Step 1: Write vitest config**

```javascript
// vitest.config.js
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    include: ['tests/**/*.test.js'],
    environment: 'node',
    testTimeout: 10000,
    globals: false,
  },
});
```

- [ ] **Step 2: Write a smoke test**

```javascript
// tests/smoke.test.js
import { describe, it, expect } from 'vitest';

describe('smoke', () => {
  it('runs', () => {
    expect(1 + 1).toBe(2);
  });
});
```

- [ ] **Step 3: Run tests**

Run: `npm test`
Expected: 1 test passes.

- [ ] **Step 4: Commit**

```bash
git add vitest.config.js tests/smoke.test.js
git commit -m "chore: configure vitest + smoke test"
```

---

## Phase 1: Config and Fixtures

### Task 1.1: Write default-sources.json

**Files:**
- Create: `config/default-sources.json`

**Interfaces:**
- Produces: `defaultSources.thirteenF` (array of `{cik, name, style}`) and `defaultSources.thirteenDG` (`{enabled, lookbackDays}`).

- [ ] **Step 1: Write config file**

```json
{
  "schemaVersion": 1,
  "thirteenF": [
    { "cik": "0001067983", "name": "Berkshire Hathaway Inc", "style": "value" },
    { "cik": "0001336528", "name": "Pershing Square Capital Management", "style": "activist-value" },
    { "cik": "0001641562", "name": "Scion Asset Management", "style": "deep-value" },
    { "cik": "0001061768", "name": "Baupost Group", "style": "value" },
    { "cik": "0000945323", "name": "Oaktree Capital Management", "style": "distressed-value" },
    { "cik": "0001601072", "name": "ARK Invest", "style": "thematic-growth" },
    { "cik": "0001167483", "name": "Tiger Global Management", "style": "growth" },
    { "cik": "0001532173", "name": "Coatue Management", "style": "growth" }
  ],
  "thirteenDG": {
    "enabled": true,
    "lookbackDays": 3
  }
}
```

- [ ] **Step 2: Write a loader test**

```javascript
// tests/config.test.js
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const configPath = join(__dirname, '..', 'config', 'default-sources.json');

describe('default-sources.json', () => {
  it('contains 8 CIKs', () => {
    const cfg = JSON.parse(readFileSync(configPath, 'utf8'));
    expect(cfg.thirteenF).toHaveLength(8);
    for (const f of cfg.thirteenF) {
      expect(f.cik).toMatch(/^\d{10}$/);
      expect(f.name).toBeTruthy();
      expect(f.style).toBeTruthy();
    }
  });

  it('has 13D/G config enabled', () => {
    const cfg = JSON.parse(readFileSync(configPath, 'utf8'));
    expect(cfg.thirteenDG.enabled).toBe(true);
    expect(cfg.thirteenDG.lookbackDays).toBeGreaterThan(0);
  });
});
```

- [ ] **Step 3: Run tests**

Run: `npm test -- tests/config.test.js`
Expected: 2 tests pass.

- [ ] **Step 4: Commit**

```bash
git add config/default-sources.json tests/config.test.js
git commit -m "feat(config): add 8 CIKs + 13D/G config"
```

---

### Task 1.2: Create test fixtures

**Files:**
- Create: `tests/fixtures/submissions-cik-0001067983.json`
- Create: `tests/fixtures/form13fData.xml`
- Create: `tests/fixtures/search-13dg.json`
- Create: `tests/fixtures/13d-primary-doc.html`
- Create: `tests/fixtures/13g-primary-doc.html`
- Create: `tests/fixtures/feed-13f.json`
- Create: `tests/fixtures/feed-13dg/manifest.json`
- Create: `tests/fixtures/feed-13dg/2025.ndjson`
- Create: `tests/fixtures/feed-13dg/2026.ndjson`
- Create: `tests/fixtures/state-13f.json`
- Create: `tests/fixtures/state-13dg.ndjson`
- Create: `tests/fixtures/config.json`

**Interfaces:**
- Produces: real-shape sample data for every parser/fetcher test.

- [ ] **Step 1: Write submissions fixture**

```json
{
  "cik": "1067983",
  "name": "Berkshire Hathaway Inc",
  "filings": {
    "recent": {
      "form": ["13F-HR", "13F-HR/A"],
      "filingDate": ["2026-05-15", "2026-06-10"],
      "accessionNumber": ["0001067983-26-000123", "0001067983-26-000456"],
      "primaryDocument": ["form13fData.xml", "form13fData.xml"],
      "reportDate": ["2026-03-31", "2026-03-31"]
    }
  }
}
```

- [ ] **Step 2: Write 13F XML fixture**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<informationTable>
  <infoTable>
    <nameOfIssuer>APPLE INC</nameOfIssuer>
    <titleOfClass>COM</titleOfClass>
    <cusip>037833100</cusip>
    <value>58200000000</value>
    <shrsOrPrnAmt><sshPrnamt>300000000</sshPrnamt><sshPrnamtType>SH</sshPrnamtType></shrsOrPrnAmt>
    <putCall>None</putCall>
    <investmentDiscretion>SOLE</investmentDiscretion>
    <votingAuthority><Sole>300000000</Sole><Shared>0</Shared><None>0</None></votingAuthority>
  </infoTable>
</informationTable>
```

- [ ] **Step 3: Write 13D/G search fixture**

```json
{
  "hits": {
    "total": { "value": 42 },
    "hits": [
      {
        "_source": {
          "ciks": ["0000932470"],
          "display_names": ["ICAHN CARL C"],
          "file_date": "2026-06-20",
          "form": "SC 13D",
          "adsh": "0000932470-26-000045",
          "ciks": ["0000932470", "0001717393"],
          "display_names": ["ICAHN CARL C", "Jet.AI Inc"],
          "tickers": ["JTAI"]
        }
      },
      {
        "_source": {
          "ciks": ["0000893855"],
          "display_names": ["ELLIOTT INVESTMENT MANAGEMENT L.P."],
          "file_date": "2026-06-18",
          "form": "SC 13G",
          "adsh": "0000893855-26-000078",
          "ciks": ["0000893855", "0001315098"],
          "display_names": ["ELLIOTT INVESTMENT MANAGEMENT L.P.", "Activision Blizzard Inc"],
          "tickers": ["ATVI"]
        }
      }
    ]
  }
}
```

- [ ] **Step 4: Write 13D primary doc fixture**

```html
<html><body>
<SCHEDULE 13D>
<TITLE OF CLASS>Common Stock</TITLE>
<NAME OF ISSUER>Jet.AI Inc</NAME>
<TICKER>JTAI</TICKER>
<CUSIP>47800A101</CUSIP>
<PERCENT OF CLASS>6.8</PERCENT>
<SHARED VOTING POWER>0</SHARED>
<SOLE VOTING POWER>4500000</SOLE>
<AGGREGATE AMOUNT BENEFICIALLY OWNED>4500000</AGGREGATE>
</SCHEDULE>
</body></html>
```

- [ ] **Step 5: Write 13G primary doc fixture**

```html
<html><body>
<SCHEDULE 13G>
<NAME OF ISSUER>Activision Blizzard Inc</NAME>
<TICKER>ATVI</TICKER>
<PERCENT OF CLASS>5.1</PERCENT>
<AGGREGATE AMOUNT BENEFICIALLY OWNED>4900000</AGGREGATE>
</SCHEDULE>
</body></html>
```

- [ ] **Step 6: Write feed-13f.json fixture**

```json
{
  "schemaVersion": 1,
  "generatedAt": "2026-05-15T08:00:00.000Z",
  "lookbackDays": 90,
  "thirteenF": [
    {
      "filerCik": "0001067983",
      "filerName": "Berkshire Hathaway Inc",
      "latestFilingDate": "2026-05-15",
      "latestFormType": "13F-HR",
      "latestAccessionNumber": "0001067983-26-000123",
      "periodOfReport": "2026-03-31",
      "history": [
        { "filingDate": "2026-05-15", "formType": "13F-HR", "accessionNumber": "0001067983-26-000123" }
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

- [ ] **Step 7: Write feed-13dg manifest + year files**

`tests/fixtures/feed-13dg/manifest.json`:
```json
{
  "schemaVersion": 1,
  "currentYear": 2026,
  "years": {
    "2025": { "file": "feed-13dg/2025.ndjson", "count": 2, "firstDate": "2025-12-30", "lastDate": "2025-12-31" },
    "2026": { "file": "feed-13dg/2026.ndjson", "count": 2, "firstDate": "2026-06-18", "lastDate": "2026-06-20" }
  }
}
```

`tests/fixtures/feed-13dg/2025.ndjson`:
```
{"filerCik":"0000932470","filerName":"ICAHN CARL C","issuerCik":"0001717393","issuerName":"Jet.AI Inc","issuerTicker":"JTAI","formType":"SC 13D","filingDate":"2025-12-30","ownershipPercent":6.5,"sharesOwned":4300000,"intent":"active","accessionNumber":"0000932470-25-000099","primaryDocUrl":"https://www.sec.gov/Archives/edgar/data/932470/000093247025000099/primary_doc.html"}
{"filerCik":"0000893855","filerName":"ELLIOTT INVESTMENT MANAGEMENT L.P.","issuerCik":"0001315098","issuerName":"Activision Blizzard Inc","issuerTicker":"ATVI","formType":"SC 13G","filingDate":"2025-12-31","ownershipPercent":5.0,"sharesOwned":4800000,"intent":"passive","accessionNumber":"0000893855-25-000099","primaryDocUrl":"https://www.sec.gov/Archives/edgar/data/893855/000089385525000099/primary_doc.html"}
```

`tests/fixtures/feed-13dg/2026.ndjson`:
```
{"filerCik":"0000932470","filerName":"ICAHN CARL C","issuerCik":"0001717393","issuerName":"Jet.AI Inc","issuerTicker":"JTAI","formType":"SC 13D/A","filingDate":"2026-06-20","ownershipPercent":6.8,"sharesOwned":4500000,"intent":"active","accessionNumber":"0000932470-26-000045","primaryDocUrl":"https://www.sec.gov/Archives/edgar/data/932470/000093247026000045/primary_doc.html"}
{"filerCik":"0000893855","filerName":"ELLIOTT INVESTMENT MANAGEMENT L.P.","issuerCik":"0001315098","issuerName":"Activision Blizzard Inc","issuerTicker":"ATVI","formType":"SC 13G","filingDate":"2026-06-18","ownershipPercent":5.1,"sharesOwned":4900000,"intent":"passive","accessionNumber":"0000893855-26-000078","primaryDocUrl":"https://www.sec.gov/Archives/edgar/data/893855/000089385526000078/primary_doc.html"}
```

- [ ] **Step 8: Write state fixtures**

`tests/fixtures/state-13f.json`:
```json
{
  "lastUpdated": "2026-05-15T08:00:00.000Z",
  "seenFilings": { "0001067983-26-000123": 1715740800000 }
}
```

`tests/fixtures/state-13dg.ndjson`:
```
{"accession":"0000932470-25-000099","seenAt":1735526400000}
{"accession":"0000893855-25-000099","seenAt":1735612800000}
```

- [ ] **Step 9: Write config fixture**

```json
{
  "schemaVersion": 1,
  "platform": "any",
  "language": "en",
  "timezone": "America/New_York",
  "frequency": "daily",
  "deliveryTime": "08:00",
  "delivery": { "method": "stdout" },
  "lastAlertTimestamp": "2026-06-01T00:00:00.000Z",
  "onboardingComplete": true
}
```

- [ ] **Step 10: Verify fixtures load**

Create a temp test:

```javascript
// tests/fixtures.test.js
import { describe, it, expect } from 'vitest';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const fx = join(__dirname, 'fixtures');

describe('fixtures load', () => {
  it('every fixture is parseable', () => {
    const files = [
      'submissions-cik-0001067983.json',
      'search-13dg.json',
      'feed-13f.json',
      'feed-13dg/manifest.json',
      'feed-13dg/2025.ndjson',
      'feed-13dg/2026.ndjson',
      'state-13f.json',
      'config.json',
    ];
    for (const f of files) {
      const content = readFileSync(join(fx, f), 'utf8');
      if (f.endsWith('.ndjson')) {
        const lines = content.split('\n').filter(Boolean);
        expect(lines.length).toBeGreaterThan(0);
        for (const line of lines) JSON.parse(line);
      } else {
        JSON.parse(content);
      }
    }
  });
});
```

- [ ] **Step 11: Run fixture test**

Run: `npm test -- tests/fixtures.test.js`
Expected: 1 test passes.

- [ ] **Step 12: Commit**

```bash
git add tests/fixtures/
git commit -m "test(fixtures): add sample EDGAR responses + feeds + state"
```

---

### Task 1.3: Verify all 8 CIKs against EDGAR (pre-launch gate)

**Files:**
- Create: `scripts/verify-edgar.js`
- Test: `tests/scripts/verify-edgar.test.js` (uses nock, no real network)

**Interfaces:**
- Produces: zero-dependency script that, when run with real `SEC_EDGAR_USER_AGENT`, validates every CIK. Exits 0 on success, 1 on failure. Prints a per-CIK report.

- [ ] **Step 1: Write the script**

```javascript
// scripts/verify-edgar.js
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const cfg = JSON.parse(readFileSync(join(__dirname, '..', 'config', 'default-sources.json'), 'utf8'));

const UA = process.env.SEC_EDGAR_USER_AGENT;
if (!UA) {
  console.error('ERROR: SEC_EDGAR_USER_AGENT env var required (format: "AppName email@example.com")');
  process.exit(1);
}

const bucket = { tokens: 10, lastRefill: Date.now(), rate: 10 };
async function take() {
  while (true) {
    const now = Date.now();
    const elapsed = (now - bucket.lastRefill) / 1000;
    bucket.tokens = Math.min(10, bucket.tokens + elapsed * bucket.rate);
    bucket.lastRefill = now;
    if (bucket.tokens >= 1) { bucket.tokens -= 1; return; }
    await new Promise(r => setTimeout(r, 50));
  }
}

async function fetchWithRetry(url) {
  await take();
  for (let attempt = 0; attempt < 3; attempt++) {
    const res = await fetch(url, { headers: { 'User-Agent': UA, 'Accept-Encoding': 'gzip, deflate' } });
    if (res.status === 429) {
      const wait = Number(res.headers.get('Retry-After') || 1) * 1000;
      await new Promise(r => setTimeout(r, wait));
      continue;
    }
    if (!res.ok) throw new Error(`HTTP ${res.status} for ${url}`);
    return res;
  }
  throw new Error(`Failed after 3 retries: ${url}`);
}

async function checkCik(cik) {
  const url = `https://data.sec.gov/submissions/CIK${cik}.json`;
  const res = await fetchWithRetry(url);
  const data = await res.json();
  return { cik, name: data.name, ok: true };
}

async function check13DGSearch() {
  const url = `https://efts.sec.gov/LATEST/search-index?q=%22SC+13D%22&dateRange=custom&startDate=2026-06-22&endDate=2026-06-25&forms=SC+13D`;
  const res = await fetchWithRetry(url);
  const data = await res.json();
  return { ok: (data?.hits?.total?.value ?? 0) > 0, count: data?.hits?.total?.value ?? 0 };
}

async function main() {
  console.log('Verifying 8 CIKs against EDGAR...');
  const results = [];
  for (const f of cfg.thirteenF) {
    try {
      const r = await checkCik(f.cik);
      results.push(r);
      console.log(`  ✓ ${f.cik} ${r.name}`);
    } catch (e) {
      results.push({ cik: f.cik, ok: false, error: e.message });
      console.log(`  ✗ ${f.cik} ERROR: ${e.message}`);
    }
  }
  const search = await check13DGSearch();
  console.log(`  ${search.ok ? '✓' : '✗'} 13D/G search returned ${search.count} results`);
  const allOk = results.every(r => r.ok) && search.ok;
  console.log(allOk ? '\nVERIFICATION PASSED' : '\nVERIFICATION FAILED');
  process.exit(allOk ? 0 : 1);
}

main().catch(err => {
  console.error('Fatal:', err);
  process.exit(1);
});
```

- [ ] **Step 2: Write a nock-based test**

```javascript
// tests/scripts/verify-edgar.test.js
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import nock from 'nock';

describe('verify-edgar.js (mocked)', () => {
  beforeEach(() => {
    process.env.SEC_EDGAR_USER_AGENT = 'TestApp test@example.com';
    nock.disableNetConnect();
  });
  afterEach(() => { nock.cleanAll(); nock.enableNetConnect(); });

  it('fails with helpful message if env var missing', async () => {
    delete process.env.SEC_EDGAR_USER_AGENT;
    const { execSync } = await import('node:child_process');
    expect(() => execSync('node scripts/verify-edgar.js', { stdio: 'pipe' })).toThrow(/SEC_EDGAR_USER_AGENT/);
  });

  it('reports VERIFICATION PASSED when all CIKs resolve', async () => {
    for (const cik of ['1067983', '1336528', '1641562', '1061768', '945323', '1601072', '1167483', '1532173']) {
      nock('https://data.sec.gov')
        .get(`/submissions/CIK${cik}.json`)
        .reply(200, { cik, name: `Mock Filer ${cik}` });
    }
    nock('https://efts.sec.gov')
      .get(/LATEST\/search-index.*/)
      .reply(200, { hits: { total: { value: 5 } } });
    const { execSync } = await import('node:child_process');
    const out = execSync('node scripts/verify-edgar.js', { encoding: 'utf8' });
    expect(out).toMatch(/VERIFICATION PASSED/);
  });
});
```

- [ ] **Step 3: Run test (mocked, no real network)**

Run: `npm test -- tests/scripts/verify-edgar.test.js`
Expected: 2 tests pass.

- [ ] **Step 4: Commit**

```bash
git add scripts/verify-edgar.js tests/scripts/verify-edgar.test.js
git commit -m "feat(verify): pre-launch EDGAR CIK + search validator"
```

---

## Phase 2: Core Library Modules (TDD)

### Task 2.1: Token bucket rate limiter

**Files:**
- Create: `lib/token-bucket.js`
- Test: `tests/token-bucket.test.js`

**Interfaces:**
- Produces: `class TokenBucket(rate, capacity)` with `async take()` method. Throws on invalid args.

- [ ] **Step 1: Write failing test**

```javascript
// tests/token-bucket.test.js
import { describe, it, expect } from 'vitest';
import { TokenBucket } from '../lib/token-bucket.js';

describe('TokenBucket', () => {
  it('throws if rate or capacity invalid', () => {
    expect(() => new TokenBucket(0, 1)).toThrow();
    expect(() => new TokenBucket(10, 0)).toThrow();
    expect(() => new TokenBucket(-1, 1)).toThrow();
  });

  it('allows up to capacity instant takes', async () => {
    const tb = new TokenBucket(1, 3);
    await Promise.all([tb.take(), tb.take(), tb.take()]);
    expect(true).toBe(true); // no throw
  });

  it('blocks the 4th take when capacity is 3', async () => {
    const tb = new TokenBucket(1, 3);
    await Promise.all([tb.take(), tb.take(), tb.take()]);
    const start = Date.now();
    await tb.take();
    expect(Date.now() - start).toBeGreaterThanOrEqual(900);
  });

  it('refills at the configured rate', async () => {
    const tb = new TokenBucket(20, 1); // 20/sec → one token every 50ms
    await tb.take();
    const start = Date.now();
    await tb.take();
    expect(Date.now() - start).toBeGreaterThanOrEqual(40);
    expect(Date.now() - start).toBeLessThan(200);
  });
});
```

- [ ] **Step 2: Run test, verify it fails**

Run: `npm test -- tests/token-bucket.test.js`
Expected: FAIL with "Cannot find module '../lib/token-bucket.js'".

- [ ] **Step 3: Implement TokenBucket**

```javascript
// lib/token-bucket.js
export class TokenBucket {
  constructor(rate, capacity) {
    if (!Number.isFinite(rate) || rate <= 0) throw new Error('rate must be > 0');
    if (!Number.isInteger(capacity) || capacity <= 0) throw new Error('capacity must be a positive integer');
    this.rate = rate;       // tokens per second
    this.capacity = capacity;
    this.tokens = capacity;
    this.lastRefill = Date.now();
  }

  _refill() {
    const now = Date.now();
    const elapsedSec = (now - this.lastRefill) / 1000;
    this.tokens = Math.min(this.capacity, this.tokens + elapsedSec * this.rate);
    this.lastRefill = now;
  }

  async take() {
    while (true) {
      this._refill();
      if (this.tokens >= 1) { this.tokens -= 1; return; }
      const deficit = 1 - this.tokens;
      const waitMs = Math.max(10, Math.ceil((deficit / this.rate) * 1000));
      await new Promise(r => setTimeout(r, waitMs));
    }
  }
}
```

- [ ] **Step 4: Run test, verify it passes**

Run: `npm test -- tests/token-bucket.test.js`
Expected: 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add lib/token-bucket.js tests/token-bucket.test.js
git commit -m "feat(rate-limit): token bucket with configurable rate + capacity"
```

---

### Task 2.2: HTTP client with rate limit + retry

**Files:**
- Create: `lib/http-client.js`
- Test: `tests/http-client.test.js`

**Interfaces:**
- Produces: `createHttpClient({ userAgent, bucket })` → `{ fetch(url, opts) }` that wraps `globalThis.fetch`. Honors 429 `Retry-After` and retries 3× on network errors with exponential backoff.

- [ ] **Step 1: Write failing test**

```javascript
// tests/http-client.test.js
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import nock from 'nock';
import { createHttpClient } from '../lib/http-client.js';
import { TokenBucket } from '../lib/token-bucket.js';

describe('HttpClient', () => {
  let bucket, client;
  beforeEach(() => {
    bucket = new TokenBucket(100, 100);
    client = createHttpClient({ userAgent: 'TestApp test@example.com', bucket });
    nock.disableNetConnect();
  });
  afterEach(() => { nock.cleanAll(); nock.enableNetConnect(); });

  it('adds User-Agent to every request', async () => {
    const scope = nock('https://example.com', { reqheaders: { 'user-agent': 'TestApp test@example.com' } })
      .get('/foo').reply(200, { ok: true });
    const res = await client.fetch('https://example.com/foo');
    expect(await res.json()).toEqual({ ok: true });
    expect(scope.isDone()).toBe(true);
  });

  it('retries on 429 honoring Retry-After', async () => {
    nock('https://example.com').get('/bar').reply(429, '', { 'Retry-After': '0' });
    nock('https://example.com').get('/bar').reply(200, { ok: true });
    const res = await client.fetch('https://example.com/bar');
    expect(res.status).toBe(200);
  });

  it('retries 3× on network error then throws', async () => {
    nock('https://example.com').get('/baz').times(3).replyWithError('boom');
    await expect(client.fetch('https://example.com/baz')).rejects.toThrow(/boom|Failed/);
  });
});
```

- [ ] **Step 2: Run test, verify it fails**

Run: `npm test -- tests/http-client.test.js`
Expected: FAIL with "Cannot find module".

- [ ] **Step 3: Implement HttpClient**

```javascript
// lib/http-client.js
export function createHttpClient({ userAgent, bucket }) {
  if (!userAgent) throw new Error('userAgent required');
  if (!bucket) throw new Error('bucket required');

  async function fetchWithBackoff(url, opts = {}, attempt = 0) {
    try {
      await bucket.take();
      const res = await globalThis.fetch(url, {
        ...opts,
        headers: { 'User-Agent': userAgent, ...(opts.headers || {}) },
      });
      if (res.status === 429 && attempt < 2) {
        const wait = Number(res.headers.get('Retry-After') || 1) * 1000;
        await new Promise(r => setTimeout(r, wait));
        return fetchWithBackoff(url, opts, attempt + 1);
      }
      return res;
    } catch (err) {
      if (attempt < 2) {
        const wait = 2 ** attempt * 500;
        await new Promise(r => setTimeout(r, wait));
        return fetchWithBackoff(url, opts, attempt + 1);
      }
      throw new Error(`Failed after 3 retries: ${err.message}`);
    }
  }

  return { fetch: fetchWithBackoff };
}
```

- [ ] **Step 4: Run test, verify it passes**

Run: `npm test -- tests/http-client.test.js`
Expected: 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add lib/http-client.js tests/http-client.test.js
git commit -m "feat(http): client with rate limit, UA, 429 retry, exp backoff"
```

---

### Task 2.3: EDGAR submissions + 13F XML fetcher

**Files:**
- Create: `lib/edgar/fetch-submissions.js`
- Create: `lib/edgar/fetch-thirteen-f-xml.js`
- Test: `tests/edgar/fetch-submissions.test.js`
- Test: `tests/edgar/fetch-thirteen-f-xml.test.js`

**Interfaces:**
- `fetchLatest13FFilings(httpClient, cik)` → `Array<{ filingDate, formType, accessionNumber, primaryDocument, periodOfReport }>` filtered to `13F-HR` and `13F-HR/A`, sorted desc by `filingDate`.
- `fetchThirteenFXml(httpClient, cik, accessionNumber, primaryDocument)` → `string` (raw XML).

- [ ] **Step 1: Write failing test for submissions**

```javascript
// tests/edgar/fetch-submissions.test.js
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import nock from 'nock';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { fetchLatest13FFilings } from '../../lib/edgar/fetch-submissions.js';
import { createHttpClient } from '../../lib/http-client.js';
import { TokenBucket } from '../../lib/token-bucket.js';

const __dirname = dirname(fileURLToPath(import.meta.url));

describe('fetchLatest13FFilings', () => {
  let client;
  beforeEach(() => {
    client = createHttpClient({ userAgent: 'T t@e.com', bucket: new TokenBucket(100, 100) });
    nock.disableNetConnect();
  });
  afterEach(() => { nock.cleanAll(); nock.enableNetConnect(); });

  it('returns only 13F-HR and 13F-HR/A, sorted desc', async () => {
    const fixture = JSON.parse(readFileSync(join(__dirname, '../fixtures/submissions-cik-0001067983.json'), 'utf8'));
    nock('https://data.sec.gov').get('/submissions/CIK0001067983.json').reply(200, fixture);
    const r = await fetchLatest13FFilings(client, '0001067983');
    expect(r).toHaveLength(2);
    expect(r[0].formType).toBe('13F-HR/A'); // most recent
    expect(r[1].formType).toBe('13F-HR');
  });

  it('handles 10-digit CIK with and without leading zeros', async () => {
    nock('https://data.sec.gov').get('/submissions/CIK0001067983.json').reply(200, {
      filings: { recent: { form: ['13F-HR'], filingDate: ['2026-01-01'], accessionNumber: ['0001067983-26-000001'], primaryDocument: ['form13fData.xml'], reportDate: ['2025-12-31'] } },
    });
    const r = await fetchLatest13FFilings(client, '1067983');
    expect(r).toHaveLength(1);
    expect(r[0].accessionNumber).toBe('0001067983-26-000001');
  });
});
```

- [ ] **Step 2: Run test, verify it fails**

Run: `npm test -- tests/edgar/fetch-submissions.test.js`
Expected: FAIL with "Cannot find module".

- [ ] **Step 3: Implement fetch-submissions**

```javascript
// lib/edgar/fetch-submissions.js
const THIRTEEN_F_FORMS = new Set(['13F-HR', '13F-HR/A']);

export async function fetchLatest13FFilings(httpClient, cik) {
  const padded = cik.padStart(10, '0');
  const url = `https://data.sec.gov/submissions/CIK${padded}.json`;
  const res = await httpClient.fetch(url);
  if (!res.ok) throw new Error(`submissions HTTP ${res.status} for CIK ${cik}`);
  const data = await res.json();
  const recent = data.filings?.recent;
  if (!recent) return [];
  const out = [];
  for (let i = 0; i < recent.form.length; i++) {
    const formType = recent.form[i];
    if (!THIRTEEN_F_FORMS.has(formType)) continue;
    out.push({
      filingDate: recent.filingDate[i],
      formType,
      accessionNumber: recent.accessionNumber[i],
      primaryDocument: recent.primaryDocument[i],
      periodOfReport: recent.reportDate[i],
    });
  }
  out.sort((a, b) => b.filingDate.localeCompare(a.filingDate));
  return out;
}
```

- [ ] **Step 4: Run test, verify it passes**

Run: `npm test -- tests/edgar/fetch-submissions.test.js`
Expected: 2 tests pass.

- [ ] **Step 5: Write failing test for XML fetcher**

```javascript
// tests/edgar/fetch-thirteen-f-xml.test.js
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import nock from 'nock';
import { fetchThirteenFXml } from '../../lib/edgar/fetch-thirteen-f-xml.js';
import { createHttpClient } from '../../lib/http-client.js';
import { TokenBucket } from '../../lib/token-bucket.js';

describe('fetchThirteenFXml', () => {
  let client;
  beforeEach(() => {
    client = createHttpClient({ userAgent: 'T t@e.com', bucket: new TokenBucket(100, 100) });
    nock.disableNetConnect();
  });
  afterEach(() => { nock.cleanAll(); nock.enableNetConnect(); });

  it('builds archive URL from accession (strips dashes)', async () => {
    const xml = '<?xml version="1.0"?><informationTable/>';
    nock('https://www.sec.gov')
      .get('/Archives/edgar/data/1067983/000106798326000123/form13fData.xml')
      .reply(200, xml);
    const out = await fetchThirteenFXml(client, '0001067983', '0001067983-26-000123', 'form13fData.xml');
    expect(out).toBe(xml);
  });
});
```

- [ ] **Step 6: Run test, verify it fails**

Run: `npm test -- tests/edgar/fetch-thirteen-f-xml.test.js`
Expected: FAIL with "Cannot find module".

- [ ] **Step 7: Implement fetch-thirteen-f-xml**

```javascript
// lib/edgar/fetch-thirteen-f-xml.js
export async function fetchThirteenFXml(httpClient, cik, accessionNumber, primaryDocument) {
  const cikNoPad = String(parseInt(cik, 10));
  const accNoDash = accessionNumber.replace(/-/g, '');
  const url = `https://www.sec.gov/Archives/edgar/data/${cikNoPad}/${accNoDash}/${primaryDocument}`;
  const res = await httpClient.fetch(url);
  if (!res.ok) throw new Error(`13F XML HTTP ${res.status} for ${url}`);
  return res.text();
}
```

- [ ] **Step 8: Run test, verify it passes**

Run: `npm test -- tests/edgar/fetch-thirteen-f-xml.test.js`
Expected: 1 test passes.

- [ ] **Step 9: Commit**

```bash
git add lib/edgar/fetch-submissions.js lib/edgar/fetch-thirteen-f-xml.js \
        tests/edgar/fetch-submissions.test.js tests/edgar/fetch-thirteen-f-xml.test.js
git commit -m "feat(edgar): submissions + 13F XML fetchers"
```

---

### Task 2.4: 13F XML parser

**Files:**
- Create: `lib/parsers/thirteen-f.js`
- Test: `tests/parsers/thirteen-f.test.js`

**Interfaces:**
- `parseThirteenF(xml)` → `Array<{ cusip, issuerName, valueUsd, shares, votingAuthority: { sole, shared, none } }>`.

- [ ] **Step 1: Write failing test**

```javascript
// tests/parsers/thirteen-f.test.js
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { parseThirteenF } from '../../lib/parsers/thirteen-f.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const xml = readFileSync(join(__dirname, '../fixtures/form13fData.xml'), 'utf8');

describe('parseThirteenF', () => {
  it('parses holdings with voting authority split', () => {
    const r = parseThirteenF(xml);
    expect(r).toHaveLength(1);
    expect(r[0]).toMatchObject({
      cusip: '037833100',
      issuerName: 'APPLE INC',
      valueUsd: 58200000000,
      shares: 300000000,
      votingAuthority: { sole: 300000000, shared: 0, none: 0 },
    });
  });

  it('returns [] on empty <informationTable/>', () => {
    expect(parseThirteenF('<?xml version="1.0"?><informationTable/>')).toEqual([]);
  });
});
```

- [ ] **Step 2: Run test, verify it fails**

Run: `npm test -- tests/parsers/thirteen-f.test.js`
Expected: FAIL with "Cannot find module".

- [ ] **Step 3: Implement parser (zero-deps via regex on flat tag structure)**

```javascript
// lib/parsers/thirteen-f.js
function pickTag(block, tag) {
  const re = new RegExp(`<${tag}>([\\s\\S]*?)</${tag}>`);
  const m = block.match(re);
  return m ? m[1].trim() : '';
}

function pickInt(s) { return Number(s.replace(/,/g, '')) || 0; }

export function parseThirteenF(xml) {
  const holdings = [];
  const blockRe = /<infoTable>([\s\S]*?)<\/infoTable>/g;
  let m;
  while ((m = blockRe.exec(xml)) !== null) {
    const block = m[1];
    const innerRe = /<shrsOrPrnAmt>([\s\S]*?)<\/shrsOrPrnAmt>/;
    const inner = block.match(innerRe);
    const shares = inner ? pickInt(pickTag(inner[1], 'sshPrnamt')) : 0;
    holdings.push({
      cusip: pickTag(block, 'cusip'),
      issuerName: pickTag(block, 'nameOfIssuer'),
      shares,
      valueUsd: pickInt(pickTag(block, 'value')) * 1000, // SEC reports in thousands
      votingAuthority: {
        sole: pickInt(pickTag(block, '<Sole>([\\s\\S]*?)</Sole>')) ||
               pickInt(block.match(/<Sole>([\s\S]*?)<\/Sole>/)?.[1] || '0'),
        shared: pickInt(block.match(/<Shared>([\s\S]*?)<\/Shared>/)?.[1] || '0'),
        none: pickInt(block.match(/<None>([\s\S]*?)<\/None>/)?.[1] || '0'),
      },
    });
  }
  return holdings;
}
```

- [ ] **Step 4: Run test, verify it passes**

Run: `npm test -- tests/parsers/thirteen-f.test.js`
Expected: 2 tests pass.

- [ ] **Step 5: Commit**

```bash
git add lib/parsers/thirteen-f.js tests/parsers/thirteen-f.test.js
git commit -m "feat(parser): 13F XML to normalized holdings (zero deps)"
```

---

### Task 2.5: 13F summary computer (deltas vs prior period)

**Files:**
- Create: `lib/compute/thirteen-f-summary.js`
- Test: `tests/compute/thirteen-f-summary.test.js`

**Interfaces:**
- `compute13FSummary(currentHoldings, priorHoldings)` → `{ totalHoldingsCount, totalValueUsd, newPositions, closedPositions, increasedPositions, decreasedPositions }`.
- `cusips` are the join key. Empty `priorHoldings` means every holding is `new`.

- [ ] **Step 1: Write failing test**

```javascript
// tests/compute/thirteen-f-summary.test.js
import { describe, it, expect } from 'vitest';
import { compute13FSummary } from '../../lib/compute/thirteen-f-summary.js';

const aapl = { cusip: '037833100', issuerName: 'APPLE INC', shares: 300000000, valueUsd: 58200000000, votingAuthority: { sole: 300000000, shared: 0, none: 0 } };
const goog = { cusip: '02079K305', issuerName: 'ALPHABET INC', shares: 10000000, valueUsd: 17000000000, votingAuthority: { sole: 10000000, shared: 0, none: 0 } };

describe('compute13FSummary', () => {
  it('all new when no prior', () => {
    const r = compute13FSummary([aapl, goog], []);
    expect(r.newPositions).toEqual(['037833100', '02079K305']);
    expect(r.closedPositions).toEqual([]);
    expect(r.totalValueUsd).toBe(58200000000 + 17000000000);
  });

  it('detects increased / decreased / closed', () => {
    const prior = [
      { ...aapl, shares: 200000000, valueUsd: 38800000000 },
      { cusip: '999999999', issuerName: 'OLDCO', shares: 1, valueUsd: 1, votingAuthority: { sole: 1, shared: 0, none: 0 } },
    ];
    const r = compute13FSummary([aapl], prior);
    expect(r.newPositions).toEqual([]);
    expect(r.closedPositions).toEqual(['999999999']);
    expect(r.increasedPositions).toBe(1);
    expect(r.decreasedPositions).toBe(0);
  });
});
```

- [ ] **Step 2: Run test, verify it fails**

Run: `npm test -- tests/compute/thirteen-f-summary.test.js`
Expected: FAIL with "Cannot find module".

- [ ] **Step 3: Implement summary computer**

```javascript
// lib/compute/thirteen-f-summary.js
export function compute13FSummary(currentHoldings, priorHoldings = []) {
  const prior = new Map(priorHoldings.map(h => [h.cusip, h]));
  const curr = new Map(currentHoldings.map(h => [h.cusip, h]));

  const newPositions = [];
  const increasedPositions = currentHoldings.filter(h => {
    if (!prior.has(h.cusip)) { newPositions.push(h.cusip); return false; }
    return h.shares > prior.get(h.cusip).shares;
  }).length;
  const decreasedPositions = currentHoldings.filter(h => {
    const p = prior.get(h.cusip);
    return p && h.shares < p.shares;
  }).length;
  const closedPositions = [...prior.keys()].filter(c => !curr.has(c));

  const totalValueUsd = currentHoldings.reduce((s, h) => s + h.valueUsd, 0);

  return {
    totalHoldingsCount: currentHoldings.length,
    totalValueUsd,
    newPositions,
    closedPositions,
    increasedPositions,
    decreasedPositions,
  };
}
```

- [ ] **Step 4: Run test, verify it passes**

Run: `npm test -- tests/compute/thirteen-f-summary.test.js`
Expected: 2 tests pass.

- [ ] **Step 5: Commit**

```bash
git add lib/compute/thirteen-f-summary.js tests/compute/thirteen-f-summary.test.js
git commit -m "feat(compute): 13F deltas (new/closed/inc/dec) vs prior period"
```

---

### Task 2.6: 13D/G search fetcher

**Files:**
- Create: `lib/edgar/fetch-thirteen-dg-search.js`
- Test: `tests/edgar/fetch-thirteen-dg-search.test.js`

**Interfaces:**
- `fetchThirteenDGSearch(httpClient, { startDate, endDate, formType })` → `Array<{ ciks, displayNames, fileDate, form, adsh, tickers }>` for the given date range and form type (`SC 13D`, `SC 13D/A`, `SC 13G`, or `SC 13G/A`).

- [ ] **Step 1: Write failing test**

```javascript
// tests/edgar/fetch-thirteen-dg-search.test.js
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import nock from 'nock';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { fetchThirteenDGSearch } from '../../lib/edgar/fetch-thirteen-dg-search.js';
import { createHttpClient } from '../../lib/http-client.js';
import { TokenBucket } from '../../lib/token-bucket.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const fixture = JSON.parse(readFileSync(join(__dirname, '../fixtures/search-13dg.json'), 'utf8'));

describe('fetchThirteenDGSearch', () => {
  let client;
  beforeEach(() => {
    client = createHttpClient({ userAgent: 'T t@e.com', bucket: new TokenBucket(100, 100) });
    nock.disableNetConnect();
  });
  afterEach(() => { nock.cleanAll(); nock.enableNetConnect(); });

  it('queries EDGAR full-text search with the form and date range', async () => {
    const scope = nock('https://efts.sec.gov')
      .get(/LATEST\/search-index.*forms=SC\+13D.*startDate=2026-06-20.*endDate=2026-06-25/)
      .reply(200, fixture);
    const r = await fetchThirteenDGSearch(client, {
      startDate: '2026-06-20', endDate: '2026-06-25', formType: 'SC 13D',
    });
    expect(r).toHaveLength(2);
    expect(r[0].form).toBe('SC 13D');
    expect(scope.isDone()).toBe(true);
  });

  it('encodes form name with + (not %20) per EDGAR convention', async () => {
    let capturedUrl = null;
    nock('https://efts.sec.gov').get(/.*/).reply(200, (uri) => { capturedUrl = uri; return fixture; });
    await fetchThirteenDGSearch(client, { startDate: '2026-06-20', endDate: '2026-06-25', formType: 'SC 13G/A' });
    expect(capturedUrl).toMatch(/forms=SC\+13G%2FA/);
  });
});
```

- [ ] **Step 2: Run test, verify it fails**

Run: `npm test -- tests/edgar/fetch-thirteen-dg-search.test.js`
Expected: FAIL with "Cannot find module".

- [ ] **Step 3: Implement fetcher**

```javascript
// lib/edgar/fetch-thirteen-dg-search.js
const VALID_FORMS = new Set(['SC 13D', 'SC 13D/A', 'SC 13G', 'SC 13G/A']);

export async function fetchThirteenDGSearch(httpClient, { startDate, endDate, formType }) {
  if (!VALID_FORMS.has(formType)) throw new Error(`invalid formType: ${formType}`);
  const formParam = encodeURIComponent(formType).replace(/%2F/g, '/'); // SC 13D/A → SC+13D%2FA, then we re-encode
  const url = `https://efts.sec.gov/LATEST/search-index?q=&dateRange=custom&startDate=${startDate}&endDate=${endDate}&forms=${encodeURIComponent(formType)}`;
  const res = await httpClient.fetch(url);
  if (!res.ok) throw new Error(`EDGAR search HTTP ${res.status}`);
  const data = await res.json();
  return data?.hits?.hits ?? [];
}
```

- [ ] **Step 4: Run test, verify it passes**

Run: `npm test -- tests/edgar/fetch-thirteen-dg-search.test.js`
Expected: 2 tests pass.

- [ ] **Step 5: Commit**

```bash
git add lib/edgar/fetch-thirteen-dg-search.js tests/edgar/fetch-thirteen-dg-search.test.js
git commit -m "feat(edgar): 13D/G full-text search fetcher"
```

---

### Task 2.7: 13D/G primary doc parser (intent by form type)

**Files:**
- Create: `lib/parsers/thirteen-dg.js`
- Test: `tests/parsers/thirteen-dg.test.js`

**Interfaces:**
- `parseThirteenDG(html, { formType })` → `{ issuerName, issuerTicker, ownershipPercent, sharesOwned, intent }`. **No Item 4 regex** — `intent` is set purely by `formType`: `SC 13D` / `SC 13D/A` → `'active'`; `SC 13G` / `SC 13G/A` → `'passive'`.

- [ ] **Step 1: Write failing test**

```javascript
// tests/parsers/thirteen-dg.test.js
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { parseThirteenDG } from '../../lib/parsers/thirteen-dg.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const html13d = readFileSync(join(__dirname, '../fixtures/13d-primary-doc.html'), 'utf8');
const html13g = readFileSync(join(__dirname, '../fixtures/13g-primary-doc.html'), 'utf8');

describe('parseThirteenDG', () => {
  it('parses 13D and tags intent=active by form type', () => {
    const r = parseThirteenDG(html13d, { formType: 'SC 13D' });
    expect(r).toMatchObject({
      issuerName: 'Jet.AI Inc',
      issuerTicker: 'JTAI',
      ownershipPercent: 6.8,
      sharesOwned: 4500000,
      intent: 'active',
    });
  });

  it('parses 13G and tags intent=passive by form type', () => {
    const r = parseThirteenDG(html13g, { formType: 'SC 13G' });
    expect(r.issuerName).toBe('Activision Blizzard Inc');
    expect(r.intent).toBe('passive');
  });

  it('SC 13D/A still maps to active', () => {
    const r = parseThirteenDG(html13d, { formType: 'SC 13D/A' });
    expect(r.intent).toBe('active');
  });

  it('SC 13G/A maps to passive', () => {
    const r = parseThirteenDG(html13g, { formType: 'SC 13G/A' });
    expect(r.intent).toBe('passive');
  });

  it('throws on unknown form type', () => {
    expect(() => parseThirteenDG(html13d, { formType: '10-K' })).toThrow(/invalid formType/);
  });
});
```

- [ ] **Step 2: Run test, verify it fails**

Run: `npm test -- tests/parsers/thirteen-dg.test.js`
Expected: FAIL with "Cannot find module".

- [ ] **Step 3: Implement parser (zero deps via regex + tag stripping)**

```javascript
// lib/parsers/thirteen-dg.js
const INTENT_BY_FORM = {
  'SC 13D': 'active',
  'SC 13D/A': 'active',
  'SC 13G': 'passive',
  'SC 13G/A': 'passive',
};

function stripTags(html) { return html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim(); }

function pickFirst(html, labels) {
  const text = stripTags(html);
  for (const label of labels) {
    const re = new RegExp(`${label}\\s*[:\\-]?\\s*([\\d.,]+|\\S[^\\d]*)`, 'i');
    const m = text.match(re);
    if (m) return m[1].trim();
  }
  return null;
}

export function parseThirteenDG(html, { formType }) {
  if (!INTENT_BY_FORM[formType]) throw new Error(`invalid formType: ${formType}`);
  const issuerName = pickFirst(html, ['NAME OF ISSUER']);
  const ticker = pickFirst(html, ['TICKER', 'TRADING SYMBOL']);
  const percent = Number(pickFirst(html, ['PERCENT OF CLASS']) || '0');
  const shares = Number((pickFirst(html, ['AGGREGATE AMOUNT BENEFICIALLY OWNED']) || '0').replace(/,/g, ''));
  return {
    issuerName: issuerName || 'UNKNOWN',
    issuerTicker: ticker || '',
    ownershipPercent: percent,
    sharesOwned: shares,
    intent: INTENT_BY_FORM[formType],
  };
}
```

- [ ] **Step 4: Run test, verify it passes**

Run: `npm test -- tests/parsers/thirteen-dg.test.js`
Expected: 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add lib/parsers/thirteen-dg.js tests/parsers/thirteen-dg.test.js
git commit -m "feat(parser): 13D/G primary doc parser (intent by form type only)"
```

---

### Task 2.8: State JSON store (read/write aggregator's seen 13F filings)

**Files:**
- Create: `lib/store/state-json.js`
- Test: `tests/store/state-json.test.js`

**Interfaces:**
- `readStateJson(path)` → `{ lastUpdated, seenFilings: { [accessionNumber]: epochMs } }` (defaults if file missing).
- `writeStateJson(path, state)` → void. Uses **atomic write** (temp + rename) because state must never be half-written.

- [ ] **Step 1: Write failing test**

```javascript
// tests/store/state-json.test.js
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { mkdtempSync, writeFileSync, rmSync, readFileSync, existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { readStateJson, writeStateJson } from '../../lib/store/state-json.js';

let dir;
beforeEach(() => { dir = mkdtempSync(join(tmpdir(), 'ftm-')); });
afterEach(() => { rmSync(dir, { recursive: true, force: true }); });

describe('state-json', () => {
  it('returns defaults when file missing', () => {
    const s = readStateJson(join(dir, 'missing.json'));
    expect(s).toEqual({ lastUpdated: '1970-01-01T00:00:00.000Z', seenFilings: {} });
  });

  it('round-trips via write + read', () => {
    const p = join(dir, 'state.json');
    const s = { lastUpdated: '2026-05-15T08:00:00.000Z', seenFilings: { a: 1, b: 2 } };
    writeStateJson(p, s);
    expect(readStateJson(p)).toEqual(s);
  });

  it('writes atomically (temp file cleaned up)', () => {
    const p = join(dir, 'state.json');
    writeStateJson(p, { lastUpdated: 'x', seenFilings: {} });
    expect(existsSync(p)).toBe(true);
    const tempFiles = require('node:fs').readdirSync(dir).filter(f => f.includes('.tmp'));
    expect(tempFiles).toEqual([]);
  });
});
```

- [ ] **Step 2: Run test, verify it fails**

Run: `npm test -- tests/store/state-json.test.js`
Expected: FAIL with "Cannot find module".

- [ ] **Step 3: Implement state-json**

```javascript
// lib/store/state-json.js
import { readFileSync, writeFileSync, renameSync, existsSync, mkdirSync } from 'node:fs';
import { dirname } from 'node:path';

const DEFAULTS = { lastUpdated: '1970-01-01T00:00:00.000Z', seenFilings: {} };

export function readStateJson(path) {
  if (!existsSync(path)) return structuredClone(DEFAULTS);
  try {
    return JSON.parse(readFileSync(path, 'utf8'));
  } catch {
    return structuredClone(DEFAULTS);
  }
}

export function writeStateJson(path, state) {
  mkdirSync(dirname(path), { recursive: true });
  const tmp = `${path}.${process.pid}.${Date.now()}.tmp`;
  writeFileSync(tmp, JSON.stringify(state, null, 2));
  renameSync(tmp, path);
}
```

- [ ] **Step 4: Run test, verify it passes**

Run: `npm test -- tests/store/state-json.test.js`
Expected: 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add lib/store/state-json.js tests/store/state-json.test.js
git commit -m "feat(store): state JSON read/write with atomic rename"
```

---

### Task 2.9: State NDJSON store (atomic append for aggregator's seen 13D/G)

**Files:**
- Create: `lib/store/state-ndjson.js`
- Test: `tests/store/state-ndjson.test.js`

**Interfaces:**
- `readStateNdjson(path)` → `Array<{ accession, seenAt }>` (empty if file missing).
- `appendStateNdjson(path, entries)` → void. Atomic: writes to `path.tmp` then renames (rewrites whole file, since the file is small).

- [ ] **Step 1: Write failing test**

```javascript
// tests/store/state-ndjson.test.js
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { mkdtempSync, rmSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { readStateNdjson, appendStateNdjson } from '../../lib/store/state-ndjson.js';

let dir;
beforeEach(() => { dir = mkdtempSync(join(tmpdir(), 'ftm-')); });
afterEach(() => { rmSync(dir, { recursive: true, force: true }); });

describe('state-ndjson', () => {
  it('returns [] when file missing', () => {
    expect(readStateNdjson(join(dir, 'missing.ndjson'))).toEqual([]);
  });

  it('appends entries and round-trips', () => {
    const p = join(dir, 's.ndjson');
    appendStateNdjson(p, [{ accession: 'A', seenAt: 1 }]);
    appendStateNdjson(p, [{ accession: 'B', seenAt: 2 }]);
    expect(readStateNdjson(p)).toEqual([
      { accession: 'A', seenAt: 1 },
      { accession: 'B', seenAt: 2 },
    ]);
  });

  it('skips blank lines on read', () => {
    const p = join(dir, 's.ndjson');
    appendStateNdjson(p, [{ accession: 'A', seenAt: 1 }]);
    expect(readStateNdjson(p).length).toBe(1);
  });
});
```

- [ ] **Step 2: Run test, verify it fails**

Run: `npm test -- tests/store/state-ndjson.test.js`
Expected: FAIL with "Cannot find module".

- [ ] **Step 3: Implement state-ndjson**

```javascript
// lib/store/state-ndjson.js
import { readFileSync, writeFileSync, renameSync, existsSync, mkdirSync } from 'node:fs';
import { dirname } from 'node:path';

export function readStateNdjson(path) {
  if (!existsSync(path)) return [];
  const out = [];
  for (const line of readFileSync(path, 'utf8').split('\n')) {
    if (!line.trim()) continue;
    out.push(JSON.parse(line));
  }
  return out;
}

export function appendStateNdjson(path, entries) {
  mkdirSync(dirname(path), { recursive: true });
  const existing = existsSync(path) ? readFileSync(path, 'utf8') : '';
  const next = (existing.endsWith('\n') || !existing ? existing : existing + '\n')
    + entries.map(e => JSON.stringify(e)).join('\n') + '\n';
  const tmp = `${path}.${process.pid}.${Date.now()}.tmp`;
  writeFileSync(tmp, next);
  renameSync(tmp, path);
}
```

- [ ] **Step 4: Run test, verify it passes**

Run: `npm test -- tests/store/state-ndjson.test.js`
Expected: 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add lib/store/state-ndjson.js tests/store/state-ndjson.test.js
git commit -m "feat(store): state NDJSON read/append with atomic rename"
```

---

### Task 2.10: Feed JSON store (13F) with 13F-HR/A overwrite + history

**Files:**
- Create: `lib/store/feed-json.js`
- Test: `tests/store/feed-json.test.js`

**Interfaces:**
- `readFeedJson(path)` → full feed object (defaults: `{ schemaVersion: 1, generatedAt, lookbackDays: 90, thirteenF: [], stats: {...} }`).
- `writeFeedJson(path, feed)` → void (atomic write).
- `upsert13FFiling(path, entry)` → void. If a `thirteenF[]` entry exists with same `(filerCik, periodOfReport)`, **overwrite** its `holdings` + `summary` + `latestFilingDate/FormType/AccessionNumber`, **append** the old snapshot to `history[]`. Otherwise push a new entry.
- `computeStats(feed)` → `{ thirteenFFilings, thirteenFHoldings }`.

- [ ] **Step 1: Write failing test**

```javascript
// tests/store/feed-json.test.js
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { readFeedJson, writeFeedJson, upsert13FFiling, computeStats } from '../../lib/store/feed-json.js';

let dir;
beforeEach(() => { dir = mkdtempSync(join(tmpdir(), 'ftm-')); });
afterEach(() => { rmSync(dir, { recursive: true, force: true }); });

const newEntry = (over = {}) => ({
  filerCik: '0001067983', filerName: 'Berkshire Hathaway Inc',
  latestFilingDate: '2026-05-15', latestFormType: '13F-HR',
  latestAccessionNumber: '0001067983-26-000123', periodOfReport: '2026-03-31',
  history: [{ filingDate: '2026-05-15', formType: '13F-HR', accessionNumber: '0001067983-26-000123' }],
  holdings: [{ cusip: '037833100', issuerName: 'APPLE INC', shares: 300000000, valueUsd: 58200000000, votingAuthority: { sole: 300000000, shared: 0, none: 0 } }],
  summary: { totalHoldingsCount: 1, totalValueUsd: 58200000000, newPositions: ['037833100'], closedPositions: [], increasedPositions: 0, decreasedPositions: 0 },
  ...over,
});

describe('feed-json', () => {
  it('returns defaults when missing', () => {
    const f = readFeedJson(join(dir, 'missing.json'));
    expect(f.thirteenF).toEqual([]);
    expect(f.schemaVersion).toBe(1);
  });

  it('upsert new entry when no matching (filer, period)', () => {
    const p = join(dir, 'f.json');
    upsert13FFiling(p, newEntry());
    const f = readFeedJson(p);
    expect(f.thirteenF).toHaveLength(1);
  });

  it('upsert overwrites + appends history on 13F-HR/A same period', () => {
    const p = join(dir, 'f.json');
    upsert13FFiling(p, newEntry());
    const amended = newEntry({
      latestFilingDate: '2026-06-10', latestFormType: '13F-HR/A',
      latestAccessionNumber: '0001067983-26-000456',
      holdings: [{ cusip: '037833100', issuerName: 'APPLE INC', shares: 310000000, valueUsd: 60140000000, votingAuthority: { sole: 310000000, shared: 0, none: 0 } }],
      summary: { totalHoldingsCount: 1, totalValueUsd: 60140000000, newPositions: [], closedPositions: [], increasedPositions: 1, decreasedPositions: 0 },
    });
    upsert13FFiling(p, amended);
    const f = readFeedJson(p);
    expect(f.thirteenF).toHaveLength(1);
    expect(f.thirteenF[0].latestFormType).toBe('13F-HR/A');
    expect(f.thirteenF[0].holdings[0].shares).toBe(310000000);
    expect(f.thirteenF[0].history).toHaveLength(2);
    expect(f.thirteenF[0].history[0].formType).toBe('13F-HR');
    expect(f.thirteenF[0].history[1].formType).toBe('13F-HR/A');
  });

  it('does NOT collapse different periods for the same filer', () => {
    const p = join(dir, 'f.json');
    upsert13FFiling(p, newEntry({ periodOfReport: '2025-12-31' }));
    upsert13FFiling(p, newEntry({ periodOfReport: '2026-03-31' }));
    expect(readFeedJson(p).thirteenF).toHaveLength(2);
  });

  it('computeStats counts holdings across all filers', () => {
    const f = { thirteenF: [newEntry(), newEntry({ filerCik: '0001336528', filerName: 'Pershing' })] };
    expect(computeStats(f)).toEqual({ thirteenFFilings: 2, thirteenFHoldings: 2 });
  });
});
```

- [ ] **Step 2: Run test, verify it fails**

Run: `npm test -- tests/store/feed-json.test.js`
Expected: FAIL with "Cannot find module".

- [ ] **Step 3: Implement feed-json**

```javascript
// lib/store/feed-json.js
import { readFileSync, writeFileSync, renameSync, existsSync, mkdirSync } from 'node:fs';
import { dirname } from 'node:path';

const DEFAULTS = () => ({
  schemaVersion: 1,
  generatedAt: new Date().toISOString(),
  lookbackDays: 90,
  thirteenF: [],
  stats: { thirteenFFilings: 0, thirteenFHoldings: 0 },
});

export function readFeedJson(path) {
  if (!existsSync(path)) return DEFAULTS();
  try {
    const parsed = JSON.parse(readFileSync(path, 'utf8'));
    return { ...DEFAULTS(), ...parsed, thirteenF: parsed.thirteenF ?? [], stats: parsed.stats ?? { thirteenFFilings: 0, thirteenFHoldings: 0 } };
  } catch {
    return DEFAULTS();
  }
}

export function writeFeedJson(path, feed) {
  mkdirSync(dirname(path), { recursive: true });
  const tmp = `${path}.${process.pid}.${Date.now()}.tmp`;
  writeFileSync(tmp, JSON.stringify(feed, null, 2));
  renameSync(tmp, path);
}

export function upsert13FFiling(path, entry) {
  const feed = readFeedJson(path);
  const idx = feed.thirteenF.findIndex(e => e.filerCik === entry.filerCik && e.periodOfReport === entry.periodOfReport);
  if (idx >= 0) {
    const old = feed.thirteenF[idx];
    feed.thirteenF[idx] = {
      ...entry,
      history: [...(old.history ?? []), {
        filingDate: old.latestFilingDate, formType: old.latestFormType, accessionNumber: old.latestAccessionNumber,
      }],
    };
  } else {
    feed.thirteenF.push(entry);
  }
  feed.generatedAt = new Date().toISOString();
  feed.stats = computeStats(feed);
  writeFeedJson(path, feed);
}

export function computeStats(feed) {
  const holdings = feed.thirteenF.reduce((s, e) => s + (e.holdings?.length ?? 0), 0);
  return { thirteenFFilings: feed.thirteenF.length, thirteenFHoldings: holdings };
}
```

- [ ] **Step 4: Run test, verify it passes**

Run: `npm test -- tests/store/feed-json.test.js`
Expected: 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add lib/store/feed-json.js tests/store/feed-json.test.js
git commit -m "feat(store): feed JSON with 13F-HR/A overwrite + history append"
```

---

### Task 2.11: Manifest + per-year NDJSON feed (13D/G)

**Files:**
- Create: `lib/store/manifest.js`
- Create: `lib/store/feed-ndjson.js`
- Test: `tests/store/manifest.test.js`
- Test: `tests/store/feed-ndjson.test.js`

**Interfaces:**
- `readManifest(feedDir)` → manifest object (defaults: `{ schemaVersion: 1, currentYear: <this year>, years: {} }`).
- `writeManifest(feedDir, manifest)` → atomic.
- `append13DFiling(feedDir, manifest, entry)` → updates manifest counts/dates and appends to `<year>.ndjson` (atomic rewrite).
- `read13DFilings(feedDir, manifest, { years })` → flat array across the requested years. Defaults: current year + previous year.
- `validateManifest(feedDir, manifest)` → `{ ok, warnings[] }`. Line count vs. manifest count per year.

- [ ] **Step 1: Write failing test for manifest**

```javascript
// tests/store/manifest.test.js
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { readManifest, writeManifest } from '../../lib/store/manifest.js';

let dir;
beforeEach(() => { dir = mkdtempSync(join(tmpdir(), 'ftm-')); });
afterEach(() => { rmSync(dir, { recursive: true, force: true }); });

describe('manifest', () => {
  it('returns defaults when missing', () => {
    const m = readManifest(dir);
    expect(m.schemaVersion).toBe(1);
    expect(m.years).toEqual({});
  });

  it('round-trips', () => {
    const m = { schemaVersion: 1, currentYear: 2026, years: { '2026': { file: 'feed-13dg/2026.ndjson', count: 5, firstDate: '2026-01-01', lastDate: '2026-06-25' } } };
    writeManifest(dir, m);
    expect(readManifest(dir)).toEqual(m);
  });
});
```

- [ ] **Step 2: Run test, verify it fails**

Run: `npm test -- tests/store/manifest.test.js`
Expected: FAIL with "Cannot find module".

- [ ] **Step 3: Implement manifest**

```javascript
// lib/store/manifest.js
import { readFileSync, writeFileSync, renameSync, existsSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';

const MANIFEST_FILE = 'manifest.json';
const DEFAULTS = () => ({ schemaVersion: 1, currentYear: new Date().getUTCFullYear(), years: {} });

export function readManifest(feedDir) {
  const p = join(feedDir, MANIFEST_FILE);
  if (!existsSync(p)) return DEFAULTS();
  try {
    const parsed = JSON.parse(readFileSync(p, 'utf8'));
    return { ...DEFAULTS(), ...parsed, years: parsed.years ?? {} };
  } catch {
    return DEFAULTS();
  }
}

export function writeManifest(feedDir, manifest) {
  mkdirSync(feedDir, { recursive: true });
  const p = join(feedDir, MANIFEST_FILE);
  const tmp = `${p}.${process.pid}.${Date.now()}.tmp`;
  writeFileSync(tmp, JSON.stringify(manifest, null, 2));
  renameSync(tmp, p);
}
```

- [ ] **Step 4: Run test, verify it passes**

Run: `npm test -- tests/store/manifest.test.js`
Expected: 2 tests pass.

- [ ] **Step 5: Commit manifest**

```bash
git add lib/store/manifest.js tests/store/manifest.test.js
git commit -m "feat(store): 13D/G manifest read/write"
```

- [ ] **Step 6: Write failing test for feed-ndjson**

```javascript
// tests/store/feed-ndjson.test.js
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { append13DFiling, read13DFilings, validateManifest } from '../../lib/store/feed-ndjson.js';
import { readManifest } from '../../lib/store/manifest.js';

let dir;
beforeEach(() => { dir = mkdtempSync(join(tmpdir(), 'ftm-')); });
afterEach(() => { rmSync(dir, { recursive: true, force: true }); });

const e1 = { filerCik: '0000932470', filerName: 'ICAHN CARL C', issuerCik: '0001717393', issuerName: 'Jet.AI Inc', issuerTicker: 'JTAI', formType: 'SC 13D', filingDate: '2026-06-20', ownershipPercent: 6.8, sharesOwned: 4500000, intent: 'active', accessionNumber: '0000932470-26-000045', primaryDocUrl: 'https://www.sec.gov/...' };
const e2 = { filerCik: '0000893855', filerName: 'ELLIOTT', issuerCik: '0001315098', issuerName: 'ATVI', issuerTicker: 'ATVI', formType: 'SC 13G', filingDate: '2026-06-18', ownershipPercent: 5.1, sharesOwned: 4900000, intent: 'passive', accessionNumber: '0000893855-26-000078', primaryDocUrl: 'https://www.sec.gov/...' };

describe('feed-ndjson', () => {
  it('appends to year file and updates manifest', () => {
    const m = readManifest(dir);
    append13DFiling(dir, m, e1);
    append13DFiling(dir, m, e2);
    const after = readManifest(dir);
    expect(after.years['2026'].count).toBe(2);
    expect(after.years['2026'].lastDate).toBe('2026-06-20');
    expect(after.years['2026'].firstDate).toBe('2026-06-18');
  });

  it('read13DFilings across years merges + sorts desc by date', () => {
    const m = readManifest(dir);
    append13DFiling(dir, m, { ...e1, filingDate: '2025-12-30' });
    append13DFiling(dir, m, e2);
    const m2 = readManifest(dir);
    const all = read13DFilings(dir, m2);
    expect(all).toHaveLength(2);
    expect(all[0].filingDate).toBe('2026-06-18');
  });

  it('read13DFilings with explicit years', () => {
    const m = readManifest(dir);
    append13DFiling(dir, m, { ...e1, filingDate: '2025-12-30' });
    append13DFiling(dir, m, e2);
    const m2 = readManifest(dir);
    expect(read13DFilings(dir, m2, { years: [2025] })).toHaveLength(1);
  });

  it('validateManifest flags count mismatch', () => {
    const m = readManifest(dir);
    append13DFiling(dir, m, e1);
    const m2 = readManifest(dir);
    m2.years['2026'].count = 99; // corrupt the manifest
    const r = validateManifest(dir, m2);
    expect(r.ok).toBe(false);
    expect(r.warnings.length).toBeGreaterThan(0);
  });
});
```

- [ ] **Step 7: Run test, verify it fails**

Run: `npm test -- tests/store/feed-ndjson.test.js`
Expected: FAIL with "Cannot find module".

- [ ] **Step 8: Implement feed-ndjson**

```javascript
// lib/store/feed-ndjson.js
import { readFileSync, writeFileSync, renameSync, existsSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { writeManifest, readManifest } from './manifest.js';

function yearFile(feedDir, year) { return join(feedDir, `${year}.ndjson`); }

export function append13DFiling(feedDir, manifest, entry) {
  const year = String(new Date(entry.filingDate + 'T00:00:00Z').getUTCFullYear());
  mkdirSync(feedDir, { recursive: true });
  const file = yearFile(feedDir, year);
  const existing = existsSync(file) ? readFileSync(file, 'utf8') : '';
  const next = (existing.endsWith('\n') || !existing ? existing : existing + '\n') + JSON.stringify(entry) + '\n';
  const tmp = `${file}.${process.pid}.${Date.now()}.tmp`;
  writeFileSync(tmp, next);
  renameSync(tmp, file);

  const y = manifest.years[year] ?? { file: `feed-13dg/${year}.ndjson`, count: 0, firstDate: entry.filingDate, lastDate: entry.filingDate };
  y.count = (y.count ?? 0) + 1;
  y.firstDate = entry.filingDate < (y.firstDate ?? entry.filingDate) ? entry.filingDate : y.firstDate;
  y.lastDate = entry.filingDate > (y.lastDate ?? entry.filingDate) ? entry.filingDate : y.lastDate;
  manifest.years[year] = y;
  manifest.currentYear = Math.max(Number(year), manifest.currentYear ?? Number(year));
  writeManifest(feedDir, manifest);
}

export function read13DFilings(feedDir, manifest, { years } = {}) {
  const currentYear = manifest.currentYear ?? new Date().getUTCFullYear();
  const targetYears = years ?? [currentYear, currentYear - 1];
  const out = [];
  for (const y of targetYears) {
    const file = yearFile(feedDir, y);
    if (!existsSync(file)) continue;
    for (const line of readFileSync(file, 'utf8').split('\n')) {
      if (!line.trim()) continue;
      try { out.push(JSON.parse(line)); } catch { /* skip corrupt line */ }
    }
  }
  out.sort((a, b) => b.filingDate.localeCompare(a.filingDate));
  return out;
}

export function validateManifest(feedDir, manifest) {
  const warnings = [];
  for (const [year, meta] of Object.entries(manifest.years ?? {})) {
    const file = yearFile(feedDir, year);
    if (!existsSync(file)) { warnings.push(`${year}: file missing`); continue; }
    const actual = readFileSync(file, 'utf8').split('\n').filter(Boolean).length;
    if (actual !== meta.count) warnings.push(`${year}: manifest says ${meta.count}, file has ${actual}`);
  }
  return { ok: warnings.length === 0, warnings };
}
```

- [ ] **Step 9: Run test, verify it passes**

Run: `npm test -- tests/store/feed-ndjson.test.js`
Expected: 4 tests pass.

- [ ] **Step 10: Commit**

```bash
git add lib/store/feed-ndjson.js tests/store/feed-ndjson.test.js
git commit -m "feat(store): 13D/G per-year NDJSON append + manifest validation"
```

---

### Task 2.12: Filter by lookback

**Files:**
- Create: `lib/feed/filter-by-lookback.js`
- Test: `tests/feed/filter-by-lookback.test.js`

**Interfaces:**
- `filterByLookback(items, { lookbackDays, now = new Date() })` → returns only items whose `filingDate` is within the lookback window (inclusive of `now - lookbackDays`).
- Works on any item with an ISO `filingDate` (13F entries use `latestFilingDate`; this helper expects a normalized form — see test).

- [ ] **Step 1: Write failing test**

```javascript
// tests/feed/filter-by-lookback.test.js
import { describe, it, expect } from 'vitest';
import { filterByLookback } from '../../lib/feed/filter-by-lookback.js';

const NOW = new Date('2026-06-25T00:00:00Z');

describe('filterByLookback', () => {
  it('keeps only items within window', () => {
    const items = [
      { filingDate: '2026-06-24' },
      { filingDate: '2026-06-18' },
      { filingDate: '2026-06-17' },
    ];
    const r = filterByLookback(items, { lookbackDays: 7, now: NOW });
    expect(r).toHaveLength(2);
  });

  it('handles lookbackDays=1 (only today)', () => {
    const r = filterByLookback([{ filingDate: '2026-06-25' }, { filingDate: '2026-06-24' }], { lookbackDays: 1, now: NOW });
    expect(r).toHaveLength(1);
  });
});
```

- [ ] **Step 2: Run test, verify it fails**

Run: `npm test -- tests/feed/filter-by-lookback.test.js`
Expected: FAIL with "Cannot find module".

- [ ] **Step 3: Implement**

```javascript
// lib/feed/filter-by-lookback.js
export function filterByLookback(items, { lookbackDays, now = new Date() }) {
  if (!Number.isInteger(lookbackDays) || lookbackDays <= 0) throw new Error('lookbackDays must be > 0');
  const cutoff = new Date(now.getTime() - lookbackDays * 24 * 60 * 60 * 1000);
  const cutoffStr = cutoff.toISOString().slice(0, 10);
  return items.filter(it => it.filingDate >= cutoffStr);
}
```

- [ ] **Step 4: Run test, verify it passes**

Run: `npm test -- tests/feed/filter-by-lookback.test.js`
Expected: 2 tests pass.

- [ ] **Step 5: Commit**

```bash
git add lib/feed/filter-by-lookback.js tests/feed/filter-by-lookback.test.js
git commit -m "feat(feed): filter by lookback window"
```

---

### Task 2.13: Merge by issuer (13D/A helper for alerts)

**Files:**
- Create: `lib/feed/merge-by-issuer.js`
- Test: `tests/feed/merge-by-issuer.test.js`

**Interfaces:**
- `mergeByIssuer(entries)` → groups entries by `(filerCik, issuerCik, filingDate)`, keeping the latest `ownershipPercent` / `sharesOwned` / `filingDate` in each group, and tagging `count` = number of entries in the group.

- [ ] **Step 1: Write failing test**

```javascript
// tests/feed/merge-by-issuer.test.js
import { describe, it, expect } from 'vitest';
import { mergeByIssuer } from '../../lib/feed/merge-by-issuer.js';

const a1 = { filerCik: 'A', issuerCik: 'X', filingDate: '2026-06-20', ownershipPercent: 6.0, sharesOwned: 4000000, formType: 'SC 13D/A' };
const a2 = { filerCik: 'A', issuerCik: 'X', filingDate: '2026-06-20', ownershipPercent: 6.8, sharesOwned: 4500000, formType: 'SC 13D/A' };
const b1 = { filerCik: 'B', issuerCik: 'Y', filingDate: '2026-06-20', ownershipPercent: 9.0, sharesOwned: 1000000, formType: 'SC 13D' };

describe('mergeByIssuer', () => {
  it('merges same (filer, issuer, day) into one with count', () => {
    const r = mergeByIssuer([a1, a2, b1]);
    expect(r).toHaveLength(2);
    const merged = r.find(g => g.issuerCik === 'X');
    expect(merged.count).toBe(2);
    expect(merged.ownershipPercent).toBe(6.8);
  });

  it('preserves groups with different days as separate', () => {
    const r = mergeByIssuer([a1, { ...a2, filingDate: '2026-06-21' }]);
    expect(r).toHaveLength(2);
  });
});
```

- [ ] **Step 2: Run test, verify it fails**

Run: `npm test -- tests/feed/merge-by-issuer.test.js`
Expected: FAIL with "Cannot find module".

- [ ] **Step 3: Implement**

```javascript
// lib/feed/merge-by-issuer.js
export function mergeByIssuer(entries) {
  const groups = new Map();
  for (const e of entries) {
    const key = `${e.filerCik}|${e.issuerCik}|${e.filingDate}`;
    const prev = groups.get(key);
    if (!prev) {
      groups.set(key, { ...e, count: 1, amendments: [e] });
    } else {
      prev.amendments.push(e);
      prev.count = prev.amendments.length;
      // Latest by filingDate is the same day here; if ties, last wins
      if (e.ownershipPercent != null) prev.ownershipPercent = e.ownershipPercent;
      if (e.sharesOwned != null) prev.sharesOwned = e.sharesOwned;
    }
  }
  return [...groups.values()];
}
```

- [ ] **Step 4: Run test, verify it passes**

Run: `npm test -- tests/feed/merge-by-issuer.test.js`
Expected: 2 tests pass.

- [ ] **Step 5: Commit**

```bash
git add lib/feed/merge-by-issuer.js tests/feed/merge-by-issuer.test.js
git commit -m "feat(feed): merge 13D/A amendments by (filer+issuer+day)"
```

---

### Task 2.14: Classify (13D vs 13G)

**Files:**
- Create: `lib/alert/classify.js`
- Test: `tests/alert/classify.test.js`

**Interfaces:**
- `classify(entry)` → `'alert'` if form is `SC 13D` or `SC 13D/A`, else `'digest'`.
- `ALERT_FORMS` exported as a `Set`.

- [ ] **Step 1: Write failing test**

```javascript
// tests/alert/classify.test.js
import { describe, it, expect } from 'vitest';
import { classify, ALERT_FORMS } from '../../lib/alert/classify.js';

describe('classify', () => {
  it('SC 13D and 13D/A are alert', () => {
    expect(classify({ formType: 'SC 13D' })).toBe('alert');
    expect(classify({ formType: 'SC 13D/A' })).toBe('alert');
  });
  it('SC 13G and 13G/A are digest', () => {
    expect(classify({ formType: 'SC 13G' })).toBe('digest');
    expect(classify({ formType: 'SC 13G/A' })).toBe('digest');
  });
  it('ALERT_FORMS contains exactly 13D/13D-A', () => {
    expect([...ALERT_FORMS].sort()).toEqual(['SC 13D', 'SC 13D/A']);
  });
});
```

- [ ] **Step 2: Run test, verify it fails**

Run: `npm test -- tests/alert/classify.test.js`
Expected: FAIL with "Cannot find module".

- [ ] **Step 3: Implement**

```javascript
// lib/alert/classify.js
export const ALERT_FORMS = new Set(['SC 13D', 'SC 13D/A']);

export function classify(entry) {
  return ALERT_FORMS.has(entry.formType) ? 'alert' : 'digest';
}
```

- [ ] **Step 4: Run test, verify it passes**

Run: `npm test -- tests/alert/classify.test.js`
Expected: 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add lib/alert/classify.js tests/alert/classify.test.js
git commit -m "feat(alert): classify form → alert or digest"
```

---

### Task 2.15: Merge amendments for alert payload

**Files:**
- Create: `lib/alert/merge-amendments.js`
- Test: `tests/alert/merge-amendments.test.js`

**Interfaces:**
- `mergeAmendmentsForAlert(alertEntries)` → `[{ ...entry, count, summary }]` where `count` = amendment count and `summary` = e.g. `"3 次修订，5.1% → 6.8%"` (oldPercent → newPercent when known).

- [ ] **Step 1: Write failing test**

```javascript
// tests/alert/merge-amendments.test.js
import { describe, it, expect } from 'vitest';
import { mergeAmendmentsForAlert } from '../../lib/alert/merge-amendments.js';
import { mergeByIssuer } from '../../lib/feed/merge-by-issuer.js';

const e1 = { filerCik: 'A', issuerCik: 'X', filingDate: '2026-06-20', ownershipPercent: 5.1, sharesOwned: 4000000, formType: 'SC 13D/A' };
const e2 = { filerCik: 'A', issuerCik: 'X', filingDate: '2026-06-20', ownershipPercent: 6.8, sharesOwned: 4500000, formType: 'SC 13D/A' };
const e3 = { filerCik: 'A', issuerCik: 'X', filingDate: '2026-06-20', ownershipPercent: 7.0, sharesOwned: 4600000, formType: 'SC 13D/A' };

describe('mergeAmendmentsForAlert', () => {
  it('produces count and summary across amendments in same group', () => {
    const groups = mergeByIssuer([e1, e2, e3]);
    const r = mergeAmendmentsForAlert(groups);
    expect(r).toHaveLength(1);
    expect(r[0].count).toBe(3);
    expect(r[0].summary).toBe('3 次修订，5.1% → 7.0%');
  });

  it('count=1 produces no arrow', () => {
    const groups = mergeByIssuer([e2]);
    const r = mergeAmendmentsForAlert(groups);
    expect(r[0].count).toBe(1);
    expect(r[0].summary).toBe('6.8%');
  });
});
```

- [ ] **Step 2: Run test, verify it fails**

Run: `npm test -- tests/alert/merge-amendments.test.js`
Expected: FAIL with "Cannot find module".

- [ ] **Step 3: Implement**

```javascript
// lib/alert/merge-amendments.js
export function mergeAmendmentsForAlert(groups) {
  return groups.map(g => {
    const amendments = g.amendments ?? [g];
    amendments.sort((a, b) => a.filingDate.localeCompare(b.filingDate));
    const first = amendments[0];
    const last = amendments[amendments.length - 1];
    const summary = amendments.length === 1
      ? `${last.ownershipPercent}%`
      : `${amendments.length} 次修订，${first.ownershipPercent}% → ${last.ownershipPercent}%`;
    return { ...last, count: amendments.length, summary };
  });
}
```

- [ ] **Step 4: Run test, verify it passes**

Run: `npm test -- tests/alert/merge-amendments.test.js`
Expected: 2 tests pass.

- [ ] **Step 5: Commit**

```bash
git add lib/alert/merge-amendments.js tests/alert/merge-amendments.test.js
git commit -m "feat(alert): merge 13D/A amendments into single alert payload"
```

---

## Phase 3: Center Aggregator (GitHub Action)

### Task 3.1: Pipeline A (13F by CIK list)

**Files:**
- Create: `lib/aggregate/pipeline-a.js`
- Test: `tests/aggregate/pipeline-a.test.js`

**Interfaces:**
- `runPipelineA({ httpClient, config, feedPath, statePath })` → `{ added, errors[] }`. For each CIK in `config.thirteenF`: fetch submissions, filter to 13F-HR/A, dedup via state, fetch + parse XML, compute summary (vs prior period if present in feed), upsert into feed.

- [ ] **Step 1: Write failing test**

```javascript
// tests/aggregate/pipeline-a.test.js
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import nock from 'nock';
import { mkdtempSync, rmSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { runPipelineA } from '../../lib/aggregate/pipeline-a.js';
import { createHttpClient } from '../../lib/http-client.js';
import { TokenBucket } from '../../lib/token-bucket.js';

let dir, httpClient, config;
beforeEach(() => {
  dir = mkdtempSync(join(tmpdir(), 'ftm-'));
  httpClient = createHttpClient({ userAgent: 'T t@e.com', bucket: new TokenBucket(100, 100) });
  config = { thirteenF: [{ cik: '0001067983', name: 'Berkshire Hathaway Inc' }] };
  nock.disableNetConnect();
});
afterEach(() => { nock.cleanAll(); nock.enableNetConnect(); rmSync(dir, { recursive: true, force: true }); });

describe('runPipelineA', () => {
  it('fetches, parses, upserts one 13F entry', async () => {
    nock('https://data.sec.gov').get('/submissions/CIK0001067983.json').reply(200, {
      filings: { recent: { form: ['13F-HR'], filingDate: ['2026-05-15'], accessionNumber: ['0001067983-26-000123'], primaryDocument: ['form13fData.xml'], reportDate: ['2026-03-31'] } },
    });
    nock('https://www.sec.gov').get('/Archives/edgar/data/1067983/000106798326000123/form13fData.xml').reply(200, readFileSync(join(import.meta.dirname, '../fixtures/form13fData.xml'), 'utf8'));
    const r = await runPipelineA({
      httpClient, config, feedPath: join(dir, 'feed-13f.json'), statePath: join(dir, 'state-13f.json'),
    });
    expect(r.added).toBe(1);
    expect(r.errors).toEqual([]);
  });

  it('skips already-seen accession (state dedup)', async () => {
    nock('https://data.sec.gov').get('/submissions/CIK0001067983.json').reply(200, {
      filings: { recent: { form: ['13F-HR'], filingDate: ['2026-05-15'], accessionNumber: ['0001067983-26-000123'], primaryDocument: ['form13fData.xml'], reportDate: ['2026-03-31'] } },
    });
    // Pre-seed state
    const { writeStateJson } = await import('../../lib/store/state-json.js');
    writeStateJson(join(dir, 'state-13f.json'), { lastUpdated: 'x', seenFilings: { '0001067983-26-000123': 1 } });
    const r = await runPipelineA({
      httpClient, config, feedPath: join(dir, 'feed-13f.json'), statePath: join(dir, 'state-13f.json'),
    });
    expect(r.added).toBe(0);
  });

  it('captures error per CIK, continues with others', async () => {
    config = { thirteenF: [
      { cik: '0001067983', name: 'A' },
      { cik: '0000000001', name: 'B' },
    ]};
    nock('https://data.sec.gov').get('/submissions/CIK0001067983.json').reply(200, {
      filings: { recent: { form: ['13F-HR'], filingDate: ['2026-05-15'], accessionNumber: ['0001067983-26-000123'], primaryDocument: ['form13fData.xml'], reportDate: ['2026-03-31'] } },
    });
    nock('https://data.sec.gov').get('/submissions/CIK0000000001.json').reply(500);
    nock('https://www.sec.gov').get(/.*form13fData.xml.*/).reply(200, readFileSync(join(import.meta.dirname, '../fixtures/form13fData.xml'), 'utf8'));
    const r = await runPipelineA({ httpClient, config, feedPath: join(dir, 'feed-13f.json'), statePath: join(dir, 'state-13f.json') });
    expect(r.errors).toHaveLength(1);
    expect(r.errors[0].cik).toBe('0000000001');
  });
});
```

- [ ] **Step 2: Run test, verify it fails**

Run: `npm test -- tests/aggregate/pipeline-a.test.js`
Expected: FAIL with "Cannot find module".

- [ ] **Step 3: Implement pipeline-a**

```javascript
// lib/aggregate/pipeline-a.js
import { fetchLatest13FFilings } from '../edgar/fetch-submissions.js';
import { fetchThirteenFXml } from '../edgar/fetch-thirteen-f-xml.js';
import { parseThirteenF } from '../parsers/thirteen-f.js';
import { compute13FSummary } from '../compute/thirteen-f-summary.js';
import { readFeedJson, upsert13FFiling } from '../store/feed-json.js';
import { readStateJson, writeStateJson } from '../store/state-json.js';

export async function runPipelineA({ httpClient, config, feedPath, statePath }) {
  const state = readStateJson(statePath);
  const feed = readFeedJson(feedPath);
  const added = 0;
  let addedCount = 0;
  const errors = [];

  for (const filer of config.thirteenF) {
    try {
      const filings = await fetchLatest13FFilings(httpClient, filer.cik);
      for (const f of filings) {
        if (state.seenFilings[f.accessionNumber]) continue;
        const xml = await fetchThirteenFXml(httpClient, filer.cik, f.accessionNumber, f.primaryDocument);
        const holdings = parseThirteenF(xml);
        const priorFeedEntry = feed.thirteenF.find(e => e.filerCik === filer.cik && e.periodOfReport !== f.periodOfReport);
        const summary = compute13FSummary(holdings, priorFeedEntry?.holdings ?? []);
        const entry = {
          filerCik: filer.cik.padStart(10, '0'),
          filerName: filer.name,
          latestFilingDate: f.filingDate,
          latestFormType: f.formType,
          latestAccessionNumber: f.accessionNumber,
          periodOfReport: f.periodOfReport,
          history: [{ filingDate: f.filingDate, formType: f.formType, accessionNumber: f.accessionNumber }],
          holdings, summary,
        };
        upsert13FFiling(feedPath, entry);
        state.seenFilings[f.accessionNumber] = Date.now();
        addedCount++;
      }
    } catch (err) {
      errors.push({ cik: filer.cik, error: err.message });
    }
  }
  state.lastUpdated = new Date().toISOString();
  writeStateJson(statePath, state);
  return { added: addedCount, errors };
}
```

- [ ] **Step 4: Run test, verify it passes**

Run: `npm test -- tests/aggregate/pipeline-a.test.js`
Expected: 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add lib/aggregate/pipeline-a.js tests/aggregate/pipeline-a.test.js
git commit -m "feat(aggregate): pipeline A — 13F by CIK list"
```

---

### Task 3.2: Pipeline B (13D/G by form list)

**Files:**
- Create: `lib/aggregate/pipeline-b.js`
- Test: `tests/aggregate/pipeline-b.test.js`

**Interfaces:**
- `runPipelineB({ httpClient, config, feedDir, statePath, lookbackDays = 3 })` → `{ added, errors[] }`. For each form in `{SC 13D, SC 13D/A, SC 13G, SC 13G/A}`: search EDGAR for the lookback window, dedup via state, parse each primary doc, append to feed-13dg/<year>.ndjson.

- [ ] **Step 1: Write failing test**

```javascript
// tests/aggregate/pipeline-b.test.js
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import nock from 'nock';
import { mkdtempSync, rmSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { runPipelineB } from '../../lib/aggregate/pipeline-b.js';
import { createHttpClient } from '../../lib/http-client.js';
import { TokenBucket } from '../../lib/token-bucket.js';

let dir, httpClient, config;
beforeEach(() => {
  dir = mkdtempSync(join(tmpdir(), 'ftm-'));
  httpClient = createHttpClient({ userAgent: 'T t@e.com', bucket: new TokenBucket(100, 100) });
  config = { thirteenDG: { enabled: true, lookbackDays: 3 } };
  nock.disableNetConnect();
});
afterEach(() => { nock.cleanAll(); nock.enableNetConnect(); rmSync(dir, { recursive: true, force: true }); });

describe('runPipelineB', () => {
  it('appends new 13D and dedups via state', async () => {
    nock('https://efts.sec.gov')
      .get(/LATEST\/search-index.*forms=SC\+13D.*/)
      .reply(200, { hits: { hits: [{
        _source: { ciks: ['0000932470', '0001717393'], display_names: ['ICAHN CARL C', 'Jet.AI Inc'], file_date: '2026-06-20', form: 'SC 13D', adsh: '0000932470-26-000045', tickers: ['JTAI'] }
      }] } });
    nock('https://www.sec.gov')
      .get(/Archives\/edgar\/data\/932470\/000093247026000045\/primary_doc\.html/)
      .reply(200, readFileSync(join(import.meta.dirname, '../fixtures/13d-primary-doc.html'), 'utf8'));
    const r = await runPipelineB({ httpClient, config, feedDir: join(dir, 'feed-13dg'), statePath: join(dir, 'state-13dg.ndjson'), lookbackDays: 3 });
    expect(r.added).toBe(1);
    expect(r.errors).toEqual([]);
  });

  it('skips already-seen accession', async () => {
    const { appendStateNdjson } = await import('../../lib/store/state-ndjson.js');
    appendStateNdjson(join(dir, 'state-13dg.ndjson'), [{ accession: '0000932470-26-000045', seenAt: 1 }]);
    nock('https://efts.sec.gov')
      .get(/.*/).reply(200, { hits: { hits: [{ _source: { ciks: ['0000932470', '0001717393'], display_names: ['ICAHN CARL C', 'Jet.AI Inc'], file_date: '2026-06-20', form: 'SC 13D', adsh: '0000932470-26-000045', tickers: ['JTAI'] } }] } });
    const r = await runPipelineB({ httpClient, config, feedDir: join(dir, 'feed-13dg'), statePath: join(dir, 'state-13dg.ndjson'), lookbackDays: 3 });
    expect(r.added).toBe(0);
  });
});
```

- [ ] **Step 2: Run test, verify it fails**

Run: `npm test -- tests/aggregate/pipeline-b.test.js`
Expected: FAIL with "Cannot find module".

- [ ] **Step 3: Implement pipeline-b**

```javascript
// lib/aggregate/pipeline-b.js
import { fetchThirteenDGSearch } from '../edgar/fetch-thirteen-dg-search.js';
import { parseThirteenDG } from '../parsers/thirteen-dg.js';
import { readManifest, writeManifest } from '../store/manifest.js';
import { append13DFiling, read13DFilings } from '../store/feed-ndjson.js';
import { readStateNdjson, appendStateNdjson } from '../store/state-ndjson.js';

const FORMS = ['SC 13D', 'SC 13D/A', 'SC 13G', 'SC 13G/A'];

function isoDay(d) { return d.toISOString().slice(0, 10); }

export async function runPipelineB({ httpClient, config, feedDir, statePath, lookbackDays = 3 }) {
  if (!config.thirteenDG.enabled) return { added: 0, errors: [] };
  const today = new Date();
  const start = new Date(today.getTime() - lookbackDays * 86400000);
  const startDate = isoDay(start), endDate = isoDay(today);
  const manifest = readManifest(feedDir);
  const seen = new Set(readStateNdjson(statePath).map(e => e.accession));
  const errors = [];
  let added = 0;
  const newEntries = [];

  for (const formType of FORMS) {
    try {
      const hits = await fetchThirteenDGSearch(httpClient, { startDate, endDate, formType });
      for (const h of hits) {
        const s = h._source;
        const accession = s.adsh;
        if (seen.has(accession)) continue;
        // Fetch primary doc
        const cikNoPad = String(parseInt(s.ciks[0], 10));
        const accNoDash = accession.replace(/-/g, '');
        const docUrl = `https://www.sec.gov/Archives/edgar/data/${cikNoPad}/${accNoDash}/primary_doc.html`;
        const res = await httpClient.fetch(docUrl);
        if (!res.ok) throw new Error(`primary doc HTTP ${res.status}`);
        const html = await res.text();
        const parsed = parseThirteenDG(html, { formType });
        newEntries.push({
          filerCik: String(s.ciks[0]).padStart(10, '0'),
          filerName: (s.display_names?.[0]) ?? 'UNKNOWN',
          issuerCik: String(s.ciks[1] ?? '').padStart(10, '0'),
          issuerName: parsed.issuerName,
          issuerTicker: parsed.issuerTicker || (s.tickers?.[0] ?? ''),
          formType,
          filingDate: s.file_date,
          ownershipPercent: parsed.ownershipPercent,
          sharesOwned: parsed.sharesOwned,
          intent: parsed.intent,
          accessionNumber: accession,
          primaryDocUrl: docUrl,
        });
      }
    } catch (err) {
      errors.push({ formType, error: err.message });
    }
  }

  for (const entry of newEntries) {
    append13DFiling(feedDir, manifest, entry);
    added++;
  }
  if (newEntries.length > 0) {
    appendStateNdjson(statePath, newEntries.map(e => ({ accession: e.accessionNumber, seenAt: Date.now() })));
  }
  return { added, errors };
}
```

- [ ] **Step 4: Run test, verify it passes**

Run: `npm test -- tests/aggregate/pipeline-b.test.js`
Expected: 2 tests pass.

- [ ] **Step 5: Commit**

```bash
git add lib/aggregate/pipeline-b.js tests/aggregate/pipeline-b.test.js
git commit -m "feat(aggregate): pipeline B — 13D/G full-market scan"
```

---

### Task 3.3: aggregate.js entry script (GitHub Action runs this)

**Files:**
- Create: `scripts/aggregate.js`
- Test: `tests/scripts/aggregate.test.js`

**Interfaces:**
- Reads `SEC_EDGAR_USER_AGENT` env var. Loads `config/default-sources.json`. Runs pipeline A and B. Exits 0 on partial success (some errors but at least one added); exits 1 only on total failure (both pipelines crashed).

- [ ] **Step 1: Write failing test**

```javascript
// tests/scripts/aggregate.test.js
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import nock from 'nock';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

describe('aggregate.js (mocked, execSync)', () => {
  beforeEach(() => {
    process.env.SEC_EDGAR_USER_AGENT = 'T t@e.com';
    nock.disableNetConnect();
  });
  afterEach(() => { nock.cleanAll(); nock.enableNetConnect(); });

  it('fails with clear error if env var missing', async () => {
    delete process.env.SEC_EDGAR_USER_AGENT;
    const { execSync } = await import('node:child_process');
    expect(() => execSync('node scripts/aggregate.js', { stdio: 'pipe' })).toThrow(/SEC_EDGAR_USER_AGENT/);
  });

  it('exits 0 on partial success (one CIK 500, one OK)', async () => {
    nock('https://data.sec.gov').get('/submissions/CIK0001067983.json').reply(500);
    nock('https://efts.sec.gov').get(/.*/).reply(200, { hits: { hits: [] } });
    const { execSync } = await import('node:child_process');
    expect(() => execSync('node scripts/aggregate.js', { stdio: 'pipe' })).not.toThrow();
  });
});
```

- [ ] **Step 2: Run test, verify it fails**

Run: `npm test -- tests/scripts/aggregate.test.js`
Expected: FAIL with "Cannot find module".

- [ ] **Step 3: Implement aggregate.js**

```javascript
// scripts/aggregate.js
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { TokenBucket } from '../lib/token-bucket.js';
import { createHttpClient } from '../lib/http-client.js';
import { runPipelineA } from '../lib/aggregate/pipeline-a.js';
import { runPipelineB } from '../lib/aggregate/pipeline-b.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const config = JSON.parse(readFileSync(join(__dirname, '..', 'config', 'default-sources.json'), 'utf8'));

const UA = process.env.SEC_EDGAR_USER_AGENT;
if (!UA) {
  console.error('ERROR: SEC_EDGAR_USER_AGENT env var required (format: "AppName email@example.com")');
  process.exit(1);
}

async function main() {
  const httpClient = createHttpClient({ userAgent: UA, bucket: new TokenBucket(10, 10) });
  const a = await runPipelineA({
    httpClient, config,
    feedPath: 'feed-13f.json', statePath: 'state-13f.json',
  });
  console.log(`[aggregate] Pipeline A: added ${a.added} filings, ${a.errors.length} errors`);

  let b = { added: 0, errors: [] };
  if (config.thirteenDG.enabled) {
    b = await runPipelineB({
      httpClient, config,
      feedDir: 'feed-13dg', statePath: 'state-13dg.ndjson',
      lookbackDays: config.thirteenDG.lookbackDays ?? 3,
    });
    console.log(`[aggregate] Pipeline B: added ${b.added} filings, ${b.errors.length} errors`);
  }

  const totalErrors = (a.errors?.length ?? 0) + (b.errors?.length ?? 0);
  const totalAdded = (a.added ?? 0) + (b.added ?? 0);
  if (totalErrors > 0 && totalAdded === 0) {
    console.error('[aggregate] Total failure: no filings added');
    process.exit(1);
  }
  // Partial success → exit 0 so feed gets committed
}

main().catch(err => {
  console.error('[aggregate] Fatal:', err);
  process.exit(1);
});
```

- [ ] **Step 4: Run test, verify it passes**

Run: `npm test -- tests/scripts/aggregate.test.js`
Expected: 2 tests pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/aggregate.js tests/scripts/aggregate.test.js
git commit -m "feat(aggregate): entry script for GitHub Action"
```

---

## Phase 4: Local Scripts (run on user's machine)

### Task 4.1: prepare-digest.js

**Files:**
- Create: `scripts/prepare-digest.js`
- Test: `tests/scripts/prepare-digest.test.js`

**Interfaces:**
- Reads `feed-13f.json`, `feed-13dg/manifest.json`, current + previous year NDJSON. Filters by lookback (1 day for daily, 7 days for weekly; CLI flag). Emits unified JSON to stdout. Reads `~/.follow-the-money/config.json` for `frequency`.

- [ ] **Step 1: Write failing test**

```javascript
// tests/scripts/prepare-digest.test.js
import { describe, it, expect } from 'vitest';
import { execSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { mkdirSync, writeFileSync } from 'node:fs';

const __dirname = dirname(fileURLToPath(import.meta.url));

describe('prepare-digest.js', () => {
  it('emits JSON with lookbackDays applied', () => {
    const cwd = join(__dirname, '..', '..');
    const out = execSync('node scripts/prepare-digest.js --lookback 7', { cwd, encoding: 'utf8' });
    const j = JSON.parse(out);
    expect(j.lookbackDays).toBe(7);
    expect(j).toHaveProperty('thirteenF');
    expect(j).toHaveProperty('thirteenDG');
  });
});
```

- [ ] **Step 2: Run test, verify it fails**

Run: `npm test -- tests/scripts/prepare-digest.test.js`
Expected: FAIL with "Cannot find module" or non-zero exit.

- [ ] **Step 3: Implement prepare-digest.js**

```javascript
// scripts/prepare-digest.js
import { readFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import { filterByLookback } from '../lib/feed/filter-by-lookback.js';
import { readFeedJson } from '../lib/store/feed-json.js';
import { readManifest, read13DFilings } from '../lib/store/feed-ndjson.js';

const REPO = process.cwd();
const FEED_13F = join(REPO, 'feed-13f.json');
const FEED_13DG_DIR = join(REPO, 'feed-13dg');

const args = process.argv.slice(2);
const lookbackIdx = args.indexOf('--lookback');
const lookbackDays = lookbackIdx >= 0 ? Number(args[lookbackIdx + 1]) : 1;

const f13 = existsSync(FEED_13F) ? readFeedJson(FEED_13F) : { thirteenF: [] };
const manifest = existsSync(FEED_13DG_DIR) ? readManifest(FEED_13DG_DIR) : { years: {}, currentYear: new Date().getUTCFullYear() };
// Spec §NDJSON robustness: validate line counts on startup
import { validateManifest } from '../lib/store/feed-ndjson.js';
if (existsSync(FEED_13DG_DIR)) {
  const v = validateManifest(FEED_13DG_DIR, manifest);
  if (!v.ok) console.warn(`[prepare-digest] feed-13dg manifest mismatch: ${v.warnings.join('; ')}`);
}
const dgRaw = read13DFilings(FEED_13DG_DIR, manifest);
const dgFiltered = filterByLookback(dgRaw, { lookbackDays });

const f13Filtered = f13.thirteenF.filter(e => {
  const cutoff = new Date(Date.now() - lookbackDays * 86400000).toISOString().slice(0, 10);
  return e.latestFilingDate >= cutoff;
});

const out = {
  schemaVersion: 1,
  generatedAt: new Date().toISOString(),
  lookbackDays,
  thirteenF: f13Filtered,
  thirteenDG: dgFiltered,
  stats: {
    thirteenFFilings: f13Filtered.length,
    thirteenDGFilings: dgFiltered.length,
  },
};
process.stdout.write(JSON.stringify(out, null, 2));
```

- [ ] **Step 4: Run test, verify it passes**

Run: `npm test -- tests/scripts/prepare-digest.test.js`
Expected: 1 test passes.

- [ ] **Step 5: Commit**

```bash
git add scripts/prepare-digest.js tests/scripts/prepare-digest.test.js
git commit -m "feat(digest): prepare-digest.js (lookback filter, unified JSON output)"
```

---

### Task 4.2: check-alerts.js (DERIVED alert state)

**Files:**
- Create: `scripts/check-alerts.js`
- Test: `tests/scripts/check-alerts.test.js`

**Interfaces:**
- Reads `feed-13dg/manifest.json` + current year NDJSON. Reads `~/.follow-the-money/config.json` for `lastAlertTimestamp`. Filters to `SC 13D` / `SC 13D/A` with `filingDate > lastAlertTimestamp`. Merges 13D/A by (filer+issuer+day). Applies soft cap (≤ 8 detail, > 8 adds summary). Emits JSON `[{ formType, filerName, issuerName, issuerTicker, filingDate, count, summary, ownershipPercent, primaryDocUrl, accessionNumber }]`. **Does NOT update config** — that's done by the agent after successful delivery.

- [ ] **Step 1: Write failing test**

```javascript
// tests/scripts/check-alerts.test.js
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { execSync } from 'node:child_process';
import { mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { homedir } from 'node:os';

let fakeroot;
beforeEach(() => { fakeroot = mkdtempSync(join(tmpdir(), 'ftm-home-')); });
afterEach(() => { rmSync(fakeroot, { recursive: true, force: true }); });

describe('check-alerts.js', () => {
  it('emits alerts for new 13D/13D-A after lastAlertTimestamp', () => {
    writeFileSync(join(fakeroot, 'config.json'), JSON.stringify({ lastAlertTimestamp: '2026-01-01T00:00:00.000Z' }));
    const out = execSync(`HOME=${fakeroot} node scripts/check-alerts.js`, { encoding: 'utf8' });
    const alerts = JSON.parse(out);
    expect(Array.isArray(alerts)).toBe(true);
  });
});
```

- [ ] **Step 2: Run test, verify it fails**

Run: `npm test -- tests/scripts/check-alerts.test.js`
Expected: FAIL with "Cannot find module" or parse error.

- [ ] **Step 3: Implement check-alerts.js**

```javascript
// scripts/check-alerts.js
import { readFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import { homedir } from 'node:os';
import { readManifest, read13DFilings, validateManifest } from '../lib/store/feed-ndjson.js';
import { classify, ALERT_FORMS } from '../lib/alert/classify.js';
import { mergeByIssuer } from '../lib/feed/merge-by-issuer.js';
import { mergeAmendmentsForAlert } from '../lib/alert/merge-amendments.js';

const REPO = process.cwd();
const FEED_13DG_DIR = join(REPO, 'feed-13dg');
const CONFIG_PATH = join(homedir(), '.follow-the-money', 'config.json');

const config = existsSync(CONFIG_PATH) ? JSON.parse(readFileSync(CONFIG_PATH, 'utf8')) : {};
const lastAlert = config.lastAlertTimestamp || '1970-01-01T00:00:00.000Z';

const manifest = existsSync(FEED_13DG_DIR) ? readManifest(FEED_13DG_DIR) : { years: {}, currentYear: new Date().getUTCFullYear() };
// Spec §NDJSON robustness: validate line counts on startup
if (existsSync(FEED_13DG_DIR)) {
  const v = validateManifest(FEED_13DG_DIR, manifest);
  if (!v.ok) console.warn(`[check-alerts] feed-13dg manifest mismatch: ${v.warnings.join('; ')}`);
}
const raw = read13DFilings(FEED_13DG_DIR, manifest, { years: [manifest.currentYear] });
const newCritical = raw.filter(f => ALERT_FORMS.has(f.formType) && f.filingDate > lastAlert);
if (newCritical.length === 0) { process.stdout.write('[]'); process.exit(0); }

const groups = mergeByIssuer(newCritical);
const alerts = mergeAmendmentsForAlert(groups);

const DETAIL_CAP = 8;
let payload;
if (alerts.length <= DETAIL_CAP) {
  payload = { alerts, capped: false, summary: null };
} else {
  payload = { alerts: alerts.slice(0, DETAIL_CAP), capped: true, summary: `📊 另 ${alerts.length - DETAIL_CAP} 条 13D/G 详见 digest` };
}
process.stdout.write(JSON.stringify(payload, null, 2));
```

- [ ] **Step 4: Run test, verify it passes**

Run: `npm test -- tests/scripts/check-alerts.test.js`
Expected: 1 test passes.

- [ ] **Step 5: Commit**

```bash
git add scripts/check-alerts.js tests/scripts/check-alerts.test.js
git commit -m "feat(alerts): derived-state check-alerts.js with soft cap"
```

---

### Task 4.3: deliver.js

**Files:**
- Create: `scripts/deliver.js`
- Test: `tests/scripts/deliver.test.js`

**Interfaces:**
- `node scripts/deliver.js --text "..."` → delivers to stdout (always), plus Telegram or Email if configured. Reads `~/.follow-the-money/config.json` for delivery method. Reads `~/.follow-the-money/.env` for API keys (only if needed).

- [ ] **Step 1: Write failing test**

```javascript
// tests/scripts/deliver.test.js
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { execSync } from 'node:child_process';
import { mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

let fakeroot;
beforeEach(() => { fakeroot = mkdtempSync(join(tmpdir(), 'ftm-home-')); });
afterEach(() => { rmSync(fakeroot, { recursive: true, force: true }); });

describe('deliver.js', () => {
  it('writes to stdout for default config', () => {
    writeFileSync(join(fakeroot, 'config.json'), JSON.stringify({ delivery: { method: 'stdout' } }));
    const out = execSync(`HOME=${fakeroot} node scripts/deliver.js --text "hello"`, { encoding: 'utf8' });
    expect(out).toMatch(/hello/);
  });

  it('exits non-zero if method=telegram but env var missing', () => {
    writeFileSync(join(fakeroot, 'config.json'), JSON.stringify({ delivery: { method: 'telegram' } }));
    expect(() => execSync(`HOME=${fakeroot} node scripts/deliver.js --text "x"`, { stdio: 'pipe' })).toThrow(/TELEGRAM_BOT_TOKEN/);
  });
});
```

- [ ] **Step 2: Run test, verify it fails**

Run: `npm test -- tests/scripts/deliver.test.js`
Expected: FAIL with "Cannot find module".

- [ ] **Step 3: Implement deliver.js**

```javascript
// scripts/deliver.js
import { readFileSync, existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { homedir } from 'node:os';
import { config as loadEnv } from 'dotenv/config';

const CONFIG_PATH = join(homedir(), '.follow-the-money', 'config.json');
const ENV_PATH = join(homedir(), '.follow-the-money', '.env');
if (existsSync(ENV_PATH)) loadEnv({ path: ENV_PATH });

const args = process.argv.slice(2);
const textIdx = args.indexOf('--text');
const text = textIdx >= 0 ? args[textIdx + 1] : '';
if (!text) { console.error('ERROR: --text required'); process.exit(1); }

const config = existsSync(CONFIG_PATH) ? JSON.parse(readFileSync(CONFIG_PATH, 'utf8')) : { delivery: { method: 'stdout' } };
const method = config.delivery?.method ?? 'stdout';

if (method === 'stdout' || method === 'any') {
  console.log(text);
  process.exit(0);
}

if (method === 'telegram') {
  const token = process.env.TELEGRAM_BOT_TOKEN;
  const chatId = process.env.TELEGRAM_CHAT_ID;
  if (!token || !chatId) { console.error('ERROR: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID required'); process.exit(1); }
  const url = `https://api.telegram.org/bot${token}/sendMessage`;
  const res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ chat_id: chatId, text, parse_mode: 'Markdown' }) });
  if (!res.ok) { console.error(`Telegram HTTP ${res.status}: ${await res.text()}`); process.exit(1); }
  console.log(text);
  process.exit(0);
}

if (method === 'email') {
  const apiKey = process.env.RESEND_API_KEY;
  const to = process.env.EMAIL_TO;
  if (!apiKey || !to) { console.error('ERROR: RESEND_API_KEY and EMAIL_TO required'); process.exit(1); }
  const res = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${apiKey}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ from: 'follow-the-money@resend.dev', to, subject: 'follow-the-money digest', text }),
  });
  if (!res.ok) { console.error(`Resend HTTP ${res.status}: ${await res.text()}`); process.exit(1); }
  console.log(text);
  process.exit(0);
}

console.error(`Unknown delivery method: ${method}`);
process.exit(1);
```

- [ ] **Step 4: Add `dotenv` to dependencies (used only by deliver.js)**

```bash
npm install dotenv
```

- [ ] **Step 5: Run test, verify it passes**

Run: `npm test -- tests/scripts/deliver.test.js`
Expected: 2 tests pass.

- [ ] **Step 6: Commit**

```bash
git add scripts/deliver.js tests/scripts/deliver.test.js package.json package-lock.json
git commit -m "feat(deliver): stdout/Telegram/email with .env loading"
```

---

## Phase 5: Content (Prompts, References, SKILL.md)

### Task 5.1: Write the 5 prompt files

**Files:**
- Create: `prompts/digest-intro.md`
- Create: `prompts/format-13f.md`
- Create: `prompts/format-13dg.md`
- Create: `prompts/format-alert.md`
- Create: `prompts/translate.md`

**Interfaces:**
- Plain Markdown. Each loaded by the agent at runtime; no code.

- [ ] **Step 1: Write digest-intro.md**

```markdown
# Digest 整体规则

## 严格事实原则
- 每一句都必须在 feed 数据里有依据；不添加解释、预测或评论。
- 不出现"可能"、"也许"、"或将"等推测性词汇。

## 结构（严格按此顺序）
1. 一句话开头总结本期要点（不超过 30 字）
2. 📋 13F 板块（按 fund 排列）
3. 📊 13D/G 板块（按 filer 排列）
4. 末尾注明数据来源（feed-13f.json、feed-13dg/）

## 排版
- 标题用 `###` 三级
- 列表用 `-`
- 关键数字加粗 `**` 包裹
- 链接保留 SEC primary doc URL

## 长度
- 整体控制在 800 字以内（中文）
- 13F 段每个 fund 不超过 100 字
- 13D 段每条不超过 80 字；13G 段每条不超过 40 字
```

- [ ] **Step 2: Write format-13f.md**

```markdown
# 13F 写法

## 触发
`formType in {13F-HR, 13F-HR/A}` 且 `latestFilingDate` 在 lookback 窗口内。

## 单个基金 13F 输出模板
### {filerName}（Q1/Q2/Q3/Q4 {periodOfReport 年份}）

- 总持仓：{totalHoldingsCount} 只，价值 **${totalValueUsd 亿/M}**
- 新进：{newPositions.length} 只
- 清仓：{closedPositions.length} 只
- 加仓：{increasedPositions} 只
- 减仓：{decreasedPositions} 只

前 5 大持仓：
1. {issuerName}（{cusip}）— **{shares}** 股，价值 **${valueUsd 亿/M}**
2. ...（按 valueUsd 降序）

## 排序
fund 间按 `totalValueUsd` 降序。

## 简化规则
- 仅当 `newPositions` / `closedPositions` 非空时才列具体 cusip；否则只写计数。
- 单只基金持仓 ≤ 5 只时全部列出。
```

- [ ] **Step 3: Write format-13dg.md**

```markdown
# 13D/G 写法

## 触发
`formType in {SC 13D, SC 13D/A, SC 13G, SC 13G/A}` 且 `filingDate` 在 lookback 窗口内。

## 单条 13D 输出模板（active 投资者，重点写）
### {filerName} 举牌 {issuerName}（{ticker}）

- 持股比例：**{ownershipPercent}%**
- 持股数：{sharesOwned}
- 性质：active 投资（5% 阈值主动披露）
- 来源：[SEC 文件]({primaryDocUrl})

## 单条 13G 输出模板（passive 投资者，简写）
### {filerName} 披露 {issuerName}（{ticker}）{ownershipPercent}% 持仓

- 来源：[SEC 文件]({primaryDocUrl})

## 排序
13D 在前（按 filingDate 降序）；13G 在后（按 filingDate 降序）。

## 13D/A 多条合并
当 `count > 1` 时，追加一行：`修订 {count} 次，{summary}`
```

- [ ] **Step 4: Write format-alert.md**

```markdown
# Alert 写法

## 触发
由 `check-alerts.js` 产出；每条对应一次 13D 或一次合并后的 13D/A。

## 长度
单条 alert 不超过 80 字（中文）。

## 模板
🚨 **{filerName} 举牌 {issuerName}（{ticker}）**
- 持股：**{ownershipPercent}%**（{sharesOwned} 股）
- {if count > 1: 修订 {count} 次，{summary}}
- [SEC 文件]({primaryDocUrl})

## 严格规则
- 用 🚨 开头，不加 emoji 装饰
- 链接必须用 SEC primaryDocUrl
- 软上限超出时，附加 `📊 另 N 条 13D/G 详见 digest` 单行
```

- [ ] **Step 5: Write translate.md**

```markdown
# 翻译规则（en → zh）

## 保留原文（不译）
- 公司名（如 "APPLE INC"）
- CUSIP
- accession number
- SEC primary doc URL
- 英文公司名后的 ticker（`（AAPL）`）

## 翻译映射
- "shares" → "持股"
- "value" → "价值"
- "13F-HR" → 不译
- "13D" → "13D"（不译）
- "active" → "主动"
- "passive" → "被动"
- "activist" → "激进"
- "value investor" → "价值投资者"

## 数字格式
- 大数字用 `亿` / `万` / `千` 简写
- USD 用 `$` 前缀
- 百分比保留 1 位小数（`6.8%` 而非 `6.800%`）

## 句式
- 用陈述句，不用"我觉得"、"我认为"
- 时间用 `2026-06-20` ISO 格式
```

- [ ] **Step 6: Commit**

```bash
git add prompts/
git commit -m "feat(prompts): 5 prompt files (intro, 13F, 13D/G, alert, translate)"
```

---

### Task 5.2: Write the 8 reference files

**Files:**
- Create: `references/architecture.md`
- Create: `references/data-formats.md`
- Create: `references/edgar-fetching.md`
- Create: `references/alert-rules.md`
- Create: `references/onboarding.md`
- Create: `references/cron-setup.md`
- Create: `references/prompt-customization.md`
- Create: `references/delivery-setup.md`

**Interfaces:**
- Plain Markdown. Agent loads on demand. Each ≤ 200 lines.

- [ ] **Step 1: Write architecture.md**

(Include the 4-layer data flow, layer responsibilities, and key design decisions. Full content: see spec §Architecture.)

- [ ] **Step 2: Write data-formats.md**

(Include the schemas for feed-13f.json, feed-13dg/manifest.json, feed-13dg/<year>.ndjson, state-13f.json, state-13dg.ndjson. Field naming conventions. NDJSON robustness rules.)

- [ ] **Step 3: Write edgar-fetching.md**

(API endpoints, User-Agent requirement, rate limit handling, error fallbacks, parser notes.)

- [ ] **Step 4: Write alert-rules.md**

(Trigger conditions, three-level strategy, soft cap, intent-by-form-type, dedup via derived state, push timing, failure handling.)

- [ ] **Step 5: Write onboarding.md (8 steps)**

(Detailed 8-step onboarding flow per spec §Onboarding. Includes: introduction, frequency, time+timezone, delivery method, language, API keys, show sources, settings reminder, cron setup, welcome digest.)

- [ ] **Step 6: Write cron-setup.md**

(Per-OS crontab examples: macOS, Linux, Windows Task Scheduler. Includes how to set `FTM_SKILL_DIR` env var pointing to the repo root.)

- [ ] **Step 7: Write prompt-customization.md**

```markdown
# 自定义 Prompt

## 步骤
1. 在用户目录创建 `~/.follow-the-money/prompts/`（如果不存在）
2. 拷贝你想修改的 prompt：
   - macOS / Linux:
     ```bash
     mkdir -p ~/.follow-the-money/prompts
     cp $FTM_SKILL_DIR/prompts/format-13f.md ~/.follow-the-money/prompts/format-13f.md
     ```
   - Windows (PowerShell):
     ```powershell
     New-Item -ItemType Directory -Force -Path $env:USERPROFILE\.follow-the-money\prompts
     Copy-Item $env:FTM_SKILL_DIR\prompts\format-13f.md $env:USERPROFILE\.follow-the-money\prompts\format-13f.md
     ```
3. 编辑用户副本
4. 下次运行 digest 时会自动优先用用户版本

> **注意：** `FTM_SKILL_DIR` 必须是绝对路径指向本仓库根目录。
> 加载顺序：用户 `~/.follow-the-money/prompts/<file>.md` > 仓库 `prompts/<file>.md`。
```

- [ ] **Step 8: Write delivery-setup.md**

(Telegram: create bot via @BotFather, set TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID in `~/.follow-the-money/.env`. Email: Resend API key, EMAIL_TO, sender domain. Step-by-step for each.)

- [ ] **Step 9: Commit**

```bash
git add references/
git commit -m "docs(references): 8 deep-dive reference files"
```

---

### Task 5.3: Write SKILL.md (~100 lines, agent-agnostic)

**Files:**
- Create: `SKILL.md`

**Interfaces:**
- Frontmatter with `description` (used by agent to trigger). Concise. Agent loads on every run. **Zero agent brand names.**

- [ ] **Step 1: Write SKILL.md**

```markdown
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

## Daily path (cron or `/money`)

1. **Load config** from `~/.follow-the-money/config.json`. If missing or `onboardingComplete: false`, run onboarding (see `references/onboarding.md`).
2. **Prepare digest**:
   ```bash
   node scripts/prepare-digest.js --lookback 1
   ```
   Reads `feed-13f.json` + `feed-13dg/manifest.json` + current year NDJSON, filters by lookback, emits unified JSON to stdout.
3. **Render**: apply `prompts/digest-intro` + `prompts/format-13f` + `prompts/format-13dg` + `prompts/translate` (if `config.language != 'en'`) to the JSON. Output is a Markdown digest.
4. **Deliver**:
   ```bash
   node scripts/deliver.js --text "<digest>"
   ```
5. **Check alerts** (always, in parallel):
   ```bash
   node scripts/check-alerts.js
   ```
   For each alert, apply `prompts/format-alert` and deliver individually.
6. **Update state** (after successful delivery): atomically write the latest alert's `filingDate` back to `config.lastAlertTimestamp`.

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
```

- [ ] **Step 2: Verify no agent names**

```bash
grep -iE "openclaw|claude code|cursor|codex|copilot|gemini" SKILL.md
```

Expected: no output (empty result).

- [ ] **Step 3: Verify line count**

Run: `wc -l SKILL.md`
Expected: between 80 and 130 lines.

- [ ] **Step 4: Commit**

```bash
git add SKILL.md
git commit -m "docs(skill): concise agent-agnostic SKILL.md (~100 lines)"
```

---

## Phase 6: Evals

### Task 6.1: Write evals/evals.json (machine-checkable)

**Files:**
- Create: `evals/evals.json`
- Create: `scripts/eval.js`
- Test: `tests/scripts/eval.test.js`

**Interfaces:**
- Each entry: `{ id, prompt, description, checks[] }`. Supported check types: `contains`, `not_contains`, `regex`, `min_length`, `max_length`, `json_field_exists`, `json_field_equals`, `contains_url_from`.
- `scripts/eval.js` reads evals.json, runs each prompt through the agent (or, for CI, uses a deterministic stub), runs the checks, reports pass/fail, exits non-zero on any fail.

- [ ] **Step 1: Write evals.json**

```json
{
  "schemaVersion": 1,
  "evals": [
    {
      "id": 1,
      "prompt": "/money",
      "description": "Daily digest — must include 13F section emoji, 13D/G section emoji, and at least one SEC URL",
      "checks": [
        { "type": "contains", "value": "📋", "description": "13F section emoji" },
        { "type": "regex", "pattern": "https://www\\.sec\\.gov/.*primaryDoc.*", "description": "SEC primary doc URL" },
        { "type": "min_length", "value": 200, "description": "non-trivial digest" }
      ]
    },
    {
      "id": 2,
      "prompt": "/alerts",
      "description": "Alert check — must mention at least one filer, ticker, and primary doc URL when alerts exist",
      "checks": [
        { "type": "regex", "pattern": "🚨|举牌|披露", "description": "alert language marker" },
        { "type": "regex", "pattern": "https://www\\.sec\\.gov/.*primaryDoc.*", "description": "SEC URL" }
      ]
    },
    {
      "id": 3,
      "prompt": "show my settings",
      "description": "Config read — must show frequency, delivery method, language",
      "checks": [
        { "type": "contains", "value": "frequency", "description": "frequency field shown" },
        { "type": "contains", "value": "delivery", "description": "delivery field shown" },
        { "type": "contains", "value": "language", "description": "language field shown" }
      ]
    },
    {
      "id": 4,
      "prompt": "switch to weekly",
      "description": "Config change — must write frequency=weekly and confirm",
      "checks": [
        { "type": "regex", "pattern": "weekly", "description": "weekly reflected" },
        { "type": "not_contains", "value": "error", "description": "no error" }
      ]
    },
    {
      "id": 5,
      "prompt": "/money --lookback 7",
      "description": "Weekly lookback — digest must cover 7 days of 13F",
      "checks": [
        { "type": "min_length", "value": 400, "description": "weekly digest is longer" },
        { "type": "regex", "pattern": "Q1|Q2|Q3|Q4", "description": "quarter reference present" }
      ]
    }
  ]
}
```

- [ ] **Step 2: Write scripts/eval.js**

```javascript
// scripts/eval.js
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { execSync } from 'node:child_process';

const __dirname = dirname(fileURLToPath(import.meta.url));
const evalsPath = join(__dirname, '..', 'evals', 'evals.json');
const data = JSON.parse(readFileSync(evalsPath, 'utf8'));

function runChecks(output, checks) {
  const results = [];
  for (const c of checks) {
    let pass = false, detail = '';
    try {
      if (c.type === 'contains') pass = output.includes(c.value);
      else if (c.type === 'not_contains') pass = !output.includes(c.value);
      else if (c.type === 'regex') pass = new RegExp(c.pattern, 's').test(output);
      else if (c.type === 'min_length') pass = output.length >= c.value;
      else if (c.type === 'max_length') pass = output.length <= c.value;
      else if (c.type === 'json_field_exists') {
        const j = JSON.parse(output); pass = c.field.split('.').reduce((o, k) => o?.[k], j) !== undefined;
      } else if (c.type === 'json_field_equals') {
        const j = JSON.parse(output); pass = c.field.split('.').reduce((o, k) => o?.[k], j) === c.value;
      } else if (c.type === 'contains_url_from') {
        pass = output.includes(c.value);
      } else { pass = false; detail = `unknown check type: ${c.type}`; }
    } catch (e) { pass = false; detail = e.message; }
    results.push({ check: c.description, pass, detail });
  }
  return results;
}

// For CI: invoke a deterministic stub that calls the digest script and returns its output.
// Real agent invocation would replace this with the actual agent call.
function invokeAgent(prompt) {
  if (prompt.startsWith('/money')) {
    try { return execSync('node scripts/prepare-digest.js', { encoding: 'utf8' }); }
    catch { return ''; }
  }
  return '';
}

let totalPass = 0, totalFail = 0;
for (const e of data.evals) {
  const out = invokeAgent(e.prompt);
  const results = runChecks(out, e.checks);
  const failed = results.filter(r => !r.pass);
  const status = failed.length === 0 ? '✓' : '✗';
  console.log(`${status} Eval #${e.id}: ${e.description}`);
  for (const r of results) {
    console.log(`    ${r.pass ? '✓' : '✗'} ${r.check}${r.detail ? ' — ' + r.detail : ''}`);
  }
  if (failed.length === 0) totalPass++; else totalFail++;
}
console.log(`\nResult: ${totalPass} passed, ${totalFail} failed`);
process.exit(totalFail === 0 ? 0 : 1);
```

- [ ] **Step 3: Write a smoke test**

```javascript
// tests/scripts/eval.test.js
import { describe, it, expect } from 'vitest';
import { execSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));

describe('eval.js (CI stub mode)', () => {
  it('runs and reports results', () => {
    const out = execSync('node scripts/eval.js', { cwd: join(__dirname, '..', '..'), encoding: 'utf8' });
    expect(out).toMatch(/Result: \d+ passed, \d+ failed/);
  });
});
```

- [ ] **Step 4: Run**

Run: `npm test -- tests/scripts/eval.test.js && node scripts/eval.js`
Expected: smoke test passes, eval runner reports results (some checks may fail with the empty stub — that's expected; the framework works).

- [ ] **Step 5: Commit**

```bash
git add evals/evals.json scripts/eval.js tests/scripts/eval.test.js
git commit -m "feat(evals): 5 sample evals with machine-checkable checks[]"
```

---

## Phase 7: GitHub Action

### Task 7.1: Write the workflow file

**Files:**
- Create: `.github/workflows/aggregate.yml`

**Interfaces:**
- Twice-daily cron (08:00 ET = `0 12 * * *` UTC, 20:00 ET = `0 0 * * *` UTC). Manual `workflow_dispatch`. Runs `node scripts/aggregate.js` then commits `feed-13f.json`, `feed-13dg/`, `state-13f.json`, `state-13dg.ndjson` if changed.

- [ ] **Step 1: Write the workflow**

```yaml
name: Aggregate SEC Filings

on:
  schedule:
    - cron: '0 12 * * *'   # 08:00 ET (winter) — UTC offset may shift; cron uses UTC
    - cron: '0 0 * * *'    # 20:00 ET
  workflow_dispatch:

permissions:
  contents: write

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

- [ ] **Step 2: Validate YAML**

Run: `node -e "const y=require('fs').readFileSync('.github/workflows/aggregate.yml','utf8'); console.log('lines:',y.split('\n').length)"`
Expected: prints line count, no error.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/aggregate.yml
git commit -m "ci: twice-daily cron aggregate workflow"
```

---

## Phase 8: Documentation and Final Integration

### Task 8.1: Write README.md and LICENSE

**Files:**
- Create: `README.md`
- Create: `LICENSE`

- [ ] **Step 1: Write LICENSE (MIT)**

```
MIT License

Copyright (c) 2026 follow-the-money contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 2: Write README.md**

```markdown
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
git clone https://github.com/<your-org>/follow-the-money
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
node scripts/prepare-digest.js --lookback 7
node scripts/deliver.js --text "$(cat digest.txt)"
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
```

- [ ] **Step 3: Commit**

```bash
git add README.md LICENSE
git commit -m "docs: README + MIT license"
```

---

### Task 8.2: Final integration test

**Files:**
- Create: `tests/integration.test.js`

**Interfaces:**
- End-to-end: stub EDGAR, run aggregator, then run digest + alerts locally, assert all outputs are non-empty and well-formed.

- [ ] **Step 1: Write the integration test**

```javascript
// tests/integration.test.js
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import nock from 'nock';
import { execSync } from 'node:child_process';
import { mkdtempSync, rmSync, writeFileSync, readFileSync, existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

let workdir, homedir;
beforeEach(() => {
  workdir = mkdtempSync(join(tmpdir(), 'ftm-int-'));
  homedir = mkdtempSync(join(tmpdir(), 'ftm-home-'));
  writeFileSync(join(homedir, 'config.json'), JSON.stringify({ lastAlertTimestamp: '1970-01-01T00:00:00.000Z' }));
  nock.disableNetConnect();
});
afterEach(() => { nock.cleanAll(); nock.enableNetConnect(); rmSync(workdir, { recursive: true, force: true }); rmSync(homedir, { recursive: true, force: true }); });

describe('integration: aggregate → digest → alert', () => {
  it('produces a digest and an alert from stubbed EDGAR', async () => {
    // Stub 13F
    nock('https://data.sec.gov').get('/submissions/CIK0001067983.json').reply(200, {
      filings: { recent: { form: ['13F-HR'], filingDate: ['2026-05-15'], accessionNumber: ['0001067983-26-000123'], primaryDocument: ['form13fData.xml'], reportDate: ['2026-03-31'] } },
    });
    nock('https://www.sec.gov').get(/Archives\/edgar\/data\/1067983\/000106798326000123\/form13fData\.xml/).reply(200, readFileSync(join(import.meta.dirname, 'fixtures/form13fData.xml'), 'utf8'));
    // Stub 13D search
    nock('https://efts.sec.gov').get(/LATEST\/search-index.*/).reply(200, { hits: { hits: [{ _source: { ciks: ['0000932470', '0001717393'], display_names: ['ICAHN CARL C', 'Jet.AI Inc'], file_date: '2026-06-20', form: 'SC 13D', adsh: '0000932470-26-000045', tickers: ['JTAI'] } }] } });
    nock('https://www.sec.gov').get(/Archives\/edgar\/data\/932470\/000093247026000045\/primary_doc\.html/).reply(200, readFileSync(join(import.meta.dirname, 'fixtures/13d-primary-doc.html'), 'utf8'));

    // Run aggregator
    execSync('SEC_EDGAR_USER_AGENT="T t@e.com" node scripts/aggregate.js', { cwd: workdir, env: { ...process.env, SEC_EDGAR_USER_AGENT: 'T t@e.com' }, encoding: 'utf8' });

    // Assert feed files were written
    expect(existsSync(join(workdir, 'feed-13f.json'))).toBe(true);
    expect(existsSync(join(workdir, 'feed-13dg', 'manifest.json'))).toBe(true);
    expect(existsSync(join(workdir, 'feed-13dg', '2026.ndjson'))).toBe(true);

    // Run digest
    const digestOut = execSync('node scripts/prepare-digest.js --lookback 7', { cwd: workdir, encoding: 'utf8' });
    const digest = JSON.parse(digestOut);
    expect(digest.thirteenF.length).toBeGreaterThan(0);
    expect(digest.thirteenDG.length).toBeGreaterThan(0);

    // Run alerts
    const alertOut = execSync(`HOME=${homedir} node scripts/check-alerts.js`, { cwd: workdir, encoding: 'utf8' });
    const payload = JSON.parse(alertOut);
    expect(payload.alerts.length).toBeGreaterThan(0);
    expect(payload.alerts[0].filerName).toBeTruthy();
  });
});
```

- [ ] **Step 2: Run integration test**

Run: `npm test -- tests/integration.test.js`
Expected: 1 test passes.

- [ ] **Step 3: Run the full test suite**

Run: `npm test`
Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add tests/integration.test.js
git commit -m "test(integration): end-to-end aggregate → digest → alerts"
```

---

## Self-Review

After completing all tasks, the implementer should re-verify against the spec:

**1. Spec coverage** — every section in `docs/superpowers/specs/2026-06-24-follow-the-money-design.md` maps to a task:

| Spec section | Task(s) |
|---|---|
| Overview / Why | SKILL.md, README (5.3, 8.1) |
| 4-layer Architecture | 3.3, 5.3, references/architecture.md (5.2) |
| 8 CIKs + verification gate | 1.1, 1.3 |
| Data Formats (feed-13f.json, feed-13dg/, manifest, state) | 2.8, 2.9, 2.10, 2.11 |
| 13F-HR/A overwrite + history | 2.10 |
| Three-level alert + soft cap | 2.14, 2.15, 4.2 |
| Intent by form type (no Item 4 regex) | 2.7 |
| Derived alert state | 4.2 |
| Atomic NDJSON writes | 2.9, 2.10, 2.11 |
| Prompts | 5.1 |
| References | 5.2 |
| SKILL.md architecture (~100 lines) | 5.3 |
| Testing (vitest + nock) | every task |
| verify-edgar.js | 1.3 |
| evals.json + eval.js | 6.1 |
| GitHub Action (cron × 2) | 7.1 |
| README + LICENSE | 8.1 |
| Out of Scope | README "Limitations" (8.1) |

**2. Placeholder scan** — no "TBD", "TODO", "implement later", "add appropriate error handling", "fill in details" appear in any task. Every step with code shows the actual code.

**3. Type consistency** — function signatures match across tasks:
- `fetchLatest13FFilings(httpClient, cik)` (2.3) → consumed by pipeline-a (3.1)
- `fetchThirteenFXml(httpClient, cik, accessionNumber, primaryDocument)` (2.3) → consumed by pipeline-a (3.1)
- `parseThirteenF(xml)` (2.4) → consumed by pipeline-a (3.1)
- `compute13FSummary(current, prior)` (2.5) → consumed by pipeline-a (3.1)
- `fetchThirteenDGSearch(httpClient, { startDate, endDate, formType })` (2.6) → consumed by pipeline-b (3.2)
- `parseThirteenDG(html, { formType })` (2.7) → consumed by pipeline-b (3.2)
- `readStateJson/writeStateJson(path, state)` (2.8) → consumed by pipeline-a (3.1)
- `appendStateNdjson(path, entries)` (2.9) → consumed by pipeline-b (3.2)
- `readFeedJson/writeFeedJson/upsert13FFiling/upsert13FFiling` (2.10) → consumed by pipeline-a (3.1) and prepare-digest (4.1)
- `readManifest/writeManifest/append13DFiling/read13DFilings/validateManifest` (2.11) → consumed by pipeline-b (3.2), prepare-digest (4.1), check-alerts (4.2)
- `filterByLookback(items, { lookbackDays, now })` (2.12) → consumed by prepare-digest (4.1)
- `mergeByIssuer(entries)` (2.13) → consumed by merge-amendments (2.15)
- `classify(entry) / ALERT_FORMS` (2.14) → consumed by check-alerts (4.2)
- `mergeAmendmentsForAlert(groups)` (2.15) → consumed by check-alerts (4.2)
- `runPipelineA({ httpClient, config, feedPath, statePath })` (3.1) → consumed by aggregate.js (3.3)
- `runPipelineB({ httpClient, config, feedDir, statePath, lookbackDays })` (3.2) → consumed by aggregate.js (3.3)

If any task reference is missing, the implementer must add it before claiming completion.

## Execution Handoff

After the implementer finishes all 26 tasks (0.1 → 8.2), they should:

1. Run the full suite: `npm test` — all green.
2. Run pre-launch verify: `npm run verify-edgar` (with real `SEC_EDGAR_USER_AGENT`).
3. Tag a release: `git tag v0.1.0`.
4. Hand off to user for cron / GitHub Action setup.

For execution options, see the writing-plans skill output: **subagent-driven development** (recommended, fresh subagent per task with two-stage review) or **inline execution** (executing-plans skill, batch with checkpoints).

---

---

---

---

---

---

---

---

</new_string>