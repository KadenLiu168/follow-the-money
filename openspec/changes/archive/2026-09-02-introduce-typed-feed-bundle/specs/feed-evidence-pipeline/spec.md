## ADDED Requirements

### Requirement: Typed Feed bundle has one authoritative manifest
Every newly generated Feed SHALL consist of canonical `feed-manifest.json` bytes and exactly one canonical domain artifact for each existing Feed payload discriminator: `news`, `macro_release`, `policy`, `market_data`, `flow`, `positioning`, `filing`, and `calendar`. Each item SHALL occur in exactly one artifact selected solely by its `payload.type`; each required artifact SHALL exist even when its `items` array is empty. Grouping SHALL NOT depend on Provider identity and SHALL introduce no new evidence category.

The manifest SHALL be the only authoritative bundle entry point and SHALL contain bundle identity, window and cutoff, truthful generation metadata, producer/configuration/Provider contracts, Provider outcomes, pipeline result, schema descriptors, and a complete artifact inventory. It SHALL contain no evidence item, duplicated evidence payload, analysis, ranking, signal, regime, impact, or recommendation. A domain artifact SHALL contain only its artifact schema version, bundle `run_id`, domain discriminator, and evidence items.

#### Scenario: Mixed evidence is routed
- **WHEN** normalized evidence contains items with different supported `payload.type` values
- **THEN** each item appears once in the matching domain artifact and no Provider identity affects routing

#### Scenario: A domain has no evidence
- **WHEN** a valid run produces no item for one or more supported payload types
- **THEN** the manifest inventories the corresponding required empty domain artifacts

#### Scenario: Consumer discovers available evidence
- **WHEN** a consumer reads a valid manifest
- **THEN** its closed inventory identifies every required domain, canonical relative artifact path, item count, byte size, and SHA-256 digest without inspecting evidence payloads

#### Scenario: Intelligence enters the bundle
- **WHEN** the manifest or a domain item contains prohibited financial interpretation or investment intelligence
- **THEN** bundle validation rejects the candidate before publication or consumption

### Requirement: Feed bundle validation fails closed
A Feed bundle SHALL validate its manifest and every inventoried artifact against their supported schema majors and semantic invariants before publication or use. Validation SHALL require the exact supported domain set once each in deterministic domain order; safe canonical repository-relative artifact paths; canonical bytes; matching declared byte sizes and SHA-256 digests; matching artifact schema versions, domains, and bundle `run_id`; deterministic item order; payload/domain agreement; and unchanged item provenance semantics. Validation SHALL reconstruct the logical Feed semantic projection from manifest metadata and domain items in the existing global `(source.knowledge_available_at, id)` order, recompute `content_digest` and cutoff-derived `run_id`, and reject missing, extra, corrupt, inconsistent, mixed-generation, or identity-invalid bundles.

#### Scenario: Required artifact is missing
- **WHEN** the manifest inventories a required artifact whose file is absent
- **THEN** validation rejects the whole bundle and exposes no partial evidence as consumable

#### Scenario: Artifact bytes are corrupted
- **WHEN** an artifact's canonical bytes, declared size, or declared SHA-256 differ
- **THEN** validation rejects the whole bundle

#### Scenario: Generations are mixed
- **WHEN** an artifact has another `run_id`, domain, schema version, or generation-qualified path
- **THEN** validation rejects the whole bundle even if the artifact is otherwise valid

#### Scenario: Inventory is incomplete or duplicated
- **WHEN** a supported domain is missing, duplicated, reordered, or supplemented by an unknown domain
- **THEN** the closed inventory fails validation

#### Scenario: Provenance is changed during routing
- **WHEN** reconstruction finds that an evidence item no longer satisfies existing source, lineage, time, identity, or payload semantics
- **THEN** validation rejects the bundle rather than repairing or promoting the evidence

