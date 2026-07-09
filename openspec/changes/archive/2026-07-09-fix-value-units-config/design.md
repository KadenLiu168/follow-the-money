## Context

`normalizeValueUnits(filerEntry, configSources)` currently applies: `sum < $1B → thousands (×1000)`, `sum === 0 || sum ≥ $1B → dollars`. SEC EDGAR 13F `<value>` is officially in thousands of dollars, so the "most filers emit raw dollars" assumption in the code comment is incorrect; the committed sample confirms thousands. The only safe, testable behavior is to declare the unit per source and stop guessing.

## Goals / Non-Goals

**Goals:**
- Make unit resolution declarative and deterministic via `config.default-sources.json`.
- Preserve idempotency and the `small-fund`/unknown opt-out.
- Eliminate the 1000× amplification hazard.

**Non-Goals:**
- Changing the digest/periodDiff math (already idempotent-safe).
- Auto-detecting units from the filing itself (out of scope; SEC units are constant per form type).

## Decisions

- **Per-source `valueUnit` over heuristic.** Rationale: SEC 13F units are fixed by form type, not by portfolio size; a config flag is the only correct source of truth. Alternative (keep heuristic) rejected: it cannot distinguish a raw-dollar sub-$1B filer from a thousands filer.
- **Default for unmatched source = `'thousands'`.** Rationale: SEC 13F `<value>` is officially thousands; defaulting to the spec value is safer than defaulting to dollars. `small-fund`/`unknown` opt-out preserved.
- **Keep `valueUnitAdjusted` idempotency marker unchanged.** The fix only changes how the unit is *chosen*, not the idempotency contract.

## Risks / Trade-offs

- [Risk] A source missing `valueUnit` would previously fall to the heuristic; now it defaults to `'thousands'`. → Mitigation: `config/default-sources.json` is authored with explicit `valueUnit` for all 8 sources; a validation note is added (see tasks).
- [Risk] Existing tests encode the old magnitude boundaries. → Mitigation: update them to assert config-driven behavior.
