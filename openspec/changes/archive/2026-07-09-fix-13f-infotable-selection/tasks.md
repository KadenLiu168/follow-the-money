## 1. Selection logic (P1-3)

- [x] 1.1 In `lib/edgar/fetch-thirteen-f-xml.js`, select `form13fInfoTable.xml` (case-insensitive) from `index.json` when present.
- [x] 1.2 Keep the largest-`.xml` heuristic only as fallback when canonical name is absent.
- [x] 1.3 Remove `primaryDocument` from the holdings fallback; throw when no usable infoTable file is found.

## 2. Sanity check

- [x] 2.1 In `lib/parsers/thirteen-f.js`, throw a descriptive error when parsed `holdings` is empty.

## 3. Tests

- [x] 3.1 Add a fixture where cover page > infoTable in size; assert `form13fInfoTable.xml` is selected.
- [x] 3.2 Add a test: no usable infoTable file → function throws (no cover-page parse).
- [x] 3.3 Add a test: `parseThirteenF` with empty `<infoTable>` throws.
- [x] 3.4 Run `npm test` green.

## 4. Notes / Findings

- **F1 (test conflict → adjusted):** The new contract (`parseThirteenF` throws on empty holdings; `fetchThirteenFXml` throws instead of falling back to `primaryDocument`) conflicts with three existing tests that encoded the OLD behavior:
  - `tests/parsers/thirteen-f.test.js` asserted `parseThirteenF('<informationTable/>')` returns `[]` → changed to assert a throw.
  - `tests/edgar/fetch-thirteen-f-xml.test.js` asserted the `primaryDocument` fallback (index.json 404 → return cover page) → changed to assert a throw.
  - `tests/aggregate/pipeline-a.test.js` and `tests/integration.test.js` mocked only the `form13fData.xml` (cover-page) URL and never `index.json`, relying on the old fallback. Updated both to resolve the infoTable via `index.json` → `form13fInfoTable.xml`. These are integration tests that should have mocked `index.json` from the start.
  - No production caller changes were needed: `lib/aggregate/pipeline-a.js` already wraps the fetch+parse in try/catch, so the new throws surface as recorded errors (the intended "fail loudly" behavior).
- **F2:** The `primaryDocument` parameter is retained in `fetchThirteenFXml`'s signature for caller compatibility but is intentionally no longer used as a holdings fallback.
