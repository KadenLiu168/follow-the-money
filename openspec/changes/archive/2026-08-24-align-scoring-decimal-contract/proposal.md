## Why

The accepted `deterministic-research-engine` scoring requirement combines the repository-owned normative Decimal context with unconditional equality to every pre-ECO-29 Decimal result. Those promises conflict for fractional Systemic Breadth values because the historical calculation could inherit ambient Decimal precision and rounding, while the current implementation correctly evaluates `affected_groups / 9 * 100` inside the normative context.

The living contract should describe the deterministic scoring semantics that the current implementation and `docs/scoring.md` already follow, rather than preserve an accidental historical Decimal tail. A nearby `selection` reference in the Market State documentation also needs the current neutral term `ranking`.

## What Changes

- Modify the `Versioned deterministic scoring` requirement so neutral terminology preserves formulas, configured weights, mappings, bins, missing-data semantics, and operation order, while the repository-owned normative Decimal context determines numerical results.
- Narrow the equivalent-vector scenario so it proves semantic parity and ambient-context independence instead of unconditional equality with historical implementation artifacts.
- Plan focused regression coverage using a fractional Systemic Breadth input to prove both Systemic Breadth and downstream Event Significance are invariant under materially different ambient Decimal precision and rounding settings.
- Correct only the final Market State sentence in `docs/scoring.md` from `selection` to `ranking`.
- Preserve the scoring model, configuration, ranking behavior, retained-library boundary, and current production implementation unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `deterministic-research-engine`: Clarify that current normative Decimal arithmetic is authoritative while neutral scoring terminology preserves the existing scoring semantics rather than historical ambient-context numeric artifacts.

## Impact

- Contract delta: `openspec/specs/deterministic-research-engine/spec.md` through this Change's delta spec.
- Eventual focused tests: existing scoring tests covering `significance_components(...)` and `event_significance(...)`, including fractional Systemic Breadth under hostile ambient Decimal contexts.
- Eventual focused documentation: the stale Market State terminology in `docs/scoring.md` only.
- No production-code, scoring-configuration, ranking, provider, Feed, schema, Agent Contract, orchestration, dependency, or archived ECO-29 change is expected.
