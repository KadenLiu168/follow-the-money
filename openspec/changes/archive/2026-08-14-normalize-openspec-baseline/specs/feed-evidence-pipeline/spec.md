## ADDED Requirements

### Requirement: Credential-free verified provider contracts
The Feed SHALL load enabled providers through the common adapter interface from
closed configuration, SHALL require no model credential or paid financial-data key
for the shipped core provider set, and SHALL reject an enabled adapter whose
checked-in manifest does not fully declare and verify fetch hosts, redirect hosts,
evidence source-link hosts, source timing, stable identity, pagination, rate policy,
units, freshness, empty-window behavior, and fixture provenance. Every accepted
evidence URL SHALL be HTTPS, credential-free, canonicalized once under its owning
provider's closed host/path/query policy, and validated before identity or
publication.

#### Scenario: Default providers run without credentials
- **WHEN** the minimal Feed entry loads the shipped default configuration without any model or paid financial-data credential
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

#### Scenario: Commit crosses the nominal deadline
- **WHEN** a candidate is fully staged and admitted by second 285 but durable commit completes after second 300
- **THEN** commit finishes without cancellation or rollback and reports the overrun only outside the immutable Feed payload

### Requirement: Evidence-only deterministic Feed generation
The live pipeline SHALL perform provider fetching, strict decoding, normalization,
exact and conservative near deduplication, validation, and publication without an
LLM. Feed items SHALL contain evidence and provenance only and SHALL reject
importance, direction, price-in, money-flow interpretation, market regime, asset
impact, ranking, or other analysis fields.

#### Scenario: Feed generation executes
- **WHEN** a valid Feed collection runs
- **THEN** no LLM client, model, prompt, model credential, or Agent-analysis object is loaded or called

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
succeeded, permitted-empty, partially valid, failed, skipped, fetched, accepted, and
rejected outcomes and SHALL publish `degraded` when at least one valid item exists but
an enabled provider or required coverage group is incomplete. Manifest-permitted
empty outcomes MAY count healthy for their group but SHALL NOT satisfy the global
requirement for at least one accepted item. Zero accepted items, zero enabled
providers, or an unrecoverable planning/integrity failure SHALL produce failure and
SHALL NOT replace the last valid latest Feed.

#### Scenario: One provider fails and another succeeds
- **WHEN** one enabled provider fails or times out while another contributes valid evidence
- **THEN** a schema-valid degraded Feed may publish with the exact provider and coverage warning recorded

#### Scenario: Every provider returns no accepted item
- **WHEN** all enabled requests complete but the pipeline accepts zero items
- **THEN** the run fails and does not replace the last valid latest Feed

#### Scenario: A page is partially invalid
- **WHEN** a provider produces valid items before an item or later-page validation failure
- **THEN** valid items and rejection counters are retained and the provider and pipeline are explicitly degraded

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
Before publication, a healthy or degraded candidate SHALL pass Feed schema,
semantic, provenance, identity, and digest validation. Publication SHALL create the
immutable dated `feeds/daily/YYYY-MM-DD/<run_id>.json` artifact before atomically
replacing `feeds/latest.json`, using unpredictable same-parent staging, create-only
writes, file and directory `fsync`, atomic no-replace dated rename, same-directory
latest replacement, and parent-directory `fsync`. It SHALL be idempotent for the
same run and SHALL use the maximum `(evidence_cutoff_at, content_digest)` tuple for
latest ownership. Failure or durability uncertainty SHALL remain explicit and SHALL
NOT fabricate rollback guarantees.

#### Scenario: Valid candidate publishes
- **WHEN** all validation succeeds and durable filesystem primitives are available
- **THEN** the immutable dated artifact becomes durable before latest is replaced and both carry the same validated Feed

#### Scenario: Latest replacement fails
- **WHEN** the dated artifact is durable but latest replacement fails
- **THEN** the previous valid latest remains unchanged and the run reports a retryable publication failure without deleting the dated artifact

#### Scenario: Stale candidate reaches publication
- **WHEN** an older valid externally prepared candidate is submitted after a newer latest Feed
- **THEN** it may retain its immutable dated artifact but cannot replace the newer latest Feed

### Requirement: Minimal internal Feed entry outcomes
Exactly one minimal internal Feed entry SHALL expose configuration, explicit output
root, deterministic clock/window injection, status output, and `--dry-run` for the
Agent/Skill. It SHALL expose no public console script or `brief`, `eval`, or `replay`
subcommand. Healthy or degraded success SHALL exit `0`; typed planning, collection,
runtime, validation, integrity, deadline, rate-state, filesystem, publication, or
durability failure SHALL exit `1`; usage, configuration, invalid explicit input, or
startup-capability rejection SHALL exit `2`. Expected exit categories SHALL derive
from explicit types or typed outcomes, never message text.

#### Scenario: Degraded Feed succeeds
- **WHEN** a degraded candidate remains valid and dry-run or publication completes
- **THEN** the entry exits `0` while machine-readable status and stderr identify the degradation

#### Scenario: Input and execution errors use misleading words
- **WHEN** typed input and execution failures contain arbitrary words associated with the opposite category
- **THEN** their exits remain respectively `2` and `1` based only on type or typed outcome

#### Scenario: Dry run is requested
- **WHEN** `--dry-run` is set
- **THEN** the entry validates and reports the candidate without changing dated or latest Feed artifacts, while any real provider sends still obey lock and durable rate-state contracts
