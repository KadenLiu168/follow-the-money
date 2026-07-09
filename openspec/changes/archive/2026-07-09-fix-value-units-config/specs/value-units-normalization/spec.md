## MODIFIED Requirements

### Requirement: `normalizeValueUnits` MUST resolve unit from config `valueUnit`

`normalizeValueUnits(filerEntry, configSources)` MUST resolve the value unit from the `valueUnit` field of the config source matching `filerEntry.filerCik`. When `valueUnit === 'thousands'`, every holding's `valueUsd` MUST be multiplied by 1000 and `valueUnitAdjusted` set to `true`. When `valueUnit === 'dollars'`, holdings MUST be returned unchanged and `valueUnitAdjusted` MUST NOT be set. The magnitude-based (`< $1B`) heuristic MUST be removed.

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
