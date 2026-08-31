# feed-evidence-pipeline Specification

## Purpose
Define the current credential-free provider-to-Feed collection, deterministic evidence normalization and validation, provenance, bounded timing and rate discipline, and durable publication boundary.

## Requirements

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
- **THEN** the Feed makes zero Provider network requests, performs no normal collection work, does not create or mutate rate-registry state, and does not publish or replace a dated or latest Feed

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
Production planning for an enabled market Provider SHALL create canonical market-role acquisition work only for mappings that passed the evidence-backed verification contract. An unverified mapping SHALL NOT emit a Feed item whose `market_data.instrument_id` asserts that canonical role identity, and SHALL NOT be made eligible by attaching an item-level unverified flag after acquisition. All mappings SHALL remain visible in deterministic order in the resolved Provider contract and corresponding Feed `provider_contracts` snapshot, including verification provenance for verified mappings and reasons for unverified mappings. The Feed schema SHALL remain unchanged.

#### Scenario: Production market adapters are planned
- **WHEN** an enabled market Provider has both verified and unverified resolved role mappings
- **THEN** production planning creates adapters only for the verified mappings in canonical role order

#### Scenario: Unverified mapping cannot emit canonical role evidence
- **WHEN** a role mapping remains unverified
- **THEN** no production adapter is planned for that mapping and no Feed item can enter through that path with its canonical `market_data.instrument_id`

#### Scenario: Provider contract snapshot is built
- **WHEN** the resolved Provider contract contains verified and unverified mappings
- **THEN** its deterministic snapshot exposes every mapping with the verified provenance or unverified reason required by its state

#### Scenario: Verification fails before runtime mutation
- **WHEN** any mapping verification, evidence-reference, tuple-association, or mapping-parity check fails during static resolution
- **THEN** the Feed makes zero Provider network requests, performs no normal collection work, does not create or mutate rate-registry state, and does not publish or replace a dated or latest Feed

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
Before reading the current latest Feed or capturing the cutoff, collection SHALL
acquire one exclusive lock in the explicit output root and hold it through
publication. Provider dispatch SHALL use the persistent closed output-root registry
and per-scope rate state, durably debit and install the crash-conservative provisional
cooldown before every possible send, reconcile controlled outcomes without refunding
the send, honor valid `Retry-After`, and fail closed on missing, corrupt, unknown, or
unrecoverable active state. Collection SHALL enforce the configured global and
per-host concurrency limits, stable provider-ID result order, sequential pagination
unless the manifest proves otherwise, and cancellation with no late Feed mutation.

#### Scenario: Two entries share one output root
- **WHEN** a second process starts with the same output root while the first holds the collection lock
- **THEN** it waits without consuming provider concurrency and plans from the latest state only after lock acquisition, or fails typed `collection_lock_timeout` before any provider call

#### Scenario: A dispatched process crashes
- **WHEN** a process exits after the durable pre-send debit and before controlled reconciliation
- **THEN** the next process retains the debit and provisional cooldown instead of resetting the scope or assuming no request occurred

#### Scenario: Provider completions are reordered
- **WHEN** identical provider fixtures complete under different schedules within the concurrency limits
- **THEN** normalized provider outcomes and Feed bytes remain in stable provider-ID order

#### Scenario: Production dry run can send a request
- **WHEN** `--dry-run` dispatches an enabled production adapter that may contact its verified host
- **THEN** the run acquires the output-root collection lock and durably debits and reconciles rate state exactly as a publishing run, while creating no dated or latest Feed artifact

### Requirement: Bounded command deadline and non-cancellable commit
The minimal Feed entry SHALL enforce the existing 300-second command-start monotonic
deadline with an exact 15-second pre-commit reserve. Lock waits, rate waits,
pagination, retries, request attempts, reversible processing, and staging `fsync`
SHALL fit before second 285. Once a fully staged candidate is admitted to filesystem
commit by second 285, rename and parent-directory `fsync` SHALL run to their normal
result without cancellation or rollback; completion after second 300 MAY only add
`commit_elapsed_overrun` to external status or stderr and SHALL NOT change the
already hashed Feed bytes.

#### Scenario: No attempt fits before the reserve
- **WHEN** the next wait or request attempt cannot complete within the remaining pre-commit budget
- **THEN** collection stops with the typed deadline outcome before that attempt begins

