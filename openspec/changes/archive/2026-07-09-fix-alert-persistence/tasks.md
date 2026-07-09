## 1. Pre-flight

- [x] 1.1 Confirm `tests/scripts/check-alerts.test.js` exists and read its current fixtures/assertions (do not assume).
- [x] 1.2 Confirm `feed-ndjson.js` returns `read13DFilings` sorted **descending** by `filingDate` (line ~38) — this justifies `newCritical[0]` = newest.

## 2. Implement script persistence

- [x] 2.1 In `scripts/check-alerts.js`, add `writeFileSync` + `renameSync` to the `node:fs` import.
- [x] 2.2 Add an inline `atomicWriteJSON(path, obj)` helper (write `<path>.tmp` then `renameSync` into place).
- [x] 2.3 After `process.stdout.write(JSON.stringify(payload, null, 2))`, persist: `config.lastAlertTimestamp = newCritical[0].filingDate;` then `atomicWriteJSON(CONFIG_PATH, config);`.
- [x] 2.4 Leave the early-exit path (`newCritical.length === 0` → `exit(0)`) unchanged — no advancement when nothing new was seen.

## 3. Single-writer: remove agent's manual write-back

- [x] 3.1 In `SKILL.md`, delete step 7 ("Update state (after successful delivery): atomically write the latest alert's filingDate back to config.lastAlertTimestamp").
- [x] 3.2 Keep the existing `SKILL.md` error-handling note: `prepare-digest.js` non-zero exit MUST NOT update `lastAlertTimestamp` (now owned by the script).

## 4. Correct the doc pseudo-code

- [x] 4.1 In `references/alert-rules.md:56`, change the pseudo-code `config.lastAlertTimestamp = newCritical.at(-1).filingDate;` to use the **newest** emitted date (`newCritical[0].filingDate`, given descending sort). Add a one-line comment explaining the descending-sort rationale.

## 5. Tests

- [x] 5.1 In `tests/scripts/check-alerts.test.js`, add a two-run persistence test: with a fixture `config.json` whose `lastAlertTimestamp` predates some fixture filings, run the script once (assert alerts emitted + `config.json` `lastAlertTimestamp` advanced to newest), run again (assert empty `{ alerts: [] }`).
- [x] 5.2 Add a regression assertion that the persisted value equals the **newest** filing date, not the oldest.

## 6. Validate

- [x] 6.1 Run `node ./node_modules/vitest/vitest.mjs run` — all tests pass (especially the new check-alerts persistence tests).
- [x] 6.2 `openspec validate fix-alert-persistence` — change is valid.
- [x] 6.3 `openspec validate alert-persistence` — new spec is valid.