### Requirement: Current single-file Feed has manifest-absent read compatibility
During migration, a consumer SHALL first look for `feed-manifest.json`. When it exists, the consumer SHALL validate and use only that bundle and SHALL NOT fall back to `latest.json` after any manifest or artifact error. Only when the manifest is absent MAY the consumer load an existing supported-major `latest.json` through the legacy schema, semantic, provenance, identity, and health validation path. New production SHALL NOT create or replace `latest.json`.

#### Scenario: Valid bundle is present with legacy latest
- **WHEN** both `feed-manifest.json` and `latest.json` exist
- **THEN** the consumer uses only the manifest-selected bundle

#### Scenario: Present bundle is invalid
- **WHEN** `feed-manifest.json` exists but the manifest or any required artifact is invalid
- **THEN** consumption fails closed without falling back to `latest.json`

#### Scenario: Only legacy latest exists
- **WHEN** `feed-manifest.json` is absent and a supported valid `latest.json` exists
- **THEN** the consumer may consume that legacy Feed with its existing health and warning semantics

#### Scenario: New generation succeeds
- **WHEN** a new producer publishes a Feed after this change
- **THEN** it publishes the bundle contract and does not dual-write `latest.json`

### Requirement: Current-state migration activates the first bundle without Provider work
Repository deployment SHALL recognize a valid current `feeds/latest.json` with no manifest as pre-bundle product state. A migration-only invocation SHALL deterministically split that validated Feed into the typed bundle, preserve its semantic `content_digest`, `run_id`, evidence, provenance, cutoff, pipeline, and checkpoint identity, publish the first manifest-led bundle through the bundle publication boundary, remove `latest.json` in the same repository generated-state commit, perform zero Provider requests, and exit before collection. Missing or invalid required migration state SHALL fail closed without deleting the legacy product or advancing continuity.

#### Scenario: Valid current latest is migrated
- **WHEN** deployment finds a valid legacy latest, matching checkpoint, and no bundle manifest
- **THEN** it publishes an equivalent validated bundle, removes `latest.json` in the same generated-state commit, performs zero Provider requests, and leaves checkpoint identity unchanged

#### Scenario: Legacy product cannot be trusted
- **WHEN** latest, checkpoint, schema, identity, provenance, or repository state is invalid or inconsistent
- **THEN** migration makes zero Provider requests and does not partially create or activate a bundle

#### Scenario: Bundle state already exists
- **WHEN** a valid manifest-led bundle is present
- **THEN** current-state migration does not reinterpret `latest.json` as another authority

## MODIFIED Requirements

### Requirement: Single authoritative production configuration
Production configuration SHALL assign exactly one authoritative checked-in source to each normative field: application and deterministic-domain runtime fields to `config/config.yaml`, Provider-specific contract facts to the owning Provider manifest, and Provider activation plus coverage policy to `config/providers.yaml`. Static startup resolution SHALL require, parse, validate, and explicitly materialize every normative field from its authority without silently substituting a Python or loader default. A duplicated field retained for compatibility SHALL be validation-only, SHALL match its authority, and SHALL NOT independently affect runtime behavior. Coverage membership SHALL derive only from the coverage matrix and SHALL support one Provider belonging to multiple coverage groups without a Provider-level single-group authority.

#### Scenario: YAML-owned value changes
- **WHEN** a valid representative application, Feed, scoring, Market State, calendar, safety, rate-registry, or other YAML-owned runtime value changes
- **THEN** the resolved runtime configuration reflects that declared value without requiring a Python-code change

#### Scenario: Required normative value is missing
- **WHEN** a required normative field is absent from its authoritative checked-in source
- **THEN** static startup fails through the existing configuration/startup failure category instead of using a language-level or loader fallback

#### Scenario: Compatibility mirror disagrees
- **WHEN** a retained duplicate declaration differs from its authoritative field
- **THEN** static startup fails closed and neither declaration independently controls runtime behavior

#### Scenario: Provider belongs to multiple coverage groups
- **WHEN** the coverage matrix lists one Provider in more than one row
- **THEN** coverage assessment uses every declared matrix membership and ignores any Provider-level single-group value as coverage authority

