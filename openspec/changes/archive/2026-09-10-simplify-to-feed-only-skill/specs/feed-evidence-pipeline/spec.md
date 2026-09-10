## ADDED Requirements

### Requirement: Production Provider set is closed and required
The shipped production Feed SHALL plan exactly Federal Reserve, BLS, PBOC, NBS, SSE, SZSE, SEC EDGAR, and CFTC as required credential-free Providers. Provider manifests SHALL declare only payload types that their current adapters can emit within the five-domain contract. Yahoo Market and every `market_data`, `flow`, or `calendar` Provider declaration, activation, coverage claim, mapping, and acquisition path SHALL be absent.

#### Scenario: Shipped Provider plan is resolved
- **WHEN** production configuration and verified manifests are resolved
- **THEN** exactly the eight required Providers are planned and no Yahoo or optional Provider path exists

#### Scenario: Provider declaration exceeds its adapter
- **WHEN** a manifest declares a payload type outside the adapter's implemented five-domain output
- **THEN** static resolution fails closed before Provider requests or runtime-state mutation

#### Scenario: Removed Provider is configured
- **WHEN** activation or coverage configuration names Yahoo Market or another removed Provider
- **THEN** startup rejects the configuration instead of ignoring it or restoring `market_data`

### Requirement: Five-domain migration is explicit and atomic
The producer, consumer, schemas, active bundle, continuity state, and generated-state allowlists SHALL migrate coherently to a new major whose closed domain set is `news`, `macro_release`, `policy`, `positioning`, and `filing`. A previous eight-domain bundle MAY be accepted only by the bounded migration path; normal five-domain consumption SHALL NOT treat removed artifacts as current evidence. Activation SHALL remain atomic through the authoritative manifest.

#### Scenario: Existing eight-domain bundle is migrated
- **WHEN** a fully validated previous-major active bundle is migrated
- **THEN** only evidence belonging to the five retained domains enters the new validated bundle and its new identity is computed under the five-domain contract

#### Scenario: Mixed domain generations are presented
- **WHEN** a five-domain manifest is combined with a removed-domain artifact or another generation
- **THEN** bundle validation rejects the whole product

## MODIFIED Requirements

### Requirement: Typed Feed bundle has one authoritative manifest
Every newly generated Feed SHALL consist of canonical `feed-manifest.json` bytes and exactly one canonical domain artifact for each supported Feed payload discriminator, in this deterministic order: `news`, `macro_release`, `policy`, `positioning`, and `filing`. Each item SHALL occur in exactly one artifact selected solely by its `payload.type`; each required artifact SHALL exist even when its `items` array is empty. `market_data`, `flow`, `calendar`, and any unknown payload or artifact domain SHALL be rejected. Grouping SHALL NOT depend on Provider identity or introduce another evidence category.

The manifest SHALL be the only authoritative bundle entry point and SHALL contain bundle identity, window and cutoff, truthful generation metadata, producer/configuration/Provider contracts, Provider outcomes, pipeline result, schema descriptors, and a complete five-domain artifact inventory. It SHALL contain no evidence item, duplicated evidence payload, analysis, ranking, signal, regime, impact, or recommendation. A domain artifact SHALL contain only its artifact schema version, bundle `run_id`, domain discriminator, and evidence items.

#### Scenario: Mixed evidence is routed
- **WHEN** normalized evidence contains different supported payload types
- **THEN** each item appears once in its matching artifact in the closed five-domain inventory

#### Scenario: A domain has no evidence
- **WHEN** a valid run produces no item for a supported payload type
- **THEN** the manifest inventories the corresponding required empty artifact

#### Scenario: Removed evidence type is supplied
- **WHEN** normalized evidence or an inventory entry uses `market_data`, `flow`, or `calendar`
- **THEN** validation rejects the candidate before publication or consumption

#### Scenario: Consumer discovers available evidence
- **WHEN** a consumer reads a valid manifest
- **THEN** its closed inventory identifies all five required domains, canonical paths, item counts, byte sizes, and digests without inspecting payloads

#### Scenario: Intelligence enters the bundle
- **WHEN** the manifest or a domain item contains prohibited financial interpretation or investment intelligence
- **THEN** bundle validation rejects the candidate before publication or consumption

### Requirement: Single authoritative production configuration
Production configuration SHALL assign exactly one authoritative checked-in source to each surviving normative Feed field: application and Feed runtime fields to `config/config.yaml`, Provider-specific contract facts to the owning Provider manifest, and Provider activation plus coverage policy to `config/providers.yaml`. It SHALL contain no Audit, Event, entity-resolution, market role/session, Market State, watchlist, scoring/ranking, Brief run/freshness, or other removed-capability field. Static startup resolution SHALL require, parse, validate, and explicitly materialize every surviving normative field without silently substituting a Python or loader default. A duplicated field retained for compatibility SHALL be validation-only, match its authority, and not independently affect behavior. Coverage membership SHALL derive only from the coverage matrix and MAY place a Provider in multiple groups.