#### Scenario: Staging crosses the reserve boundary
- **WHEN** candidate staging or its required pre-commit `fsync` advances the monotonic clock to or beyond second 285
- **THEN** publication removes reversible staging files and fails typed `pre_commit_deadline_exceeded` before any dated or latest rename

#### Scenario: Commit crosses the nominal deadline
- **WHEN** a candidate is fully staged and admitted by second 285 but durable commit completes after second 300
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

### Requirement: Feed is the serialized external contract
Every published Feed SHALL validate against the supported major version of
`feed.schema.json` and its semantic invariants. It SHALL contain the fixed window
and collection timestamps, provider outcomes, canonical redacted Feed configuration
snapshot, Feed-schema descriptor, enabled-provider runtime-contract snapshots,
producer application descriptor, canonical `content_digest`, cutoff-derived
`run_id`, and exactly one supported typed payload per item. Validation SHALL
recompute embedded aggregate identities, the canonical digest projection, and run
identity from the Feed's embedded producer contracts rather than requiring equality
with the current consumer build or manifests.

#### Scenario: Feed identity is recomputed
- **WHEN** a published or fixture Feed is consumed
- **THEN** schema, semantic, embedded-contract, digest, and cutoff-derived run-ID validation all succeed or consumption fails closed

#### Scenario: Consumer build differs
- **WHEN** a valid Feed was produced by another build with the same supported schema major
- **THEN** the consumer validates it from embedded producer descriptors without requiring its current build or manifest hashes to match

#### Scenario: Payload type and shape disagree
- **WHEN** an item declares one supported type but supplies another type's payload
- **THEN** closed-schema validation rejects the Feed

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
Every Feed item SHALL retain owning provider identity, source name, tier, kind,
canonical URL, knowledge time, effective/reference time, retrieval time, precision,
and payload-specific selection basis. Event-like items SHALL be selected by knowledge
time in the half-open Feed window; bounded market lookbacks, current positioning,
and future calendar snapshots MAY include earlier effective times only under their
declared availability contracts. Retrieval time SHALL remain audit metadata and
SHALL NOT establish cutoff eligibility.

#### Scenario: Evidence becomes known after cutoff
- **WHEN** an item or market observation has an earlier effective time but source availability at or after `evidence_cutoff_at`
- **THEN** it is excluded from the run rather than admitted from effective time alone

#### Scenario: Calendar evidence was announced earlier
- **WHEN** a previously announced calendar item was known before cutoff and remains inside the configured future horizon
- **THEN** the current calendar snapshot may include it with its original provenance and scheduled time

#### Scenario: Tier 3 evidence is normalized
- **WHEN** an enabled commentary source emits an otherwise valid item
- **THEN** the item remains explicitly Tier 3 and normalization does not promote its authority

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
One provider failure SHALL NOT stop other providers. The Feed SHALL record attempted,
succeeded, empty, partially valid, failed, skipped, fetched, accepted, and rejected
outcomes. A provider outcome SHALL contribute to coverage only when it is `healthy`,
or when it is `empty` and that provider's verified `empty_valid_for_window` contract
is true. An `empty` outcome whose provider contract does not permit empty, and every
`partial`, `failed`, or `skipped` outcome, SHALL NOT contribute to coverage. A
provider SHALL be `partial` when it retains accepted evidence but also has rejected
items or incomplete later sub-request, role, or page work; retained valid evidence
SHALL remain available, but a partial provider SHALL NOT satisfy full mandatory
coverage. With at least one accepted item, any enabled-provider or mandatory-group
degradation SHALL produce `degraded`; otherwise complete mandatory coverage and no
enabled-provider degradation SHALL produce `healthy`. Zero accepted items SHALL
produce `failure` regardless of permitted-empty outcomes, and a failure candidate
SHALL NOT be published or replace the last valid latest Feed. Provider-specific and
coverage-group warnings SHALL identify every cause used to degrade the pipeline.

#### Scenario: One provider fails and another succeeds
- **WHEN** one enabled provider fails or times out while another contributes valid evidence
- **THEN** a schema-valid degraded Feed publishes, exits `0`, retains the valid evidence, and records warnings identifying the failed provider and any deficient coverage group

#### Scenario: Mandatory group is deficient with accepted evidence
- **WHEN** the pipeline accepts at least one valid item but fewer eligible provider outcomes contribute than a non-optional coverage group's minimum
- **THEN** the Feed is degraded, publishes, exits `0`, and identifies the deficient coverage group

