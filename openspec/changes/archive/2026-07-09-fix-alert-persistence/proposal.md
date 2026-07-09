## Why

`scripts/check-alerts.js` reads `config.lastAlertTimestamp` to decide which 13D/G filings are "new", but **never writes it back**. In 🅱️ local-cron mode (README step, `node scripts/check-alerts.js` on a timer), nothing else persists that timestamp — so every cron run falls back to the `1970-01-01` default and re-emits **all** historical 13D filings. This is a real, user-visible defect ("alert storm"), not just a doc mismatch.

Notably, `references/alert-rules.md:47-58` already documents the *intended* behavior: the script writes `config.lastAlertTimestamp` back atomically after a run. The implementation silently diverged from that contract. Fixing it makes the doc true again.

## What Changes

- `scripts/check-alerts.js`: after emitting the alert payload, atomically persist `config.lastAlertTimestamp` to the newest filing date in the emitted set. Add a minimal atomic-write helper (temp-file + rename) — no existing shared helper exists (`atomicWriteConfig` is doc-only).
- `SKILL.md` step 7 ("Update state after successful delivery"): **remove** the agent's manual write-back, because the script now owns persistence. Single writer for both 🅰️ agent and 🅱️ local modes.
- `references/alert-rules.md`: the dedup pseudo-code becomes **true** (no doc edit strictly required), but fix the subtle `.at(-1)` error — the 13DG feed is sorted **descending** by `filingDate`, so `.at(-1)` is the *oldest*; the persisted timestamp must be the *newest* (`newCritical[0]`), otherwise a between-run filing is re-emited.
- `tests/scripts/check-alerts.test.js`: add a persistence assertion (run twice with a fixture config; second run emits nothing).

## Capabilities

### New Capabilities
- `alert-persistence`: the contract that `scripts/check-alerts.js` is the single owner of `config.lastAlertTimestamp` and atomically advances it to the newest emitted filing date on every run that produces alerts.

### Modified Capabilities
<!-- None. No existing spec's REQUIREMENTS change. -->

## Impact

- **Code**: `scripts/check-alerts.js` (add import + atomic-write + write-back), `SKILL.md` (delete step 7).
- **Behavior**: 🅱️ local-cron mode stops re-sending history; 🅰️ agent mode behavior unchanged (agent no longer double-writes).
- **Config**: `~/.follow-the-money/config.json` `lastAlertTimestamp` is now advanced by the script itself.
- **Tests**: new test in `tests/scripts/check-alerts.test.js`.
- **No API / dependency / network changes.** Pure local file I/O; no new runtime deps.
