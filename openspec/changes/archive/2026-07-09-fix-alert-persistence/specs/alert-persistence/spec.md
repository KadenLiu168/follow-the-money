## ADDED Requirements

### Requirement: Script owns lastAlertTimestamp persistence
`scripts/check-alerts.js` SHALL be the single owner of `config.lastAlertTimestamp`. After a run that emits at least one alert, it MUST atomically persist the advanced timestamp back to `~/.follow-the-money/config.json`. No other component (agent, SKILL step, cron wrapper) SHALL write this field.

#### Scenario: Run with new filings advances timestamp
- **WHEN** `check-alerts.js` finds filings with `filingDate > config.lastAlertTimestamp`
- **THEN** it emits the alert payload to stdout AND atomically writes `config.lastAlertTimestamp` to the run's newest emitted filing date

#### Scenario: Second run with no newer filings emits empty (no storm)
- **WHEN** `check-alerts.js` runs again after the timestamp was persisted, and no filing is newer than `config.lastAlertTimestamp`
- **THEN** it emits `{ alerts: [], capped: false, summary: null }` and does NOT re-emit historical filings

#### Scenario: Write is atomic
- **WHEN** `check-alerts.js` persists `lastAlertTimestamp`
- **THEN** it writes to a temp file and renames into place (no partial `config.json` on crash/mid-write)

### Requirement: Advance to newest emitted filing date
On a run that emits alerts, `config.lastAlertTimestamp` MUST be set to the **newest** filing date among the emitted set (the 13DG feed is sorted descending by `filingDate`, so this is `newCritical[0]`, not `.at(-1)`).

#### Scenario: Multiple new filings in one run
- **WHEN** a run emits alerts for filings dated 2026-07-01, 2026-07-05, and 2026-07-09 (descending order)
- **THEN** `config.lastAlertTimestamp` becomes the 2026-07-09 value, so only filings strictly newer than 2026-07-09 alert on the next run

### Requirement: No double-write from agent/SKILL
The agent consumption path (🅰️) SHALL rely on `check-alerts.js` for persistence and SHALL NOT also write `lastAlertTimestamp` itself.

#### Scenario: Agent mode does not re-write timestamp
- **WHEN** an agent runs `check-alerts.js` as part of its daily path
- **THEN** the script persists the timestamp; the agent's coordination instructions do not contain a separate "update state" step that writes `lastAlertTimestamp`