#### Scenario: Static resolution fails before runtime mutation
- **WHEN** configuration, manifest, version, identity, verification, or cross-source reference validation fails
- **THEN** the Feed makes zero Provider network requests, performs no normal collection work, does not create or mutate rate-registry state, and does not publish or replace the active `feeds/feed-manifest.json` bundle

### Requirement: Verified mappings gate canonical Feed identity
Production planning for an enabled market Provider SHALL create canonical market-role acquisition work only for mappings that passed the evidence-backed verification contract. An unverified mapping SHALL NOT emit a Feed item whose `market_data.instrument_id` asserts that canonical role identity, and SHALL NOT be made eligible by attaching an item-level unverified flag after acquisition. All mappings SHALL remain visible in deterministic order in the resolved Provider contract and corresponding Feed manifest `provider_contracts` snapshot, including verification provenance for verified mappings and reasons for unverified mappings. The evidence item payload schemas SHALL remain unchanged; only their typed bundle envelopes and bundle manifest SHALL change.

#### Scenario: Production market adapters are planned
- **WHEN** an enabled market Provider has both verified and unverified resolved role mappings
- **THEN** production planning creates adapters only for the verified mappings in canonical role order

#### Scenario: Unverified mapping cannot emit canonical role evidence
- **WHEN** a role mapping remains unverified
- **THEN** no production adapter is planned for that mapping and no Feed item can enter through that path with its canonical `market_data.instrument_id`

#### Scenario: Provider contract snapshot is built
- **WHEN** the resolved Provider contract contains verified and unverified mappings
- **THEN** its deterministic manifest snapshot exposes every mapping with the verified provenance or unverified reason required by its state

#### Scenario: Verification fails before runtime mutation
- **WHEN** any mapping verification, evidence-reference, tuple-association, or mapping-parity check fails during static resolution
- **THEN** the Feed makes zero Provider network requests, performs no normal collection work, does not create or mutate rate-registry state, and does not publish or replace the active Feed bundle

## REMOVED Requirements

### Requirement: Feed is the serialized external contract
**Reason**: A single mixed envelope is replaced by the manifest-led typed bundle external contract.
**Migration**: Consumers use `feed-manifest.json`; the legacy schema remains read-only compatibility when the manifest is absent.

### Requirement: Durable monotonic publication
**Reason**: Single-file atomic replacement cannot publish a multi-artifact bundle safely.
**Migration**: Use immutable generation-qualified artifacts and atomically replace the manifest as the sole activation point under the replacement requirement below.

### Requirement: Minimal internal Feed entry outcomes
**Reason**: The outcome contract must report and dry-run a bundle rather than one `latest.json` product.
**Migration**: Preserve exit categories and diagnostics while returning the manifest-led candidate and manifest relative path.

### Requirement: Feed consumption rejects pipeline failure
**Reason**: Consumption now validates bundle integrity before applying the same health rule.
**Migration**: Apply the replacement bundle consumption requirement below; legacy fallback retains the old rule.

### Requirement: Feed semantic identity is separate from execution audit metadata
**Reason**: Identity must be reconstructed across manifest metadata and domain artifacts.
**Migration**: Preserve the existing logical semantic projection under the replacement bundle identity requirement below.

### Requirement: Canonical serializer owns published Feed bytes
**Reason**: Publication now owns canonical bytes for multiple typed artifacts and the manifest.
**Migration**: Apply the shared canonical serializer independently to every bundle file.

### Requirement: Publication is idempotent by semantic identity
**Reason**: Idempotence and monotonic ownership now apply to an active manifest-led bundle.
**Migration**: Compare validated bundle semantic identity and retain the current active manifest and artifact bytes for an idempotent candidate.

### Requirement: Exact allowlisted repository finalization
**Reason**: Successful generated state must include a closed bundle path set rather than only `feeds/latest.json`.
**Migration**: Use the replacement bundle finalization requirement below.

