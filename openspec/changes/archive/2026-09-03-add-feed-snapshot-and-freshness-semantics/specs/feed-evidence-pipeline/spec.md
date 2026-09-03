## ADDED Requirements

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

## MODIFIED Requirements

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