#### Scenario: Permitted empty contributes to coverage
- **WHEN** a provider returns no accepted item and its `empty_valid_for_window` contract is true
- **THEN** its `empty` outcome contributes to coverage without contributing an accepted evidence item

#### Scenario: Non-permitted empty does not contribute to coverage
- **WHEN** a provider returns no accepted item and its `empty_valid_for_window` contract is false
- **THEN** its `empty` outcome does not satisfy coverage and is identified as provider degradation when other accepted evidence makes a degraded Feed usable

#### Scenario: Every provider returns no accepted item
- **WHEN** all enabled requests complete but the pipeline accepts zero items, including when every empty outcome is contract-permitted
- **THEN** the run is failure, exits `1`, does not publish a dated Feed, and does not replace the last valid latest Feed

#### Scenario: An item is partially invalid
- **WHEN** a provider produces accepted items and rejects one or more other normalized items
- **THEN** accepted items and rejection counters are retained, the provider is partial, and the pipeline is degraded

#### Scenario: Later provider work fails after valid evidence
- **WHEN** a provider retains accepted evidence from one sub-request, role, or page and later work fails or is incomplete
- **THEN** the retained evidence remains, the provider is partial rather than healthy or wholly failed, and the pipeline is degraded

#### Scenario: Partial provider cannot satisfy full coverage
- **WHEN** a partial provider belongs to a mandatory coverage group
- **THEN** it contributes no full mandatory coverage even though its accepted items remain usable in the degraded Feed

### Requirement: Fixed advancing Feed window
After acquiring the collection lock, the run SHALL read and validate the current
latest Feed, capture one `evidence_cutoff_at` before provider requests, and publish a
strictly advancing half-open `[window.start, evidence_cutoff_at)` interval. The first
run SHALL use the bounded bootstrap lookback; later runs SHALL advance from the prior
valid cutoff subject to the configured maximum gap. Equal or earlier cutoffs,
unreadable or invalid existing latest state, look-ahead evidence, and invalid
timestamp ordering SHALL fail closed before provider calls or publication as their
phase requires. Deadlines SHALL use monotonic time while persisted instants use RFC
3339 UTC with Asia/Shanghai schedule metadata.

#### Scenario: Existing latest Feed is invalid
- **WHEN** `feeds/latest.json` exists but fails schema, semantic, digest, run-ID, or embedded-contract validation
- **THEN** planning fails typed `invalid_latest_integrity` with zero provider calls and no new dated or latest artifact

#### Scenario: Cutoff does not advance
- **WHEN** the captured cutoff is equal to or earlier than the current valid latest cutoff
- **THEN** planning returns typed `non_advancing_cutoff` before any provider call or artifact write

#### Scenario: Collection finishes after cutoff
- **WHEN** collection completes several minutes after the fixed cutoff
- **THEN** the Feed preserves the original cutoff and records later collection timestamps without claiming later evidence coverage

### Requirement: Durable monotonic publication
Before publication, only a healthy or degraded candidate SHALL be admitted and SHALL
pass Feed schema, semantic, provenance, identity, and digest validation. A failure
candidate SHALL NOT be passed to the publication subsystem. Publication SHALL create
the immutable dated `feeds/daily/YYYY-MM-DD/<run_id>.json` artifact before atomically
replacing `feeds/latest.json`, using unpredictable same-parent staging, create-only
writes, file and directory `fsync`, atomic no-replace dated rename, same-directory
latest replacement, and parent-directory `fsync`. It SHALL be idempotent for the
same run and SHALL use the maximum `(evidence_cutoff_at, content_digest)` tuple for
latest ownership independently of candidate submission order. Publication failure
or durability uncertainty SHALL remain an execution failure and SHALL NOT be
reported as degraded success or fabricate rollback guarantees.

#### Scenario: Valid candidate publishes
- **WHEN** a healthy or degraded candidate passes validation and durable filesystem primitives are available
- **THEN** the immutable dated artifact becomes durable before latest is replaced and both carry the same validated Feed

#### Scenario: Failure candidate is not admitted
- **WHEN** pipeline assessment produces `failure`
- **THEN** the orchestration does not call the publication subsystem, creates no normal dated Feed artifact, and leaves the previous valid latest unchanged

