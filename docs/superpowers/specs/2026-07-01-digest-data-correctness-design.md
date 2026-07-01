# Digest Data Correctness — Design Spec

**Date:** 2026-07-01
**Status:** Draft (post-brainstorming, pre-implementation)
**Scope:** Sub-project A of the post-digest improvement backlog
**Implementation plan:** TBD (will be created via writing-plans skill)

---

## Overview

### Purpose

Make the 13F digest output **internally consistent in `valueUsd` units** and **enriched with period-over-period diff** (new/closed positions). Without this, the digest shows portfolio totals that are off by 1000× for some filers, and never shows what the manager actually bought or sold.

### Why

The 2026-07-01 manual `/money` trigger surfaced two real bugs in the digest path:

1. **Baupost Group** portfolio renders as $5.1M when it should be ~$5B (1000× too small).
2. **Every filer** shows `increasedPositions / decreasedPositions / newPositions / closedPositions` as `undefined` — the digest reader never computes the diff.

Both are silent — the digest renders fine, the user just gets wrong numbers and no insight.

### Non-goals

- **Re-parsing EDGAR or re-running the aggregator.** Existing `feed-13f.json` is the source of truth; fixes are entirely in the reader/enrichment path.
- **Per-filer units config table.** Edge detector infers units at runtime; we don't author a units map.
- **Backfilling historical filings.** Older periods (<2022-12-31) have varying magnitudes that the detector handles ad hoc; not part of this spec.
- **Scion Q4 2025 missing filing.** Investigated and confirmed upstream (Scion has not filed since 2025-09-30; likely AUM dropped below $100M). Not our bug; not in scope.

### Out of scope (will be brainstormed separately)

- Renderer dedup (Top N grouping by issuer) — sub-project B
- Prompts infrastructure (`~/.follow-the-money/prompts/`) — sub-project C
- Coatue multi-period handling in renderer — sub-project B

---

## Background — what the data actually looks like

Pulled 2026-07-01 from `feed-13f.json` (374 filings, 36980 holdings, all 8 tracked CIKs):

```
Filer                     | periodOfReport | raw valueUsd sum  | in dollars
--------------------------|----------------|-------------------|-------------
Berkshire Hathaway Inc    | 2026-03-31     |   263,095,703,570 | ~$263B  ✓
Pershing Square Capital   | 2026-03-31     |    13,714,299,861 | ~$13.7B ✓
Baupost Group             | 2026-03-31     |         5,115,380 | ~$5M    ✗ (×1000 too small)
Oaktree Capital Mgmt      | 2026-03-31     |     6,557,119,230 | ~$6.6B  ✓
ARK Investment Mgmt       | 2026-03-31     |    12,859,485,476 | ~$12.9B ✓
Tiger Global Management   | 2026-03-31     |    22,845,413,829 | ~$22.8B ✓
Coatue Management         | 2026-03-31     |    29,056,031,305 | ~$29B   ✓
Scion Asset Management    | (last) 2025-09 |     1,381,198,076 | ambiguous — see below
```

**Root cause (Bug 1):** SEC EDGAR's 13F informationTable XML `<value>` field is **officially in thousands of dollars** per the Form 13F DataFeed schema. Most filers conform and emit thousands; a few (notably Baupost) appear to emit raw dollars, OR vice-versa — the parser at `lib/parsers/thirteen-f.js:41` (`pickInt(pickTag(block, 'value'))`) does no conversion, so the units are whatever EDGAR returned.

**Per-filer inconsistency is empirical**, not date-bounded — the same period (2026-03-31) shows both formats in our feed.

**Scion ambiguity:** 2025-09-30 raw sum is $1,381,198,076. If thousands: ~$1.4B portfolio (small but plausible for a deep-value shop). If dollars: ~$1.4B (same answer, but by coincidence). The detector must handle this case without false-positive ×1000.

---

## Architecture

### Layer placement

```
scripts/prepare-digest.js   ← entry point (existing)
        │
        ▼
lib/enrich/                 ← new directory
  ├── normalize-value-units.js
  └── period-diff.js
        │
        ▼
lib/compute/thirteen-f-summary.js   ← existing (already used by pipeline-a)
```

