## Context

See `proposal.md` for motivation and the delta specs for normative behavior. ECO-26 now resolves Provider manifests before normal Feed runtime work and carries each manifest's `role_mappings` into one immutable `ProviderEntry` and its Feed snapshot. However, manifest validation currently accepts `mapping_verified: true` without mapping-level evidence, canonical roles retain a `source_provenance` string that is not consumed outside config tests, Yahoo adapter planning fans out over every canonical role, and the mandatory coverage row claims all 13 roles.

The current shipped truth is asymmetric. The only checked-in Yahoo chart fixture identifies `meta.symbol == "^GSPC"`; it can support the S&P 500 mapping contract after explicit binding. The CSI 300 role's cited repository path is absent and cannot support its current verified claim. The remaining eleven mappings are already false and carry manifest reasons. MarketSnapshot already checks `mapping_verified` before consuming observations, but it remains a post-Feed retained library with no production orchestration caller.

## Goals / Non-Goals

**Goals:**

- Extend the resolved manifest mapping already established by ECO-26 instead of adding a registry or a second resolver.
- Encode one closed asymmetric mapping-verification state that is deterministic to validate and serialize.
- Complete every mapping and coverage validation before adapter construction, rate-state mutation, Provider I/O, or Feed publication.
- Make adapter planning and Provider-level coverage derive from the same resolved verified subset while preserving the complete mapping audit record.
- Migrate current declarations to the narrowest supported truth: retain S&P 500 only if its fixture satisfies the new contract and downgrade CSI 300.

**Non-Goals:**

- Deterministically deciding financial semantics from arbitrary evidence, researching additional mappings, or validating remote content at startup.
- Generalizing mapping verification across a plugin framework or adding a separate evidence database/service.
- Changing Feed item/schema shape, semantic identity algorithms, Provider outcome taxonomy, or publication behavior.
- Wiring MarketSnapshot, adding Agent contracts, or changing retained analytical orchestration.

## Decisions

### 1. Put one typed provenance branch inside each authoritative manifest mapping

Keep `providers/<provider_id>/manifest.yaml.role_mappings` as the mapping authority. A verified entry adds one closed nested object:

```yaml
- role_id: sp500
  instrument: "^GSPC"
  unit: index
  mapping_verified: true
  verification_provenance:
    kind: repository_fixture
    reference: providers/yahoo_market/fixtures/chart.json
```

An unverified entry keeps `reason` and has no `verification_provenance`. Validation uses an exclusive branch:

- `mapping_verified: true` requires exactly `verification_provenance` and forbids `reason`;
- `mapping_verified: false` requires exactly a non-empty `reason` and forbids `verification_provenance`.

The tuple binding is structural rather than duplicated: `provider_id` comes from the owning manifest, while `role_id`, `instrument`, and `unit` are siblings of the nested provenance object in that one mapping. The resolved immutable mapping and its snapshot preserve that full record. This avoids adding tuple copies that could drift.

Remove canonical-role `source_provenance` from strict application config and `MarketRole`: it is currently only a parallel mapping-evidence string and has no runtime consumer. Retain the ECO-26 canonical-role `instrument`, `unit`, and `mapping_verified` fields as validation-only compatibility mirrors because current contract/tests explicitly require their parity; the manifest remains authoritative for execution.

Alternative considered: keep `source_provenance` and require it to equal the manifest reference. Rejected because that preserves two mapping-level provenance authorities without a consumer need. A separate verification registry was rejected because it recreates the split-source problem ECO-26 removed.

### 2. Support two narrow provenance kinds under Provider-owned policy

Use a closed `kind` enum and one `reference` field:

- `repository_fixture`: a normalized repository-relative path under `providers/<provider_id>/`; absolute paths, `..` traversal, symlink escape, missing paths, directories, and paths owned by another Provider fail.
- `authoritative_https`: a canonical HTTPS URL with no userinfo or fragment whose host and port are already permitted by the owning manifest's exact contract URL or declared fetch, redirect, or source-link host policies. No request is made during static resolution.

For a Yahoo repository fixture that parses as the shipped chart JSON shape, require exactly one usable chart result and compare its explicit `chart.result[0].meta.symbol` with the mapping instrument. The deterministic check proves fixture identity, not that the symbol semantically represents the financial role. Role/unit meaning remains a reviewed declaration bound to the cited evidence.

Reject opaque local text as structured proof when the provenance kind promises a Yahoo chart fixture. ECO-27 does not add a generic document parser, HTML extractor, fuzzy matcher, or remote freshness checker.

Alternative considered: accept any existing repository file as evidence. Rejected because path existence alone cannot prevent the current CSI-style unrelated or stale reference from being presented as tuple evidence. Adding a new Provider-wide verification-host registry was also rejected because the existing Provider URL policies can express the currently needed HTTPS boundary without a second policy family.

### 3. Derive runnable mappings only after full static composition