#### Scenario: Latest replacement fails
- **WHEN** the dated artifact is durable but latest replacement fails
- **THEN** the previous valid latest remains unchanged, the dated artifact is not falsely rolled back, and the run exits `1` as a publication failure

#### Scenario: Publication fails before commit
- **WHEN** a healthy or degraded candidate is admitted but publication fails before any dated or latest commit
- **THEN** the run exits `1` and does not convert the failure into degraded success

#### Scenario: Stale candidate reaches publication
- **WHEN** an older valid externally prepared candidate is submitted after a newer latest Feed
- **THEN** it may retain its immutable dated artifact but cannot replace the newer latest Feed

#### Scenario: Equal-cutoff variants arrive in either order
- **WHEN** two valid candidates have the same `evidence_cutoff_at`, different `content_digest` values, and are submitted in either order
- **THEN** both immutable dated artifacts remain and latest deterministically contains the candidate with the lexicographically greater canonical `content_digest`

### Requirement: Minimal internal Feed entry outcomes
Exactly one minimal internal Feed entry SHALL expose configuration, explicit output
root, deterministic clock/window injection, status output, and `--dry-run`.
Healthy or degraded success SHALL exit `0`; zero accepted evidence and typed
planning, collection, runtime, validation, integrity, deadline, rate-state,
filesystem, publication, or durability failure SHALL exit `1`; usage,
configuration, invalid explicit input, or startup-capability rejection SHALL exit
`2`. Expected exit categories SHALL derive from explicit types or typed outcomes,
never message text. Dry-run SHALL execute the same fetch, normalize, validation,
coverage, and pipeline-health decision as publication mode while omitting dated and
latest Feed publication.

#### Scenario: Degraded Feed succeeds
- **WHEN** a degraded candidate remains valid and dry-run or publication completes
- **THEN** the entry exits `0` while machine-readable status and stderr identify the degradation

#### Scenario: Failure dry run exits nonzero
- **WHEN** dry-run completes assessment with zero accepted evidence and pipeline status `failure`
- **THEN** the entry exits `1`, reports the failure status and warnings, and creates no dated or latest Feed artifact

#### Scenario: Failure publication run exits nonzero
- **WHEN** publication mode completes assessment with pipeline status `failure`
- **THEN** the entry exits `1` without invoking publication or exposing success artifact paths

#### Scenario: Input and execution errors use misleading words
- **WHEN** typed input and execution failures contain arbitrary words associated with the opposite category
- **THEN** their exits remain respectively `2` and `1` based only on type or typed outcome

#### Scenario: Dry run is requested for usable evidence
- **WHEN** `--dry-run` is set and assessment produces healthy or degraded status
- **THEN** the entry validates and reports the candidate with exit `0` without changing dated or latest Feed artifacts, while any real provider sends still obey lock and durable rate-state contracts

### Requirement: Feed consumption rejects pipeline failure
The Feed consumer health boundary SHALL distinguish structural validity from
consumability. After schema and identity validation, it SHALL accept a healthy Feed,
accept a degraded Feed while propagating its warnings, and reject a Feed whose
`pipeline.status` is `failure`. Producer admission SHALL NOT be the sole protection
against historical artifacts, manual writes, fixtures, or regressions.

#### Scenario: Healthy Feed is consumable
- **WHEN** a structurally and semantically valid Feed has pipeline status `healthy` and satisfies the existing freshness checks
- **THEN** the consumer accepts it as healthy

#### Scenario: Degraded Feed is consumable with context
- **WHEN** a structurally and semantically valid Feed has pipeline status `degraded` and satisfies the existing hard freshness checks
- **THEN** the consumer accepts it as degraded and propagates its pipeline warnings

#### Scenario: Schema-valid failure Feed is rejected
- **WHEN** a Feed passes schema and identity validation but has pipeline status `failure`
- **THEN** the consumer raises a typed Feed load or health error and does not continue analysis

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

### Requirement: Feed semantic identity is separate from execution audit metadata
`content_digest` SHALL be the canonical digest of an explicit semantic projection containing `schema_version`, `window`, `evidence_cutoff_at`, semantic provider outcomes, `producer`, `feed_config`, `feed_schema`, `provider_contracts`, `items`, and the pipeline semantic result. The semantic provider outcomes SHALL contain every serialized provider-outcome field except `retrieved_at`. The projection SHALL exclude `collection_started_at`, `collection_completed_at`, `generated_at`, provider `retrieved_at`, `content_digest`, `run_id`, and any undeclared top-level execution metadata. `run_id` SHALL continue to derive from the fixed cutoff and `content_digest`.