### Requirement: Generated-state commits avoid recursive full CI
**Reason**: The generated product allowlist changes from one Feed file to the closed active bundle set.
**Migration**: Use the replacement generated-state path requirement below.

### Requirement: Versioned Feed continuity checkpoint
**Reason**: Checkpoint advancement must match the authoritative bundle identity instead of `latest.json`.
**Migration**: Keep the checkpoint schema and continuity values unchanged and validate them against `feed-manifest.json`.

## ADDED Requirements

### Requirement: Feed bundle is the serialized external contract
Every published bundle SHALL validate against the supported major versions of its manifest and domain-artifact schemas and their semantic invariants. It SHALL retain the existing fixed window, truthful collection timestamps, Provider outcomes, canonical redacted Feed configuration snapshot, enabled-Provider contract snapshots, producer descriptor, canonical logical `content_digest`, cutoff-derived `run_id`, pipeline semantics, and exactly one supported typed payload per evidence item. Consumers SHALL validate from embedded producer contracts without requiring equality with the current consumer build or Provider manifests.

#### Scenario: Producer and consumer builds differ
- **WHEN** a valid bundle was produced by another build with supported schema majors
- **THEN** the consumer validates it from the manifest and embedded producer descriptors without requiring current build or manifest hashes to match

#### Scenario: Payload type and artifact domain disagree
- **WHEN** an item is stored outside the artifact matching its supported payload discriminator
- **THEN** closed bundle validation rejects it

### Requirement: Feed bundle semantic identity preserves the logical Feed projection
`content_digest` SHALL remain the canonical digest of the existing explicit logical Feed projection containing `schema_version`, `window`, `evidence_cutoff_at`, semantic Provider outcomes, `producer`, `feed_config`, the logical `feed_schema` descriptor, `provider_contracts`, the globally ordered evidence items, and the pipeline semantic result. Execution-audit timestamps, Provider `retrieved_at`, Git metadata, free-form warnings, physical bundle schema descriptors, artifact paths, sizes, checksums, `content_digest`, and `run_id` SHALL remain outside that semantic projection. `run_id` SHALL continue to derive from the fixed cutoff and `content_digest`. Splitting or rejoining unchanged logical evidence SHALL NOT by itself change semantic identity.

#### Scenario: Only physical bundle layout changes
- **WHEN** identical logical evidence and metadata are represented by the required deterministic artifacts rather than the legacy mixed envelope
- **THEN** reconstructed semantic identity remains stable

#### Scenario: Artifact inventory or evidence is tampered with
- **WHEN** physical integrity changes or reconstructed semantic evidence differs
- **THEN** integrity validation fails or the recomputed semantic identity differs, and the bundle is rejected

#### Scenario: Only execution timing changes
- **WHEN** two bundles have the same logical semantic projection and cutoff but different truthful audit timestamps
- **THEN** they have the same `content_digest` and `run_id`

### Requirement: Canonical serializer owns every published Feed bundle file
Every byte sequence passed to bundle publication SHALL equal the shared canonical serialization of its validated manifest or domain-artifact object. The manifest inventory SHALL hash and size those exact canonical artifact bytes. Feed-producing modules SHALL NOT use independent JSON serializer settings for bundle products.

#### Scenario: Bundle files are serialized
- **WHEN** a valid candidate is admitted to publication
- **THEN** every manifest and artifact byte sequence is canonical and every inventory checksum and size matches the exact published artifact bytes

### Requirement: Durable monotonic Feed bundle publication
Only a healthy or accepted degraded, fully validated candidate bundle SHALL be admitted. Publication SHALL place each artifact at a deterministic generation-qualified safe relative path, using unpredictable create-only same-parent staging, file and directory `fsync`, and no-replace installation; then it SHALL stage, revalidate ownership, and atomically replace `feed-manifest.json` as the sole activation point. Before that manifest replacement, failure SHALL leave the previous active manifest and all of its artifacts valid and unchanged. After replacement, parent-directory `fsync` failure SHALL report durability uncertainty without claiming rollback or advancing the checkpoint. Superseded or failed-candidate files SHALL never be discoverable through the active manifest and SHALL be removed as cleanup state rather than retained as a history or query product.

