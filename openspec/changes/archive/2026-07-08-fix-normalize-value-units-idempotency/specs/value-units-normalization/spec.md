## ADDED Requirements

### Requirement: `normalizeValueUnits` MUST be idempotent

The `normalizeValueUnits(filerEntry, configSources)` function in `lib/enrich/normalize-value-units.js` MUST be idempotent: calling it on an entry that has already been processed (signaled by `valueUnitAdjusted === true`) MUST return an entry whose `holdings[].valueUsd` values are unchanged from the input.

#### Scenario: Repeated call on already-normalized small filer (raw sum < $1M)
- **WHEN** `normalizeValueUnits` is called on an entry with raw holdings sum < $1,000,000 and `valueUnitAdjusted === true`
- **THEN** every holding's `valueUsd` MUST equal the input `valueUsd`
- **AND** the returned entry's `valueUnit` MUST equal `'thousands'`
- **AND** the returned entry's `valueUnitAdjusted` MUST equal `true`

#### Scenario: Repeated call on already-normalized large filer (raw sum ≥ $1B after first call)
- **WHEN** `normalizeValueUnits` is called on an entry with `valueUnitAdjusted === true` and holdings sum ≥ $1,000,000,000
- **THEN** every holding's `valueUsd` MUST equal the input `valueUsd`
- **AND** the returned entry's `valueUnit` MUST equal `'dollars'`

#### Scenario: First call on un-normalized entry with raw sum < $1B
- **WHEN** `normalizeValueUnits` is called on an entry with `valueUnitAdjusted` not equal to `true` and raw holdings sum < $1,000,000,000 and non-zero
- **THEN** every holding's `valueUsd` MUST equal input `valueUsd` × 1000
- **AND** the returned entry's `valueUnit` MUST equal `'thousands'`
- **AND** the returned entry's `valueUnitAdjusted` MUST equal `true`

#### Scenario: First call on un-normalized entry with raw sum ≥ $1B
- **WHEN** `normalizeValueUnits` is called on an entry with `valueUnitAdjusted` not equal to `true` and raw holdings sum ≥ $1,000,000,000
- **THEN** every holding's `valueUsd` MUST equal the input `valueUsd`
- **AND** the returned entry's `valueUnit` MUST equal `'dollars'`
- **AND** the returned entry MUST NOT have `valueUnitAdjusted` set

### Requirement: `valueUnitAdjusted` is the canonical "already-normalized" marker

`valueUnitAdjusted` MUST be the sole signal that an entry has been processed by `normalizeValueUnits`. The function MUST treat `valueUnitAdjusted === true` on input as an authoritative "already normalized" flag regardless of `valueUnit` value, and MUST short-circuit before any heuristic re-evaluation that could mutate holdings.

#### Scenario: Marker set by the function on output
- **WHEN** `normalizeValueUnits` multiplies holdings by 1000 (the `thousands` branch)
- **THEN** the returned entry's `valueUnitAdjusted` MUST be exactly `true`

#### Scenario: Marker not set in dollars branch
- **WHEN** `normalizeValueUnits` takes the `dollars` branch (sum ≥ $1B or sum === 0)
- **THEN** the returned entry MUST NOT have `valueUnitAdjusted` set

#### Scenario: Marker not set in small-fund branch
- **WHEN** the matching config source has `style: 'small-fund'`
- **THEN** the returned entry MUST NOT have `valueUnitAdjusted` set regardless of holdings sum
- **AND** the returned entry's `valueUnit` MUST equal `'unknown'`

### Requirement: `valueUnit` has three mutually exclusive states

`normalizeValueUnits` MUST return a `valueUnit` of exactly one of three string values, mutually exclusive:

- `'dollars'`: heuristics determined holdings are already in dollars.
- `'thousands'`: heuristics determined holdings were in thousands and were ×1000 to dollars.
- `'unknown'`: the matching config source has `style: 'small-fund'`; unit detection was intentionally skipped.

#### Scenario: All three states are reachable via distinct inputs
- **WHEN** `normalizeValueUnits` is called with (a) raw sum ≥ $1B, (b) raw sum > 0 and < $1B, (c) `style: 'small-fund'` config
- **THEN** the three calls return `valueUnit` values `'dollars'`, `'thousands'`, `'unknown'` respectively

### Requirement: Heuristic threshold preserved

The unit-detection heuristic MUST remain unchanged: raw holdings sum strictly greater than 0 and strictly less than $1,000,000,000 is treated as thousands (×1000); sum === 0 or sum ≥ $1,000,000,000 is treated as dollars (no change).

#### Scenario: Boundary sum = $1,000,000,000
- **WHEN** `normalizeValueUnits` is called with raw holdings sum exactly equal to $1,000,000,000
- **THEN** the function MUST take the `dollars` branch (sum ≥ $1B)
- **AND** every holding's `valueUsd` MUST equal the input `valueUsd`

#### Scenario: Boundary sum = $1
- **WHEN** `normalizeValueUnits` is called with raw holdings sum of $1
- **THEN** the function MUST take the `thousands` branch (sum > 0 and < $1B)
- **AND** every holding's `valueUsd` MUST equal input × 1000

### Requirement: small-fund style takes precedence over heuristic

When a config source matching the entry's `filerCik` has `style: 'small-fund'`, `normalizeValueUnits` MUST return `{ valueUnit: 'unknown' }` without evaluating the sum heuristic and without modifying holdings.

#### Scenario: small-fund style with sum that would otherwise trigger thousands
- **WHEN** the matching config source has `style: 'small-fund'` and raw holdings sum < $1B
- **THEN** the returned entry's `valueUnit` MUST equal `'unknown'`
- **AND** every holding's `valueUsd` MUST equal the input `valueUsd`
- **AND** the returned entry MUST NOT have `valueUnitAdjusted` set

### Requirement: `periodDiff` re-normalization is safe

`lib/enrich/period-diff.js` calls `normalizeValueUnits` on the prior entry as a defensive measure. After this change, this re-normalization MUST be safe for all prior entries regardless of whether they originate from a pre-normalized feed (e.g., `normalizedFeed` in `scripts/prepare-digest.js`) or a raw feed.

#### Scenario: Re-normalization of prior from pre-normalized feed
- **WHEN** `periodDiff` is called with a prior entry whose `valueUnitAdjusted === true`
- **THEN** the prior's `holdings[].valueUsd` values used in `priorTotalValueUsd` and `deltaPct` computation MUST equal the values produced by the upstream normalization pass, not double-multiplied

#### Scenario: Re-normalization of prior from raw feed (no pre-normalization)
- **WHEN** `periodDiff` is called with a prior entry whose `valueUnitAdjusted` is unset and raw holdings sum < $1B
- **THEN** the prior's `holdings[].valueUsd` values MUST be ×1000 once
- **AND** the prior's holdings MUST NOT be ×1000 a second time