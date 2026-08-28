## Why

AKShare is represented only by an optional dependency, disabled configuration, an unverified manifest, exclusion logic, and scaffold-specific tests; it has no import, concrete adapter, fetch host, fixture, or verified executable contract. Keeping that future-provider scaffold expands dependency, registry, runtime, and test surfaces without adding a shipped evidence capability.

## What Changes

- Remove the AKShare manifest and disabled provider entry.
- Remove the `akshare` optional dependency and regenerate `uv.lock` so AKShare and dependencies retained only by that extra are no longer resolved.
- Remove the AKShare-specific exclusion from the explicit adapter registry while preserving the existing concrete adapter mapping.
- Remove AKShare-only assertions and update shipped-provider counts and manifest-set expectations; retain general unverified-provider, mandatory-coverage, provenance, and manifest-completeness coverage.
- Do not add a replacement provider or change Feed evidence semantics, provider behavior, mandatory coverage membership, minimums, or verified provider facts.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. AKShare is implementation scaffolding rather than a normative capability, and `skill-capability-surface` explicitly treats provider adapters and manifests as implementation machinery. This Change therefore sets `skip_specs: true` and creates no delta spec.

## Impact

- Dependency metadata: `pyproject.toml`, generated `uv.lock`.
- Provider configuration and manifests: `config/providers.yaml`, `providers/akshare/manifest.yaml`.
- Runtime registry construction: `src/follow_the_money/providers/adapters.py`.
- Provider/config/manifest tests that currently encode AKShare-specific scaffold expectations.
- No public API, serialized schema, living spec, mandatory coverage policy, provider fetch/normalize behavior, Feed output, docs capability claim, or architecture boundary changes.
