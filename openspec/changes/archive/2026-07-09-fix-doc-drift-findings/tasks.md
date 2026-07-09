## 1. Data-format & Architecture doc fixes

- [x] 1.1 F-09: In `references/data-formats.md`, correct the `thirteenF` description — upsert key is `filerCik + periodOfReport` (one entry per filer per quarter; not capped at 8). Remove "max 8" wording.
- [x] 1.2 F-10: In `README.md` and `references/architecture.md`, replace "08:00 + 20:00 ET (fixed)" with the literal cron `0 12 * * *` + `0 0 * * *` (UTC) and label it "≈08:00 ET (DST-naive)".
- [x] 1.3 F-11: In `references/architecture.md`, replace "downloads the 5 data files" with "downloads 4 static files + per-year NDJSON discovered from manifest".

## 2. Alert doc & prompt fix

- [x] 2.1 F-15: In `references/alert-rules.md`, clarify "three-level classification" is a behavior taxonomy; note `classify.js` returns only `alert`/`digest`, `merged alert` is emergent from `merge-by-issuer` + `merge-amendments`, and `intent` is written by the parsers (not `classify`).
- [x] 2.2 F-04: In `prompts/format-alert.md`, remove the `修订 {count} 次，` prefix from the amendment block (summary already contains "N 次修订" via `merge-amendments.js`).

## 3. Tooling & review-doc fixes

- [x] 3.1 F-14: Create `.nvmrc` with `20.19.0` and raise `engines.node` to `>=20.19.0` in `package.json` (matches `prepare-digest.js` `with { type: 'json' }` requirement).
- [x] 3.2 F-16: In `docs/code-quality-review-2026-07-08.md`, annotate the 3 High items (H1/H2/H3) as resolved by OpenSpec changes `stdout-only-delivery`, `value-units-normalization`, `add-digest-time-seam`.

## 4. Verification

- [x] 4.1 Re-run `npm test` to confirm no regression (expected: 125 passing, no behavior change).
- [x] 4.2 `openspec validate fix-doc-drift-findings` to confirm the change artifacts are consistent.
