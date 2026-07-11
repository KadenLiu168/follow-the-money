## 1. Parser fix — `lib/parsers/thirteen-dg.js`

- [x] 1.1 Add `toNumber(raw)` helper: extract first numeric token (`/[\d,]+(?:\.\d+)?/`), strip commas, return `0` on missing/NaN.
- [x] 1.2 Fix `pickFirst` SGML regex: build terminator `alts` array conditionally and `.filter(Boolean)` so an empty `stopLabels` does NOT produce a zero-width `(?:)` / `()` branch; join with `|`. Also admit `%` in the capture class so `pickFirst` can return `"6.8%"`.
- [x] 1.3 Apply `toNumber` to `ownershipPercent` (replace `Number(pickFirst(...) || '0')`) and `sharesOwned` (replace `Number((pickFirst(...)||'0').replace(/,/g,''))`).

## 2. Test guard — HTML-shape fixture + unit test

- [x] 2.1 Create `tests/fixtures/13d-html-shape.html`: a realistic HTML 13D (Title Case labels, `Percent of Class 6.8%`, `Aggregate Amount Beneficially Owned 1,234,567`, plus issuer/ticker fields).
- [x] 2.2 Add a test in `tests/parsers/thirteen-dg.test.js` asserting `ownershipPercent === 6.8` and `sharesOwned === 1234567` on the HTML-shape fixture.

## 3. Validation

- [x] 3.1 Run `npm test` (parsers suite) — confirm new HTML test passes and all existing SGML tests still green.
- [x] 3.2 Run `openspec validate fix-d7-13dg-html-parse` — confirm change validates.
