# feed-evidence-pipeline Specification

## Purpose
Define the current credential-free provider-to-Feed collection, deterministic evidence normalization and validation, provenance, bounded timing and rate discipline, and durable publication boundary.

## Requirements

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
Repository deployment SHALL recognize a valid current `feeds/latest.json` with no manifest as pre-bundle product state. A migration-only invocation SHALL deterministically split that validated Feed into the typed bundle, preserve its semantic `content_digest`, `run_id`, evidence, provenance, cutoff, pipeline, and checkpoint identity, publish the first manifest-led bundle through the bundle publication boundary, remove `latest.json` in the same repository generated-state commit, perform zero Provider requests, and exit before collection. When runtime state is already established in `.feed-state/`, product-only migration SHALL stage the required runtime files, generated manifest and exact artifact inventory, and tracked `latest.json` deletion without requiring nonexistent or untracked legacy runtime paths under `feeds/`. A complete legacy runtime-state migration SHALL continue to stage its exact tracked legacy runtime deletions. Missing or invalid required migration state SHALL fail closed without deleting the legacy product or advancing continuity.

#### Scenario: Valid current latest is migrated
- **WHEN** deployment finds a valid legacy latest, matching checkpoint, and no bundle manifest
- **THEN** it publishes an equivalent validated bundle, removes `latest.json` in the same generated-state commit, performs zero Provider requests, and leaves checkpoint identity unchanged

#### Scenario: Product-only migration has no legacy runtime paths
- **WHEN** valid runtime state is already established in `.feed-state/`, `feeds/latest.json` is tracked, and no legacy runtime paths under `feeds/` exist or are tracked
- **THEN** migration stages only the required runtime state, exact generated bundle inventory, and `latest.json` deletion without passing nonexistent legacy runtime paths to repository publication

#### Scenario: Complete legacy runtime state is relocated
- **WHEN** migration relocates complete tracked legacy runtime state from `feeds/` into `.feed-state/`
- **THEN** repository publication stages the exact new runtime additions and exact tracked legacy runtime deletions without broad or unrelated paths

#### Scenario: Legacy product is not tracked for deletion
- **WHEN** migration publication finds `feeds/latest.json` present but not tracked by the repository index
- **THEN** migration fails closed before removing it or committing a partial generated-state migration

#### Scenario: Legacy product cannot be trusted
- **WHEN** latest, checkpoint, schema, identity, provenance, or repository state is invalid or inconsistent
- **THEN** migration makes zero Provider requests and does not partially create or activate a bundle

#### Scenario: Required migration path is missing
- **WHEN** a required runtime file, manifest, or inventoried artifact is missing or inconsistent before publication
- **THEN** migration fails closed rather than silently omitting the required path or publishing partial state

#### Scenario: Bundle state already exists
- **WHEN** a valid manifest-led bundle is present
- **THEN** current-state migration does not reinterpret `latest.json` as another authority

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

### Requirement: Credential-free verified provider contracts
The Feed SHALL resolve every enabled Provider by strictly composing activation and coverage policy with that Provider's supported checked-in verified manifest before normal execution. The manifest SHALL be authoritative for Provider identity and contract version, verification and evidence metadata, authentication and protocol requirements, fetch and redirect hosts, evidence source-link rules, charset and content-type rules, request and response limits, rate policy, pagination, empty-window semantics, Provider-specific runtime behavior, mapping declarations already present in the manifest, and fixture provenance. The resulting single resolved Provider contract SHALL drive adapter construction and behavior, rate handling, empty-window decisions, host-concurrency planning, enablement, coverage assessment, and the embedded Feed `provider_contracts` snapshot; runtime consumers SHALL NOT re-read or independently reinterpret a second Provider contract after resolution. The shipped core Provider set SHALL require no paid financial-data key, and every accepted evidence URL SHALL be HTTPS, credential-free, canonicalized once under its owning resolved host/path/query policy, and validated before identity or publication.

#### Scenario: Default providers run without credentials
- **WHEN** the minimal Feed entry loads the shipped default configuration without any paid financial-data credential
- **THEN** it can initialize and attempt every enabled verified free Provider without reading an API key

#### Scenario: Enabled Provider contract cannot be resolved
- **WHEN** an enabled Provider manifest is missing, invalid, has an unsupported contract version or mismatched Provider identity, or fails the required verification contract
- **THEN** static startup fails closed before that or any other Provider request and before normal persistent Feed runtime mutation

#### Scenario: Provider contract is incomplete
- **WHEN** an enabled Provider manifest omits a required contract fact or an adapter emits evidence outside its resolved source-link policy
- **THEN** configuration or item validation fails closed before the Provider or item can count toward Feed coverage

#### Scenario: Manifest-owned runtime value changes
- **WHEN** a valid authoritative manifest-owned runtime value changes for an enabled Provider
- **THEN** the resolved adapter behavior and corresponding embedded Provider contract snapshot both reflect that same value without an independent matching runtime definition elsewhere

#### Scenario: Provider is disabled
- **WHEN** registry policy marks a Provider disabled
- **THEN** collection neither initializes nor contacts that Provider even when its manifest is otherwise valid and verified

### Requirement: Production Feed activates CFTC weekly positioning evidence
The shipped production Feed plan SHALL enable the existing verified, credential-free CFTC Provider and publish its accepted `positioning` items in the typed positioning domain artifact inventoried by `feed-manifest.json`. The Provider outcome and embedded Provider contract SHALL preserve CFTC identity, Tier 1 provenance, the authoritative weekly cadence with `data_as_of` reference time, and its declared validity window. CFTC evidence SHALL remain evidence-only and SHALL NOT contain signals, ranking, scoring, interpretation, or investment conclusions.

#### Scenario: Production planning includes CFTC
- **WHEN** the shipped production Provider configuration is resolved
- **THEN** CFTC is enabled, its verified contract is embedded in the Feed manifest, and exactly one planned CFTC outcome is required

#### Scenario: A new CFTC report is available
- **WHEN** a complete CFTC check returns a valid report whose canonical semantic content is new or changed and whose authoritative `positioning.as_of` is within the weekly validity window
- **THEN** the current CFTC slice deterministically replaces the prior slice, its freshness is `fresh`, and its items are published only in the positioning domain artifact with original source and payload timestamps

#### Scenario: No new weekly report is available
- **WHEN** a complete daily CFTC check returns no new observation and a fully validated prior CFTC slice remains within the declared weekly validity window
- **THEN** the prior slice is carried unchanged with freshness `valid_unchanged`, current operational retrieval and generation timestamps are recorded independently, and no source, knowledge, or `positioning.as_of` timestamp is rewritten

#### Scenario: CFTC fails after a prior snapshot exists
- **WHEN** current CFTC acquisition fails, is partial, or otherwise remains incomplete while a prior valid CFTC slice exists
- **THEN** the CFTC outcome remains incomplete with freshness `not_evaluated`, the prior slice does not substitute for current success, and the failed candidate is not published

#### Scenario: Published CFTC evidence is inspected
- **WHEN** a consumer validates a successfully published bundle containing CFTC positioning evidence
- **THEN** the manifest and positioning artifact expose the CFTC Provider outcome, provenance, originating contract hash, cadence status, and unchanged source-semantic timestamps required by the existing Feed contracts

