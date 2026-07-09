## Why

`normalizeValueUnits` infers 13F value units from portfolio magnitude (sum < $1B → treat as thousands, ×1000). This heuristic is both factually wrong against the SEC 13F spec (where `<value>` is officially in thousands) and a latent data-correctness hazard: a filer that stores raw dollars with a sub-$1B portfolio would be wrongly multiplied by 1000. The leading comment even contradicts the committed `feed-13f.json` sample (Berkshire `valueUsd: 488930` is in thousands, not raw dollars). No source in `config/default-sources.json` declares a unit, so the `small-fund` escape hatch never fires.

## What Changes

- `config/default-sources.json`: add an explicit `valueUnit` field (`'thousands'` | `'dollars'`) to every 13F source. SEC 13F filers are uniformly `'thousands'`.
- `lib/enrich/normalize-value-units.js`: resolve the unit from the matching source's `valueUnit` instead of the `<$1B` sum heuristic. Remove the magnitude-based branch; keep idempotency (`valueUnitAdjusted`) and the `small-fund`/unknown opt-out.
- `lib/enrich/normalize-value-units.js` header comment: correct to match the SEC 13F thousands convention and the committed sample.
- `references/data-formats.md`: document the new `valueUnit` config contract and drop the magnitude-inference description.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `value-units-normalization`: replace the magnitude-heuristic requirement with a config-driven `valueUnit` requirement.

## Impact

- **Code**: `lib/enrich/normalize-value-units.js`, `config/default-sources.json`, `references/data-formats.md`.
- **Behavior**: unit detection becomes declarative and deterministic; removes the 1000× amplification risk for raw-dollar sub-$1B filers. No change for the 8 currently tracked filers (all become `'thousands'`, same effective result as today).
- **Config**: `config/default-sources.json` gains a required `valueUnit` per 13F source.
- **Tests**: existing idempotency/scenario tests must be updated to the config-driven model; add a test asserting a config `valueUnit: 'dollars'` source is not multiplied.
- **No API / dependency / network changes.**
