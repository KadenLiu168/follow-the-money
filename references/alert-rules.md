# Alert Rules

What triggers an immediate push vs. what waits for the next digest. Load this when tuning alert behavior, debugging dedup, or building new alert types.

## Three-Level Classification

| Form | Treatment | Rationale |
|---|---|---|
| SC 13D | Always alert (full details) | Active investor, 5% threshold cross, rare & important |
| SC 13D/A | Alert but merged per (filer + issuer + day) | Amendment — usually a small tweak, can be noisy |
| SC 13G | Digest only | Passive, high volume |
| SC 13G/A | Digest only | Same as 13G |

## Merge Rule (13D/A)

When multiple `13D/A` filings share the same `(filerCik, issuerCik, filingDate)`:

- Combine into one alert: `🚨 [filer] 修订了 [issuer] 的 13D（N 次修订，[position change summary]）`
- Position change summary derived from comparing last vs. current `ownershipPercent`

This avoids "alert storms" when a filer amends the same filing several times in one day.

## Soft Cap (anti-spam)

- Single cron run produces ≤ 8 alerts → push all in detail
- Single cron run produces > 8 alerts → push first 8 in detail, then append one summary line:

  `📊 另 N 条 13D/G 详见 digest`

The user can read the full list in the next digest. The summary line keeps the notification from drowning the channel.

## Intent Field — by Form Type Only

`intent` is derived purely from form type. No Item 4 text regex.

| Form | intent |
|---|---|
| SC 13D / 13D/A | `active` |
| SC 13G / 13G/A | `passive` |

Rationale: SEC's legal framework already separates 13D (active) from 13G (passive). Item 4 text is mostly legal boilerplate — unreliable signal. Alert wording uses "举牌" (active) vs "披露" (passive) for clarity in Chinese.

## Deduplication (derived state)

`scripts/check-alerts.js` logic:

```js
const lastAlert = config.lastAlertTimestamp || "1970-01-01";
const newCritical = feed.filter(f =>
  ALERT_FORMS.has(f.formType) && f.filingDate > lastAlert
);
if (newCritical.length === 0) exit(0);
deliver(newCritical);
config.lastAlertTimestamp = newCritical.at(-1).filingDate;
atomicWriteConfig(config);
```

`atomicWriteConfig` uses temp+rename. If print crashes between output and timestamp update, the next run re-prints the last item — acceptable for v1.

### Why no separate state file

- The feed is the single source of truth
- Reinstalling `~/.follow-the-money/` does not lose seen-alert history
- Multi-device sync comes for free

## Push Timing

Alerts run on **every cron tick** of the local skill, not just on digest schedule. Typical local cron: 4-6× per day (more frequent than the center's 2× per day) so 13D alerts land within minutes of the feed update.

| Center cron (GitHub Actions) | Local cron (user machine) |
|---|---|
| 08:00 ET + 20:00 ET | User choice (typical: every 2-4h, plus alert checks hourly) |

If the center hasn't updated since the last local cron run, no new alerts are generated. `check-alerts.js` exits 0 silently.

## Failure Handling

| Failure | Behavior |
|---|---|
| Print errors (file read failure) | Surface stderr to agent session |
| Crash between print and timestamp write | Next run re-prints last item; acceptable |
| Feed files missing | `check-alerts.js` exits 0 with "no data" message |
| Config.json missing | Onboarding triggered (see `onboarding.md`) |
| Bad NDJSON line in feed | Skip line, log, continue |

See `data-formats.md` for the `lastAlertTimestamp` field location in config.