#### Scenario: YAML-owned value changes
- **WHEN** a valid Feed limit, path, rate, Provider, coverage, provenance, or SEC watched-company value changes
- **THEN** resolved Feed behavior reflects that declared value without a Python-code change

#### Scenario: Compatibility mirror disagrees
- **WHEN** a surviving compatibility declaration differs from its authoritative Feed or Provider field
- **THEN** startup fails closed and neither declaration independently controls runtime behavior

#### Scenario: Provider belongs to multiple coverage groups
- **WHEN** the coverage matrix places a required Provider in more than one surviving group
- **THEN** coverage assessment uses every declared membership from the matrix

#### Scenario: Removed configuration is supplied
- **WHEN** configuration contains a scoring, Market State, watchlist, safety lexicon, entity, role/session, Yahoo, or Brief-only field
- **THEN** startup fails closed rather than ignoring the field

#### Scenario: Required normative value is missing
- **WHEN** a surviving required field is absent from its authoritative source
- **THEN** startup fails through the configuration/startup category instead of using a hidden default

#### Scenario: Static resolution fails before runtime mutation
- **WHEN** configuration, manifest, identity, verification, or cross-source validation fails
- **THEN** the Feed makes zero Provider requests, performs no normal collection work, mutates no rate state, and does not replace the active bundle

### Requirement: Credential-free verified provider contracts
The Feed SHALL strictly compose required activation and coverage policy with each of the eight supported checked-in verified Provider manifests before execution. Each manifest SHALL remain authoritative for Provider identity/version, verification and evidence metadata, authentication/protocol, fetch/redirect/source-link rules, charset/content type, request/response limits, rate policy, pagination, empty-window semantics, implemented payload types, cadence, and fixture provenance. The one resolved contract SHALL drive adapter behavior, rate handling, planning, coverage, and the embedded `provider_contracts` snapshot. All eight Providers SHALL require no paid data credential, and every accepted URL SHALL be HTTPS, credential-free, canonicalized under its owning policy, and validated before identity or publication.

#### Scenario: Default providers run without credentials
- **WHEN** shipped configuration loads without a paid data credential
- **THEN** all eight required verified Providers initialize for planning without reading an API key

#### Scenario: Enabled Provider contract cannot be resolved
- **WHEN** any required manifest is missing, invalid, unsupported, mismatched, unverified, or outside the five-domain contract
- **THEN** startup fails closed before any Provider request or normal persistent mutation

#### Scenario: Provider contract is incomplete
- **WHEN** a required manifest omits a contract fact or an adapter emits evidence outside its resolved payload or source-link policy
- **THEN** validation fails closed before the Provider can count toward coverage

#### Scenario: Manifest-owned runtime value changes
- **WHEN** a valid authoritative manifest-owned value changes for a required Provider
- **THEN** resolved adapter behavior and its embedded contract snapshot reflect the same value without a second runtime authority

#### Scenario: Provider is disabled
- **WHEN** shipped policy disables one of the eight required Providers
- **THEN** static coverage validation rejects the incomplete production plan before collection

### Requirement: Production Feed activates CFTC weekly positioning evidence
The shipped production Feed plan SHALL enable the verified credential-free CFTC Provider as required coverage with minimum one and publish accepted `positioning` items only in the positioning artifact. Its outcome and embedded contract SHALL preserve CFTC identity, Tier 1 provenance, weekly cadence with `data_as_of` reference time, and declared validity window. A complete check with no new weekly report MAY produce a contract-valid empty or validation-gated unchanged result, but CFTC SHALL NOT be optional or silently omitted. Its evidence SHALL contain no signals, ranking, scoring, interpretation, or investment conclusions.

#### Scenario: Production planning includes CFTC
- **WHEN** shipped production configuration is resolved
- **THEN** CFTC is enabled, included in minimum-one required coverage, embedded in the manifest, and represented by exactly one planned outcome

#### Scenario: A new CFTC report is available
- **WHEN** a complete CFTC check returns a valid new or changed report within its weekly validity window
- **THEN** the current slice deterministically replaces the prior slice and is published only as positioning evidence with original source times

#### Scenario: No new weekly report is available
- **WHEN** a complete CFTC check returns no new observation and a fully validated prior slice remains valid
- **THEN** that slice is carried unchanged with `valid_unchanged` freshness and no source-semantic timestamp is rewritten

#### Scenario: CFTC fails after a prior snapshot exists
- **WHEN** CFTC acquisition fails, is partial, or otherwise cannot establish a complete current check while prior evidence exists
- **THEN** required coverage records the incomplete outcome, does not treat CFTC as optional, and does not substitute prior evidence for current success

#### Scenario: Published CFTC evidence is inspected
- **WHEN** a consumer validates a published bundle containing CFTC positioning evidence
- **THEN** the positioning artifact and manifest expose its Provider outcome, provenance, cadence, originating contract, and unchanged source-semantic timestamps

