## ADDED Requirements

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

The 13F feed-generation path MUST stamp `valueUnit: 'thousands'` on each filer entry it writes to `feed-13f.json`, reflecting the SEC 13F `<value>` official thousands semantics. The single 13F feed writer is `lib/store/feed-json.js` (`upsert13FFiling`, called by `lib/aggregate/pipeline-a.js`); this is where the marker is stamped. This ensures future snapshots are self-describing and no new mixed-unit debt is introduced.

#### Scenario: pipeline write includes marker
- **WHEN** `upsert13FFiling` appends/updates a filer entry in the feed (`feed-13f.json`)
- **THEN** the written entry MUST include `valueUnit: 'thousands'`

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
