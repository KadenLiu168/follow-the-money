## Why

`fetchThirteenFXml` selects the 13F infoTable by picking the *largest* `.xml` in the filing directory, falling back to `primaryDocument` (the cover page) when `index.json` is missing. SEC 13F filings separate the cover page (`form13f.hr` / `primaryDocument`) from the information table (`form13fInfoTable.xml`). The "largest xml" heuristic is not guaranteed: if the cover page is larger than the infoTable, the cover page is parsed as holdings → `parseThirteenF` finds no `<infoTable>` → empty/incorrect holdings in the digest. This is a silent data-correctness defect on the 13F holdings path used by all 8 tracked filers.

## What Changes

- `lib/edgar/fetch-thirteen-f-xml.js`: prefer the canonical filename `form13fInfoTable.xml` when present in `index.json`; use the "largest xml" heuristic only as a fallback; never fall back to `primaryDocument` as the holdings source.
- `lib/parsers/thirteen-f.js`: after parsing, if `holdings` is empty, surface a clear error so the caller can retry/alert instead of silently emitting an empty position set.

## Capabilities

### New Capabilities
- `edgar-13f-fetch`: the contract for resolving the 13F information table file by canonical name with a safe fallback and a non-empty holdings sanity check.

### Modified Capabilities
<!-- none -->

## Impact

- **Code**: `lib/edgar/fetch-thirteen-f-xml.js`, `lib/parsers/thirteen-f.js`.
- **Behavior**: holdings are read from the correct file; empty-holdings parses fail loudly instead of silently.
- **Tests**: add a fixture where the cover page is larger than the infoTable, asserting `form13fInfoTable.xml` is still selected; add an empty-holdings error test.
- **No API / dependency / network changes** (beyond existing EDGAR calls).
