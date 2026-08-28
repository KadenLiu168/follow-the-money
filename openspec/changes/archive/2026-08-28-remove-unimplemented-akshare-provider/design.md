## Context

See `proposal.md` for motivation. The scaffold spans packaging, the checked-in provider registry, manifest discovery, registry construction, and tests, but it has no concrete adapter or executable provider boundary. The living `skill-capability-surface` classifies provider adapters and manifests as implementation machinery, so no semantic capability delta is required.

The current explicit adapter mapping already lists every implemented provider. Its only AKShare accommodation is filtering that manifest before mapping, while `config/providers.yaml` separately carries a disabled AKShare entry. Mandatory coverage rows do not reference AKShare and must remain byte-for-byte unchanged.

The active untracked `simplify-strict-config-resolution` Change overlaps `tests/test_config.py` and the configuration test surface. Apply must confirm the linked Linear issue and blockers, then sequence or isolate the two Changes and re-establish the shared-test baseline before editing; it must not absorb that Change's loader or fixture migration.

## Goals / Non-Goals

**Goals:**

- Make the shipped provider set equal the manifest-backed, concretely implemented provider set.
- Remove AKShare's package-resolution, configuration, manifest, runtime-special-case, and test-only surface together.
- Preserve strict trust-boundary validation and exact mandatory coverage policy.

**Non-Goals:**

- No provider replacement, dynamic discovery, registry abstraction, or adapter refactor.
- No strict config-loader, fetch, normalize, provenance, Feed schema/output, or documentation capability changes.
- No cleanup of unrelated dependencies, helpers, caches, tests, or archived Changes.

## Decisions

### Delete the scaffold at every live ownership point

Delete the manifest and registry row, remove the optional dependency, and let `uv lock` recompute reachability from `pyproject.toml`. This avoids hand-editing generated lock data and removes transitive packages only when no remaining dependency requires them.

Alternative: leave a disabled registry or manifest placeholder. Rejected because either preserves the same speculative surface and keeps shipped providers out of alignment with concrete adapters.

### Remove only the AKShare registry exception

Delete the `pid != "akshare"` filter and leave the explicit `adapter_types` mapping and enablement filtering unchanged. After the manifest is removed, ordinary manifest discovery naturally supplies only implemented provider IDs.

Alternative: derive adapters dynamically from manifests or introduce a plugin registry. Rejected as unnecessary and outside the accepted explicit-registry architecture.

### Separate scaffold assertions from reusable trust-boundary tests

Remove assertions whose only purpose is proving the checked-in AKShare entry is disabled, unverified, absent from mandatory coverage, or not imported. Update the exact provider count and manifest set. Preserve synthetic config tests that reject enabled or coverage-counted unverified providers, plus all verified-provider, mandatory-row/minimum, provenance, and manifest-completeness invariants. Remove or reshape any shipped-manifest loop that becomes vacuous once every shipped manifest is verified rather than preserving a test that cannot exercise its branch.

Alternative: introduce a fake unverified shipped manifest solely to exercise the test. Rejected because test scaffolding must not recreate a live provider scaffold; existing synthetic fixtures exercise the fail-closed loader contract.

### Treat this as a no-spec implementation cleanup

Use `skip_specs: true`; do not create a delta spec or edit living specs. Provider implementation machinery may change without changing the accepted semantic capability surface, and AKShare is not named as a normative provider capability.

## Risks / Trade-offs

- [A transitive package used elsewhere is accidentally removed] → Regenerate with `uv lock`, then run `uv sync --frozen --all-groups` and the canonical quality gate instead of editing `uv.lock` manually.
- [Mandatory coverage is weakened while editing adjacent YAML] → Keep every coverage row, member list, capability, optional flag, and minimum unchanged; retain exact-matrix tests.
- [Registry completeness silently drifts] → Retain exact manifest-set and concrete-adapter completeness assertions after changing the expected shipped set.
- [A concurrent Change makes the shared configuration-test baseline ambiguous] → Confirm Linear scope and blockers, sequence or isolate `simplify-strict-config-resolution`, and keep this Change's diff limited to the AKShare scaffold and directly attributable assertions.
- [Broad residue checks flag intentional history] → Scope live-reference checks to source, config, tests, docs, packaging, and provider directories; do not edit archived Changes or this Change's planning record.
