## Why

The normal production Brief pipeline never calls the implemented Market State classifier and instead publishes a literal all-`unknown` regime/vector on every successful run. This leaves the documented Market State section permanently non-functional while isolated unit tests continue to pass, violating the existing script-owned, data-derived regime contract.

## What Changes

- Collect an explicit daily market-history lookback sufficient to calculate the current change against 20 current-excluded reference changes for every configured dashboard role.
- Re-verify each role's provider symbol, unit, daily-close semantics, and session ownership before that role may contribute to a production classification.
- Bind each dashboard role to an explicit completed-session policy and fail individual metrics closed when history is stale, post-cutoff, unit-incompatible, non-consecutive, or insufficient.
- Build one deterministic market snapshot from Feed market observations and in-window CPI/PCE/PPI releases, containing dashboard returns/anomaly flags, classifier inputs, missing reasons, and evidence provenance.
- Call `classify_market_state` in the normal production pipeline before the editor pass and expose only the script-derived regime/vector and bounded supporting evidence to the editor for explanation.
- Merge the required `market_state_explanation` wording into the rendered Market State section while preventing the editor from changing any script-owned state field.
- Preserve the informational boundary: Market State does not change event scoring, confidence, eligibility, selection, or ordering.
- Replace isolation-only coverage with production-path fixtures proving a sufficiently observed Feed produces non-`unknown` Market State and incomplete inputs degrade visibly and deterministically.

## Capabilities

### New Capabilities

- `production-market-state-pipeline`: Defines historical market-data acquisition, completed-session analytics, deterministic Market State snapshot construction, production Brief integration, provenance, and fail-closed behavior.

### Modified Capabilities

None. The existing Market State voting, coverage, precedence, and informational semantics remain unchanged; this Change activates and verifies them in the production path.

## Impact

- Affected code: Yahoo-compatible market adapter/fetch orchestration, role/session configuration, deterministic market analytics, dashboard assembly, `state.py` missing-role accounting, `pipeline.py` editor evidence projection, Brief integration, and focused fixtures.
- Affected contracts: normalized market-history observations, role-to-session ownership, Market State provenance, and production integration tests.
- Dependencies: reuse the existing `Decimal` formula engine and `exchange-calendars`; no new LLM pass, external service, paid credential, scoring input, or product surface is introduced.