### Requirement: Provider cadence is a closed freshness authority
Every resolved Provider contract SHALL replace the opaque freshness policy with exactly one closed cadence mode: `weekly`, `scheduled`, `event_driven`, or `market_session`, and one reference-time selector from `data_as_of`, `source_updated_at`, or `checked_at`. `weekly`, `scheduled`, and `market_session` contracts SHALL use a source-semantic reference and declare a positive validity window; `market_session` SHALL use `data_as_of`. `event_driven` SHALL use `checked_at` and declare no age window because a successful current check, rather than elapsed source age, establishes unchanged validity. The owning verified Provider manifest SHALL be the sole cadence, reference, and validity authority, and the resolved contract plus embedded Provider contract snapshot SHALL preserve it without a Feed-level Provider lookup table, inferred default, or duplicated configuration source.

#### Scenario: Weekly contract is resolved
- **WHEN** a verified weekly Provider declares its required positive validity window
- **THEN** static resolution and the embedded Provider contract expose that exact cadence contract without a Feed-code default

#### Scenario: Event-driven contract declares an age window
- **WHEN** an event-driven Provider declares an age-based validity window
- **THEN** static configuration validation fails closed before Provider work because elapsed age is not authoritative for that cadence

#### Scenario: Market-session contract selects check time
- **WHEN** a market-session Provider selects `checked_at` or `source_updated_at` instead of `data_as_of`
- **THEN** static configuration validation fails closed rather than allowing a recent request or publication timestamp to refresh an old market observation

#### Scenario: Bounded cadence omits its validity window
- **WHEN** a weekly, scheduled, or market-session Provider omits or misstates its positive validity window
- **THEN** static configuration validation fails closed before Provider work or publication

### Requirement: Evidence-backed market mapping contract
Every Provider market-role mapping SHALL remain in the owning Provider's existing resolved `role_mappings` contract and SHALL bind one exact tuple of Provider identity, canonical role identity, Provider instrument, and unit. A mapping declared verified SHALL include one authoritative mapping-level verification-provenance declaration that is explicit, non-empty, auditable, and associated with that exact tuple. A mapping declared unverified SHALL include a non-empty deterministic reason and SHALL NOT be treated as runnable canonical market capability. No second market-mapping registry or independently authoritative mapping-provenance source SHALL be introduced.

Static resolution SHALL validate mapping provenance without making a network request solely for verification. A checked-in repository reference SHALL have valid repository-relative syntax, remain within the repository, exist, belong to the owning Provider contract, and identify the declared tuple through its mapping declaration; when a structured Yahoo chart fixture is used, its explicit `meta.symbol` SHALL equal the declared instrument. An authoritative HTTPS reference SHALL satisfy the owning Provider's declared verification host policy and SHALL be bound to the declared tuple. Arbitrary text or document content SHALL NOT be treated as deterministically proving financial semantics.

#### Scenario: Verified mapping has valid checked-in evidence
- **WHEN** a verified mapping declaration structurally binds its Provider, role, instrument, and unit tuple and its checked-in Provider-owned evidence exposes an explicit structured instrument identity matching the declared instrument
- **THEN** static resolution retains the mapping as verified and preserves its verification provenance in the resolved Provider contract

#### Scenario: Verified mapping omits provenance
- **WHEN** `mapping_verified` is true but mapping-level verification provenance is absent or empty
- **THEN** static resolution fails through the existing configuration/startup failure category

#### Scenario: Unverified mapping omits reason
- **WHEN** `mapping_verified` is false but the mapping has no non-empty explicit reason
- **THEN** static resolution fails through the existing configuration/startup failure category

#### Scenario: Repository evidence is unavailable or escapes its boundary
- **WHEN** verified mapping provenance names a missing path, an absolute path, a repository-escaping path, or evidence outside the owning Provider contract
- **THEN** static resolution rejects the mapping before normal Feed execution

#### Scenario: HTTPS verification reference violates Provider policy
- **WHEN** a verified mapping declares a malformed, non-HTTPS, credential-bearing, or disallowed-host verification reference
- **THEN** static resolution rejects the mapping without making a verification network request

#### Scenario: Verification evidence belongs to another tuple
- **WHEN** verification provenance is associated with another Provider, role, instrument, or unit
- **THEN** static resolution rejects the verified claim instead of transferring evidence between mappings

#### Scenario: Structured Yahoo symbol disagrees
- **WHEN** a checked-in Yahoo chart fixture is used as mapping evidence and its explicit `meta.symbol` differs from the declared instrument
- **THEN** static resolution rejects the verified claim

#### Scenario: Compatibility mapping declaration disagrees
- **WHEN** any retained canonical-role compatibility declaration differs from the manifest authority for instrument, unit, or `mapping_verified`
- **THEN** static resolution fails closed and the compatibility declaration does not independently control execution

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

### Requirement: Market coverage is bounded by verified runnable capability
Provider-level coverage policy SHALL claim no market capability broader than the enabled Provider's verified runnable mappings. Coverage SHALL NOT claim all configured roles, China/HK market support, or cross-asset completeness unless the verified runnable mappings establish that breadth. Unsupported claims SHALL be removed or narrowed within the existing Provider-level coverage model; no role-level coverage engine SHALL be introduced. An enabled market Provider with zero verified runnable mappings SHALL fail through the existing configuration/startup category unless registry policy explicitly disables it.

#### Scenario: Only a subset of market mappings is verified
- **WHEN** fewer than all configured market mappings are verified and runnable
- **THEN** coverage omits `market_data_all_13_roles` and any China/HK or cross-asset capability not supported by that verified subset

#### Scenario: Coverage claim exceeds runnable mappings
- **WHEN** a configured Provider-level market capability is not a subset of verified runnable mappings
- **THEN** static resolution rejects the unsupported coverage contract before Provider requests or runtime mutation

#### Scenario: Enabled market Provider has no verified mapping
- **WHEN** an enabled market Provider resolves with zero verified runnable mappings
- **THEN** startup fails through the existing configuration/startup category rather than reporting a healthy zero-work Provider outcome

#### Scenario: Market Provider is explicitly disabled
- **WHEN** registry policy disables a market Provider with zero verified runnable mappings
- **THEN** no adapter work is planned for that Provider and the disabled state is handled by the existing activation and coverage contracts

### Requirement: Durable collection coordination and rate discipline
Before loading continuity state or capturing the cutoff, collection SHALL acquire one exclusive lock in the explicit runtime-state root and hold it through planning, Provider work, Feed product publication, and checkpoint advancement. Provider dispatch SHALL use the persistent closed runtime-state-root registry and per-scope rate state, durably debit and install the crash-conservative provisional cooldown before every possible send, reconcile controlled outcomes without refunding the send, honor valid `Retry-After`, and fail closed on missing, corrupt, unknown, or unrecoverable active state. Collection SHALL enforce the configured global and per-host concurrency limits, stable provider-ID result order, sequential pagination unless the manifest proves otherwise, and cancellation with no late Feed or checkpoint mutation. Product publication SHALL remain under the separately resolved Feed product root.

#### Scenario: Two entries share one output root
- **WHEN** a second process starts with the same runtime-state root while the first holds the collection lock
- **THEN** it waits without consuming provider concurrency and plans from checkpoint state only after lock acquisition, or fails typed `collection_lock_timeout` before any provider call

#### Scenario: A dispatched process crashes
- **WHEN** a process exits after the durable pre-send debit and before controlled reconciliation
- **THEN** the next process retains the debit and provisional cooldown instead of resetting the scope or assuming no request occurred