#### Scenario: Only execution timing changes
- **WHEN** two valid Feed envelopes have the same semantic projection and cutoff but different collection duration, provider `retrieved_at`, or `generated_at` values
- **THEN** they have the same `content_digest` and `run_id`

#### Scenario: Semantic evidence changes
- **WHEN** an item, provider semantic outcome, embedded producer contract, Feed configuration, window, cutoff, or pipeline semantic result changes
- **THEN** the recomputed `content_digest` changes

#### Scenario: Identity is validated by a consumer
- **WHEN** a Feed is consumed
- **THEN** validation reconstructs the explicit semantic projection, recomputes `content_digest` and `run_id`, and fails closed on any mismatch

#### Scenario: Existing supported-major Feed uses the legacy projection
- **WHEN** a previously published schema-major-compatible Feed is read during migration and its identity validates only under the former whole-envelope projection
- **THEN** the reader accepts that legacy artifact, while every newly produced Feed uses the semantic projection

### Requirement: Feed audit timestamps are truthful lifecycle observations
The pipeline SHALL obtain `collection_started_at` from the actual start of collection, capture one `evidence_cutoff_at` after collection starts and before any provider request, obtain a non-null provider `retrieved_at` when that provider request actually returns, obtain `collection_completed_at` only after all provider work has reached a terminal or fenced state, and obtain `generated_at` when the Feed envelope is finalized. Failed or skipped work that never returns a provider response SHALL retain null `retrieved_at`. The pipeline SHALL NOT derive audit timestamps by offsetting the cutoff, copying another lifecycle timestamp, or otherwise synthesizing an unobserved event.

#### Scenario: Successful collection lifecycle
- **WHEN** providers return and a Feed envelope is built
- **THEN** observed timestamps satisfy `collection_started_at <= evidence_cutoff_at <= each non-null retrieved_at <= collection_completed_at <= generated_at`

#### Scenario: Provider never returns evidence
- **WHEN** a provider is skipped or reaches its recorded terminal state before any response returns
- **THEN** its outcome has null `retrieved_at` rather than a synthetic timestamp

#### Scenario: Clock calls identify lifecycle events
- **WHEN** a deterministic test clock supplies distinct instants at collection start, cutoff capture, provider return, collection completion, and envelope generation
- **THEN** the Feed records those corresponding instants without fixed offsets or timestamp reuse

### Requirement: Canonical serializer owns published Feed bytes
Every dated or latest Feed byte sequence passed to publication SHALL equal the shared `canonical_bytes()` serialization of its validated Feed object. Feed-producing modules SHALL NOT use independent JSON serializer settings for published Feed bytes.

#### Scenario: Feed is serialized for publication
- **WHEN** a valid healthy or degraded Feed is admitted to publication
- **THEN** its dated and latest candidate bytes are produced by the shared canonical serializer and are byte-identical to `canonical_bytes(feed)`

### Requirement: Publication is idempotent by semantic identity
When a valid immutable dated artifact already exists at the path for a candidate's semantic `run_id`, publication SHALL validate that artifact and compare semantic identity rather than require equality with the candidate's execution-metadata bytes. If the semantic identities match, publication SHALL retain the existing dated bytes, report the run as idempotent, and use the retained immutable bytes for any required `latest.json` repair or replacement. Different semantic identity at the same dated path, invalid existing content, and identity mismatches SHALL continue to fail closed. Existing create-only dated publication, atomic latest replacement, monotonic latest ownership, and `fsync` durability requirements SHALL remain unchanged.

#### Scenario: Same semantic Feed runs with different audit timing
- **WHEN** a later execution has the same semantic `run_id` as an existing valid dated artifact but different truthful audit timestamps
- **THEN** publication retains the first immutable artifact, reports idempotent success, and does not raise an incompatible-content conflict

#### Scenario: Idempotent recovery repairs latest
- **WHEN** the semantic dated artifact exists but `latest.json` is absent or is owned by an older semantic identity
- **THEN** publication repairs `latest.json` from the retained dated artifact bytes rather than the later execution envelope

#### Scenario: Same path carries different semantic identity
- **WHEN** an existing dated path is invalid or its validated `content_digest` and `run_id` differ from the candidate semantic identity
- **THEN** publication fails closed without overwriting the immutable artifact

