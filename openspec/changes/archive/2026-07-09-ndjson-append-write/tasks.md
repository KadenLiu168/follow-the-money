## 1. Feed append (P1-2)

- [x] 1.1 Change `append13DFiling` in `lib/store/feed-ndjson.js` to append a single line (appendFileSync / open fd) instead of read+rewrite.
- [x] 1.2 Keep the existing `${file}.${pid}.${Date.now()}.tmp` + rename atomic write. → **Deviation (see F1):** replaced by `appendFileSync` (O_APPEND) because tmp+rename requires a full read, which conflicts with the binding O(1) spec requirement.

## 2. Validation & accounting (P2-3, P2-5)

- [x] 2.1 Validate `filingDate` with `^\d{4}-\d{2}-\d{2}$` in `append13DFiling`; `console.warn` + skip on invalid (no NaN file).
- [x] 2.2 In `read13DFilings`, count `catch`/skipped lines and surface via return value (`{ entries, skipped }`).
- [x] 2.3 Propagate `skipped` into `validateManifest` diagnostics (and `prepare-digest` diagnostics).

## 3. State file parity

- [x] 3.1 Apply the same append-mode + corrupt-count + `filingDate` validation to `lib/store/state-ndjson.js` (`appendStateNdjson` / `readStateNdjson`). → **Note (F2):** the state store has no `filingDate`/year dimension, so the date-validation rule is N/A there; only append-mode + corrupt-count were applied.

## 4. Tests

- [x] 4.1 Test: N appends → N lines, no full rewrite (spy on readFileSync or assert file growth pattern).
- [x] 4.2 Test: corrupt line counted (`skipped >= 1`).
- [x] 4.3 Test: invalid `filingDate` does not create a NaN file.
- [x] 4.4 Run `npm test` green.

## 5. Notes / Findings

- **F1 (intentional deviation, task 1.2):** The change's `design.md` suggested keeping tmp+rename, but the spec's binding requirement is "MUST NOT read the full file and rewrite it on each call" — tmp+rename inherently reads the whole file. Resolved with `fs.appendFileSync` (O_APPEND), which appends a single line atomically at the OS level and is O(1). Documented inline in `feed-ndjson.js`.
- **F2 (scope note, task 3.1):** `appendStateNdjson`/`readStateNdjson` have no `filingDate`/year concept, so the invalid-`filingDate`→NaN-file rule does not apply to the state store. Only append-mode + corrupt-count parity was implemented there.
- **F3 (robustness):** `validateManifest` now counts only *valid* parsed lines toward `actual`, with `corrupt` tracked separately, so a corrupt line surfaces a single `corrupt` diagnostic instead of a misleading count-mismatch + corrupt double warning.
- **F4:** Added `thirteenDGSkipped` to `prepare-digest` diagnostics per `design.md`.