#### Scenario: Provider completions are reordered
- **WHEN** identical provider fixtures complete under different schedules within the concurrency limits
- **THEN** normalized provider outcomes and Feed bytes remain in stable provider-ID order

#### Scenario: Production dry run can send a request
- **WHEN** `--dry-run` dispatches an enabled production adapter that may contact its verified host
- **THEN** the run acquires the runtime-state-root collection lock and durably debits and reconciles rate state exactly as a publishing run, while creating or replacing no `feeds/latest.json` product and not advancing the checkpoint

#### Scenario: Product and runtime roots are distinct
- **WHEN** production orchestration resolves configuration
- **THEN** it explicitly materializes the Feed product root and runtime-state root independently so product validation cannot target runtime state and runtime-state validation cannot target Feed products

### Requirement: Bounded command deadline and non-cancellable commit
The minimal Feed entry SHALL enforce the existing 300-second command-start monotonic deadline with an exact 15-second pre-commit reserve. Lock waits, rate waits, pagination, retries, request attempts, reversible processing, and staging `fsync` SHALL fit before second 285. Once a fully staged candidate is admitted to filesystem commit by second 285, rename and parent-directory `fsync` SHALL run to their normal result without cancellation or rollback; completion after second 300 MAY only add `commit_elapsed_overrun` to external status or stderr and SHALL NOT change the already hashed Feed bytes.

#### Scenario: No attempt fits before the reserve
- **WHEN** the next wait or request attempt cannot complete within the remaining pre-commit budget
- **THEN** collection stops with the typed deadline outcome before that attempt begins

#### Scenario: Staging crosses the reserve boundary
- **WHEN** candidate staging or its required pre-commit `fsync` advances the monotonic clock to or beyond second 285
- **THEN** publication removes reversible staging files and fails typed `pre_commit_deadline_exceeded` before replacing `feeds/latest.json`

#### Scenario: Commit crosses the nominal deadline
- **WHEN** a candidate is fully staged and admitted by second 285 but durable replacement completes after second 300
- **THEN** commit finishes without cancellation or rollback and reports the overrun only outside the immutable Feed payload

### Requirement: Evidence-only deterministic Feed generation
The live pipeline SHALL perform provider fetching, strict decoding, normalization,
exact and conservative near deduplication, validation, and publication. Feed items
SHALL contain evidence and provenance only and SHALL reject
importance, direction, price-in, money-flow interpretation, market regime, asset
impact, ranking, or other analysis fields.

#### Scenario: Intelligence enters an item
- **WHEN** a normalized item contains a ranking, interpretation, recommendation, regime, or asset-impact field
- **THEN** Feed validation rejects the candidate before publication

### Requirement: Feed bundle is the serialized external contract
Every published bundle SHALL validate against the supported major versions of its manifest and domain-artifact schemas and their semantic invariants. Newly produced logical Feeds and manifests SHALL use the freshness-capable major, while the immediately preceding major SHALL remain read-compatible as a fully validated active-bundle input for bounded migration and carry-forward; new production SHALL NOT emit the preceding major. The bundle SHALL retain the existing fixed acquisition window, truthful collection timestamps, Provider outcomes with semantic freshness results, canonical redacted Feed configuration snapshot, enabled-Provider contract snapshots, producer descriptor, canonical logical `content_digest`, cutoff-derived `run_id`, pipeline semantics, and exactly one supported typed payload per evidence item. Consumers SHALL validate from embedded producer contracts without requiring equality with the current consumer build or Provider manifests.

#### Scenario: Producer and consumer builds differ
- **WHEN** a valid bundle was produced by another build with supported schema majors
- **THEN** the consumer validates it from the manifest and embedded producer descriptors without requiring current build or manifest hashes to match

#### Scenario: Payload type and artifact domain disagree
- **WHEN** an item is stored outside the artifact matching its supported payload discriminator
- **THEN** closed bundle validation rejects it

#### Scenario: Previous-major active bundle is read
- **WHEN** the active bundle uses the immediately preceding supported major and passes its complete original contract
- **THEN** it may supply a prior Provider slice to a new freshness-capable candidate, which records the slice's original embedded Provider-contract hash

#### Scenario: New production attempts the preceding major
- **WHEN** a producer candidate omits required freshness results or declares the preceding logical/manifest major
- **THEN** new-production validation rejects it before publication

### Requirement: Bounded canonical evidence and conservative deduplication
Normalized text SHALL use strict manifest-declared decoding, Unicode scalar values,
NFC normalization, and bounded UTF-8 fields; news-like items SHALL NOT retain full
copyrighted article bodies. Raw numeric tokens SHALL satisfy the existing lexical,
digit, exponent, magnitude, sign, and unit-domain bounds before `Decimal`
construction, and persisted financial values SHALL be canonical plain decimal
strings without exponent or negative zero. Stable IDs and canonical URLs SHALL
remove exact and same-source near duplicates while retaining independently
originated cross-source reports and their source-lineage provenance.

#### Scenario: Full article content is returned
- **WHEN** a provider response contains an article body beyond the bounded evidence fields
- **THEN** the Feed retains only the schema-permitted title, snippet, source, time, URL, hints, and typed metadata

#### Scenario: Numeric input is adversarial
- **WHEN** a raw numeric token exceeds the configured byte, significant-digit, exponent, magnitude, sign, or unit-domain bounds
- **THEN** it is rejected before `Decimal` arithmetic, hashing, or Feed publication

#### Scenario: Independent sources report one event
- **WHEN** two independent sources publish similar evidence at distinct canonical URLs
- **THEN** both items remain available for later corroboration rather than being collapsed as one origin

### Requirement: Provenance tiers and payload-specific time semantics
Every Feed item SHALL retain owning Provider identity, source name, tier, kind, canonical URL, `source.published_at` and `source.updated_at` when supplied by the source, `source.knowledge_available_at`, payload-specific observation/effective/reference time, precision, and selection basis. The Provider outcome `retrieved_at` SHALL remain the single response-return/check observation for that Provider work, and Feed `generated_at` SHALL remain the bundle-generation observation; neither timestamp SHALL be copied into an evidence item or treated as source publication/update or data-as-of time. Event-like newly acquired items SHALL be selected by knowledge time in the half-open acquisition window; bounded market lookbacks, current positioning, future calendar snapshots, and validation-gated carried Provider slices MAY contain earlier effective or knowledge times only under their declared availability or freshness contracts. Retrieval time SHALL remain audit metadata and SHALL NOT establish cutoff eligibility or freshness.

#### Scenario: Evidence becomes known after cutoff
- **WHEN** an item or market observation has an earlier effective time but source availability at or after `evidence_cutoff_at`
- **THEN** it is excluded from the run rather than admitted from effective time alone

#### Scenario: Calendar evidence was announced earlier
- **WHEN** a previously announced calendar item was known before cutoff and remains inside the configured future horizon
- **THEN** the current calendar snapshot may include it with its original provenance and scheduled time

#### Scenario: Tier 3 evidence is normalized
- **WHEN** an enabled commentary source emits an otherwise valid item
- **THEN** the item remains explicitly Tier 3 and normalization does not promote its authority

#### Scenario: Unchanged evidence is checked again
- **WHEN** a Provider response is observed during the current run but its prior evidence slice is carried forward
- **THEN** current `retrieved_at` records the check while the carried items retain their original publication, update, knowledge, observation, effective, and reference times

