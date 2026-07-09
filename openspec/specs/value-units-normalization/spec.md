# value-units-normalization Specification

## Purpose

Declarative, config-driven resolution of 13F value units. SEC EDGAR's 13F
`<value>` field is officially in thousands of dollars; each filer's unit is
declared via `valueUnit` in `config/default-sources.json`. Replaces the removed
magnitude (`< $1B`) heuristic (see change `fix-value-units-config`).
## Requirements
### Requirement: `normalizeValueUnits` MUST resolve unit from config `valueUnit`

`normalizeValueUnits(filerEntry, configSources)` MUST resolve the value unit from the `valueUnit` field of the config source matching `filerEntry.filerCik`. When `valueUnit === 'thousands'`, every holding's `valueUsd` MUST be multiplied by 1000 and `valueUnitAdjusted` set to `true`. When `valueUnit === 'dollars'`, holdings MUST be returned unchanged and `valueUnitAdjusted` MUST NOT be set. The magnitude-based (`< $1B`) heuristic MUST be removed. An unmatched CIK MUST default to `'thousands'` (SEC 13F spec).

#### Scenario: Source declares thousands
- **WHEN** the matching config source has `valueUnit: 'thousands'`
- **THEN** every holding's `valueUsd` MUST equal input `valueUsd` × 1000
- **AND** the returned entry's `valueUnit` MUST equal `'thousands'`
- **AND** the returned entry's `valueUnitAdjusted` MUST equal `true`

#### Scenario: Source declares dollars
- **WHEN** the matching config source has `valueUnit: 'dollars'`
- **THEN** every holding's `valueUsd` MUST equal the input `valueUsd`
- **AND** the returned entry's `valueUnit` MUST equal `'dollars'`
- **AND** the returned entry MUST NOT have `valueUnitAdjusted` set

#### Scenario: Unmatched source defaults to thousands (SEC 13F spec)
- **WHEN** no config source matches `filerCik`
- **THEN** the function MUST treat the unit as `'thousands'` and multiply by 1000
- **AND** `valueUnitAdjusted` MUST equal `true`

### Requirement: `normalizeValueUnits` MUST be idempotent

The `normalizeValueUnits(filerEntry, configSources)` function in `lib/enrich/normalize-value-units.js` MUST be idempotent: calling it on an entry that has already been processed (signaled by `valueUnitAdjusted === true`) MUST return an entry whose `holdings[].valueUsd` values are unchanged from the input.

#### Scenario: Repeated call on already-normalized thousands filer
- **WHEN** `normalizeValueUnits` is called on an entry with `valueUnitAdjusted === true` and matching config `valueUnit: 'thousands'`
- **THEN** every holding's `valueUsd` MUST equal the input `valueUsd`
- **AND** the returned entry's `valueUnit` MUST equal `'thousands'`

#### Scenario: Repeated call on already-normalized dollars filer
- **WHEN** `normalizeValueUnits` is called on an entry with `valueUnitAdjusted === true` and matching config `valueUnit: 'dollars'`
- **THEN** every holding's `valueUsd` MUST equal the input `valueUsd`
- **AND** the returned entry's `valueUnit` MUST equal `'dollars'`

#### Scenario: First call on un-normalized entry, source declares thousands
- **WHEN** `normalizeValueUnits` is called on an entry with `valueUnitAdjusted` not equal to `true` and matching config `valueUnit: 'thousands'`
- **THEN** every holding's `valueUsd` MUST equal input `valueUsd` × 1000
- **AND** the returned entry's `valueUnit` MUST equal `'thousands'`
- **AND** the returned entry's `valueUnitAdjusted` MUST equal `true`

#### Scenario: First call on un-normalized entry, source declares dollars
- **WHEN** `normalizeValueUnits` is called on an entry with `valueUnitAdjusted` not equal to `true` and matching config `valueUnit: 'dollars'`
- **THEN** every holding's `valueUsd` MUST equal the input `valueUsd`
- **AND** the returned entry's `valueUnit` MUST equal `'dollars'`
- **AND** the returned entry MUST NOT have `valueUnitAdjusted` set

### Requirement: `valueUnitAdjusted` is the canonical "already-normalized" marker