During existing strict config/manifest composition, validate mappings in deterministic manifest order, validate the canonical-role mirror tuple, and derive the verified runnable mapping subset from the resolved `ProviderEntry`. Do not delete unverified mappings or construct a second public model. The full `role_mappings` tuple remains the audit representation; adapter planning filters it through its verified state and resolves each verified `role_id` to the canonical role semantics needed by the adapter.

If an enabled Provider with market-role mappings has no verified runnable entry, raise the existing `ConfigError`/startup category during static resolution. Explicit registry disablement remains the supported no-work state. This check occurs before `_production_adapters` and therefore before the existing output-root, rate-registry, network, and publication boundaries established by ECO-26.

Alternative considered: build all adapters and reject unverified items during normalization. Rejected because canonical `instrument_id` would already have crossed the acquisition/Feed trust boundary. Silently returning an empty adapter list was rejected because it makes an enabled Provider appear operational while doing no useful work.

### 4. Plan Yahoo adapters from the authoritative verified subset

Yahoo production planning iterates canonical roles in their existing deterministic order but creates an adapter only when the corresponding resolved manifest mapping is verified and tuple-parity validation has passed. Adapter constructor inputs continue to be `instrument`, `role_id`, and `unit` from the resolved mapping/canonical composition; no item-level `mapping_verified` field is added.

Provider snapshots continue serializing every resolved mapping. Because verification provenance and the CSI truth correction change `provider_contracts`, affected Feed semantic digests are expected to change through the existing identity projection; the digest algorithm itself does not change.

MarketSnapshot remains untouched except for regression tests proving its existing early `unverified_mapping` outcome, including a defensive fixture containing a matching canonical item. No production caller is added.

### 5. Narrow coverage to generic verified market data

Replace the unsupported `china_hk_cross_asset_market` / `market_data_all_13_roles` row with a Provider-level row named and described as generic `verified_market_data`, still backed by `yahoo_market` with the existing minimum of one. Its meaning is only that the enabled Provider has at least one verified runnable market mapping; the zero-mapping startup check makes that static claim truthful.

Do not enumerate roles in the coverage engine or derive per-role health. Runtime Provider outcome semantics remain Provider-level: a partial Yahoo run still follows existing partial/degradation rules. Documentation and checked snapshots that mention all 13 runnable roles, China/HK breadth, or cross-asset completeness must be narrowed only where needed for contract truth.

Alternative considered: add one coverage row per role. Rejected because it would redesign coverage and Provider outcome semantics beyond ECO-27. Keeping the old label while filtering adapters was rejected because the declared capability would remain false.

## Risks / Trade-offs

- [A checked-in fixture proves symbol identity but not arbitrary financial semantics] → Keep semantic approval human/review-owned, make the provenance tuple explicit, and limit deterministic validation to structural claims it can actually establish.
- [Removing `source_provenance` changes config fixtures and the `MarketRole` constructor] → Remove only this unused duplicate, update direct constructors narrowly, and retain required mirror parity for `instrument`, `unit`, and `mapping_verified`.
- [A future authoritative reference may use a host absent from current Provider URL policy] → Fail closed until the owning manifest explicitly permits that host in a future scoped change; do not add permissive wildcard behavior.
- [Filtering to verified mappings reduces Yahoo evidence and changes Feed digests/coverage labels] → Treat this as the intended trust correction, preserve unverified mappings in snapshots, and rerun deterministic identity, degradation, and publication regression suites.
- [Coverage stays Provider-level and cannot express per-role runtime completeness] → Use the deliberately narrow `verified_market_data` claim and defer role-level accounting rather than implying unsupported precision.

## Migration Plan

1. Add failing contract tests for asymmetric provenance, path/URL/Provider/tuple checks, Yahoo `meta.symbol`, zero verified mappings, pre-runtime-mutation ordering, verified-only planning, snapshot completeness, truthful coverage, and MarketSnapshot's secondary guard.
2. Extend the manifest/resolved mapping parser with the closed provenance branch and deterministic validators; remove the unused canonical `source_provenance` mirror while preserving the existing tuple parity checks.
3. Migrate shipped Yahoo mappings without grandfathering: attach the checked-in `^GSPC` fixture to S&P 500, change CSI 300 to unverified with a deterministic missing-evidence reason, retain all other false mappings and reasons, and verify every branch.
4. Filter production Yahoo adapter planning to verified mappings, add the zero-runnable startup guard, and retain all mappings in deterministic Provider snapshots.
5. Narrow the market coverage row and any directly affected capability documentation/snapshots; do not introduce role-level coverage logic.
6. Run focused tests, the repository quality gate, `openspec doctor`, target strict validation, and all-spec strict validation.

Rollback is a normal source rollback before publication. A rollback after new Feed artifacts exist may restore broader unverified execution and older contract snapshots, so it must not be represented as a safe trust-preserving operational fallback; keep the previous valid Feed under the existing monotonic publication contract and correct forward instead.