### Requirement: Raw bounded market history
Market-data items MAY retain the configured bounded chronological series of raw
timestamped observations, values, units, volumes, availability metadata, and session
identity needed by deterministic analytics. The Feed SHALL preserve missing history
as missing, SHALL reject conflicting duplicate timestamps and post-cutoff or
incompatible observations, and SHALL NOT serialize calculated significance, regime,
or investment interpretation with the raw series.

#### Scenario: Lookback is incomplete
- **WHEN** a verified provider returns fewer eligible observations than requested
- **THEN** the Feed records the available observations without filling or inventing missing values

#### Scenario: Duplicate timestamp conflicts
- **WHEN** one instrument contains the same observation timestamp with incompatible values
- **THEN** provider validation records the conflict and does not silently select a value

### Requirement: Explicit degradation and coverage outcomes
One Provider failure SHALL NOT stop collection already planned for other Providers. The Feed SHALL record attempted, succeeded, empty, partially valid, failed, skipped, fetched, accepted, and rejected outcomes. Provider membership for completeness assessment SHALL derive only from the actual resolved run plan, and the resolved Provider contract SHALL be the sole authority for `empty_valid_for_window`; disabled Providers and unverified mappings excluded from that plan SHALL create no completeness obligation.

Every planned Provider SHALL have exactly one unambiguous terminal outcome matching its planned Provider identity. A planned Provider SHALL be complete only when its outcome is `healthy`, or when its outcome is `empty` and its resolved `empty_valid_for_window` contract is true. A `failed`, `partial`, or `skipped` outcome, a non-permitted `empty` outcome, or a missing, duplicate, ambiguous, or identity-mismatched terminal outcome SHALL be incomplete. Accepted and fetched item counts SHALL NOT determine Provider completeness.

Mandatory coverage SHALL count only complete planned Providers that belong to the configured group. A contract-permitted empty Provider SHALL count toward the configured minimum without contributing an evidence item; an incomplete Provider SHALL not count. Existing optional-group semantics SHALL remain unchanged. Any incomplete planned Provider or deficient mandatory coverage group SHALL produce `pipeline.status = failure` regardless of evidence returned by other Providers. A provider SHALL be `partial` when it retains accepted evidence but also has rejected items or incomplete later sub-request, role, or page work; retained valid evidence and outcome counters SHALL remain available for diagnostics but SHALL NOT make the failed run publishable.

The total accepted evidence count and final `items` length SHALL NOT independently determine pipeline health. When every planned Provider is complete, mandatory coverage is satisfied, and all existing non-source hard-failure boundaries succeed, the Feed SHALL remain eligible for the existing healthy or otherwise accepted non-source status even when `items` is empty. Planned source incompleteness SHALL NOT produce `degraded`; existing degraded semantics unrelated to source acquisition completeness SHALL remain available and no new degraded condition is introduced. Provider-specific and coverage-group warnings SHALL identify every source-completeness cause used to fail the pipeline.

#### Scenario: One provider fails and another succeeds
- **WHEN** one planned Provider fails or times out while another contributes valid evidence
- **THEN** the Feed run fails, exits non-zero, retains both Provider outcomes for diagnostics, and does not replace the previous valid `feeds/latest.json`

#### Scenario: Mandatory group is deficient with accepted evidence
- **WHEN** the pipeline accepts at least one valid item but fewer complete planned Provider outcomes contribute than a non-optional coverage group's minimum
- **THEN** the Feed run fails, exits non-zero, does not publish, and identifies the deficient coverage group

#### Scenario: Permitted empty contributes to coverage
- **WHEN** a provider returns no accepted item and its `empty_valid_for_window` contract is true
- **THEN** its `empty` outcome contributes to coverage without contributing an accepted evidence item

#### Scenario: Non-permitted empty does not contribute to coverage
- **WHEN** a planned Provider reaches `empty` and its `empty_valid_for_window` contract is false
- **THEN** the Provider is incomplete, contributes no coverage, and makes the Feed run fail regardless of evidence from other Providers

#### Scenario: Every provider returns no accepted item
- **WHEN** every planned Provider reaches `healthy` or contract-permitted `empty`, mandatory coverage is satisfied, all other hard-failure boundaries succeed, and the final Feed has `items: []`
- **THEN** zero accepted evidence does not fail the run and the empty Feed remains eligible for normal successful publication

#### Scenario: An item is partially invalid
- **WHEN** a provider produces accepted items and rejects one or more other normalized items
- **THEN** accepted items and rejection counters are retained, the Provider is partial, and source incompleteness makes the Feed run fail rather than degrade

#### Scenario: Later provider work fails after valid evidence
- **WHEN** a provider retains accepted evidence from one sub-request, role, or page and later work fails or is incomplete
- **THEN** the retained evidence remains, the Provider is partial rather than healthy or wholly failed, and the Feed run fails without publication

#### Scenario: Planned Provider is skipped
- **WHEN** a Provider exists in the actual run plan but its terminal outcome is `skipped`
- **THEN** the Provider is incomplete and the Feed run fails

#### Scenario: Planned outcome is missing or ambiguous
- **WHEN** a planned Provider has no valid terminal outcome, more than one competing outcome, or an outcome whose identity does not match the planned Provider
- **THEN** completeness assessment fails closed instead of inferring success from counters, other outcomes, or evidence items

#### Scenario: Work is outside the actual plan
- **WHEN** a Provider is disabled or a market mapping is unverified and therefore excluded by authoritative resolved production planning
- **THEN** no synthetic skipped outcome or completeness requirement is created for that unplanned work

#### Scenario: Evidence quantity does not determine coverage
- **WHEN** a planned Provider is complete with zero accepted evidence
- **THEN** it remains eligible to satisfy configured mandatory coverage according to its terminal state and resolved empty-window contract

#### Scenario: Partial provider cannot satisfy full coverage
- **WHEN** a partial provider belongs to a mandatory coverage group
- **THEN** it contributes no full mandatory coverage even though its accepted items remain usable in the failed Feed candidate

### Requirement: Fixed advancing Feed window
After acquiring the runtime-state collection lock, the run SHALL load and validate previous-success state exclusively from the runtime checkpoint, capture one `evidence_cutoff_at` before Provider requests, and plan a strictly advancing half-open `[window.start, evidence_cutoff_at)` acquisition interval. Explicit null previous success SHALL use the bounded bootstrap lookback; later runs SHALL advance from the checkpoint cutoff subject to the configured maximum gap, including when the corresponding prior successful Feed contained `items: []`. Equal or earlier cutoffs, missing or invalid established checkpoint state, look-ahead evidence, and invalid timestamp ordering SHALL fail closed before Provider calls or publication as their phase requires. Exact-threshold and over-threshold gap handling and coverage-gap reporting SHALL remain unchanged. Deadlines SHALL use monotonic time while persisted instants use RFC 3339 UTC with Asia/Shanghai schedule metadata.

The checkpoint SHALL remain the sole continuity and window-planning authority. Planning SHALL NOT read a Feed product to derive the next window; only after current acquisition reaches a complete outcome MAY snapshot selection validate the active bundle as an optional carry-forward input. Carried evidence outside the current acquisition interval SHALL retain its original knowledge and source times and SHALL NOT claim that the current interval observed or published it.

#### Scenario: Existing latest Feed is invalid
- **WHEN** steady-state planning has a valid checkpoint while the active Feed product is absent or fails product integrity validation
- **THEN** planning still derives its window from the checkpoint and snapshot carry-forward remains unavailable