### Requirement: GitHub-hosted repository-native Feed deployment
The repository SHALL define an active credential-free Feed job on GitHub-hosted `ubuntu-latest` for `workflow_dispatch` and daily cron `20 0 * * *` (08:20 Asia/Shanghai). The job SHALL use the checked-out repository's `feeds/` directory as the Feed output root and the repository as the durable cross-run state authority, require only the built-in repository publication credential with `contents: write`, and use one non-cancelling concurrency group. It SHALL NOT require a self-hosted runner, external persistent filesystem, `FOLLOW_THE_MONEY_OUTPUT_ROOT`, or a custom mandatory default-off enable variable. The nominal schedule SHALL NOT determine `evidence_cutoff_at`; the existing Feed runtime SHALL capture the truthful cutoff after the job actually starts. The job SHALL generate and publish deterministic evidence only and SHALL NOT invoke Host-Agent reasoning, Audit, Event Structuring, or retained market/scoring capabilities.

#### Scenario: Daily hosted invocation
- **WHEN** GitHub schedules the repository Feed workflow from cron `20 0 * * *`
- **THEN** a non-cancelling `ubuntu-latest` job is eligible to establish repository state and run the credential-free Feed without a custom opt-in or external output root

#### Scenario: Manual hosted invocation
- **WHEN** an operator uses `workflow_dispatch`
- **THEN** the invocation follows the same repository-state, lease, recovery, Feed, and publication contracts as the scheduled invocation

#### Scenario: GitHub starts the job late
- **WHEN** the scheduled job begins after nominal 08:20 Asia/Shanghai
- **THEN** the Feed captures its actual runtime cutoff and does not claim the nominal cron instant as its evidence cutoff

#### Scenario: Host Agent consumes a published Feed later
- **WHEN** the workflow successfully publishes a deterministic Evidence Feed
- **THEN** Host-Agent reasoning remains a separate later consumer action and no Agent, Audit, Event Structuring, market-state, watchlist, or scoring invocation is added to the workflow

#### Scenario: Repository write policy is not verified
- **WHEN** Actions `contents: write` or branch policy has not been shown to permit the required non-force fast-forward generated-state commits
- **THEN** the checked-in workflow SHALL NOT be declared operationally complete even if local and static validation passes

### Requirement: Repository bootstrap and durable pre-network lease
After checkout and before normal network-capable execution, deployment preflight SHALL load the authoritative checked-in configuration and resolve enabled verified Provider contracts through the existing resolution boundary. Static resolution failure SHALL make zero Provider requests and SHALL NOT create or mutate normal deployment or rate state. A repository without an authoritative RateRegistry baseline SHALL use the existing RateRegistry first-use lifecycle to establish the registry, persistence marker, and every currently enabled scope, persist a bootstrap recovery boundary, fast-forward push that explicit state, perform zero Provider requests, and block collection until the configured crash-cooldown quiet boundary has elapsed.

For every later network-capable run, repository state SHALL contain a minimal versioned `in_progress` deployment lease and all newly required scope state before the first possible Provider request. The lease SHALL identify the deployment run and its arming/start/recovery bounds, but SHALL NOT contain token balances, cooldown values, last-dispatch values, policy fingerprints, Provider evidence, HTTP history, or Agent state. Provider work SHALL begin only after the allowlisted lease and state have been committed and fast-forward pushed to the remote branch and only within the lease's enforced Feed-start bound. A pre-network commit or push failure, non-fast-forward conflict, or missed Feed-start bound SHALL cause zero Provider requests; the workflow SHALL NOT force push or destructively reset the remote branch.

#### Scenario: Static deployment preflight fails
- **WHEN** authoritative configuration, enabled Provider resolution, deployment compatibility, repository RateRegistry, or lease validation fails before arming
- **THEN** the run performs zero Provider requests, does not enter normal Feed execution, and does not create or mutate normal rate or lease state

#### Scenario: Clean repository bootstrap
- **WHEN** valid resolved Provider contracts exist but the repository has no authoritative repository-backed RateRegistry baseline
- **THEN** the run durably establishes the existing registry, marker, current scope states, and bootstrap recovery boundary in the repository and exits without any Provider request

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

