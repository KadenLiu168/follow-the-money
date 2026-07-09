## Context

`scripts/check-alerts.js` decides "new" 13D/G filings by comparing `f.filingDate > config.lastAlertTimestamp` (`check-alerts.js:22,34`). It reads the timestamp but **never writes it back** — the file ends at `process.stdout.write(...)` (line 47).

Two consumption modes:
- 🅰️ **Agent** (`SKILL.md` daily path): step 7 instructs the *agent* to atomically write `lastAlertTimestamp` after delivery.
- 🅱️ **Local cron** (`README` step, `node scripts/check-alerts.js` on a timer): **nothing** writes it back.

So in 🅱️ mode the timestamp stays at its `1970-01-01` default forever, and every cron run re-emits **all** historical 13D filings → alert storm (real, user-visible).

The intended behavior is already documented in `references/alert-rules.md:47-58` (the `config.lastAlertTimestamp = ...; atomicWriteConfig(config)` pseudo-code) — the code silently diverged from that contract.

## Goals / Non-Goals

**Goals:**
- Make `check-alerts.js` the single owner of `lastAlertTimestamp` persistence.
- Eliminate the 🅱️ alert storm.
- Make `alert-rules.md` true again (it already describes this design).

**Non-Goals:**
- No change to dedup logic, the soft cap, or the three-level taxonomy.
- No separate alert state file (keep deriving "seen" from `config.json`; preserves multi-device sync per `data-formats.md:113`).
- No change to agent delivery/rendering flow.
- No new runtime dependency.

## Decisions

**D1 — Script self-persists (Option A), not doc-only (B) or `--no-persist` (C).**
- A: script writes back → fixes 🅱️ immediately, unifies both modes to one writer, makes `alert-rules.md` true. Lowest surface area.
- B (doc-only): leaves existing 🅱️ deployments storming; only helps future readers. Rejected.
- C (`--no-persist` flag for agent): keeps two writers + a flag; more complexity than the defect warrants. Rejected.

**D2 — Atomic write inline in the script (temp-file + rename).**
No shared `atomicWriteConfig` exists (the name appears only in docs). A new `lib/store/atomic-write.js` (the M1 item from the old code-quality review) would be cleaner but is scope creep for this fix. Inline `atomicWriteJSON(path, obj)` in `check-alerts.js` keeps the change localized. Note as a follow-up (F-07-adjacent) to extract the shared helper.

**D3 — Advance to the NEWEST emitted filing date, not the oldest.**
`feed-ndjson.js:38` sorts `read13DFilings` output **descending** by `filingDate`. Therefore `newCritical[0]` is the newest and `newCritical.at(-1)` the oldest. `alert-rules.md` pseudo-code uses `.at(-1)` — that is a latent bug: it would set `lastAlert` to the *oldest* new filing, so a between-run filing newer than that is re-emitted. **Fix: persist `newCritical[0].filingDate`.** This corrects the doc.

**D4 — Write-back happens AFTER stdout emit.**
Matches `alert-rules.md` ("after output") and its accepted trade-off: if a crash occurs between output and write, the next run re-prints the last item — acceptable for v1.

**D5 — Remove `SKILL.md` step 7.**
With the script owning persistence, the agent's manual write-back is redundant (double-writer). Delete step 7; keep the existing error-handling note that `prepare-digest.js` non-zero exit must not advance `lastAlertTimestamp`.

## Risks / Trade-offs

- **[Risk]** Crash after stdout, before write-back → next run re-prints last item. → **Mitigation:** accepted (documented in `alert-rules.md:60`); write-back placed immediately after stdout to minimize the window.
- **[Risk]** 🅰️ agent mode: script now advances `lastAlertTimestamp` right after stdout, *before* the agent renders/delivers each alert. If the agent fails to deliver, that alert is "seen" and won't re-fire. → **Mitigation:** accepted single-writer trade-off; the "seen" gate is intentionally the script, not the agent's delivery success.
- **[Risk]** `config.json` missing → script would write `{ "lastAlertTimestamp": ... }`. → **Mitigation:** onboarding normally creates config; this fallback is harmless and self-heals on next run.
- **[Risk]** Early-exit path (`newCritical.length === 0` → `exit(0)` at line 35) does NOT advance the timestamp. → **Mitigation:** correct — nothing new was seen, so `lastAlert` stays put; next run with genuinely new filings still alerts them.

## Migration Plan

- Deploy: edit `check-alerts.js` + delete `SKILL.md` step 7; no config schema change.
- Existing `~/.follow-the-money/config.json` keeps working; `lastAlertTimestamp` gets updated by the next run.
- Rollback: revert `check-alerts.js` and restore `SKILL.md` step 7 (agent writes again). No data migration needed.

## Open Questions

- None. Option A (D1) is chosen; the only sub-decision (D3 newest-vs-oldest) is resolved by the confirmed descending sort.