#### Scenario: Cutoff does not advance
- **WHEN** the captured cutoff is equal to or earlier than the current valid checkpoint cutoff
- **THEN** planning returns typed `non_advancing_cutoff` before any provider call or artifact write

#### Scenario: Collection finishes after cutoff
- **WHEN** collection completes several minutes after the fixed cutoff
- **THEN** the Feed preserves the original cutoff and records later collection timestamps without claiming later evidence coverage

#### Scenario: Successful empty Feed advances the next window
- **WHEN** a source-complete empty Feed is successfully published and recorded in the checkpoint
- **THEN** the next run derives `window.start` from that checkpoint's newer `evidence_cutoff_at` rather than reusing the preceding older cutoff

#### Scenario: No previous success uses bounded bootstrap
- **WHEN** a valid checkpoint explicitly contains `previous_success: null`
- **THEN** planning uses the existing bounded bootstrap lookback without reading Feed products for continuity

#### Scenario: Gap reaches or exceeds the configured threshold
- **WHEN** the checkpoint cutoff produces a gap exactly at or beyond the configured maximum
- **THEN** planning preserves the existing exact-threshold, bounded-gap/bootstrap, and coverage-gap behavior

#### Scenario: Prior evidence is carried outside the acquisition window
- **WHEN** a validated Provider slice is retained after a complete no-new-observation check
- **THEN** its original times remain unchanged and the Feed does not represent it as newly acquired within the advancing window

### Requirement: Provider snapshot freshness is explicit and deterministic
Every newly generated Feed SHALL record exactly one semantic freshness result beside each planned Provider outcome in ascending `provider_id` order. The result SHALL use the resolved cadence and exactly one status: `fresh` for a current Provider slice within its cadence window, `valid_unchanged` for an unchanged carried slice that remains valid, `stale` for a current or carried slice beyond an age-bounded cadence window, `no_snapshot` for complete no-observation acquisition with no prior slice, or `not_evaluated` for incomplete acquisition. It SHALL record the originating embedded Provider-contract hash for a present slice and the immediately preceding validated `run_id` only when bytes were carried forward.

For weekly, scheduled, and market-session cadence, evaluation SHALL compare `evidence_cutoff_at` with the latest authoritative payload-specific observation/effective time in the Provider slice and the declared validity window. For event-driven cadence, a complete current check SHALL keep an unchanged carried slice valid without rewriting its source time. Invalid, missing, future, or ambiguous time authority SHALL fail validation rather than select a convenient timestamp. Freshness status SHALL be part of semantic Feed identity, but SHALL NOT independently rewrite Provider completeness or pipeline status.

#### Scenario: Weekly source is checked daily
- **WHEN** a complete daily check finds no new observation, a validated prior weekly slice is available, and its cadence window has not expired
- **THEN** the prior slice is retained unchanged and the Provider freshness status is `valid_unchanged`

#### Scenario: Source publishes a new observation
- **WHEN** complete acquisition produces a new evidence identity or changes the canonical semantic content of an existing identity and its authoritative observation time is within the cadence window
- **THEN** the current slice replaces the prior Provider slice and freshness status is `fresh`

#### Scenario: Scheduled source remains unchanged
- **WHEN** a complete scheduled-source check finds no new observation and the validated prior slice remains within its declared validity window
- **THEN** the prior slice remains `valid_unchanged` without changing its observation or source timestamps

#### Scenario: Event-driven source remains unchanged
- **WHEN** a complete event-driven check finds no new observation and a validated prior slice exists
- **THEN** the prior slice remains `valid_unchanged` because the current successful check, not an invented age limit, establishes unchanged validity

#### Scenario: Market-session window expires
- **WHEN** the latest authoritative market observation precedes the cutoff by more than the Provider's declared market-session validity window
- **THEN** the Provider freshness status is `stale` even when retrieval and Feed generation occurred recently

#### Scenario: No prior snapshot exists
- **WHEN** acquisition is complete and contract-permitted empty but no validated prior Provider slice exists
- **THEN** the Provider freshness status is `no_snapshot` and no evidence is invented

### Requirement: Snapshot carry-forward is validation-gated and failure-isolated
The Feed MAY carry a Provider slice only after complete current acquisition establishes that every accepted current item has an exact canonical semantic match under the same identity in the prior slice and the current active bundle has passed full schema, integrity, semantic identity, provenance, pipeline-consumability, and item validation. Carry-forward SHALL reuse the prior Provider items byte-for-byte in semantic form, including stable IDs, payloads, original source publication/update and knowledge times, provenance, and source lineage; it SHALL preserve the originating embedded Provider-contract hash and SHALL NOT merge successive slices into unbounded history. A current slice containing a new identity or changed canonical semantic content under an existing identity SHALL replace, rather than merge with, the prior slice.

Failed, partial, skipped, missing, duplicate, ambiguous, identity-mismatched, or non-permitted-empty current acquisition SHALL set freshness to `not_evaluated`, SHALL NOT consult retained evidence as a substitute, and SHALL retain the existing source-incomplete pipeline failure and no-publication behavior. Absence or invalidity of the active bundle SHALL disable carry-forward without weakening current Provider outcome or coverage rules.

#### Scenario: Valid prior slice is carried
- **WHEN** current Provider acquisition is complete with no new observation and the active bundle plus that Provider slice validate fully
- **THEN** the new candidate carries exactly the prior semantic items, records the prior `run_id`, and preserves their originating Provider-contract hash

#### Scenario: Prior bundle is invalid
- **WHEN** the active manifest, inventory, artifact, semantic identity, pipeline consumability, or prior Provider slice fails validation
- **THEN** no prior item is carried and current acquisition is evaluated without fallback

#### Scenario: Current acquisition fails with a previous snapshot
- **WHEN** current Provider acquisition fails while a prior valid Provider slice exists
- **THEN** the Provider remains failed with freshness `not_evaluated`, the pipeline remains source-incomplete, and the prior slice cannot convert the run into success or publication

#### Scenario: New slice replaces prior slice
- **WHEN** complete acquisition returns an identity absent from the prior Provider slice or different canonical semantic content under an existing identity
- **THEN** the current Provider slice becomes the snapshot without unioning prior items into Feed history

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

### Requirement: Deterministic Feed aggregation and normalization
Provider work SHALL remain eligible for concurrent execution, but every Feed SHALL serialize one outcome for each provider represented by the collection plan in ascending `provider_id` order, including failed and skipped providers. Before duplicate comparison, duplicate-survivor selection, lineage merging, or final serialization, Feed items SHALL use the total order `(source.knowledge_available_at, id)`. Every merged `source_lineage` SHALL use the same contributing-item order, and no semantic result SHALL depend on provider completion order or input list order.

#### Scenario: Provider completion schedule changes
- **WHEN** the same provider results complete under different schedules
- **THEN** every Feed has the same `provider_outcomes` order and the same semantic identity

#### Scenario: Failed and skipped providers are present
- **WHEN** a collection plan produces successful, failed, and skipped provider outcomes
- **THEN** all outcomes are represented once and ordered by `provider_id` independently of when their terminal states were recorded

#### Scenario: Item input order changes
- **WHEN** the same evidence items are supplied in different permutations
- **THEN** duplicate survivors, dropped identities, merged lineage, final item order, and semantic identity are identical