### Requirement: Conservative incomplete-run recovery envelope
An `in_progress` remote lease SHALL mean that the previous ephemeral runner may have sent Provider requests whose exact resulting local RateRegistry state was lost. Its deterministic `recovery_not_before` SHALL conservatively include the latest workflow-permitted Feed start, the existing configured Feed command deadline, and the configured RateRegistry crash cooldown; lease creation time plus crash cooldown alone or an unenforced Provider-time estimate SHALL NOT establish recovery safety. Before that boundary, a later run SHALL make zero Provider requests and SHALL NOT reset or weaken the last committed registry state.

After the boundary, the run MAY reuse the last committed exact RateRegistry state only when static validation of the authoritative currently enabled resolved Provider contracts proves, for every distinct rate scope, that the configured crash cooldown is at least both the scope's complete token-refill period and its minimum dispatch interval. The validation SHALL derive scopes and policies from resolved contracts without hard-coded Provider IDs. Existing RateRegistry refill, eligibility, migration, debit, refund, and reconcile behavior SHALL remain authoritative; recovery SHALL NOT synthesize token balances or introduce a second rate-state model. Missing, corrupt, unsupported, or incompatible registry or lease state SHALL fail closed.

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
- **WHEN** an established repository has a missing, corrupt, unknown-version, or internally inconsistent registry, scope state, or lease
- **THEN** hosted execution fails before Provider network without silently bootstrapping over the established state

### Requirement: Exact allowlisted repository finalization
The workflow SHALL execute safety-state finalization after any controlled Feed outcome and SHALL stage only explicitly resolved generated-state paths. On Feed success, one final non-force fast-forward commit SHALL contain the exact resulting RateRegistry registry and per-scope files, persistence marker when required, terminal success lease, successful run-scoped dated Feed, and `feeds/latest.json`. On controlled Feed failure after Provider work, finalization SHALL commit the exact resulting RateRegistry files and terminal failure lease but SHALL NOT fabricate or promote a successful Feed; the Feed failure SHALL remain the workflow result even when safety-state persistence succeeds.

Ephemeral collection locks, temporary and staging files, `feed-status.json`, local run bundles, debug/failure workspaces, and unrelated repository paths SHALL remain outside the generated-state allowlist. If final commit or push fails, conflicts, or the runner disappears, the remote `in_progress` lease SHALL remain the conservative recovery signal; the workflow SHALL NOT force push, destructively reset, or claim rollback of possibly sent requests.

#### Scenario: Successful Feed finalization
- **WHEN** Feed execution succeeds and exact local state can be fast-forward published
- **THEN** one allowlisted final commit contains terminal success, exact RateRegistry state, the successful dated artifact, and `feeds/latest.json`

#### Scenario: Controlled Feed failure after Provider work
- **WHEN** Feed execution fails after Provider work and the runner remains able to finalize
- **THEN** one allowlisted final commit persists exact RateRegistry state and terminal failure without adding or promoting a successful Feed, and the workflow remains failed

#### Scenario: Final publication fails or conflicts
- **WHEN** the final generated-state commit cannot be fast-forward pushed
- **THEN** the workflow fails and remote `in_progress` remains authoritative for conservative recovery

#### Scenario: Runner disappears before finalization
- **WHEN** the runner terminates after the durable lease and before terminal state reaches the remote repository
- **THEN** the next invocation treats the remote lease as incomplete and follows its recovery boundary

#### Scenario: Unrelated or transient files exist
- **WHEN** finalization finds transient generated files or unrelated worktree changes
- **THEN** it stages none of them and publishes only the explicit generated-state allowlist for that outcome

### Requirement: Generated-state commits avoid recursive full CI
The normal CI workflow SHALL exclude pushes whose changed paths consist only of the accepted generated Feed, RateRegistry, persistence-marker, and deployment-lease allowlist. A push containing any other path, including code, configuration, Provider contracts, schemas, tests, workflows, OpenSpec, or documentation, SHALL remain eligible for the full normal CI suite. This distinction SHALL be path-based and SHALL NOT rely solely on commit-message conventions.

#### Scenario: Generated-state-only push
- **WHEN** a workflow commit changes only accepted generated Feed, rate, marker, and lease paths
- **THEN** that push does not recursively invoke the full normal CI workflow

#### Scenario: Mixed generated and source push
- **WHEN** a push changes an accepted generated-state path and any non-generated path
- **THEN** the full normal CI workflow remains eligible to run

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
