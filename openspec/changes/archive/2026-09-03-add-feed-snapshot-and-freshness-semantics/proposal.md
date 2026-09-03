## Why

Recurring Feed execution currently conflates a successful check with a newly published observation and has no cadence-aware way to distinguish unchanged valid evidence from stale evidence. ECO-77 must close this ambiguity before scheduled execution expands to more Providers or broader Feed behavior.

## What Changes

- **BREAKING**: Extend newly generated Feed manifests with a required, closed Provider freshness result and advance the logical/manifest contract version; existing evidence payload shapes remain unchanged.
- Replace each Provider manifest's opaque freshness policy string with one verified, structured cadence contract for `weekly`, `scheduled`, `event-driven`, or `market-session` evaluation, including only the parameters needed for deterministic validity.
- Reuse existing payload observation/effective times, `source.published_at` / `source.updated_at`, Provider `retrieved_at`, and Feed `generated_at` as the respective time authorities instead of duplicating timestamps.
- Permit a current successful no-new-observation check to carry forward that Provider's unchanged evidence slice only from the fully validated active Feed bundle, preserving item identity, source timestamps, provenance, and lineage.
- Evaluate each Provider snapshot deterministically as `fresh`, `valid_unchanged`, `stale`, `no_snapshot`, or `not_evaluated`; a stale snapshot remains explicit and cannot be made current by changing retrieval or generation metadata.
- Preserve existing Provider completeness and failure admission: failed, partial, skipped, missing, ambiguous, or identity-mismatched acquisition cannot use retained evidence to become successful or publishable.
- Add focused deterministic contract, configuration, assembly, identity, validation, bundle, and consumption tests plus truthful Feed/configuration documentation.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `feed-evidence-pipeline`: Add cadence-authoritative Provider snapshot carry-forward and freshness evaluation to the existing manifest-led evidence contract without changing Provider completeness or the evidence-only boundary.

## Impact

Affected surfaces include Provider manifest parsing and resolved contract snapshots, Feed planning/assembly and active-bundle loading, logical and manifest schemas/version handling, semantic identity, validation and consumer health, deterministic Feed tests/fixtures, `docs/feed-contract.md`, configuration documentation, and current capability documentation. No new Provider, dependency, storage subsystem, credential, network fallback, application runtime, Host Agent behavior, LLM/model path, analysis, ranking, scoring, or interpretation is introduced.
