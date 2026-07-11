## 1. Pre-flight

- [x] 1.1 Spike results recorded (`.workbuddy/memory/2026-07-11.md`): `startDate`/`endDate` ignored; `forms=` fails for 2025+; `q=` works; `root_forms` noise exists.

## 2. Implement `fetch-thirteen-dg-search.js`

- [x] 2.1 Build URL as `https://efts.sec.gov/LATEST/search-index?q=%22${formParam}%22&dateRange=custom&startdt=${startDate}&enddt=${endDate}` (keep `formParam` encoding, drop `forms=`).
- [x] 2.2 After reading `hits`, filter by `_source.root_forms`: keep when `root_forms` includes `formType` or `SCHEDULE ${formType.slice(3)}`; drop otherwise.

## 3. Fix `verify-edgar.js`

- [x] 3.1 Line 19: remove `&forms=SC+13D`; change `startDate`/`endDate` → `startdt`/`enddt` so the dev check mirrors production.

## 4. Tests + fixtures

- [x] 4.1 `tests/edgar/fetch-thirteen-dg-search.test.js`: updated the URL-match regex to `q=%22SC\+13D%22.*startdt=.*enddt=`; updated the encoding test to assert `q=%22SC\+13G%2FA%22`; added a noise-rejection test (`root_forms: ["SC TO-T"]` → `[]`); corrected the length assertion to 1 (filter drops the SC 13G fixture hit).
- [x] 4.2 `tests/aggregate/pipeline-b.test.js`: updated all 8 `forms=SC\+...` nock regexes to `q=%22SC\+...%22`; added `root_forms: ["SC 13D"]` to the 3 mock hits.
- [x] 4.3 `tests/fixtures/search-13dg.json` and the inline `search13dg` in `tests/integration.test.js`: added `root_forms` (`["SC 13D"]` / `["SC 13G"]`) so the filter keeps the legit hits.

## 5. Validate

- [x] 5.1 `node ./node_modules/vitest/vitest.mjs run` — all 164 tests pass (including the new noise-rejection test).
- [x] 5.2 `openspec validate fix-edgar-13dg-query` — change is valid.
- [x] 5.3 `openspec validate edgar-13dg-query` — new spec is valid (post-archive).