Latest ownership SHALL use the maximum `(evidence_cutoff_at, content_digest)` tuple independently of submission order. A validated current bundle with the candidate's `run_id`, `content_digest`, cutoff, and identical artifact integrity SHALL be accepted idempotently without replacement. Stale, conflicting, unsafe-path, invalid-current, or incompatible equal-ownership candidates SHALL fail closed without changing the active manifest.

#### Scenario: Valid candidate publishes
- **WHEN** all required canonical artifacts and the manifest validate and durable filesystem primitives are available
- **THEN** artifacts are installed first and `feed-manifest.json` is atomically activated last

#### Scenario: Artifact installation fails
- **WHEN** any required artifact cannot be staged, synced, installed, or validated
- **THEN** the previous active manifest remains unchanged and valid, and the candidate is not activated

#### Scenario: Manifest replacement fails before commit
- **WHEN** candidate manifest staging, validation, ownership checking, commit admission, or rename fails
- **THEN** the previous active manifest and referenced artifacts remain unchanged and the run exits as publication failure

#### Scenario: Manifest durability becomes uncertain
- **WHEN** manifest replacement succeeds but required parent-directory `fsync` fails
- **THEN** execution reports durability uncertainty, claims no rollback, and does not advance the checkpoint

#### Scenario: Same semantic bundle is submitted again
- **WHEN** the current valid bundle has the candidate's semantic identity and identical artifact inventory integrity
- **THEN** publication retains current bytes and accepts idempotent ownership

#### Scenario: Candidate order varies
- **WHEN** valid candidates arrive in different orders
- **THEN** the active manifest deterministically retains the maximum ownership tuple

### Requirement: Minimal internal Feed entry reports bundle outcomes
Exactly one minimal internal Feed entry SHALL preserve existing configuration, explicit product/runtime roots, deterministic clock/window injection, deadline, status, `--dry-run`, source-completeness, and typed exit behavior. A successful publication status SHALL expose `feed-manifest.json` as the product entry path and matching `run_id` and cutoff. Dry-run SHALL build and validate the same in-memory manifest and domain artifacts without writing bundle products or advancing the checkpoint. Existing Provider work, rate-state, lock, diagnostics, and exit-code semantics SHALL remain unchanged.

#### Scenario: Successful publication is reported
- **WHEN** a healthy or accepted degraded bundle is durably activated
- **THEN** the command exits `0` and status names `feed-manifest.json` with matching identity and cutoff

#### Scenario: Dry run succeeds
- **WHEN** dry-run produces a valid healthy or degraded bundle candidate
- **THEN** it exits `0`, reports the candidate, creates or replaces no bundle product, and does not advance the checkpoint

#### Scenario: Source completeness fails
- **WHEN** planned source work is incomplete
- **THEN** the command preserves existing deterministic Provider diagnostics, exits `1`, and does not admit a bundle to publication

### Requirement: Feed bundle consumption rejects invalid or failed products
The consumer health boundary SHALL first validate the complete manifest inventory and artifact integrity, then reconstruct the logical Feed and apply existing structural, identity, freshness, pipeline, warning, and calendar-horizon semantics. It SHALL accept healthy bundles, accept degraded bundles while propagating warnings, and reject `pipeline.status = failure`. A consumer needing one domain MAY parse only that domain's evidence after validating hashes and required existence for the complete inventory.

#### Scenario: Healthy bundle is consumed
- **WHEN** a complete valid bundle is healthy and fresh
- **THEN** the consumer accepts it and can select evidence by manifest domain inventory

#### Scenario: Degraded bundle is consumed
- **WHEN** a complete valid bundle is degraded and satisfies hard freshness checks
- **THEN** the consumer accepts it and propagates manifest pipeline warnings

#### Scenario: Structurally valid failure bundle is presented
- **WHEN** bundle files pass structure and identity checks but pipeline status is `failure`
- **THEN** the consumer rejects it as non-consumable

