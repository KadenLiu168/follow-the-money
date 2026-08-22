## Context

See `proposal.md` for motivation and `specs/feed-evidence-pipeline/spec.md` for the behavioral contract. The current `AppConfig` loader combines `config/config.yaml` and `config/providers.yaml`, but it requires only a small top-level subset, supplies many `.get(..., default)` values, passes only selected scoring fields, and constructs Market State, calendar, safety, and rate-registry models entirely from Python defaults. `FeedLimits.lock_timeout_seconds` is consumed by collection even though it is not shipped in YAML.

Provider truth is split more deeply. `config/providers.yaml` supplies the `ProviderEntry` objects used by rate, coverage, enablement, orchestration, and Feed snapshots, while each adapter calls the manifest loader and interprets manifest mappings independently. Manifest validation therefore occurs after configuration load and, in the normal Feed path, after output-root preparation, lock acquisition, planning, and rate-registry creation. The Feed schema deliberately leaves each embedded Provider snapshot as an opaque hashed object, so this Change can normalize its contents without changing the external schema shape or identity algorithm.

## Goals / Non-Goals

**Goals:**

- Preserve the existing configuration and Provider model family while making production construction strict and explicit.
- Give distinct global safety ceilings, Provider contract facts, activation policy, and coverage policy distinct field ownership even when they participate in one effective decision.
- Complete all static composition before output-root, lock, rate-state, collection, or publication work.
- Keep the Feed snapshot a deterministic projection of the exact resolved Provider object supplied to its adapter.
- Make source-authority tests sensitive to ignored declarations and hidden fallback paths.

**Non-Goals:**

- Re-evaluating the evidence behind any current role mapping or changing instruments, symbols, verification facts, Providers, coverage groups, or minimums.
- Replacing the configuration framework, generalizing arbitrary Provider plugins, or redesigning adapter acquisition protocols.
- Changing Feed health, semantic identity, canonical serialization, publication durability, or the external Feed schema.
- Connecting retained post-Feed libraries or introducing any Agent runtime, LLM, prompt, or later Skill–Agent contract type.

## Decisions

### 1. Assign authority at field granularity

Use this ownership matrix during migration:

| Authority | Owned fields |
| --- | --- |
| `config/config.yaml` | configuration schema, application identity and paths, timezone/freshness/lag policy, global Feed limits and ceilings, scoring, Market State, calendar, safety lexicon, rate-registry contract, session and source-family registries, entities, watched companies, and the role registry's application/domain semantics |
| `providers/<provider_id>/manifest.yaml` | manifest contract version and Provider identity, name and provenance tier, verification evidence, authentication/user-agent/protocol facts, common and Provider-specific fetch/redirect/source-link rules, charset/content type, Provider request/response constraints, rate policy, pagination, empty-window behavior, source identity/timing/units/freshness, existing role-mapping declarations, and fixture provenance |
| `config/providers.yaml` | registry schema, Provider ID plus shipped `enabled` policy, and coverage rows including members, minimums, capabilities, and optionality |

Where role declarations currently overlap, `config/config.yaml` remains authoritative for the canonical role set, role-to-Provider reference, economic/session semantics, and application availability policy; the owning manifest is authoritative for the Provider-specific instrument/unit/mapping declaration. Existing duplicate instrument, unit, or mapping-verification values may remain only as checked compatibility assertions and must preserve their present truth until ECO-27.

Global Feed bounds and Provider-specific limits are separate fields, not duplicate authorities. The resolved contract must apply the global bound as a ceiling and the manifest value as the Provider contract, or reject an impossible composition; neither source silently replaces the other.

Remove redundant registry fields when their removal is narrow and test fixtures can migrate directly. If a legacy field must remain, encode an explicit parity check and exclude it from behavior. In particular, Provider-level `group` never supplies coverage membership. Coverage is represented only by coverage rows; the existing Feed configuration snapshot already embeds those rows, so the Provider contract snapshot does not need a singular coverage group.

Alternative considered: leave all current duplicate fields and compare the two complete records. Rejected because it preserves two parsers and makes future authority unclear even when parity is checked. Moving enablement and coverage into manifests was also rejected because deployment policy and multi-group coverage are not intrinsic Provider facts.

### 2. Make checked-in configuration closed and complete

Each owned mapping receives an explicit allowed/required key set and value validation. Production loading uses required indexing after validation and passes every field into the resolved dataclass; `.get(..., default)` is not used for normative values. Nested collections receive the same treatment so a missing scoring map, Market State threshold, calendar value, safety term set, rate-registry field, Feed limit, session field, or Provider rule cannot be masked by a Python default.

Add any currently consumed but unshipped normative value, including `feed.lock_timeout_seconds`, to its authoritative YAML. Python dataclass defaults may remain only for direct language-level convenience where production loading always supplies the field explicitly; tests must prove deleting the YAML field fails. Closed schemas continue to reject unknown fields and unsupported versions.

Alternative considered: mechanically remove every dataclass default. Rejected because constructor syntax is not the trust boundary; strict production composition and tests provide the behavioral guarantee with less unrelated churn.

### 3. Resolve Provider policy and manifest once

Evolve the existing manifest loader and `ProviderEntry` boundary instead of adding a new configuration subsystem. Static loading performs these steps in deterministic Provider-ID order:

1. Strictly parse the application config and Provider registry.
2. Validate unique registry identities and complete coverage references.
3. Load and strictly validate the supported manifest for every enabled Provider; disabled entries may also be validated when present, but cannot become required for execution unless referenced by a mandatory policy.
4. Validate Provider ID/version/verification, role and source-family references, shared rate-scope equality, mapping mirrors, and any retained compatibility mirrors.
5. Materialize one immutable resolved `ProviderEntry` per registry entry from manifest facts plus the single `enabled` policy; derive coverage only from `CoverageMatrix`.

The resolved representation includes all common fields used by transport, normalization, orchestration, rate handling, and snapshots, plus only the narrowly required typed Provider-specific declarations. Adapter constructors receive the resolved Provider entry (and existing application-owned inputs such as watched CIKs or role/session context) and do not call `load_manifest()` or interpret a filesystem mapping. Adapter-specific constants unrelated to configuration remain code.

Alternative considered: pass the raw manifest mapping from startup to adapters. Rejected because it would avoid a second file read but would retain independent parsing and hidden manifest defaults rather than one validated contract.

### 4. Put static resolution before all normal runtime state

The Feed entry resolves the complete `AppConfig`, including manifests and cross-source validation, before selecting or creating the output root, starting the collection deadline, acquiring the collection lock, reading latest state, constructing rate state, or building adapters. Static failures map to the existing input/configuration startup outcome and exit category; they do not create a new taxonomy.

This order makes tests able to assert zero client calls, zero adapter fetches, no rate files, no dated artifact, and unchanged `latest.json`. It also avoids leaving a collection lock artifact for a configuration that never became runnable. Failures that depend on existing latest contents, filesystem durability, or live Provider responses remain in their current later phases.

Alternative considered: validate manifests lazily while building the production adapter registry. Rejected because the current lazy location occurs after persistent runtime initialization and cannot satisfy the static trust-boundary guarantee.

### 5. Project snapshots and runtime decisions from resolved objects

`provider_contracts` snapshots are constructed only from the resolved Provider entries supplied to adapters. Common nested members retain deterministic ordering and redaction; coverage rows remain in the Feed configuration snapshot. A Provider's rate, charset, host, response, pagination, empty-window, and verification members therefore cannot diverge between adapter behavior, orchestration, and its embedded contract hash.

Changing a manifest-owned fixture value must alter the adapter-observed resolved field and snapshot projection in the same test. The external Feed schema, semantic projection allowlist, digest algorithm, run-ID derivation, and canonical serialization remain unchanged; naturally changed resolved snapshot content is handled by the existing ECO-25 identity rules.

Alternative considered: build snapshots directly from manifests. Rejected because a direct manifest snapshot would not prove that the adapter used the same validated and policy-composed object.

### 6. Freeze financial mapping truth for ECO-27

Migration compares the existing config role declarations and manifest role mappings structurally and preserves all current symbols, units, Provider assignments, `mapping_verified` values, reasons, and the 13-role set. A contradiction discovered during Apply becomes a startup-validation finding unless the existing sources can be normalized without changing truth. This Change does not perform new external research or decide whether a mapping deserves verification; that evidence review remains ECO-27.

## Risks / Trade-offs

- [Strict completeness exposes previously masked missing fields in shipped files and tests] → Add RED missing-field and source-mutation tests first, then update checked-in YAML and fixture builders together with the parser.
- [Moving common contract fields into manifests can create a large noisy migration] → Limit changes to fields that already affect runtime or are required by the accepted Provider contract; remove registry duplicates mechanically and avoid adapter redesign.
- [Provider-specific protocol sections do not fit the current common dataclass] → Add only the typed fields consumed by current adapters and pass existing application-owned context separately; do not introduce an extensible plugin schema.
- [Role mapping overlap could accidentally change financial truth] → Capture current role/mapping values in regression fixtures, require parity during migration, and prohibit value changes in this Change.
- [Snapshot content changes produce new semantic Feed identities] → Preserve the existing identity algorithm and schema; verify deterministic snapshots and legacy embedded-Feed validation rather than pinning old incorrect runtime-contract hashes.
- [Validating disabled manifests could block an intentionally unavailable optional Provider] → Require supported verified manifests for enabled and mandatory-policy Providers; keep any broader disabled-manifest validation explicit and non-activating.

## Migration Plan

1. Add RED tests for representative YAML authority, required-field deletion, manifest version/identity/verification failures, mirror mismatch, multi-group coverage, adapter/snapshot parity, and pre-runtime failure side effects.
2. Normalize the shipped application and Provider registry YAML to the ownership matrix, adding explicit missing normative values without changing their current effective values.
3. Strictly validate existing manifests and move only current Provider contract truth needed by resolved runtime consumers; preserve all market-role mapping facts.
4. Evolve existing models/loaders to compose immutable resolved Provider entries and make adapters consume them without filesystem re-reads.
5. Move complete static resolution ahead of output-root, lock, latest, rate, adapter, and collection work; update snapshots and docs/SKILL claims that describe configuration authority.
6. Run focused config/manifest/provider/Feed regressions, the full repository quality gate, OpenSpec doctor, and strict Change/all validation.

Rollback is code/config-only and requires reverting the normalized loader, registry, manifests, and adapter construction as one unit. No data migration or Feed schema rollback is required; previously published Feed artifacts remain validated from their embedded producer configuration and Provider contracts.