`prepare-digest.js` adds an `enrichFilers(filerEntries)` step that runs the two new enrichers in order. No change to `lib/parsers/`, `lib/store/`, `lib/aggregate/`.

### Data flow

```
feed-13f.json (raw, mixed units)
  │
  ▼ readFeedJson()
  │
  ▼ filterByLookback(90d)
  │
  ▼ enrichFilers()
  │   1. normalizeValueUnits(filer) → adds valueUnit, valueUnitAdjusted
  │   2. periodDiff(filer, history)  → adds summary {newPositions, closedPositions, increasedPositions, decreasedPositions}
  │
  ▼ emit JSON to stdout
```

---

## Component 1: `lib/enrich/normalize-value-units.js`

### Public API

```js
export function normalizeValueUnits(filerEntry, config) → filerEntry
```

- **Input:** one entry from `feed-13f.json.thirteenF[]` (shape: `{filerName, filerCik, periodOfReport, latestFilingDate, holdings[], history[]}`) plus `config.thirteenF[]` (the source list with `style` and `name`).
- **Output:** same shape plus:
  - `valueUnit: 'dollars' | 'thousands'` (always set)
  - `valueUnitAdjusted: true` (only set when detector overrode the raw value; absent when raw is already plausible)
  - `holdings[]` with `valueUsd` recomputed if adjusted
- **Pure function.** No I/O. Same input → same output.

### Detector algorithm

```
sum = holdings.reduce((s, h) => s + h.valueUsd, 0)
matchedSource = config.thirteenF.find(s => s.cik === filerEntry.filerCik)
explicitlySmall = matchedSource?.style === 'small-fund'  // opt-in escape hatch

if (explicitlySmall) {
  // Tagged in config: leave raw, do not infer
  return { ...entry, valueUnit: 'unknown' }
} else if (sum < 1_000_000_000) {  // sum < $1B for a non-tagged fund
  // Treat as thousands → ×1000
  entry.holdings = entry.holdings.map(h => ({...h, valueUsd: h.valueUsd * 1000}))
  entry.valueUnit = 'thousands'
  entry.valueUnitAdjusted = true
  return entry
} else {
  entry.valueUnit = 'dollars'
  return entry
}
```

### Edge cases

| Case | Detector behavior | Reasoning |
|---|---|---|
| Berkshire-style ~$263B raw | keep as `dollars` | sum ≥ $1B → confident in dollars |
| Baupost ~$5M raw | ×1000 → $5.1B → `thousands` | sum < $1B → likely thousands |
| Scion ~$1.4B raw (ambiguous) | keep as `dollars` | sum ≥ $1B → don't risk ×1000 |
| Genuinely tiny fund tagged `style: 'small-fund'` | unchanged, `valueUnit: 'unknown'` | explicit opt-out; detector stays passive |
| Genuinely tiny fund NOT tagged ($50M raw, no tag) | ×1000 → $50B | sum < $1B → default ×1000 path fires |
| All-zero `holdings: []` (late/amended filing) | unchanged, `valueUnit: 'dollars'` (default) | detector doesn't fire on empty (`sum === 0`) |

### Why `$1B` threshold (and explicit `style: 'small-fund'` escape hatch)

- **$1B**: Below this, a major fund's portfolio sum is implausible in raw dollars (Berkshire/Tiger/Coatue all comfortably above). The cutoff catches Baupost-style thousands bug without misfiring on legitimately small portfolios.
- **`style: 'small-fund'`**: Explicit opt-out for genuinely small funds (none currently tagged, but the escape hatch exists). Tagged funds get `valueUnit: 'unknown'` and no transformation.

Threshold is heuristic. If a tracked fund ever sits between $1B and ~$1T with non-conforming units, the detector would silently keep the wrong values. The `style` field mitigates that risk by giving config authors an explicit override.

### Error handling

- `holdings` missing or non-array → return entry unchanged, log warning to stderr, do not throw.
- `filerCik` not in `config.thirteenF[]` → treat as `style: 'unknown'`, default dollar heuristic, no `smallFund` override.

---

## Allowed renderer-side change (per brainstorming decision Q5)