`valueUnitAdjusted` MUST be the sole signal that an entry has been processed by `normalizeValueUnits`. The function MUST treat `valueUnitAdjusted === true` on input as an authoritative "already normalized" flag regardless of `valueUnit` value, and MUST short-circuit before any unit resolution that could mutate holdings.

#### Scenario: Marker set by the function on output
- **WHEN** `normalizeValueUnits` multiplies holdings by 1000 (the `thousands` branch)
- **THEN** the returned entry's `valueUnitAdjusted` MUST be exactly `true`

#### Scenario: Marker not set in dollars branch
- **WHEN** `normalizeValueUnits` takes the `dollars` branch (config `valueUnit: 'dollars'`)
- **THEN** the returned entry MUST NOT have `valueUnitAdjusted` set

#### Scenario: Marker not set in small-fund branch
- **WHEN** the matching config source has `style: 'small-fund'`
- **THEN** the returned entry MUST NOT have `valueUnitAdjusted` set regardless of `valueUnit`
- **AND** the returned entry's `valueUnit` MUST equal `'unknown'`

### Requirement: `valueUnit` has three mutually exclusive states

`normalizeValueUnits` MUST return a `valueUnit` of exactly one of three string values, mutually exclusive:

- `'dollars'`: the matching config source declares `valueUnit: 'dollars'`.
- `'thousands'`: the matching config source declares `valueUnit: 'thousands'` (or no source matches); holdings were ×1000 to dollars.
- `'unknown'`: the matching config source has `style: 'small-fund'`; unit detection was intentionally skipped.

#### Scenario: All three states are reachable via distinct inputs
- **WHEN** `normalizeValueUnits` is called with (a) a config source declaring `valueUnit: 'dollars'`, (b) a config source declaring `valueUnit: 'thousands'`, (c) `style: 'small-fund'` config
- **THEN** the three calls return `valueUnit` values `'dollars'`, `'thousands'`, `'unknown'` respectively

### Requirement: small-fund style takes precedence over config resolution

When a config source matching the entry's `filerCik` has `style: 'small-fund'`, `normalizeValueUnits` MUST return `{ valueUnit: 'unknown' }` without evaluating the `valueUnit` field and without modifying holdings.

#### Scenario: small-fund style with thousands-declared config
- **WHEN** the matching config source has `style: 'small-fund'` (regardless of `valueUnit`)
- **THEN** the returned entry's `valueUnit` MUST equal `'unknown'`
- **AND** every holding's `valueUsd` MUST equal the input `valueUsd`
- **AND** the returned entry MUST NOT have `valueUnitAdjusted` set

### Requirement: `periodDiff` re-normalization is safe

`lib/enrich/period-diff.js` calls `normalizeValueUnits` on the prior entry as a defensive measure. After this change, this re-normalization MUST be safe for all prior entries regardless of whether they originate from a pre-normalized feed (e.g., `normalizedFeed` in `scripts/prepare-digest.js`) or a raw feed.

#### Scenario: Re-normalization of prior from pre-normalized feed
- **WHEN** `periodDiff` is called with a prior entry whose `valueUnitAdjusted === true`
- **THEN** the prior's `holdings[].valueUsd` values used in `priorTotalValueUsd` and `deltaPct` computation MUST equal the values produced by the upstream normalization pass, not double-multiplied

#### Scenario: Re-normalization of prior from raw feed (no pre-normalization)
- **WHEN** `periodDiff` is called with a prior entry whose `valueUnitAdjusted` is unset and whose matching config source declares `valueUnit: 'thousands'`
- **THEN** the prior's `holdings[].valueUsd` values MUST be ×1000 once
- **AND** the prior's holdings MUST NOT be ×1000 a second time

### Requirement: feed entries MUST declare valueUnit marker

The feed (`feed-13f.json`) MUST carry a `valueUnit` marker on every filer entry, declaring the unit in which that entry's `holdings[].valueUsd` are stored. After the one-time repair, every entry MUST declare `'thousands'`.

#### Scenario: entry declares thousands after repair
- **WHEN** the repaired feed is read
- **THEN** every filer entry's `valueUnit` MUST equal `'thousands'`

### Requirement: normalizeValueUnits prefers entry's own valueUnit marker