### Requirement: Feed bundle semantic identity preserves the logical Feed projection
`content_digest` SHALL be the canonical digest of the explicit freshness-capable logical Feed projection containing `schema_version`, `window`, `evidence_cutoff_at`, semantic Provider outcomes including cadence/status/origin/carry-forward fields but excluding `retrieved_at`, `producer`, `feed_config`, the logical `feed_schema` descriptor, `provider_contracts`, the globally ordered evidence items, and the pipeline semantic result. Execution-audit timestamps, Provider `retrieved_at`, Git metadata, free-form warnings, physical bundle schema descriptors, artifact paths, sizes, checksums, `content_digest`, and `run_id` SHALL remain outside that semantic projection. `run_id` SHALL continue to derive from the fixed cutoff and `content_digest`. Splitting or rejoining unchanged logical evidence SHALL NOT by itself change semantic identity, while changing freshness state or carry-forward provenance SHALL change it deterministically.

#### Scenario: Only physical bundle layout changes
- **WHEN** identical logical evidence and metadata are represented by the required deterministic artifacts rather than the legacy mixed envelope
- **THEN** reconstructed semantic identity remains stable

#### Scenario: Artifact inventory or evidence is tampered with
- **WHEN** physical integrity changes or reconstructed semantic evidence differs
- **THEN** integrity validation fails or the recomputed semantic identity differs, and the bundle is rejected

#### Scenario: Only execution timing changes
- **WHEN** two bundles have the same logical semantic projection and cutoff but different truthful audit timestamps
- **THEN** they have the same `content_digest` and `run_id`

#### Scenario: Freshness status changes
- **WHEN** identical evidence at the same cutoff carries different cadence status, origin contract hash, or carry-forward provenance
- **THEN** the semantic digest differs rather than hiding the snapshot lifecycle change as execution metadata

### Requirement: Feed audit timestamps are truthful lifecycle observations
The pipeline SHALL obtain `collection_started_at` from the actual start of collection, capture one `evidence_cutoff_at` after collection starts and before any Provider request, obtain a non-null Provider `retrieved_at` when that Provider response actually returns even when it contains no new observation, obtain `collection_completed_at` only after all Provider work has reached a terminal or fenced state, and obtain `generated_at` when the Feed envelope is finalized. Failed or skipped work that never returns a Provider response SHALL retain null `retrieved_at`. The pipeline SHALL NOT derive audit timestamps by offsetting the cutoff, copying another lifecycle or source timestamp, or otherwise synthesizing an unobserved event; changing `retrieved_at` or `generated_at` SHALL NOT change original evidence times or make stale evidence fresh.

#### Scenario: Successful collection lifecycle
- **WHEN** providers return and a Feed envelope is built
- **THEN** observed timestamps satisfy `collection_started_at <= evidence_cutoff_at <= each non-null retrieved_at <= collection_completed_at <= generated_at`

#### Scenario: Provider never returns evidence
- **WHEN** a provider is skipped or reaches its recorded terminal state before any response returns
- **THEN** its outcome has null `retrieved_at` rather than a synthetic timestamp

#### Scenario: Clock calls identify lifecycle events
- **WHEN** a deterministic test clock supplies distinct instants at collection start, cutoff capture, provider return, collection completion, and envelope generation
- **THEN** the Feed records those corresponding instants without fixed offsets or timestamp reuse

#### Scenario: Current check returns no new observation
- **WHEN** a Provider response returns successfully without a new source observation
- **THEN** `retrieved_at` records that current return while carried source timestamps remain unchanged and freshness is evaluated from cadence authority rather than the audit timestamp

### Requirement: Canonical serializer owns every published Feed bundle file
Every byte sequence passed to bundle publication SHALL equal the shared canonical serialization of its validated manifest or domain-artifact object. The manifest inventory SHALL hash and size those exact canonical artifact bytes. Feed-producing modules SHALL NOT use independent JSON serializer settings for bundle products.

#### Scenario: Bundle files are serialized
- **WHEN** a valid candidate is admitted to publication
- **THEN** every manifest and artifact byte sequence is canonical and every inventory checksum and size matches the exact published artifact bytes

### Requirement: GitHub-hosted repository-native Feed deployment
The repository SHALL define an active credential-free Feed job on GitHub-hosted `ubuntu-latest` for `workflow_dispatch` and daily cron `20 0 * * *` (08:20 Asia/Shanghai). The job SHALL use the checked-out repository's explicit `feeds/` Feed product root and `.feed-state/` runtime-state root, with the repository as durable cross-run authority, require only the built-in repository publication credential with `contents: write`, and use one non-cancelling concurrency group. It SHALL NOT require a self-hosted runner, external persistent filesystem, `FOLLOW_THE_MONEY_OUTPUT_ROOT`, or a custom mandatory default-off enable variable. The nominal schedule SHALL NOT determine `evidence_cutoff_at`; the existing Feed runtime SHALL capture the truthful cutoff after the job actually starts. Prepare, migration or arming publication, collection, finalization, diagnostics, and original-failure restoration SHALL remain explicitly ordered; migration-only mode SHALL end without collection. The job SHALL generate and publish deterministic evidence only and SHALL NOT invoke Host-Agent reasoning, Audit, Event Structuring, or retained market/scoring capabilities.

After exact deployment finalization, a failed Feed step SHALL trigger an `always()` diagnostics presentation before the existing original-failure restoration remains final authority. The presentation SHALL select only known fields from transient Feed status, preserve existing Provider-outcome order, safely represent control characters, newlines, and Markdown-sensitive text, and bound human-facing message, warning, and error output. It SHALL write a concise failure report to Actions logs and `$GITHUB_STEP_SUMMARY` without re-evaluating completeness, coverage, health, publication, or exit category. Missing or corrupt transient status, unavailable summary output, or renderer failure SHALL produce at most a bounded diagnostics-unavailable notice and SHALL be non-gating: it SHALL NOT skip or alter finalization, turn a successful Feed into failure, replace an underlying Feed failure, or change the existing `.feed-exit-code` category `0`, `1`, or `2`. Transient diagnostics SHALL NOT be committed, added to durable Feed output, RateRegistry state, checkpoint, or deployment lease.

#### Scenario: Daily hosted invocation
- **WHEN** GitHub schedules the repository Feed workflow from cron `20 0 * * *`
- **THEN** a non-cancelling `ubuntu-latest` job is eligible to establish repository state and run the credential-free Feed without a custom opt-in or external output root

#### Scenario: Manual hosted invocation
- **WHEN** an operator uses `workflow_dispatch`
- **THEN** the invocation follows the same repository-state, lease, recovery, checkpoint, Feed, and publication contracts as the scheduled invocation

#### Scenario: GitHub starts the job late
- **WHEN** the scheduled job begins after nominal 08:20 Asia/Shanghai
- **THEN** the Feed captures its actual runtime cutoff and does not claim the nominal cron instant as its evidence cutoff

#### Scenario: Host Agent consumes a published Feed later
- **WHEN** the workflow successfully publishes a deterministic Evidence Feed
- **THEN** Host-Agent reasoning remains a separate later consumer action and no Agent, Audit, Event Structuring, market-state, watchlist, or scoring invocation is added to the workflow

#### Scenario: Repository write policy is not verified
- **WHEN** Actions `contents: write` or branch policy has not been shown to permit the required non-force fast-forward generated-state commits
- **THEN** the checked-in workflow SHALL NOT be declared operationally complete even if local and static validation passes