### Requirement: Provider cadence is a closed freshness authority
Every required Provider contract SHALL use exactly one cadence mode from `weekly`, `scheduled`, or `event_driven`, and one reference-time selector from `data_as_of`, `source_updated_at`, or `checked_at`. Weekly and scheduled contracts SHALL use source-semantic reference time and a positive validity window; event-driven contracts SHALL use `checked_at` with no age window. Removed `market_session` cadence SHALL be rejected. The owning verified manifest SHALL be the sole cadence/reference/validity authority, preserved in the resolved and embedded contract without inferred defaults or a duplicate lookup table.

#### Scenario: Weekly contract is resolved
- **WHEN** CFTC declares its positive weekly validity window
- **THEN** static resolution and the embedded contract expose that exact cadence without a Feed-code default

#### Scenario: Event-driven contract declares an age window
- **WHEN** an event-driven Provider declares age-based validity
- **THEN** startup fails closed because a successful current check is authoritative for that cadence

#### Scenario: Market-session contract selects check time
- **WHEN** a Provider declares the removed `market_session` cadence with any reference-time selector
- **THEN** static resolution rejects it before Provider work

#### Scenario: Bounded cadence omits its validity window
- **WHEN** a weekly or scheduled Provider omits or misstates its positive validity window
- **THEN** static validation fails before Provider work or publication

### Requirement: Feed bundle is the serialized external contract
Every published bundle SHALL validate against the new five-domain manifest, artifact, and logical Feed schema majors and their semantic invariants. The immediately preceding eight-domain major MAY remain read-compatible only for bounded migration; new production SHALL NOT emit it and normal current-Feed consumption SHALL use the five-domain major. The bundle SHALL retain fixed acquisition window, truthful lifecycle timestamps, Provider outcomes with freshness and availability, canonical redacted Feed configuration snapshot, eight required Provider contract snapshots, producer descriptor, canonical logical `content_digest`, cutoff-derived `run_id`, pipeline semantics, and exactly one supported payload per item. Consumers SHALL validate from embedded producer contracts without requiring equality with the consumer build.

#### Scenario: Producer and consumer builds differ
- **WHEN** another build produced a valid supported five-domain bundle
- **THEN** the consumer validates it from embedded descriptors without requiring current build hashes to match

#### Scenario: Payload type and artifact domain disagree
- **WHEN** an item is stored outside the artifact matching its retained payload discriminator
- **THEN** validation rejects the bundle

#### Scenario: Previous-major active bundle is read
- **WHEN** a complete previous-major bundle enters the bounded migration path
- **THEN** it may seed only a newly validated five-domain candidate and is not exposed as the normal current product after migration

#### Scenario: New production attempts the preceding major
- **WHEN** a producer candidate declares the previous eight-domain major or inventories a removed domain
- **THEN** new-production validation rejects it before publication

### Requirement: Provenance tiers and payload-specific time semantics
Every Feed item SHALL retain Provider identity, source name, tier, kind, canonical URL, supplied publication/update time, `source.knowledge_available_at`, and the retained payload's source-semantic effective/reference time and selection basis. Provider `retrieved_at` and Feed `generated_at` SHALL remain execution observations and SHALL NOT be copied into evidence or treated as source time. Newly acquired `news`, `macro_release`, `policy`, and `filing` evidence SHALL be selected by knowledge time in the half-open window; current `positioning` and validation-gated carried slices MAY contain earlier source times only under declared cadence contracts. Retrieval time SHALL NOT establish cutoff eligibility or freshness.

#### Scenario: Evidence becomes known after cutoff
- **WHEN** retained evidence has an earlier effective time but source availability at or after the cutoff
- **THEN** it is excluded from the run rather than admitted from effective time alone

#### Scenario: Calendar evidence was announced earlier
- **WHEN** previously announced calendar evidence is encountered during migration or collection
- **THEN** it is excluded from the five-domain candidate rather than retained through a future-horizon exception

#### Scenario: Tier 3 evidence is normalized
- **WHEN** a supported commentary source emits an otherwise valid retained-domain item
- **THEN** it remains explicitly Tier 3 and is not promoted

#### Scenario: Unchanged evidence is checked again
- **WHEN** a complete Provider check allows a prior slice to be carried
- **THEN** current retrieval time records the check while carried evidence retains original source-semantic times

## REMOVED Requirements

### Requirement: Evidence-backed market mapping contract
**Reason**: Yahoo Market, market roles, and `market_data` are removed.
**Migration**: Remove all role mappings and mapping-verification configuration; no replacement market Provider is added.

### Requirement: Verified mappings gate canonical Feed identity
**Reason**: No market mapping or market-data payload remains.
**Migration**: Feed identity is recomputed over the five retained domains and eight required Provider contracts.

### Requirement: Market coverage is bounded by verified runnable capability
**Reason**: Market coverage and Yahoo acquisition are removed.
**Migration**: Remove market coverage rows and narrow exchange coverage to implemented news evidence.

### Requirement: Raw bounded market history
**Reason**: `market_data` and post-Feed market analytics are outside the simplified product.
**Migration**: No raw market history is published; consumers receive only the five retained evidence domains.