`normalizeValueUnits(filerEntry, configSources)` MUST prefer `filerEntry.valueUnit` when it is explicitly declared (non-empty), resolving the unit from that marker. The config `valueUnit` MUST be used only as a fallback when the entry marker is absent. This makes self-describing feeds authoritative and removes reliance on a global config guess.

#### Scenario: entry marker present takes precedence
- **WHEN** `filerEntry.valueUnit === 'thousands'` is declared
- **THEN** the function MUST resolve the unit from the entry marker and multiply holdings by 1000

#### Scenario: entry marker present, config differs (marker wins)
- **WHEN** `filerEntry.valueUnit === 'thousands'` is declared but the matching config source declares `'dollars'`
- **THEN** the function MUST resolve the unit from the entry marker (`'thousands'`) and multiply by 1000, NOT from config

#### Scenario: entry marker absent falls back to config
- **WHEN** `filerEntry.valueUnit` is absent/undeclared
- **THEN** the function MUST resolve the unit from the matching config source (existing config-driven behavior)

### Requirement: feed MUST contain no mixed-unit debt

The committed feed MUST NOT contain entries stored in mixed units. Every filer entry's `holdings[].valueUsd` MUST be in the unit declared by its `valueUnit` marker, and all entries MUST share the same declared unit (single-unit feed). A one-time repair normalizes historical data to this state.

#### Scenario: all entries single-unit after repair
- **WHEN** the repaired feed is validated
- **THEN** no entry's maximum `valueUsd` under the declared `'thousands'` unit MUST exceed 1e9 (i.e., none are stored in dollars)

### Requirement: pipeline stamps valueUnit marker on write (prevent recurrence)

The 13F feed-generation path MUST stamp `valueUnit: 'thousands'` on each filer entry it writes to `feed-13f.json`, reflecting the SEC 13F `<value>` official thousands semantics. The stamping MUST happen in the single pure merge function `merge13FFiling(feed, entry)` in `lib/store/feed-json.js`, which stamps the marker, applies the history-dedupe-by-accession merge, and recomputes feed stats. `upsert13FFiling(path, entry)` is a thin wrapper that writes `merge13FFiling(readFeedJson(path), entry)` to disk for backward compatibility and single-shot callers. The aggregator `lib/aggregate/pipeline-a.js` MUST accumulate entries in memory via `merge13FFiling` and write the feed exactly once per run via `writeFeedJson` (NOT once per filing). This keeps future snapshots self-describing, introduces no new mixed-unit debt, and makes per-run disk writes O(1) instead of O(N).

#### Scenario: pipeline write includes marker
- **WHEN** `merge13FFiling` (via `upsert13FFiling` or `pipeline-a`) appends/updates a filer entry in the feed (`feed-13f.json`)
- **THEN** the written entry MUST include `valueUnit: 'thousands'`

#### Scenario: pipeline-a writes feed once per run
- **WHEN** `runPipelineA` processes N new filings in a single run
- **THEN** `feed-13f.json` MUST be written to disk exactly once at the end of the run (after in-memory accumulation via `merge13FFiling`), not once per filing

### Requirement: one-time repair normalizes historical feed to single unit

A repair operation (`scripts/repair-feed-units.js`) MUST detect per-snapshot unit (a snapshot whose maximum `holdings[].valueUsd` is >= 1e9 is stored in dollars), divide its `holdings[].valueUsd` and `summary` totals by 1000 to convert to thousands, stamp `valueUnit: 'thousands'`, and write the feed atomically. The operation MUST be idempotent (re-running leaves already-normalized snapshots unchanged) and MUST report the count of converted snapshots.

#### Scenario: dollar-stored snapshot normalized
- **WHEN** the repair runs on a snapshot with maximum `valueUsd` = 86.8e9
- **THEN** that snapshot's `holdings[].valueUsd` MUST equal 86.8e6 after repair
- **AND** the entry's `valueUnit` MUST equal `'thousands'`

#### Scenario: already-thousands snapshot unchanged
- **WHEN** the repair runs on a snapshot with maximum `valueUsd` < 1e9
- **THEN** its `holdings[].valueUsd` MUST be unchanged

#### Scenario: idempotent re-run
- **WHEN** the repair runs a second time on an already-repaired feed
- **THEN** zero snapshots are converted (count = 0) and values are unchanged

