## Why

Canonical Event construction currently skips null effective-time values when choosing the economic projection, synthesizes `instant` precision when all values are null, and can report a common time when only the known subset agrees. This contradicts the accepted ordering and all-key-facts semantics now exposed through `event.structure`.

## What Changes

- Derive `economic_effective_time.value` and `precision` from the first canonical key fact even when its value is null.
- Emit `common_effective_time` only when every key fact has the same non-null value and precision.
- Add focused canonical Event regressions for first-null, all-null, and partially-null inputs, plus one `event.structure` smoke regression.
- Preserve existing `multiple_effective_times` behavior and the current Agent invocation DTO, schema, and contract version.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `deterministic-research-engine`: Clarify nullable effective-time projections for canonical Event construction without changing the accepted ordering rule.

## Impact

- Production behavior changes only in `src/follow_the_money/events.py` within `build_event()` effective-time projection.
- Regression coverage changes in `tests/test_events.py` and `tests/test_agent_invocation_runtime.py`.
- No changes to Agent schemas, `agent_invocation.py`, Event identity, key-fact ordering, Feed, Audit, Market, Watchlist, Scoring, configuration, providers, or dependencies.
