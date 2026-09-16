## Why

ECO-124 proved deterministic current/change evidence through SEC 13F and CFTC COT, but the two Provider-specific pure cores still duplicate canonical numeric handling and subtraction-based derivation. The duplicated arithmetic depends on ambient Python decimal context, so a caller-controlled precision change can alter derived output and undermine the existing same-input/same-output guarantee.

## What Changes

- Add a small Producer-internal semantic core for measured numeric facts and derived numeric facts.
- Give every derived numeric fact immutable deterministic derivation metadata containing its operation and ordered references to its input fact objects.
- Centralize bounded canonical-decimal parsing, formatting, validation, and owned-context arithmetic so results do not depend on ambient decimal state.
- Migrate only the shared SEC 13F and CFTC COT numeric fact construction and subtraction-based derivations proven by ECO-124.
- Add regression verification for internal derivation provenance, ambient-context independence, existing Provider behavior, and byte-identical Feed projection.
- Keep comparison policy, entity identity, Provider-specific provenance projection, and existing CFTC formula descriptors Provider-specific.
- Do not change the Feed wire contract, SEC/CFTC v2 payloads, canonical identity, Provider contract versions, manifests, Host Agent behavior, or introduce a formula registry or generic semantic framework.

## Capabilities

### New Capabilities

- `deterministic-derived-metrics`: Defines the internal measured-numeric-fact and deterministic-derivation contract shared by validated Producer vertical slices while preserving Provider-specific semantics and existing Feed projection.

### Modified Capabilities

None.

## Impact

- Producer internals: a narrow module under `src/follow_the_money/semantic/` and focused migration in `src/follow_the_money/providers/sec_13f.py` and `src/follow_the_money/providers/cftc_cot.py`.
- Numeric validation ownership: existing canonical numeric guards may move behind the semantic core while retaining compatibility at current internal call sites.
- Tests: focused semantic primitive tests plus SEC, CFTC, Feed determinism, validation, and canonical-byte regressions.
- No schema, manifest, configuration, dependency, public API, Feed domain, Provider set, publication, snapshot, or Host-Agent change.