### Requirement: Exact allowlisted repository bundle finalization
After any controlled Feed outcome, deployment SHALL stage only explicitly resolved generated-state paths. On success, finalization SHALL validate status, checkpoint, active manifest, and every inventoried artifact; require their `run_id` and cutoff to match; and make one non-force fast-forward commit containing exact runtime safety state, terminal success lease, matching checkpoint, `feed-manifest.json`, exactly its closed artifact inventory, deletion of the superseded active generation, and deletion of migration-only `latest.json` when applicable. On controlled failure after Provider work, finalization SHALL preserve existing exact RateRegistry and terminal-failure behavior without staging a changed checkpoint, manifest, domain artifact, or candidate/superseded product. Transient stages, orphan candidates, status files, locks, history directories, and unrelated paths SHALL remain outside the allowlist.

#### Scenario: Successful bundle finalization
- **WHEN** status, checkpoint, manifest, and all inventoried artifacts validate and match
- **THEN** one generated-state commit contains exactly the active bundle and required durable state, with superseded product paths removed

#### Scenario: Bundle identity or inventory does not match
- **WHEN** status, checkpoint, manifest, artifact set, digest, size, `run_id`, or cutoff differs
- **THEN** finalization fails closed without publishing a success commit

#### Scenario: Controlled Feed failure is finalized
- **WHEN** Feed execution fails after Provider work
- **THEN** exact rate state and terminal failure may be committed, but no Feed product or checkpoint change is staged

### Requirement: Generated-state commits avoid recursive full CI for the closed active bundle
Normal CI SHALL exclude pushes whose changed paths consist only of accepted `.feed-state/` durable state and the closed Feed product set: `feeds/feed-manifest.json`, manifest-inventoried generation-qualified domain artifacts, deletion of the immediately superseded generation, and migration deletion of `feeds/latest.json`. A push containing code, configuration, Provider contracts, schemas, tests, workflows, OpenSpec, documentation, unreferenced Feed artifacts, history directories, unexpected runtime/transient state, or any other path SHALL remain eligible for full CI. This decision SHALL be path- and manifest-validation-based rather than commit-message-based.

#### Scenario: Valid generated-state-only bundle push
- **WHEN** a workflow commit changes only accepted durable state and the exactly validated active/superseded bundle paths
- **THEN** that push does not recursively invoke full CI

#### Scenario: Unreferenced artifact is changed
- **WHEN** a push changes an artifact not in the validated active or immediately superseded bundle set
- **THEN** full CI remains eligible

#### Scenario: Source and bundle paths are mixed
- **WHEN** a push changes accepted generated state and any source-controlled non-generated path
- **THEN** full CI remains eligible

### Requirement: Versioned Feed continuity checkpoint tracks the active bundle
The closed versioned checkpoint schema and its `previous_success` cutoff and `run_id` values SHALL remain unchanged. After accepted durable manifest ownership, the run SHALL atomically advance the checkpoint to the active bundle identity before releasing the runtime lock. It SHALL not advance for dry-run, source incompleteness, validation failure, publication failure, durability uncertainty, stale ownership, or any outcome without accepted active-manifest ownership. Deployment SHALL validate successful checkpoint identity against the active manifest rather than `latest.json`; checkpoint persistence failure after manifest activation SHALL fail without claiming rollback and MAY leave continuity lagging but never leading the active bundle.

#### Scenario: Accepted bundle advances continuity
- **WHEN** a healthy or accepted degraded bundle durably establishes active manifest ownership
- **THEN** checkpoint `previous_success` advances to exactly its cutoff and `run_id`

#### Scenario: Bundle publication is failed or uncertain
- **WHEN** active ownership is not accepted or manifest durability is uncertain
- **THEN** the checkpoint does not advance

#### Scenario: Checkpoint persistence fails after activation
- **WHEN** manifest activation succeeds but checkpoint persistence fails
- **THEN** execution fails, preserves the active bundle, and leaves continuity conservatively lagging