The digest renderer is out of scope for this spec's **detection / enrichment logic**. However, one minimal renderer change is permitted to keep the digest honest with users:

- After rendering the per-filer sections, render a footer line:
  > *Unit adjustments: <comma-separated list of `diagnostics.valueUnitsAdjusted`> were inferred as thousands-of-dollars (×1000). Raw feed values were inconsistent per filer.*

This change is additive (existing digest structure unchanged) and exists so users see when a portfolio total was auto-corrected. Defer per-row annotations to sub-project B.

---

## Component 2: `lib/enrich/period-diff.js`

### Public API

```js
export function periodDiff(filerEntry, allFilings) → filerEntry
```

- **Input:** filer entry (post-`normalizeValueUnits`) + full feed array (so we can find the prior period).
- **Output:** same shape plus:
  - `summary: { newPositions: [], closedPositions: [], increasedPositions: int, decreasedPositions: int, totalValueUsd: int, priorTotalValueUsd: int, deltaPct: number }`
  - `summary: null` if prior period not found (with warning)

### Algorithm

```
priorEntry = allFilings
  .filter(e => e.filerCik === filerEntry.filerCik
            && e.periodOfReport < filerEntry.periodOfReport)
  .sort((a, b) => b.periodOfReport.localeCompare(a.periodOfReport))[0]

if (!priorEntry) return { ...filerEntry, summary: null }

summary = compute13FSummary(filerEntry.holdings, priorEntry.holdings)
return { ...filerEntry, summary }
```

`compute13FSummary` already exists at `lib/compute/thirteen-f-summary.js` and is battle-tested in `pipeline-a` (commit `a4153db`). We reuse it as-is.

### Edge cases

| Case | Behavior |
|---|---|
| No prior period in feed (first-ever filing) | `summary: null` + warning |
| Prior period has 0 holdings (late/amended) | `compute13FSummary` returns zeros — fine |
| Coatue filed Q4 2025 + Q1 2026 in same week | Diff runs against immediately prior Q4 2025; correct |
| Filer appears multiple times with same `periodOfReport` (duplicate run) | Diff uses `sort().[0]` which is the latest `latestFilingDate`; correct |
| Per-CIK diff only — never cross-CIK (Scion vs ARK) | Coded |

---

## Integration: `scripts/prepare-digest.js`

### Change scope (single function addition)

```js
import { normalizeValueUnits } from '../lib/enrich/normalize-value-units.js';
import { periodDiff } from '../lib/enrich/period-diff.js';
import defaultSources from '../config/default-sources.json' with { type: 'json' };

// ... existing code that builds f13Filtered ...

const enriched = f13Filtered
  .map(f => normalizeValueUnits(f, defaultSources))
  .map(f => periodDiff(f, f13.thirteenF));

const out = {
  schemaVersion: 1,
  generatedAt: new Date().toISOString(),
  lookbackDays,
  thirteenF: enriched,
  thirteenDG: dgFiltered,
  stats: {
    thirteenFFilings: enriched.length,
    thirteenDGFilings: dgFiltered.length,
  },
  // NEW: aggregate stats for surfaceability
  diagnostics: {
    valueUnitsAdjusted: enriched.filter(f => f.valueUnitAdjusted).map(f => f.filerName),
    summaryMissing: enriched.filter(f => f.summary === null).map(f => f.filerName),
  },
};
```

### Output schema additions

```jsonc
{
  "schemaVersion": 1,
  "generatedAt": "...",
  "lookbackDays": 90,
  "thirteenF": [
    {
      // ... existing fields ...
      "valueUnit": "dollars" | "thousands",
      "valueUnitAdjusted": true,        // optional, only when detector overrode
      "summary": {                       // null if no prior period
        "newPositions": [{cusip, issuerName, shares, valueUsd}, ...],
        "closedPositions": [{cusip, issuerName, sharesAtClose, valueUsdAtClose}, ...],
        "increasedPositions": 12,        // count
        "decreasedPositions": 8,         // count
        "totalValueUsd": 263095703570,
        "priorTotalValueUsd": 274160086701,
        "deltaPct": -0.0404
      }
    }
  ],
  "diagnostics": {
    "valueUnitsAdjusted": ["Baupost Group"],
    "summaryMissing": []
  }
}
```

