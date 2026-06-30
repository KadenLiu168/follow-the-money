# Data Formats

Schema reference for every data file the aggregator writes and the local skill reads. Load this when parsing or debugging feed files.

## Directory Layout

```
follow-the-money/
├── feed-13f.json                          # 13F aggregated feed (single file)
├── feed-13dg/                             # 13D/G aggregated feed (split by year)
│   ├── manifest.json
│   ├── 2024.ndjson
│   ├── 2025.ndjson
│   └── 2026.ndjson
├── state-13f.json                         # aggregator's 13F dedup state
└── state-13dg.ndjson                      # aggregator's 13D/G dedup state
```

## `feed-13f.json`

Single JSON file. Top-level fields:

| Field | Type | Description |
|---|---|---|
| `schemaVersion` | number | Always `1` |
| `generatedAt` | string (ISO 8601) | When aggregator ran |
| `lookbackDays` | number | Default 90 |
| `thirteenF` | array | One entry per filer (max 8) |
| `stats` | object | `{ thirteenFFilings, thirteenFHoldings }` |

Each `thirteenF[]` entry:

| Field | Type | Description |
|---|---|---|
| `filerCik` | string | 10-digit zero-padded |
| `filerName` | string | |
| `latestFilingDate` | string (`YYYY-MM-DD`) | |
| `latestFormType` | string | e.g. `13F-HR`, `13F-HR/A` |
| `latestAccessionNumber` | string | 18 chars with dashes |
| `periodOfReport` | string (`YYYY-MM-DD`) | Quarter end |
| `history` | array | Past filings, most recent first |
| `holdings` | array | CUSIP rows from form13fData.xml |
| `summary` | object | Aggregated counts + new/closed/increased/decreased |

### 13F-HR/A merge rule

When a new `13F-HR/A` arrives with the same `(filerCik, periodOfReport)` as an existing entry:
- **Overwrite** the existing `holdings` + `summary`
- **Append** to `history`
- **Update** `latestFilingDate` / `latestFormType` / `latestAccessionNumber`

Delta (new/closed/increased/decreased) is always computed against the most recent entry with a **different** `periodOfReport`.

## `feed-13dg/manifest.json`

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

## `feed-13dg/<year>.ndjson`

One JSON object per line, no trailing comma. Fields:

| Field | Type | Description |
|---|---|---|
| `filerCik` | string | 10-digit zero-padded |
| `filerName` | string | |
| `issuerCik` | string | 10-digit zero-padded |
| `issuerName` | string | |
| `issuerTicker` | string | Uppercase |
| `formType` | string | `SC 13D`, `SC 13D/A`, `SC 13G`, `SC 13G/A` |
| `filingDate` | string (`YYYY-MM-DD`) | |
| `ownershipPercent` | number | e.g. `6.8` |
| `sharesOwned` | number | |
| `intent` | string | `active` or `passive` (see `alert-rules.md`) |
| `accessionNumber` | string | 18 chars with dashes |
| `primaryDocUrl` | string | Link to EDGAR primary doc |

### Why per-year split
Feed files grow append-only forever. Year-split keeps each file ~50MB/year; git diff stays small and mergeable. Digest logic reads current year + previous year to handle cross-year boundaries.

## `state-13f.json`

```json
{
  "lastUpdated": "2026-05-15T08:00:00.000Z",
  "seenFilings": {
    "0001067983-26-000123": 1715740800000
  }
}
```

Aggregator-side dedup. Key is accession number, value is epoch millis.

## `state-13dg.ndjson`

```ndjson
{"accession":"0000932470-26-000045","seenAt":1719250000000}
{"accession":"0000893855-26-000078","seenAt":1719100000000}
```

Aggregator-side dedup. One line per accession.

## Local State — None (derived)

The local skill has **no independent alert state file**. Alert deduplication derives from `feed-13dg/manifest.json` + `config.lastAlertTimestamp` (in `~/.follow-the-money/config.json`).

Rationale:
- Single source of truth: center feed is authoritative
- Zero-cost reinstall: deleting `~/.follow-the-money/` doesn't lose "seen" info
- Multi-device sync: every device reads the same feed
- Atomic write: temp file + rename to avoid half-written lines

## Naming Conventions

| Type | Format |
|---|---|
| Times | ISO 8601 strings |
| Money | USD + units (`B` / `M`) when displayed; raw numbers in feed |
| CIK | 10-digit zero-padded string |
| Accession number | 18 chars with dashes (e.g. `0001067983-26-000456`) |
| Ticker | Uppercase |

## NDJSON Robustness

All NDJSON writers MUST:
- Use atomic write: write to `*.tmp`, then `rename()` to final path
- Flush before rename
- Never leave a half-written line on disk

All NDJSON readers MUST:
- Validate line numbers on startup
- Compare on-disk line count vs. `manifest.json` `count` field
- On mismatch: log a warning, backfill from EDGAR (next aggregator run)

All readers MUST:
- Skip + log a single bad line (do not crash the whole file)
- Count skipped lines and report in stats

See `architecture.md` for how these files flow through the layers.