#### Scenario: Failed hosted collection exposes existing facts
- **WHEN** the hosted Feed step fails after producing a transient status with an existing message, warnings, and Provider outcomes
- **THEN** exact finalization runs first and an always-run diagnostics presentation exposes the selected bounded facts in Actions logs and `$GITHUB_STEP_SUMMARY` before original Feed failure restoration

#### Scenario: Hosted diagnostics are unavailable
- **WHEN** transient status is missing or corrupt, summary output is unavailable, or diagnostics rendering otherwise cannot produce full detail
- **THEN** diagnostics remains non-gating, emits at most a bounded unavailable notice, and neither hides nor replaces the Feed or finalization result

#### Scenario: Successful hosted Feed needs no failure report
- **WHEN** the hosted Feed step succeeds as healthy or degraded accepted output
- **THEN** failure diagnostics do not change the successful path, publication, finalization, checkpoint, or exit `0`

#### Scenario: Migration-only invocation does not collect
- **WHEN** prepare classifies complete legacy state and successfully publishes the migration allowlist
- **THEN** that invocation exits before arming or Provider collection and a later invocation enters the normal lifecycle

### Requirement: Repository bootstrap and durable pre-network lease
After checkout and before normal network-capable execution, deployment preflight SHALL load the authoritative checked-in configuration, explicitly resolve the product and runtime-state roots, classify repository state, and resolve enabled verified Provider contracts through the existing resolution boundary. Static resolution or state-classification failure SHALL make zero Provider requests and SHALL NOT create or mutate normal deployment or rate state. A genuinely new repository runtime-state root with no checkpoint, persistence marker, registry, scope files, or deployment lease SHALL use the existing RateRegistry first-use lifecycle to establish the registry, persistence marker, every currently enabled scope, a supported checkpoint with `previous_success: null`, and bootstrap recovery lease, fast-forward push that explicit state, perform zero Provider requests, and block collection until the configured crash-cooldown quiet boundary has elapsed. Any established or partial runtime state SHALL NOT use this bootstrap path.

For every later network-capable run, repository state SHALL contain a valid checkpoint, minimal versioned `in_progress` deployment lease, and all required rate state before the first possible Provider request. The checkpoint SHALL remain outside the generic runtime-safety allowlist used for ordinary arming. The lease SHALL identify the deployment run and its arming/start/recovery bounds, but SHALL NOT contain token balances, cooldown values, last-dispatch values, policy fingerprints, Provider evidence, HTTP history, checkpoint continuity, or Agent state. Provider work SHALL begin only after the runtime-safety lease and state have been committed and fast-forward pushed to the remote branch and only within the lease's enforced Feed-start bound. A pre-network commit or push failure, non-fast-forward conflict, or missed Feed-start bound SHALL cause zero Provider requests; the workflow SHALL NOT force push or destructively reset the remote branch.

#### Scenario: Static deployment preflight fails
- **WHEN** authoritative configuration, enabled Provider resolution, deployment compatibility, repository layout, checkpoint, RateRegistry, or lease validation fails before arming
- **THEN** the run performs zero Provider requests, does not enter normal Feed execution, and does not create or mutate normal rate, checkpoint, or lease state

#### Scenario: Clean repository bootstrap
- **WHEN** valid resolved Provider contracts exist and neither legacy nor new repository-backed runtime state exists
- **THEN** the run durably establishes the existing registry, marker, current scope states, explicit null checkpoint, and bootstrap recovery boundary in `.feed-state/` and exits without any Provider request

#### Scenario: Bootstrap quiet boundary has not elapsed
- **WHEN** a scheduled or manual invocation occurs before the repository bootstrap recovery boundary
- **THEN** it fails or skips before Provider network without resetting the registry or assuming an unknown previous external or local deployment sent nothing

#### Scenario: New resolved rate scope appears
- **WHEN** an established repository resolves an enabled rate scope not yet present in the authoritative registry
- **THEN** the scope is initialized through the existing RateRegistry first-use semantics and included in the durable pre-network state push before that scope can be used

#### Scenario: Pre-network lease push fails or conflicts
- **WHEN** the `in_progress` lease commit cannot be fast-forward pushed to the remote branch
- **THEN** the workflow makes zero Provider requests and does not use force push or destructive reset to continue

#### Scenario: Feed-start bound is missed
- **WHEN** the durable lease was pushed but the workflow cannot start Feed execution within the lease's permitted start window
- **THEN** Provider work does not start and the workflow may publish a terminal pre-network failure only by another safe fast-forward update

#### Scenario: Established state is missing its checkpoint
- **WHEN** marker, registry, scope, or lease state proves the new runtime root is established but `feed-checkpoint.json` is absent
- **THEN** preflight fails closed before Provider network and does not run clean bootstrap

### Requirement: Conservative incomplete-run recovery envelope
An `in_progress` remote lease in either a validated legacy layout being migrated or the established runtime-state root SHALL mean that the previous ephemeral runner may have sent Provider requests whose exact resulting local RateRegistry state was lost. Its deterministic `recovery_not_before` SHALL conservatively include the latest workflow-permitted Feed start, the existing configured Feed command deadline, and the configured RateRegistry crash cooldown; lease creation time plus crash cooldown alone or an unenforced Provider-time estimate SHALL NOT establish recovery safety. Migration SHALL preserve the original lease state and bounds and SHALL NOT arm Provider work. Before that boundary, a later run SHALL make zero Provider requests and SHALL NOT reset or weaken the last committed registry state.

After the boundary, the run MAY reuse the last committed exact RateRegistry state only when static validation of the authoritative currently enabled resolved Provider contracts proves, for every distinct rate scope, that the configured crash cooldown is at least both the scope's complete token-refill period and its minimum dispatch interval. The validation SHALL derive scopes and policies from resolved contracts without hard-coded Provider IDs. Existing RateRegistry refill, eligibility, migration, debit, refund, and reconcile behavior SHALL remain authoritative; recovery SHALL NOT synthesize token balances or introduce a second rate-state model. Missing, corrupt, unsupported, or incompatible checkpoint, registry, scope, or lease state SHALL fail closed.

#### Scenario: Previous lease is incomplete before recovery
- **WHEN** repository state contains `in_progress` and current time is before `recovery_not_before`
- **THEN** the invocation performs zero Provider requests and preserves the last committed exact registry as potentially stale but authoritative state

#### Scenario: Previous lease is incomplete after compatible recovery
- **WHEN** current time is at or after `recovery_not_before` and every enabled resolved scope satisfies the crash-cooldown recovery envelope
- **THEN** the invocation may arm a new run and lets normal RateRegistry refill and eligibility rules determine dispatch without inventing token state

#### Scenario: Future policy exceeds the recovery envelope
- **WHEN** any enabled resolved scope has a refill period or minimum interval longer than the configured crash cooldown
- **THEN** hosted recovery fails closed before Provider network until the deployment contract is deliberately changed

#### Scenario: Recovery state is missing or corrupt
- **WHEN** an established repository has a missing, corrupt, unknown-version, or internally inconsistent checkpoint, registry, scope state, or lease
- **THEN** hosted execution fails before Provider network without silently bootstrapping over the established state

#### Scenario: Incomplete legacy lease is relocated
- **WHEN** complete legacy state contains a `bootstrap` or `in_progress` lease
- **THEN** migration preserves its original deployment run identity, Feed-start bound, and `recovery_not_before`, performs zero Provider requests, and leaves the next run subject to that boundary

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