### Backwards compatibility

- `schemaVersion` stays at 1 — additive changes only.
- Existing consumers reading `thirteenF[i].holdings` keep working.
- Existing consumers reading `stats` keep working.
- New `diagnostics` field is additive.

---

## Testing strategy

### TDD (red → green → refactor)

**`tests/enrich/normalize-value-units.test.js`** (new file)

| Test | Input | Expected |
|---|---|---|
| Berkshire $263B raw | raw entry | unchanged, `valueUnit: 'dollars'` |
| Baupost $5M raw | raw entry | ×1000, `valueUnit: 'thousands'`, `valueUnitAdjusted: true` |
| Scion $1.4B raw | raw entry | unchanged (≥$1B → confident) |
| Empty holdings | `{holdings: []}` | unchanged, `valueUnit: 'dollars'` |
| Holdings missing | `{...no holdings}` | unchanged, log warning |
| `style: 'small-fund'` with $50M raw | config tagged small-fund | unchanged |

**`tests/enrich/period-diff.test.js`** (new file)

| Test | Input | Expected |
|---|---|---|
| Two consecutive quarters | current + prior entry | `summary.newPositions.length` matches diff |
| First-ever filing (no prior) | current only | `summary: null` |
| Multiple prior periods | array of 3 priors | uses most recent |
| Coatue Q4 + Q1 (double-filed) | current Q1 2026 | prior is Q4 2025; correct |

**`tests/scripts/prepare-digest.test.js`** (extend existing)

- Add integration test that runs the script end-to-end against a fixture, asserts `valueUnitAdjusted` flag appears for Baupost, asserts `summary.newPositions.length > 0` for at least one filer.

### Fixture strategy

- Reuse `tests/fixtures/feed-13f.json`. If insufficient (e.g. needs Baupost with raw thousands), add `tests/fixtures/feed-13f-units-mixed.json`.

---

## Migration plan

1. **No data migration.** `feed-13f.json` stays byte-identical. The fix lives entirely in `prepare-digest.js` consumers.
2. **No re-aggregation needed.** Existing aggregator runs are unaffected.
3. **Renderers will see new fields** (`valueUnit`, `summary`). Renderer changes are out of scope for this spec (sub-project B); until then, the digest footer should expose `diagnostics.valueUnitsAdjusted` so users know which filers were adjusted.

---

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Detector false-positive (×1000 on a legitimately small portfolio) | Low | `style: 'small-fund'` opt-out; threshold tuned at $1B |
| Detector false-negative (a filer's raw values are 1000× wrong but sum stays ≥$1B by coincidence) | Very low | Sum ≥$1B with non-conforming units would mean a $1T portfolio — implausible |
| `compute13FSummary` returns stale data for Coatue's late Q4 2025 | Medium | Tested explicitly; doc note that Q4-late filings may show larger diffs than expected |
| Schema consumers break on new fields | Low | All new fields are additive; `schemaVersion` stays at 1 |

---

## Definition of done

- [ ] `npm test` passes 76+ existing tests plus ≥10 new tests for both enrichers.
- [ ] `npm run aggregate` produces identical `feed-13f.json` byte-for-byte.
- [ ] `node scripts/prepare-digest.js --lookback 90` output:
  - `diagnostics.valueUnitsAdjusted` includes Baupost Group (or whatever filers hit the detector on real data).
  - Each filer's `summary` is non-null and `summary.newPositions.length + summary.closedPositions.length > 0` for filers with non-trivial period activity.
- [ ] Manual `/money` digest render shows correct Baupost portfolio (~$5B, not $5M).
- [ ] No regressions in `tests/parsers/thirteen-f.test.js` (parser is untouched).

---

## Open questions (none blocking)

- Should `valueUnit` be exposed in the rendered Markdown digest body, or only via `diagnostics`? Default: diagnostics only. Renderer-level decision deferred to sub-project B.
- Should the detector emit a per-filer confidence score? Default: no (boolean `valueUnitAdjusted` is enough for now).