# feed-evidence-pipeline Specification

## Purpose
Define the current credential-free provider-to-Feed collection, deterministic evidence normalization and validation, provenance, bounded timing and rate discipline, and durable publication boundary.

## Requirements

### Requirement: Credential-free verified provider contracts
The Feed SHALL load enabled providers through the common adapter interface from
closed configuration, SHALL require no paid financial-data key
for the shipped core provider set, and SHALL reject an enabled adapter whose
checked-in manifest does not fully declare and verify fetch hosts, redirect hosts,
evidence source-link hosts, source timing, stable identity, pagination, rate policy,
units, freshness, empty-window behavior, and fixture provenance. Every accepted
evidence URL SHALL be HTTPS, credential-free, canonicalized once under its owning
provider's closed host/path/query policy, and validated before identity or
publication.

#### Scenario: Default providers run without credentials
- **WHEN** the minimal Feed entry loads the shipped default configuration without any paid financial-data credential
- **THEN** it can initialize and attempt every enabled verified free provider without reading an API key

#### Scenario: Provider contract is incomplete
- **WHEN** an enabled adapter lacks a current verified contract or emits evidence outside its declared source-link policy
- **THEN** configuration or item validation fails closed before the provider or item can count toward Feed coverage

#### Scenario: Provider is disabled
- **WHEN** configuration marks a provider disabled
- **THEN** collection neither initializes nor contacts that provider

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