### Requirement: Feed deployment workflow acceptance includes Actions semantics
The accepted Feed deployment workflow SHALL be valid under GitHub Actions workflow-definition and expression/context semantics. The authoritative pre-merge path SHALL evaluate the repository's real workflows with an established Actions-aware validator in addition to repository-specific hosted deployment, state ordering, explicit staging, failure-finalization, Git safety, and generated-commit CI checks. Hosted Feed runner selection SHALL remain scheduler-enforced through `runs-on: ubuntu-latest`, without an unavailable workflow-level context or redundant runtime runner guard.

#### Scenario: Accepted Feed deployment workflow
- **WHEN** the repository's real GitHub Actions workflows are evaluated by the authoritative Actions-aware validator
- **THEN** they pass workflow-definition and expression/context validation while the existing project-specific Feed workflow invariants also pass

#### Scenario: Unavailable context is used
- **WHEN** a workflow uses a GitHub Actions context at a workflow key where that context is unavailable
- **THEN** authoritative pre-merge workflow validation fails and the invalid workflow cannot satisfy repository acceptance

#### Scenario: Dedicated Feed runner is selected
- **WHEN** GitHub Actions schedules a Feed generation job
- **THEN** the job is assigned through `runs-on: ubuntu-latest` without requiring self-hosted labels or a later runtime label check

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

### Requirement: Deterministic legacy runtime-state migration
Before normal hosted arming, repository state SHALL be classified as a complete new layout, a complete legacy runtime layout with no new layout, no established layout, or mixed/partial/corrupt/unsupported state. A complete legacy layout SHALL enter a one-time zero-network migration that validates the existing persistence marker, RateRegistry registry, every registered scope, policy compatibility, deployment lease, and recovery information through their authoritative parsers and preserves exact token, refill-anchor, last-dispatch, cooldown, policy-fingerprint, scope-identity, lease-state, Feed-start, and recovery semantics. Only metadata explicitly bound to the old runtime root MAY be normalized to make relocated state truthful.

Migration SHALL move exact durable runtime files from `feeds/` to the runtime-state root, seed the checkpoint from a supported integrity-validated healthy or degraded `feeds/latest.json` when present or explicit `previous_success: null` when absent, leave consumer Feed products untouched, and SHALL NOT scan `feeds/daily/**` for another authority. It SHALL stage only the exact new durable additions and exact legacy runtime deletions, publish them through the existing non-force fast-forward boundary, make zero Provider requests, and end without arming or collecting. Mixed old/new authority, partial state, corrupt or missing registered state, invalid legacy latest when present, incompatible policy, and unsupported versions SHALL fail closed before Provider network without bootstrap, reset, force push, or destructive recovery.

#### Scenario: Complete legacy state migrates
- **WHEN** the new runtime-state layout is absent and every authoritative legacy runtime file is complete, valid, and mutually consistent
- **THEN** migration relocates the exact durable state, removes only the exact legacy runtime paths, publishes the explicit migration allowlist, performs zero Provider requests, and exits before arming

#### Scenario: Legacy latest seeds previous success
- **WHEN** complete legacy runtime state includes a valid supported healthy or degraded `feeds/latest.json`
- **THEN** migration seeds the checkpoint from exactly that Feed's `evidence_cutoff_at` and `run_id` while leaving latest and dated Feed products untouched

#### Scenario: Legacy latest is absent
- **WHEN** complete legacy runtime state has no `feeds/latest.json`
- **THEN** migration seeds `previous_success: null` and does not scan dated history for another cutoff

#### Scenario: Legacy rate and recovery semantics are preserved
- **WHEN** valid legacy state carries token, dispatch, cooldown, policy, scope, bootstrap, or in-progress lease and recovery values
- **THEN** migration preserves those semantic values and the next invocation remains subject to the original recovery boundary

#### Scenario: Mixed or partial layouts fail closed
- **WHEN** old and new authoritative state coexist unexpectedly or either layout is partial, corrupt, unsupported, incompatible, or internally inconsistent
- **THEN** preflight performs zero Provider requests and does not bootstrap, migrate a subset, reset rate state, or arm collection

#### Scenario: Migration stages exact paths only
- **WHEN** migration completes while transient or unrelated worktree files also exist
- **THEN** only exact new durable runtime-state additions and exact legacy runtime-state deletions are staged, with Feed products and unrelated files left untouched

### Requirement: Resolved Provider identity governs shared outbound requests
Every outbound request made through the shared Provider request boundary SHALL include the exact user-agent value from the owning resolved Provider contract. Provider-specific additional request headers SHALL be merged with that identity metadata, but no additional header declaration, including a differently cased user-agent field, SHALL replace or create a second authority for the resolved Provider user-agent. Existing host validation, redirect validation, request and response limits, timeout, retry classification, rate discipline, and credential-free behavior SHALL remain unchanged.

#### Scenario: Provider uses shared request boundary
- **WHEN** an enabled Provider sends a request through the shared request boundary
- **THEN** the outbound request contains the exact user-agent value from that Provider's resolved contract

#### Scenario: Provider supplies additional headers
- **WHEN** a Provider supplies request headers other than user-agent to the shared request boundary
- **THEN** those headers are preserved alongside the resolved Provider user-agent

#### Scenario: Additional headers attempt to replace identity
- **WHEN** Provider-specific headers contain a user-agent field in any letter case
- **THEN** the outbound request uses only the resolved Provider user-agent as identity authority

#### Scenario: SEC EDGAR request is issued
- **WHEN** the SEC EDGAR Provider sends its submissions request through the shared request boundary
- **THEN** its existing endpoint and descriptive resolved user-agent behavior remain valid

### Requirement: Shared HTML index date extraction isolates malformed candidates
Shared HTML index extraction SHALL retain the existing supported separated and compact Provider date formats and their deterministic candidate-source precedence. Within that precedence it SHALL select the first calendar-valid candidate, ignore invalid or unrelated date-like candidates, and continue evaluating later candidates for the same link when available. A link SHALL be promoted to a candidate evidence entry only when it has non-empty link text, a non-empty target, and a supported calendar-valid date. Ignored links SHALL NOT bypass existing URL validation, provenance, acquisition-window, or evidence-normalization rules.

#### Scenario: Production-shaped Provider link contains a valid date
- **WHEN** an HTML index link contains a supported calendar-valid date in an existing Provider URL or link-text format
- **THEN** extraction returns the same normalized UTC date and resolved candidate URL under the existing deterministic precedence

#### Scenario: Navigation link contains an invalid date-like token
- **WHEN** an unrelated navigation link contains a syntactically date-like token with an invalid month or day
- **THEN** extraction ignores that token without emitting an entry or allowing an uncategorized calendar-construction exception to escape

#### Scenario: Invalid candidate precedes a valid candidate
- **WHEN** a link contains multiple supported date-like candidates and an earlier candidate is calendar-invalid while a later candidate is calendar-valid
- **THEN** extraction deterministically selects the first calendar-valid candidate under the existing candidate-source precedence

#### Scenario: Link has no valid supported date
- **WHEN** a malformed or unrelated link contains no calendar-valid candidate in a supported date format
- **THEN** the link is ignored rather than promoted as evidence

#### Scenario: Genuine Provider acquisition fails
- **WHEN** Provider acquisition fails because of upstream blocking, throttling, timeout, network failure, undecodable content, or another existing typed failure condition
- **THEN** the Provider remains incomplete under existing retry and Feed failure semantics and prior evidence does not convert the run into success
