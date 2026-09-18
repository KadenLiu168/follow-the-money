# feed-evidence-pipeline Specification

## Purpose

Define deterministic five-domain Evidence Feed collection, validation, provenance, degradation, identity, publication, and canonical consumption.

## Requirements

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
- **THEN** the run acquires the runtime-state-root collection lock and durably debits and reconciles rate state exactly as a publishing run, while creating or replacing no the active Feed product product and not advancing the checkpoint

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
- **THEN** publication removes reversible staging files and fails typed `pre_commit_deadline_exceeded` before replacing the active Feed product

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

Every Feed item SHALL retain Provider identity, source name, tier, kind, canonical URL, supplied publication/update time, `source.knowledge_available_at`, and the retained payload's source-semantic effective/reference time and selection basis. Provider `retrieved_at` and Feed `generated_at` SHALL remain execution observations and SHALL NOT be copied into evidence or treated as source time. Newly acquired `news`, `macro_release`, `policy`, and Provider-contract-version-1 `filing` evidence SHALL be selected by knowledge time in the half-open window; SEC contract-version-2 exact `13F-HR` current-state evidence SHALL instead select the latest precise acceptance timestamp strictly before the cutoff for each configured watched CIK and MAY predate `window.start`; current `positioning` and validation-gated carried slices MAY contain earlier source times only under declared cadence contracts. Retrieval time SHALL NOT establish cutoff eligibility or freshness.

#### Scenario: Evidence becomes known after cutoff

- **WHEN** retained evidence has an earlier effective time but source availability at or after the cutoff
- **THEN** it is excluded from the run rather than admitted from effective time alone

#### Scenario: SEC v2 current state predates the window

- **WHEN** the latest eligible exact `13F-HR` for a configured watched CIK was accepted before `window.start` and no later exact filing was accepted before the cutoff
- **THEN** the filing MAY be retained as cutoff-bounded current state with its original acceptance, filing, report-period, and source provenance

#### Scenario: Calendar evidence was announced earlier

- **WHEN** previously announced calendar evidence is encountered during migration or collection
- **THEN** it is excluded from the five-domain candidate rather than retained through a future-horizon exception

#### Scenario: Tier 3 evidence is normalized

- **WHEN** a supported commentary source emits an otherwise valid retained-domain item
- **THEN** it remains explicitly Tier 3 and is not promoted

#### Scenario: Unchanged evidence is checked again

- **WHEN** a complete Provider check allows a prior slice to be carried
- **THEN** current retrieval time records the check while carried evidence retains original source-semantic times

### Requirement: Provider availability is explicit and evidence-based

The Feed SHALL classify Provider availability independently from pipeline status using the closed states `success`, `blocked`, `failed`, and `disabled`. A concrete upstream HTTP 401 or HTTP 403 response SHALL classify the affected Provider as `blocked`; no timeout, transport error, parser error, schema error, unexpected status, missing outcome, or other unconfirmed failure SHALL be inferred to be `blocked`. `degraded` SHALL remain reserved for future Provider partial-data availability and SHALL NOT be produced as a Provider availability state by this Change. A disabled Provider SHALL remain outside the actual run plan and SHALL NOT create a synthetic Provider outcome or completeness obligation.

Every serialized planned-Provider outcome in the new production schema major SHALL expose its Provider identity, availability, bounded reason or null, and affected configured coverage groups in deterministic order. Availability SHALL agree with the underlying terminal evidence: completed healthy or contract-permitted-empty work is `success`; confirmed access denial is `blocked`; all other incomplete or unexpected work is `failed`. A confirmed access denial after accepted evidence or incomplete sub-request, role, or page work SHALL remain partial and non-exempt rather than making partial-data publication acceptable.

#### Scenario: HTTP 403 is blocked

- **WHEN** an enabled planned Provider returns a concrete HTTP 403 response before any evidence is accepted
- **THEN** its availability is `blocked`, its bounded reason identifies HTTP 403, and no Provider-specific exception is required

#### Scenario: HTTP 401 is blocked

- **WHEN** an enabled planned Provider returns a concrete HTTP 401 response before any evidence is accepted
- **THEN** its availability is `blocked` and its bounded reason identifies HTTP 401

#### Scenario: Timeout remains failed

- **WHEN** Provider work ends in a timeout without a concrete HTTP 401 or HTTP 403 response
- **THEN** its availability is `failed` and it is ineligible for blocked exemption

#### Scenario: Parser error remains failed

- **WHEN** a Provider response cannot be parsed or normalized under its verified contract
- **THEN** its availability is `failed` and it is ineligible for blocked exemption

#### Scenario: Access denial follows accepted evidence

- **WHEN** a Provider accepts evidence from one sub-request, role, or page and later receives HTTP 401 or HTTP 403 before completing its planned work
- **THEN** diagnostics preserve the access-denial reason but the Provider remains partial, non-exempt, and pipeline-failing

#### Scenario: Disabled Provider is not synthesized

- **WHEN** authoritative registry policy disables a Provider before run planning
- **THEN** its availability is `disabled` in planning semantics but no Provider outcome, coverage obligation, or synthetic warning is emitted

### Requirement: Explicit degradation and coverage outcomes

One Provider failure SHALL NOT stop collection already planned for other Providers. The Feed SHALL record attempted, succeeded, empty, partially valid, failed, skipped, fetched, accepted, and rejected outcomes together with explicit availability diagnostics. Provider membership for completeness assessment SHALL derive only from the actual resolved run plan, and the resolved Provider contract SHALL be the sole authority for `empty_valid_for_window`; disabled Providers and unverified mappings excluded from that plan SHALL create no completeness obligation.

Every planned Provider SHALL have exactly one unambiguous terminal outcome matching its planned Provider identity. A planned Provider SHALL be complete only when its outcome is `healthy`, or when its outcome is `empty` and its resolved `empty_valid_for_window` contract is true. A `failed`, `partial`, or `skipped` outcome, a non-permitted `empty` outcome, or a missing, duplicate, ambiguous, or identity-mismatched terminal outcome SHALL be incomplete. Accepted and fetched item counts SHALL NOT determine Provider completeness. A Provider SHALL be blocked-exempt only when a concrete HTTP 401 or HTTP 403 establishes `availability = blocked`, no evidence was accepted, and no partial sub-request, role, or page result exists.

Mandatory coverage SHALL count only complete planned Providers that belong to the configured group. A contract-permitted empty Provider SHALL count toward the configured minimum without contributing an evidence item; an incomplete Provider SHALL not count. For each non-optional group, the effective minimum SHALL equal `max(0, configured minimum - blocked-exempt planned members in that group)`. This exemption SHALL NOT alter configured membership or minimum values, and every exempt member and affected group SHALL remain visible in deterministic diagnostics. A non-exempt incomplete planned Provider or a group below its effective minimum SHALL produce `pipeline.status = failure` regardless of evidence returned by other Providers. A Provider SHALL be `partial` when it retains accepted evidence but also has rejected items or incomplete later sub-request, role, or page work; retained valid evidence and outcome counters SHALL remain available for diagnostics but SHALL NOT make the failed run publishable.

The total accepted evidence count and final `items` length SHALL NOT independently determine pipeline health. When every planned Provider is complete or blocked-exempt, every mandatory group meets its effective minimum, and all existing non-source hard-failure boundaries succeed, the Feed SHALL be `degraded` if at least one Provider is blocked-exempt and otherwise SHALL remain eligible for the existing healthy or otherwise accepted non-source status even when `items` is empty. Unknown or non-exempt source incompleteness SHALL NOT produce `degraded`. Provider-specific and coverage-group diagnostics SHALL identify every blocked exemption or source-completeness cause used to determine pipeline status.

#### Scenario: Blocked Provider is published with warnings

- **WHEN** a planned Provider is blocked-exempt, all other planned Providers are complete, every mandatory group meets its effective minimum, and all non-source hard boundaries pass
- **THEN** the Feed is `degraded`, exits successfully, remains eligible for publication, and identifies the unavailable Provider and affected coverage groups

#### Scenario: Every member of a group is blocked

- **WHEN** every planned member of a mandatory coverage group is blocked-exempt and no other hard failure exists
- **THEN** that group's effective minimum is zero, the Feed is `degraded`, and diagnostics truthfully report the complete unavailable coverage

#### Scenario: One provider fails and another succeeds

- **WHEN** one planned Provider fails or times out without blocked exemption while another contributes valid evidence
- **THEN** the Feed run fails, exits non-zero, retains both Provider outcomes for diagnostics, and does not replace the active bundle

#### Scenario: Mandatory group is deficient with accepted evidence

- **WHEN** the pipeline accepts at least one valid item but fewer complete planned Provider outcomes contribute than a non-optional coverage group's effective minimum
- **THEN** the Feed run fails, exits non-zero, does not publish, and identifies the deficient coverage group

#### Scenario: Permitted empty contributes to coverage

- **WHEN** a Provider returns no accepted item and its `empty_valid_for_window` contract is true
- **THEN** its `empty` outcome contributes to coverage without contributing an accepted evidence item

#### Scenario: Non-permitted empty does not contribute to coverage

- **WHEN** a planned Provider reaches `empty` and its `empty_valid_for_window` contract is false
- **THEN** the Provider is incomplete, contributes no coverage, and makes the Feed run fail regardless of evidence from other Providers

#### Scenario: Every provider returns no accepted item

- **WHEN** every planned Provider reaches `healthy` or contract-permitted `empty`, mandatory coverage is satisfied, all other hard-failure boundaries succeed, and the final Feed has `items: []`
- **THEN** zero accepted evidence does not fail the run and the empty Feed remains eligible for normal successful publication

#### Scenario: An item is partially invalid

- **WHEN** a Provider produces accepted items and rejects one or more other normalized items
- **THEN** accepted items and rejection counters are retained, the Provider is partial, and source incompleteness makes the Feed run fail rather than degrade

#### Scenario: Later provider work fails after valid evidence

- **WHEN** a Provider retains accepted evidence from one sub-request, role, or page and later work fails or is incomplete
- **THEN** the retained evidence remains, the Provider is partial rather than healthy or wholly failed, and the Feed run fails without publication

#### Scenario: Later provider work is access denied after valid evidence

- **WHEN** a Provider retains accepted evidence from one sub-request, role, or page and later work receives HTTP 401 or HTTP 403
- **THEN** the retained evidence and access-denial diagnostics remain, the Provider is partial and non-exempt, and the Feed run fails without publication

#### Scenario: Planned Provider is skipped

- **WHEN** a Provider exists in the actual run plan but its terminal outcome is `skipped`
- **THEN** the Provider is incomplete and the Feed run fails

#### Scenario: Planned outcome is missing or ambiguous

- **WHEN** a planned Provider has no valid terminal outcome, more than one competing outcome, or an outcome whose identity does not match the planned Provider
- **THEN** completeness assessment fails closed instead of inferring success from counters, other outcomes, or evidence items

#### Scenario: Work is outside the actual plan

- **WHEN** a Provider is disabled or its verified contract is unavailable and therefore excluded by authoritative resolved production planning
- **THEN** no synthetic skipped outcome or completeness requirement is created for that unplanned work

#### Scenario: Evidence quantity does not determine coverage

- **WHEN** a planned Provider is complete with zero accepted evidence
- **THEN** it remains eligible to satisfy configured mandatory coverage according to its terminal state and resolved empty-window contract

#### Scenario: Partial provider cannot satisfy full coverage

- **WHEN** a partial Provider belongs to a mandatory coverage group
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

For weekly and scheduled cadence, evaluation SHALL compare `evidence_cutoff_at` with the latest authoritative payload-specific observation/effective time in the Provider slice and the declared validity window. For event-driven cadence, a complete current check SHALL keep an unchanged carried slice valid without rewriting its source time. Invalid, missing, future, or ambiguous time authority SHALL fail validation rather than select a convenient timestamp. Freshness status SHALL be part of semantic Feed identity, but SHALL NOT independently rewrite Provider completeness or pipeline status.

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

#### Scenario: No prior snapshot exists

- **WHEN** acquisition is complete and contract-permitted empty but no validated prior Provider slice exists
- **THEN** the Provider freshness status is `no_snapshot` and no evidence is invented

### Requirement: Snapshot carry-forward is validation-gated and failure-isolated

The Feed MAY carry a Provider slice only after complete current acquisition establishes that every accepted current item has an exact canonical semantic match under the same identity in the prior slice and the current active bundle has passed full schema, integrity, semantic identity, provenance, pipeline-consumability, and item validation. Carry-forward SHALL reuse the prior Provider items byte-for-byte in semantic form, including stable IDs, payloads, original source publication/update and knowledge times, provenance, and source lineage; it SHALL preserve the originating embedded Provider-contract hash and SHALL NOT merge successive slices into unbounded history. A current slice containing a new identity or changed canonical semantic content under an existing identity SHALL replace, rather than merge with, the prior slice.

Failed, partial, blocked, skipped, missing, duplicate, ambiguous, identity-mismatched, or non-permitted-empty current acquisition SHALL set freshness to `not_evaluated` and SHALL NOT consult retained evidence as a substitute. A blocked-exempt acquisition MAY produce a degraded publishable Feed without that Provider's prior slice; every other listed condition SHALL retain source-incomplete pipeline failure and no-publication behavior. Absence or invalidity of the active bundle SHALL disable carry-forward without weakening current Provider outcome, availability, or coverage rules.

#### Scenario: Valid prior slice is carried

- **WHEN** current Provider acquisition is complete with no new observation and the active bundle plus that Provider slice validate fully
- **THEN** the new candidate carries exactly the prior semantic items, records the prior `run_id`, and preserves their originating Provider-contract hash

#### Scenario: Prior bundle is invalid

- **WHEN** the active manifest, inventory, artifact, semantic identity, pipeline consumability, or prior Provider slice fails validation
- **THEN** no prior item is carried and current acquisition is evaluated without fallback

#### Scenario: Current acquisition fails with a previous snapshot

- **WHEN** current Provider acquisition fails without blocked exemption while a prior valid Provider slice exists
- **THEN** the Provider remains failed with freshness `not_evaluated`, the pipeline remains source-incomplete, and the prior slice cannot convert the run into success or publication

#### Scenario: Current acquisition is blocked with a previous snapshot

- **WHEN** current Provider acquisition is blocked-exempt while a prior valid Provider slice exists
- **THEN** freshness is `not_evaluated`, no prior item is carried for that Provider, and the degraded Feed reports the current coverage unavailability

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

Exactly one minimal internal Feed producer entry SHALL preserve existing configuration, explicit product/runtime roots, deterministic clock/window injection, deadline, status, `--dry-run`, source-completeness, Provider-availability diagnostics, and typed exit behavior. A successful publication status SHALL expose `feed-manifest.json` as the product entry path and matching `run_id` and cutoff. Dry-run SHALL build and validate the same in-memory manifest and domain artifacts without writing bundle products or advancing the checkpoint. Existing Provider work, rate-state, lock, and exit-code semantics SHALL remain unchanged. This producer entry SHALL NOT be the normal Skill consumption entry.

For an otherwise publishable healthy or degraded candidate, serialized Feed size SHALL equal the byte length of its canonical manifest plus the byte lengths of every canonical artifact in the manifest's complete fixed inventory. The producer SHALL require that total to be less than or equal to the configured `max_serialized_feed_bytes` before reporting dry-run success or attempting publication. An oversized candidate SHALL fail closed through the existing typed producer-failure boundary without truncation, publication, active-bundle replacement, or checkpoint advancement. A source-completeness `pipeline.status = failure` SHALL retain its existing authoritative failure and diagnostics rather than being replaced by this publishable-candidate size check.

#### Scenario: Successful publication is reported

- **WHEN** a healthy or accepted degraded bundle is within the configured serialized Feed limit and is durably activated
- **THEN** the producer command exits `0` and status names `feed-manifest.json` with matching identity and cutoff

#### Scenario: Dry run succeeds

- **WHEN** dry-run produces a valid healthy or degraded bundle candidate within the configured serialized Feed limit
- **THEN** the producer command exits `0`, reports the candidate, creates or replaces no bundle product, and does not advance the checkpoint

#### Scenario: Publishable candidate exceeds the serialized Feed limit

- **WHEN** the canonical manifest bytes plus all canonical artifact bytes for a healthy or degraded candidate exceed `max_serialized_feed_bytes`
- **THEN** the producer reports a typed failure, exits `1`, publishes no candidate bytes, leaves the active bundle unchanged, and does not advance the checkpoint

#### Scenario: Candidate exactly meets the serialized Feed limit

- **WHEN** the canonical manifest bytes plus all canonical artifact bytes equal `max_serialized_feed_bytes`
- **THEN** the size boundary admits the otherwise valid healthy or degraded candidate

#### Scenario: Blocked degradation is reported

- **WHEN** blocked exemption is the only source-acquisition issue and the resulting bundle is within the configured serialized Feed limit
- **THEN** the producer command exits `0` with `degraded` status and deterministic diagnostics naming each blocked Provider, reason, and affected coverage group

#### Scenario: Source completeness fails

- **WHEN** planned source work has non-exempt incompleteness
- **THEN** the producer command preserves deterministic Provider diagnostics, exits `1`, and does not admit a bundle to publication or replace that failure with the publishable-candidate size check

### Requirement: Canonical published Feed is consumed directly from the canonical main branch

Normal Skill Feed consumption SHALL retrieve `feeds/feed-manifest.json` directly from branch `main` of the public repository `KadenLiu168/follow-the-money` through `raw.githubusercontent.com`, then SHALL retrieve every Feed artifact from the same canonical repository, branch, and `feeds/` root. It SHALL perform no GitHub REST API request, SHALL NOT resolve or require a Git commit SHA, and SHALL require no GitHub token or Provider credential.

The validated manifest SHALL remain the only authoritative bundle entry point. The consumer SHALL retrieve exactly the artifact paths declared by its validated ordered inventory and SHALL NOT infer filenames, maintain another domain-to-path registry, enumerate the remote `feeds/` directory, use Git history as a Feed query API, or substitute a different repository, branch, or product root. Integrity and semantic validation SHALL remain authoritative across the mutable-branch read window; if branch movement or any other remote condition yields an unavailable, mixed-generation, inconsistent, or otherwise invalid bundle, consumption SHALL fail closed without retrying against another source or exposing evidence.

#### Scenario: Published Feed is retrieved without GitHub API discovery

- **WHEN** normal Skill consumption begins
- **THEN** its first remote request retrieves `feeds/feed-manifest.json` from the canonical repository's `main` branch on `raw.githubusercontent.com`, and the invocation makes zero requests to `api.github.com`

#### Scenario: Manifest declares the artifact inventory

- **WHEN** the canonical-main manifest is accepted for retrieval
- **THEN** only its exact validated inventory paths are requested under the same canonical `main/feeds/` root and no remote directory enumeration or independently derived artifact path is used

#### Scenario: Main advances during one invocation

- **WHEN** repository `main` advances between manifest and artifact retrieval and the returned files no longer form the complete manifest-declared bundle
- **THEN** size, digest, schema, generation, or semantic identity validation rejects the invocation and no partial logical Feed is exposed

#### Scenario: Canonical raw retrieval fails

- **WHEN** the canonical-main manifest or any declared artifact is rate-limited, unavailable, redirected, times out, returns an HTTP error, or otherwise cannot be retrieved under the existing bounded transport contract
- **THEN** consumption fails closed with a precise retrieval failure and does not query the GitHub REST API or another source

### Requirement: Feed bundle consumption rejects invalid or failed products

The consumer health boundary SHALL first validate canonical manifest bytes and the complete ordered safe inventory before using it for local or remote artifact discovery. It SHALL then validate every required artifact and its integrity, reconstruct the logical Feed, and apply the existing structural, identity, Provider freshness, pipeline, warning, and provenance semantics through the same semantic authority used for repository-local bundles. It SHALL accept healthy bundles, accept degraded bundles while preserving exact warnings and Provider availability metadata, and reject `pipeline.status = failure`. A consumer needing one domain MAY parse only that domain's evidence after validating hashes and required existence for the complete inventory.

Remote consumption SHALL NOT reinterpret retrieval time or invocation time as evidence freshness, source publication time, or Provider availability. It SHALL NOT add a consumer-level maximum Feed age, contact Providers to verify a degraded outcome, carry forward evidence, substitute another source, or add remote transport metadata to the logical Feed schema or identity.

#### Scenario: Healthy bundle is consumed

- **WHEN** a complete valid local or canonical-main remote bundle is healthy and satisfies the existing embedded Feed semantics
- **THEN** the consumer accepts it and can select evidence by manifest domain inventory

#### Scenario: Degraded bundle is consumed

- **WHEN** a complete valid local or canonical-main remote bundle is degraded and satisfies the existing embedded Feed semantics
- **THEN** the consumer accepts it and preserves manifest pipeline warnings and Provider availability metadata without contacting a Provider

#### Scenario: Structurally valid failure bundle is presented

- **WHEN** bundle files pass structure and identity checks but pipeline status is `failure`
- **THEN** the consumer rejects it as non-consumable

#### Scenario: Retrieval occurs after publication

- **WHEN** invocation time or retrieval time is later than the Feed's source-semantic timestamps
- **THEN** those transport times do not replace or refresh `evidence_cutoff_at`, collection timestamps, Provider freshness, source publication time, or evidence identity

### Requirement: Remote artifact size validation respects HTTP content encoding

The canonical-main Feed consumer SHALL interpret each manifest artifact `size_bytes` as the exact length of the transfer-decoded canonical artifact bytes presented to bundle validation. It SHALL NOT reject an otherwise valid artifact solely because an HTTP content-encoded representation has a wire `Content-Length` greater than `size_bytes`. The consumer SHALL retain bounded transfer decoding and SHALL reject decoded bytes that exceed `size_bytes`, decoded bytes whose final length differs from `size_bytes`, or bytes whose digest or bundle semantics do not match the validated manifest.

#### Scenario: Encoded representation is larger than the canonical artifact

- **WHEN** a required artifact is returned with HTTP content encoding, its encoded `Content-Length` exceeds the manifest `size_bytes`, and its decoded canonical bytes exactly match the declared size, digest, and bundle semantics
- **THEN** the consumer accepts that artifact as part of the complete valid bundle

#### Scenario: Decoded response exceeds the manifest size

- **WHEN** transfer decoding yields more bytes than the artifact's manifest `size_bytes`
- **THEN** retrieval stops at the bounded decoded-size check and the consumer exposes no logical Feed

#### Scenario: Decoded response has an invalid final size or digest

- **WHEN** transfer decoding completes but the decoded artifact length or digest differs from the validated manifest entry
- **THEN** the complete bundle is rejected without fallback or partial evidence output

#### Scenario: Identity-encoded response declares an oversized body

- **WHEN** a response without content encoding declares a `Content-Length` greater than the applicable retrieval limit
- **THEN** the consumer rejects it before accepting the response body

### Requirement: Normal Skill consumption never becomes Feed production

Normal Skill invocation SHALL use one minimal internal remote Feed consumer entry and SHALL NOT invoke Provider adapters, the local Feed producer, hosted deployment machinery, rate state, checkpoint, lease, or collection locks. The existing minimal local Feed producer SHALL remain available only for GitHub Actions, development, tests, Provider diagnostics, and explicit operator execution; its production, dry-run, state, diagnostics, and exit behavior SHALL remain unchanged.

Remote retrieval, transport, validation, or consumability failure SHALL stop the invocation. It SHALL NOT fall back to local Provider collection, repository-local `feeds/` or the active Feed product, another repository, another branch or commit, a persistent cache, or any partially retrieved evidence. Remote consumption SHALL use temporary isolated storage only and SHALL leave repository `feeds/`, `.feed-state/`, and other persistent Feed state unchanged.

#### Scenario: Remote retrieval fails

- **WHEN** any required remote operation exhausts its permitted bounded attempt or returns an unusable response
- **THEN** the invocation exposes a typed precise failure, produces no logical Feed, invokes no Provider or local producer, and mutates no persistent Feed product or runtime state

#### Scenario: Remote bundle validation fails

- **WHEN** the manifest or any required artifact is missing, unsafe, non-canonical, unsupported, schema-invalid, size- or digest-mismatched, mixed-generation, identity-invalid, or otherwise non-consumable
- **THEN** the whole invocation fails closed without local fallback, stale local substitution, or partial evidence output

#### Scenario: Local producer is explicitly operated

- **WHEN** GitHub Actions, a developer, a test, a diagnostic, or an operator explicitly invokes the existing local Feed producer
- **THEN** the producer retains its existing behavior independently of the normal Skill remote consumer entry

#### Scenario: Remote consumption completes

- **WHEN** a complete canonical-main healthy or degraded bundle is retrieved and accepted
- **THEN** temporary files are removed after the validated logical Feed is emitted and repository Feed products and runtime state remain unchanged

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

The repository SHALL define an active credential-free Feed job on GitHub-hosted `ubuntu-latest` for `workflow_dispatch` and daily cron `20 0 * * *` (08:20 Asia/Shanghai). The job SHALL use the checked-out repository's explicit `feeds/` Feed product root and `.feed-state/` runtime-state root, with the repository as durable cross-run authority, require only the built-in repository publication credential with `contents: write`, and use one non-cancelling concurrency group. It SHALL NOT require a self-hosted runner, external persistent filesystem, `FOLLOW_THE_MONEY_OUTPUT_ROOT`, or a custom mandatory default-off enable variable. The nominal schedule SHALL NOT determine `evidence_cutoff_at`; the existing Feed runtime SHALL capture the truthful cutoff after the job actually starts. Prepare, migration or arming publication, collection, finalization, diagnostics, and original-failure restoration SHALL remain explicitly ordered; bounded previous-bundle migration SHALL end without collection. The job SHALL generate and publish deterministic evidence only and SHALL NOT invoke Host-Agent reasoning, Audit, Event Structuring, or retained market/scoring capabilities.

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

An `in_progress` remote lease in the established runtime-state root SHALL mean that the previous ephemeral runner may have sent Provider requests whose exact resulting local RateRegistry state was lost. Its deterministic `recovery_not_before` SHALL conservatively include the latest workflow-permitted Feed start, the existing configured Feed command deadline, and the configured RateRegistry crash cooldown; lease creation time plus crash cooldown alone or an unenforced Provider-time estimate SHALL NOT establish recovery safety. Migration SHALL preserve the original lease state and bounds and SHALL NOT arm Provider work. Before that boundary, a later run SHALL make zero Provider requests and SHALL NOT reset or weaken the last committed registry state.

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

After any controlled Feed outcome, deployment SHALL stage only explicitly resolved generated-state paths. On success, finalization SHALL validate status, checkpoint, active manifest, and every inventoried artifact; require their `run_id` and cutoff to match; and make one non-force fast-forward commit containing exact runtime safety state, terminal success lease, matching checkpoint, `feed-manifest.json`, exactly its closed artifact inventory, deletion of the superseded active generation, and deletion of migration-only the active Feed product when applicable. On controlled failure after Provider work, finalization SHALL preserve existing exact RateRegistry and terminal-failure behavior without staging a changed checkpoint, manifest, domain artifact, or candidate/superseded product. Transient stages, orphan candidates, status files, locks, history directories, and unrelated paths SHALL remain outside the allowlist.

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

Normal CI SHALL exclude pushes whose changed paths consist only of accepted `.feed-state/` durable state and the closed Feed product set: `feeds/feed-manifest.json`, manifest-inventoried generation-qualified domain artifacts, deletion of the immediately superseded generation, and migration deletion of the active Feed product. A push containing code, configuration, Provider contracts, schemas, tests, workflows, OpenSpec, documentation, unreferenced Feed artifacts, history directories, unexpected runtime/transient state, or any other path SHALL remain eligible for full CI. This decision SHALL be path- and manifest-validation-based rather than commit-message-based.

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

The closed versioned checkpoint schema and its `previous_success` cutoff and `run_id` values SHALL remain unchanged. After accepted durable manifest ownership, the run SHALL atomically advance the checkpoint to the active bundle identity before releasing the runtime lock. It SHALL not advance for dry-run, source incompleteness, validation failure, publication failure, durability uncertainty, stale ownership, or any outcome without accepted active-manifest ownership. Deployment SHALL validate successful checkpoint identity against the active manifest rather than the active Feed product; checkpoint persistence failure after manifest activation SHALL fail without claiming rollback and MAY leave continuity lagging but never leading the active bundle.

#### Scenario: Accepted bundle advances continuity

- **WHEN** a healthy or accepted degraded bundle durably establishes active manifest ownership
- **THEN** checkpoint `previous_success` advances to exactly its cutoff and `run_id`

#### Scenario: Bundle publication is failed or uncertain

- **WHEN** active ownership is not accepted or manifest durability is uncertain
- **THEN** the checkpoint does not advance

#### Scenario: Checkpoint persistence fails after activation

- **WHEN** manifest activation succeeds but checkpoint persistence fails
- **THEN** execution fails, preserves the active bundle, and leaves continuity conservatively lagging

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

Shared HTML index extraction SHALL retain the existing supported separated and compact Provider date formats and their deterministic candidate-source precedence. Within that precedence it SHALL select the first date-valid candidate, ignore invalid or unrelated date-like candidates, and continue evaluating later candidates for the same link when available. A link SHALL be promoted to a candidate evidence entry only when it has non-empty link text, a non-empty target, and a supported date-valid value. Ignored links SHALL NOT bypass existing URL validation, provenance, acquisition-window, or evidence-normalization rules.

#### Scenario: Production-shaped Provider link contains a valid date

- **WHEN** an HTML index link contains a supported date-valid value in an existing Provider URL or link-text format
- **THEN** extraction returns the same normalized UTC date and resolved candidate URL under the existing deterministic precedence

#### Scenario: Navigation link contains an invalid date-like token

- **WHEN** an unrelated navigation link contains a syntactically date-like token with an invalid month or day
- **THEN** extraction ignores that token without emitting an entry or allowing an uncategorized date-construction exception to escape

#### Scenario: Invalid candidate precedes a valid candidate

- **WHEN** a link contains multiple supported date-like candidates and an earlier candidate is date-invalid while a later candidate is date-valid
- **THEN** extraction deterministically selects the first date-valid candidate under the existing candidate-source precedence

#### Scenario: Link has no valid supported date

- **WHEN** a malformed or unrelated link contains no date-valid candidate in a supported date format
- **THEN** the link is ignored rather than promoted as evidence

#### Scenario: Genuine Provider acquisition fails

- **WHEN** Provider acquisition fails because of upstream blocking, throttling, timeout, network failure, undecodable content, or another existing typed failure condition
- **THEN** the Provider remains incomplete under existing retry and Feed failure semantics and prior evidence does not convert the run into success

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

### Requirement: Every real Provider HTTP send is independently managed

Every real outbound Provider HTTP send SHALL independently pass cancellation and pre-commit deadline admission, durable rate eligibility and debit, global concurrency admission, target-host concurrency admission, owning Provider host and identity policy, one upstream send, and exactly one controlled rate-state reconciliation. Automatic redirect following SHALL be disabled below this boundary; each permitted redirect hop and each sequential pagination request SHALL re-enter the same boundary. Provider-level attempts, retries, normalization, item validation, and outcomes SHALL remain outside this send-level boundary and SHALL NOT perform a second debit or reconciliation for an already managed send.

#### Scenario: One acquisition uses multiple requests

- **WHEN** one Provider acquisition performs two successful HTTP sends
- **THEN** each send receives its own durable debit, concurrency admission, upstream send, and reconciliation

#### Scenario: Redirect produces another upstream send

- **WHEN** a permitted response redirects the request to another permitted URL
- **THEN** the redirect hop is admitted as a separate managed send using the redirected target host rather than being followed invisibly by the underlying client

#### Scenario: Redirect is unsafe or unbounded

- **WHEN** a redirect target violates the owning Provider redirect policy, repeats a visited URL, exceeds the bounded redirect count, or cannot fit before the deadline
- **THEN** no request is sent to that target and the acquisition fails through the typed Provider boundary

#### Scenario: Deadline expires between sends

- **WHEN** a first send completes but the next required send or wait cannot be admitted before the pre-commit deadline
- **THEN** the next send does not occur, the Provider remains incomplete, and prior evidence cannot convert the run into success

#### Scenario: Transport fails after dispatch

- **WHEN** the underlying transport raises after a durable pre-send debit and dispatch may have occurred
- **THEN** the managed boundary reconciles rather than refunds the debit exactly once and exposes a typed retry classification to Provider-level orchestration

#### Scenario: Retry-After is returned

- **WHEN** an upstream response carries a valid `Retry-After` value
- **THEN** that send reconciles the owning durable rate scope with the declared delay exactly once and any later attempt must pass normal eligibility again

#### Scenario: Existing single-request Provider runs

- **WHEN** an existing adapter performs one request and otherwise produces the same normalized evidence
- **THEN** its Provider-level retry, validation, outcome, and evidence behavior remains unchanged while its one send is managed at the new boundary

### Requirement: Multi-request failures preserve typed lifecycle and blocked-exemption evidence

The managed transport and bounded fetch helper SHALL preserve typed fetch-error retryability, concrete HTTP status, Retry-After, and actual response-observation metadata. Durable rate-state failures SHALL remain hard execution failures rather than ordinary Provider failures or retries. Each Provider outcome's `retrieved_at` SHALL reflect its last concrete response observation across requests, retries and acquisition units, or null if none occurred; a later no-response failure SHALL NOT advance or erase that observation. Response observations SHALL NOT become source time.

A terminal HTTP 401/403 after a successful terminal resource response in an unresolved acquisition unit or after accepted evidence from another unit SHALL be partial and non-exempt, even when normalization has not produced items. The outcome SHALL serialize existing `state = partial`, `availability = blocked`, the concrete HTTP status/reason, and `freshness.status = not_evaluated`; pipeline status SHALL be failure and publication SHALL be forbidden. Successful resource progress SHALL survive unsuccessful retries of that unit until a complete retry resolves it. Counters SHALL NOT be fabricated to encode progress. A terminal incomplete company unit SHALL NOT be erased by later company success.

A first-resource 401/403 with no successful partial resource, accepted/rejected evidence, or other unresolved incompleteness SHALL retain the existing blocked exemption. Redirect responses alone SHALL be response observations, not successful resource results. Genuine blocked-exempt outcomes SHALL retain no prior evidence and MAY participate in the existing degraded publication path. No new public outcome field is required.

#### Scenario: SEC data acquisition is denied after submissions succeed

- **WHEN** submissions succeeds but a required current or previous complete-submission request returns HTTP 401 or 403 before any filing item is normalized
- **THEN** SEC is partial/blocked, accepted and rejected counters remain truthful, freshness is not_evaluated, and the pipeline fails without publication or prior-slice fallback

#### Scenario: CFTC acquisition is denied after discovery or a page succeeds

- **WHEN** a required CFTC page returns HTTP 401 or 403 after date discovery or an earlier page succeeds
- **THEN** CFTC remains partial, non-exempt and pipeline-failing even if accepted is zero

#### Scenario: Denial occurs before partial evidence exists

- **WHEN** the first resource returns HTTP 401 or 403, possibly after permitted redirects, and no successful resource or other incompleteness exists
- **THEN** the Provider retains the existing failed/blocked exemption with no items, and the Feed may publish degraded if every other required gate passes

#### Scenario: An unsuccessful retry must not erase partial progress

- **WHEN** one attempt obtained a resource before failing and a later attempt for the unresolved unit returns HTTP 403 before obtaining a resource
- **THEN** prior partial-resource progress prevents blocked exemption without inventing item counts

#### Scenario: A complete retry resolves its acquisition unit

- **WHEN** a retry completely obtains and validates the required evidence for a previously failed attempt of the same unit
- **THEN** transient attempt failure does not prevent that unit from succeeding, but an independently terminal failed unit cannot be cleared

#### Scenario: A later request has no response

- **WHEN** one response is observed and a later required request times out or is cancelled before a response
- **THEN** retrieved_at remains the actual earlier observation and the terminal failure keeps its typed non-blocked classification

#### Scenario: Durable reconciliation fails

- **WHEN** the managed send boundary encounters a durable rate reconciliation failure
- **THEN** bounded_fetch preserves the hard rate-state failure, no second reconciliation is attempted by orchestration, and publication fails through the existing execution boundary

### Requirement: Feed v4 supports bounded Provider semantic contract evolution

New production SHALL continue to emit Feed `schema_version = 4`. The checked-in SEC EDGAR manifest SHALL publish Provider `contract_version = 4`, the checked-in CFTC manifest SHALL publish Provider `contract_version = 2`, and the other six required Providers SHALL remain at contract version 1. Manifest resolution and embedded-contract validation SHALL use an explicit Provider-specific supported-version set rather than a global maximum, a manifest hash, or implicit acceptance of arbitrary versions.

A current consumer SHALL retain bounded read compatibility for structurally and semantically valid v4 items carrying SEC Provider contract versions 1, 2, or 3 and CFTC Provider contract version 1. SEC contract version 2 items SHALL retain the complete required 13F semantic structure. SEC contract version 3 items SHALL retain the complete required `form13f` or `form4` subtype structure. SEC contract version 4 items SHALL carry a required closed filing subtype and satisfy the complete `form13f`, `form4`, or `beneficial_ownership` subtype contract. CFTC contract version 2 items SHALL contain the complete required COT semantic structure. Unknown fields, unsupported Provider/version combinations, malformed version declarations, and versioned items missing required semantics SHALL fail closed. New production SHALL NOT emit a legacy SEC v1/v2/v3 or CFTC v1 contract after the corresponding working manifest activation. Each checked-in manifest bump SHALL be atomic with its working semantic adapters, configuration, validation, verified fixtures, request bounds, and compatibility path.

#### Scenario: Existing v4 Provider-v1 bundle is read

- **WHEN** a valid previously published v4 bundle embeds SEC or CFTC Provider contract version 1 and uses the bounded legacy payload shape
- **THEN** the current consumer validates it without requiring newer semantic fields

#### Scenario: Existing SEC v2 bundle is read

- **WHEN** a valid previously published v4 bundle embeds SEC Provider contract version 2 with the complete existing 13F semantic structure
- **THEN** the current consumer validates it without requiring a filing subtype or Form 4 fields

#### Scenario: Existing SEC v3 bundle is read

- **WHEN** a valid previously published v4 bundle embeds SEC Provider contract version 3 with a complete `form13f` or `form4` payload
- **THEN** the current consumer validates it without requiring beneficial-ownership fields or SEC-v4 configuration

#### Scenario: SEC v2 semantics are absent

- **WHEN** a v4 item belongs to an embedded SEC contract version 2 but omits any required 13F semantic structure
- **THEN** Feed validation rejects the bundle

#### Scenario: SEC v3 subtype semantics are absent

- **WHEN** a v4 item belongs to an embedded SEC contract version 3 but omits its filing subtype or the complete semantics required by that subtype
- **THEN** Feed validation rejects the bundle

#### Scenario: SEC v4 subtype semantics are absent

- **WHEN** a v4 item belongs to an embedded SEC contract version 4 but omits its filing subtype or the complete semantics required by that subtype
- **THEN** Feed validation rejects the bundle

#### Scenario: CFTC v2 semantics are absent

- **WHEN** a v4 item belongs to an embedded CFTC contract version 2 but omits any required COT semantic structure
- **THEN** Feed validation rejects the bundle

#### Scenario: Versioned semantic item is complete

- **WHEN** a v4 SEC or CFTC item matches its embedded supported contract version and all required typed semantic and provenance fields
- **THEN** Feed validation accepts the item without requiring a Feed major-version change

#### Scenario: Unknown semantic field is supplied

- **WHEN** a versioned semantic payload contains a field outside its closed schema
- **THEN** Feed validation rejects the item rather than treating the field as untyped metadata

#### Scenario: Unsupported Provider version is embedded

- **WHEN** a bundle or checked-in manifest declares a Provider contract version outside the explicit supported set for that Provider
- **THEN** resolution or consumption fails closed without using the contract hash to select behavior

### Requirement: SEC 13F watched-company configuration is closed and fail-closed

The authoritative configuration SHALL contain a closed `watched_companies` selection
of normalized ten-digit SEC CIKs, each unique, embedded in the canonical Feed
configuration snapshot in deterministic CIK order. The CIK order in the embedded
snapshot SHALL be produced by deterministic runtime ordering of the configured
selection, independent of the checked-in list order. Unknown, duplicate, malformed,
or missing selection fields SHALL fail static resolution before Provider work or
persistent mutation, matching the `watched_form4_issuers` and
`watched_beneficial_ownership_filers` validation. A CIK SHALL be a normalized
ten-digit decimal string. Malformed or duplicate CIKs SHALL NOT be silently
corrected, deduplicated, or skipped at runtime.

#### Scenario: Malformed CIK is rejected

- **WHEN** `watched_companies` contains an entry whose `cik` is not a normalized
  ten-digit decimal string
- **THEN** static configuration resolution fails closed before any SEC Provider
  request and before any rate-registry or persistent state mutation

#### Scenario: Duplicate CIK is rejected

- **WHEN** `watched_companies` contains two entries with the same `cik`
- **THEN** static configuration resolution fails closed before any SEC Provider
  request and before any rate-registry or persistent state mutation

#### Scenario: Shipped watched-CIK set is pinned

- **WHEN** the shipped production configuration is resolved
- **THEN** the resolved watched-company CIK set equals the verified SEC identity
  set documented in `references/provider-source-verification.md`, and any silent
  drift in a shipped CIK fails the exact-set regression

#### Scenario: Runtime ordering is independent of list order

- **WHEN** the checked-in `watched_companies` list is not in CIK order
- **THEN** the embedded Feed configuration snapshot still orders the selection by
  normalized CIK, and acquisition iterates that deterministic order without
  requiring a checked-in ordering enforcement

### Requirement: SEC v2 publishes a complete cutoff-bounded watched-company 13F state

A complete SEC contract-version-2 acquisition SHALL publish exactly one filing item for every configured watched company and no other SEC item. The authoritative configured watched-company selection SHALL be embedded in the Feed configuration snapshot in deterministic CIK order. Every retained SEC item SHALL have valid v2 semantics, a configured CIK and unique company identity. For complete SEC outcomes, validation SHALL require exact configured CIK-set equality before snapshot selection and on the final candidate. Genuine blocked-exempt SEC outcomes SHALL contain zero SEC items with not_evaluated freshness and MAY participate in accepted degraded publication without placeholders. Non-exempt incomplete candidates MAY retain a valid unique subset only as pipeline-failure diagnostics and SHALL NOT publish. An empty configured watched set SHALL yield a complete permitted-empty SEC outcome, no SEC items, no_snapshot freshness and no prior carry-forward.

For each watched CIK, the current filing SHALL be the latest exact `13F-HR` whose precise SEC acceptance timestamp is earlier than `evidence_cutoff_at`. It MAY be earlier than `window.start` because this Provider contract represents current state at the cutoff rather than only filings first observed in the advancing interval. `13F-HR/A` amendments and every other form SHALL be excluded. The previous comparable filing SHALL be the nearest earlier exact `13F-HR` with a different report period. Failure, ambiguity, an unavailable current exact filing, or a missing required readable INFORMATION TABLE for any watched company SHALL make the SEC outcome partial or failed; it SHALL NOT silently omit that company. Absence of a previous comparable filing SHALL NOT make an otherwise valid current item incomplete.

#### Scenario: Only one company files during the current window

- **WHEN** eight watched companies have valid latest filings before the cutoff, only company A has a new filing in the current advancing window, and all eight acquisitions complete
- **THEN** the current SEC slice contains exactly A through H and may replace the prior whole SEC slice without losing B through H

#### Scenario: Current filing predates the window

- **WHEN** a watched company's latest exact `13F-HR` was accepted before `window.start` but before `evidence_cutoff_at`
- **THEN** that filing is retained as the company's cutoff-bounded current state with its original source times

#### Scenario: Filing is accepted at or after cutoff

- **WHEN** an exact `13F-HR` has an earlier report or filing date but its precise acceptance timestamp is at or after `evidence_cutoff_at`
- **THEN** it is ineligible and the latest earlier eligible exact filing is selected

#### Scenario: Amendment is newer than the exact filing

- **WHEN** a `13F-HR/A` is newer than the latest exact `13F-HR`
- **THEN** the amendment is neither selected nor merged in this contract

#### Scenario: One watched company is incomplete

- **WHEN** seven company acquisitions succeed and one current filing is missing, ambiguous, unreadable, or fails acquisition
- **THEN** SEC is partial or failed, required coverage is incomplete, and the seven accepted items cannot make the Feed publishable

#### Scenario: Previous filing is unavailable

- **WHEN** a valid current exact `13F-HR` exists but no earlier exact filing with a different report period exists
- **THEN** the item is publishable with comparison status `unavailable` and reason `no_previous_comparable_filing`

#### Scenario: SEC is genuinely blocked-exempt

- **WHEN** SEC is denied on its first resource without partial-resource evidence and all other publication gates pass
- **THEN** validation permits the degraded candidate with no SEC items and not_evaluated freshness rather than requiring fabricated items for each configured CIK

#### Scenario: A failed diagnostic candidate retains a company subset

- **WHEN** some configured company items are valid but SEC is non-exempt incomplete
- **THEN** validation may retain the valid unique configured subset only with pipeline failure and not_evaluated freshness, never as a publishable complete SEC slice

#### Scenario: Published company identity is inspected

- **WHEN** a SEC v2 item is validated
- **THEN** it exposes the official submissions CIK, name, and tickers while the configuration snapshot remains the authority for watched-company selection

### Requirement: SEC v2 normalizes and compares 13F holdings deterministically

Each SEC v2 item SHALL expose current and, when available, previous filing accession number, report period, precise acceptance time, and official source URL together with a closed typed holdings comparison. Security matching SHALL use only a canonical key composed of normalized CUSIP, normalized nullable put/call, and normalized `SH` or `PRN` amount type. Issuer name and title of class SHALL be display metadata and SHALL NOT determine matching. Optional FIGI SHALL remain optional; conflicting non-empty stable identity metadata under one canonical key SHALL fail closed.

Rows sharing a canonical key within one INFORMATION TABLE SHALL be deterministically aggregated before cross-period comparison by summing reported amount and reported value normalized to USD thousands. Under the verified SEC Form 13F unit transition effective 2023-01-03, supported XML filings made before that date SHALL interpret reported value as USD thousands and filings made on or after that date SHALL interpret reported value as USD and divide exactly by 1000. Selection SHALL use the official filing date, cross-checked between submissions and the complete submission, never report period or value magnitude. No arithmetic step SHALL round or truncate. The closed SEC v2 manifest unit mapping SHALL declare both source regimes and the canonical target; unsupported/missing/extra entries SHALL fail resolution and embedded-contract validation. Current and previous filing evidence SHALL expose their filing dates and closed value-normalization descriptors identifying source unit and conversion formula. Unknown/unsupported formats or contradictory unit/date provenance SHALL fail closed rather than invoke a unit heuristic. Display metadata SHALL be selected by a documented canonical rule independent of input order. Output rows SHALL be unique and ordered solely by canonical security key. Raw numeric tokens and arithmetic SHALL obey the existing bounded canonical-decimal contract; current and previous reported amounts and values SHALL be nonnegative, while matched deltas MAY be signed.

When a previous comparable filing exists, change classification SHALL use reported amount only: a key present on both sides is `increased`, `decreased`, or `unchanged`; a current-only key is `new`; and a previous-only key is `no_longer_reported`. Reported market value SHALL NOT determine that classification. For matched keys, delta fields SHALL be the reproducible current-minus-previous values. For `new` and `no_longer_reported`, the absent side and delta SHALL be null rather than an invented zero. `no_longer_reported` SHALL mean only that the key is absent from the current report.

When no previous comparable filing exists, every current holding SHALL preserve its current values while `previous`, `delta`, and `change_type` are null. Such holdings SHALL NOT be classified as `new`.

#### Scenario: Current value is reported in dollars

- **WHEN** a supported filing made on or after 2023-01-03 reports raw value 1234567 dollars
- **THEN** its reported_value_usd_thousands is the exact canonical string "1234.567" and value_normalization identifies usd and usd_divided_by_1000

#### Scenario: Comparison spans the unit transition

- **WHEN** a pre-transition filing reports raw value 1234 and the comparable post-transition filing reports 1234567
- **THEN** their normalized previous/current values are "1234" and "1234.567" USD thousands with exact delta "0.567", and each filing retains its own date and unit descriptor

#### Scenario: Late filing uses an older report period

- **WHEN** a filing made on 2023-01-03 reports holdings for a period before that date
- **THEN** the dollar source regime applies based on filing date rather than the older report period

#### Scenario: Value-unit authority is missing or conflicting

- **WHEN** official filing dates conflict, the XML format is unsupported, or the declared SEC v2 unit contract is missing or inconsistent
- **THEN** parsing or contract validation fails closed without magnitude-based conversion or invented provenance

#### Scenario: Duplicate rows are reordered

- **WHEN** the same duplicate security rows are supplied in different orders
- **THEN** their aggregate, display selection, comparison rows, and canonical output bytes are identical

#### Scenario: Issuer spelling changes

- **WHEN** current and previous rows have the same canonical security key but different issuer-name spelling
- **THEN** they are matched by the security key and issuer spelling does not create `new` or `no_longer_reported`

#### Scenario: Put and call differ

- **WHEN** two rows share a CUSIP and amount type but one is a put and the other is a call
- **THEN** they remain distinct security keys

#### Scenario: SH and PRN differ

- **WHEN** two rows share a CUSIP and put/call value but use different amount types
- **THEN** they remain distinct security keys

#### Scenario: Amount rises while market value falls

- **WHEN** a matched holding's reported amount rises and reported market value falls
- **THEN** its change type is `increased` and both numeric deltas remain independently reproducible

#### Scenario: Current-only security is compared

- **WHEN** a previous comparable filing exists and a canonical key appears only in the current filing
- **THEN** change type is `new`, previous and delta are null, and no transaction path is asserted

#### Scenario: Previous-only security is compared

- **WHEN** a previous comparable filing exists and a canonical key appears only in the previous filing
- **THEN** change type is `no_longer_reported`, current and delta are null, and no full-sale assertion is made

#### Scenario: Stable identity metadata conflicts

- **WHEN** rows under one canonical security key contain irreconcilable non-empty stable identity metadata
- **THEN** parsing fails closed instead of choosing an identity by row order

### Requirement: CFTC v2 publishes deterministic current and previous Legacy Futures-Only evidence

CFTC contract version 2 SHALL deterministically discover the latest and immediately previous distinct Legacy Futures-Only report dates whose declared conservative publication boundary is earlier than `evidence_cutoff_at`, and SHALL retrieve every row for both selected dates through bounded sequential pagination. Queries SHALL use a fixed bounded page size, total deterministic ordering including contract market code and a final stable tie-breaker, a closed maximum row/page bound, and a termination condition that proves each selected date is complete. Invalid ordering, duplicate or ambiguous current market identity, bound exhaustion, an incomplete page sequence, or a numeric parse failure SHALL fail closed.

Cross-period matching SHALL use normalized CFTC contract market code, not a display market name. The current slice SHALL publish one positioning item for every current-report market and SHALL NOT synthesize items for markets found only in the previous report. A display-name change SHALL NOT break comparison. A current market absent from the complete previous report SHALL publish explicit unavailable comparison rather than invented previous or delta values.

Each item SHALL retain legacy `instrument_id`, `as_of`, and `position`, with `position` remaining the compatibility alias for current non-commercial long contracts. It SHALL additionally expose typed market identity; current and, when available, previous non-commercial long, non-commercial short, non-commercial spreading, open interest, and net non-commercial metrics; typed deltas; comparison status and previous report date; and a derivation descriptor identifying net non-commercial as `noncommercial_long_minus_short`. All persisted numeric values SHALL be canonical decimal strings in contracts. `net_noncommercial` SHALL equal long minus short, each metric delta SHALL equal current minus previous, and net change SHALL be reproducible from both the typed net values and the component deltas.

#### Scenario: Input row order changes

- **WHEN** identical complete current and previous report rows arrive in different orders or page completion schedules
- **THEN** selected dates, matched markets, semantic output, and canonical bytes are identical

#### Scenario: A post-cutoff report is visible at retrieval

- **WHEN** the upstream dataset contains a report whose conservative publication boundary is at or after the fixed cutoff
- **THEN** that report is excluded even if it is visible when the HTTP request occurs

#### Scenario: Display name changes across weeks

- **WHEN** one market has the same contract market code but different display names in the selected reports
- **THEN** the rows are compared as one market

#### Scenario: Current metrics are compared

- **WHEN** a market exists in both complete reports
- **THEN** long, short, spreading, open-interest, net, and all deltas are typed canonical contract values reproducible from the two source rows

#### Scenario: Previous market is unavailable

- **WHEN** a current market code does not occur in the complete previous report
- **THEN** comparison is explicitly unavailable and previous and delta metrics are null

#### Scenario: Market exists only in previous report

- **WHEN** a market code occurs only in the previous report
- **THEN** no current positioning item is synthesized for that code

#### Scenario: Directional interpretation is supplied

- **WHEN** a CFTC item adds bullish, bearish, crowded, risk-on, risk-off, signal, score, importance, prediction, or recommendation semantics
- **THEN** Feed validation rejects the item

### Requirement: Semantic current-change evidence preserves Feed identity and snapshot contracts

All SEC 13F and CFTC COT typed semantic fields, including current values, previous values, report periods or dates, comparison status and reason, change classification, derivation descriptors, and deterministic deltas, SHALL participate in the existing canonical item bytes and logical Feed semantic projection. Changing any such fact SHALL change `content_digest` and cutoff-derived `run_id`; input row order, company acquisition completion order, pagination partitioning, and Provider completion order SHALL NOT change them.

Snapshot selection SHALL retain whole-Provider-slice replacement. For current SEC or CFTC contract version 2, carry-forward SHALL additionally require equality of current/prior item identity sets as well as canonical equality of each item; subset matching alone SHALL NOT permit carry-forward. Both versions represent complete current-state slices, including same-date source corrections. Removing a configured CIK SHALL select the complete current SEC slice without the removed member. An empty configured set SHALL select an empty slice with no_snapshot freshness and null carry provenance. All Provider-v1 and the other six Providers' legacy event-list and empty-check behavior SHALL remain unchanged. Dispatch SHALL use the resolved Provider contract version, not a hash or a second configuration authority.

A complete equal-set identical SEC or CFTC v2 slice MAY carry prior bytes as valid_unchanged; any added/removed identity or changed canonical content SHALL cause whole-current-slice replacement. Partial or failed acquisition SHALL remain not_evaluated without prior-slice fallback. Genuine blocked exemption MAY still publish degraded without that Provider's evidence, while all non-exempt incomplete work SHALL remain pipeline-failing. No per-company SEC merge, cross-run CFTC history merge, or unbounded evidence history SHALL be introduced.

A Host Agent inspecting only one current validated SEC v2 or CFTC v2 item SHALL be able to identify current state, previous comparable evidence when available, deterministic change or explicit unavailability, and official provenance or reproducible derivation support without Provider network access, historical Feed access, `raw_metadata` parsing, or its own cross-period arithmetic.

#### Scenario: A semantic fact changes

- **WHEN** a 13F amount, 13F change type, 13F report period, CFTC source metric, CFTC comparison date, or deterministic delta changes at the same cutoff
- **THEN** the canonical semantic projection, `content_digest`, and `run_id` change

#### Scenario: Only acquisition order changes

- **WHEN** SEC rows, CFTC rows, company adapters, pages, or Provider outcomes complete in another order with identical evidence
- **THEN** the final canonical semantic output, `content_digest`, and `run_id` remain identical

#### Scenario: Complete semantic slice changes

- **WHEN** one watched company's SEC item or one CFTC market item changes and the complete Provider acquisition succeeds
- **THEN** the whole current Provider slice replaces the prior slice without merging historical members

#### Scenario: Watched company is removed without changing remaining filings

- **WHEN** prior SEC v2 contains A-H and complete current acquisition contains byte-identical A-G after removing H from configuration
- **THEN** the selected current slice is exactly A-G, H is not carried, and the Feed identity reflects the changed selection

#### Scenario: Watched selection becomes empty

- **WHEN** configuration contains no watched companies while the prior SEC slice contains companies
- **THEN** complete permitted-empty SEC selects no items with no_snapshot and null carry provenance rather than restoring prior companies

#### Scenario: Only configuration aliases change

- **WHEN** configured aliases change but CIKs and all official SEC item bytes remain equal
- **THEN** Feed configuration identity changes while the equal-set SEC slice remains eligible for unchanged carry-forward

#### Scenario: A corrected same-date CFTC report removes a market

- **WHEN** prior CFTC v2 has markets X and Y, complete current acquisition for the same report dates contains only byte-identical X, and pagination proves the corrected report complete
- **THEN** the whole current slice contains only X and prior Y is not carried, while an empty current report still fails acquisition

#### Scenario: Legacy event-list subset remains compatible

- **WHEN** a Provider-v1 or one of the other six Providers returns the same contract-valid subset or empty check as before this Change
- **THEN** its existing validation-gated carry-forward behavior is preserved rather than receiving SEC/CFTC-v2 complete-set semantics

#### Scenario: Semantic acquisition is incomplete

- **WHEN** any required company, page, selected report, parse, or current-slice validation fails without genuine blocked exemption after prior evidence exists
- **THEN** the Provider remains partial or failed with freshness `not_evaluated`, the pipeline remains incomplete, and prior evidence cannot make the run publishable

#### Scenario: Consumer expresses current and change evidence

- **WHEN** a Host Agent receives one validated v2 semantic item
- **THEN** the item itself contains the typed current, previous or unavailable, change, provenance, and derivation facts needed for evidence-preserving expression

### Requirement: SEC v3 selects a complete watched-issuer Form 4 event set

The authoritative configuration SHALL contain a closed `watched_form4_issuers` selection distinct from the existing watched 13F-company selection, ordered by normalized CIK and embedded in the canonical Feed configuration snapshot. Shipped production SHALL select only Berkshire Hathaway issuer CIK `0001067983` for Form 4 acquisition. Unknown, duplicate, malformed, or missing selection fields SHALL fail static resolution before Provider work or persistent mutation.

For each watched issuer, SEC contract version 3 SHALL retrieve the official submissions `recent` listing, validate its aligned fields, unique accessions, and every precise acceptance time, and prove that the minimum represented precise acceptance time is at or before `window.start`. It SHALL NOT treat incidental source-row order as an acceptance-time coverage or ordering guarantee. It SHALL select every unique exact Form `4` or `4/A` whose precise SEC acceptance time is in `[window.start, evidence_cutoff_at)`, canonically order selected filings by `(accepted_at, accession_number)`, and retrieve every selected safe primary ownership XML. It SHALL NOT use filing date, period of report, transaction date, retrieval time, or current visibility to replace precise acceptance-time eligibility.

The embedded SEC v3 contract SHALL declare `max_filings_per_window = 20`. More than 20 eligible filings, a listing that cannot prove complete window coverage, misaligned or ambiguous listing data, duplicate accessions, an unsafe primary-document path, a missing selected document, malformed or unsupported ownership XML, or any omitted eligible filing or entry SHALL make SEC incomplete and prevent publication. The producer SHALL NOT truncate or choose a preferred subset. A proved-complete listing with zero eligible Form 4 filings SHALL be a valid empty Form 4 sub-slice. ECO-131 SHALL NOT traverse historical submissions files.

#### Scenario: Watched issuer has filings in the advancing window

- **WHEN** Berkshire's complete recent listing contains unique exact Form 4 or 4/A filings accepted inside the half-open window and no bound is exceeded
- **THEN** SEC retrieves and validates every selected primary ownership XML in deterministic order

#### Scenario: Filing falls on a window boundary

- **WHEN** a Form 4 acceptance time equals `window.start` or `evidence_cutoff_at`
- **THEN** the start-boundary filing is eligible and the cutoff-boundary filing is excluded

#### Scenario: Recent listing does not cover the window

- **WHEN** the minimum represented precise acceptance time is later than `window.start` or listing structure cannot prove complete coverage
- **THEN** SEC fails closed without treating an absent filing as an empty current check or consulting historical submissions files

#### Scenario: Recent source rows are not acceptance-time ordered

- **WHEN** an otherwise aligned official `recent` listing has historical rows out of acceptance-time order
- **THEN** SEC validates every row's precise acceptance time, derives coverage from the minimum time, and canonically orders the selected current-window accessions rather than rejecting the source's incidental row order

#### Scenario: Eligible filing bound is exceeded

- **WHEN** a complete listing contains more than 20 eligible Form 4/Form 4-A accessions
- **THEN** SEC is incomplete and publishes neither a truncated subset nor a replacement from prior evidence

#### Scenario: No ownership filing is eligible

- **WHEN** the recent listing proves complete coverage and contains no exact Form 4 or 4/A accepted inside the window
- **THEN** the Form 4 sub-slice is complete and empty without inventing an evidence item

### Requirement: SEC v3 publishes closed structured Form 4 evidence

Each selected accession SHALL produce exactly one `filing` item with `filing_subtype = form4`, exact form `4` or `4/A`, issuer CIK as the filing company, accession number, official filing date, precise acceptance time, period of report, official primary-document source URL, and a closed structured Form 4 payload. Source publication and `knowledge_available_at` SHALL use the precise SEC acceptance time. Issuer identity SHALL contain the filing-supplied CIK, name, and trading symbol and SHALL match one configured watched issuer CIK.

The payload SHALL contain one or more unique reporting owners ordered by normalized owner CIK. Each owner SHALL retain filing-supplied CIK and name plus the complete closed relationship fields `director`, `officer`, `ten_percent_owner`, `other`, nullable `officer_title`, and nullable `other_text`. Missing relationship booleans SHALL normalize to false, and at least one relationship boolean SHALL be true. The payload SHALL NOT publish reporting-owner address or introduce importance, ranking, or inferred entity roles.

The payload SHALL retain separate non-derivative and derivative entry arrays. Each array SHALL preserve the SEC table's mixed source order with consecutive source ordinals and support both `transaction` and standalone `holding` entry kinds. Transaction entries SHALL retain the applicable security title, transaction and deemed-execution dates, raw SEC transaction form type and transaction code, timeliness, equity-swap flag, acquisition/disposition code, reported transaction amount, price per share, derivative exercise/conversion fields, underlying security, post-transaction amount, and ownership nature. Standalone holdings SHALL retain their applicable security, derivative and underlying-security fields, post-transaction amount, and ownership nature. Fields inapplicable to an entry kind SHALL not be invented.

#### Scenario: Filing has multiple reporting owners and entries

- **WHEN** one valid filing contains multiple reporting owners and a mixture of transactions and standalone holdings across both SEC tables
- **THEN** one filing item preserves every owner, complete relationship, table, entry kind, and source ordinal without duplicating entries per owner or asserting an owner-to-entry relation absent from the filing structure

#### Scenario: Purchase, sale, or award code is published

- **WHEN** a transaction contains a supported SEC transaction code such as `P`, `S`, or `A`
- **THEN** the payload retains the SEC code and acquisition/disposition value without translating either into bullish, bearish, sentiment, signal, or recommendation semantics

#### Scenario: Standalone holding is present

- **WHEN** either SEC table contains a valid standalone holding entry
- **THEN** the entry is retained with its security, amount and ownership evidence rather than silently omitted or represented as a transaction

#### Scenario: Unsupported entry is encountered

- **WHEN** a selected ownership document contains an entry or required field that cannot be represented by the closed supported contract
- **THEN** SEC fails closed for that acquisition instead of dropping the entry or preserving it only in raw metadata

### Requirement: Form 4 numeric values and footnotes remain typed and reproducible

Every supported Form 4 source numeric SHALL be a bounded nonnegative canonical decimal string produced independently of ambient decimal context. The closed payload SHALL distinguish SEC choice branches rather than coercing them: transaction shares versus total USD value, post-transaction shares versus USD value, and underlying-security shares versus USD value. Reported price per share and conversion/exercise price SHALL use `usd_per_share`; count values SHALL use `shares`; reported total/value branches SHALL use `usd`. The producer SHALL NOT derive transaction value, holding delta, price direction, or another arithmetic or financial interpretation.

Every value-bearing Form 4 field SHALL retain its own deterministically ordered SEC footnote references and SHALL permit a null value only where the SEC structure permits footnote-supported omission. The payload SHALL retain a unique filing-level footnote table ordered numerically from `F1` through `F99`, with deterministic plain-text extraction, NFC normalization, and at most 4,000 Unicode code points per footnote. Duplicate or malformed IDs, dangling references, unsupported mixed content, oversized text, or a required null value without permitted footnote support SHALL fail closed rather than truncate or detach support. Filing remarks SHALL remain separate, normalized evidence bounded to the SEC maximum of 2,000 characters.

Ownership nature SHALL retain direct or indirect ownership and nullable nature text. Indirect ownership without non-empty nature text SHALL fail closed. Numeric fact construction MAY retain internal measured-fact provenance, but generic fact/derivation metadata SHALL NOT be serialized into the Feed.

#### Scenario: Numeric processing runs under different ambient decimal state

- **WHEN** the same valid ownership XML is processed under different process-global Decimal precision, rounding, flags, or traps
- **THEN** every numeric field and the complete canonical filing item bytes are identical

#### Scenario: Derivative transaction reports total value

- **WHEN** a derivative transaction uses `transactionTotalValue` rather than `transactionShares`
- **THEN** the payload retains the selected `total_value` branch in canonical USD without inventing a share count

#### Scenario: Value is supplied only through a footnote

- **WHEN** the SEC structure permits a numeric value to be absent and the field carries valid footnote references
- **THEN** the payload retains a null value, its explicit unit and the field-level references to available filing footnote text

#### Scenario: Footnote reference cannot be resolved

- **WHEN** a field references an absent, duplicate, malformed, unsupported, or oversized footnote
- **THEN** the selected filing fails validation and cannot enter a published Feed

#### Scenario: Indirect ownership lacks its nature

- **WHEN** an entry reports indirect ownership without non-empty nature-of-ownership evidence
- **THEN** the filing fails closed rather than representing incomplete ownership semantics

### Requirement: Form 4 amendment evidence does not infer filing lineage

A Form `4/A` item SHALL retain `is_amendment = true` and the SEC-required `date_of_original_submission`; a Form `4` item SHALL retain `is_amendment = false` and a null original-submission date. Every original and amended accession SHALL remain an independent event with its own source provenance and canonical identity. The Producer SHALL NOT infer or publish `amends_accession`, merge an amendment with another filing, overwrite historical evidence, designate an effective/latest version, or retrieve evidence outside the advancing window to construct a lineage.

#### Scenario: Form 4/A is selected

- **WHEN** a valid Form 4/A is accepted inside the advancing window
- **THEN** it is published under its own accession with its SEC-supplied original-submission date and no inferred accession linkage

#### Scenario: Original and amendment occur in one window

- **WHEN** both a Form 4 and one or more Form 4/A accessions are independently eligible
- **THEN** each accession produces a separate item and none is removed, replaced, or labeled effective by amendment resolution

#### Scenario: Consumer requests an amended accession

- **WHEN** no explicit amended accession exists in the supported SEC ownership evidence
- **THEN** the payload omits that relationship rather than deriving it from issuer, owner, period, date, ordering, or similarity

### Requirement: Form 4 identities and ordering are deterministic

A Form 4 filing item identity SHALL derive solely from the SEC Provider identity and accession number. Every non-derivative or derivative table entry SHALL expose a stable entry identity derived solely from accession number, table kind, and its zero-based source ordinal within that table's mixed transaction/holding sequence. Reporting-owner names, transaction values, security titles, issuer aliases, and acquisition completion order SHALL NOT participate in identity.

Reporting owners SHALL be unique and ordered by normalized CIK. Non-derivative entries SHALL precede derivative entries in semantic projection, and each table's entries SHALL remain in ascending consecutive source ordinal. Filing footnotes and every field-level reference list SHALL use numeric footnote-ID order. Repeated processing of identical listing and XML bytes SHALL produce byte-identical canonical items; changing a typed identity, relationship, entry, amount, date, ownership, amendment, remark, or footnote fact SHALL change canonical item content and therefore Feed semantic identity.

#### Scenario: Same filing is processed repeatedly

- **WHEN** the same selected submissions row and ownership XML are processed more than once
- **THEN** filing identity, entry identities, ordering, canonical item bytes, content digest, and cutoff-derived run identity are identical

#### Scenario: Filing has multiple table entry kinds

- **WHEN** transaction and standalone-holding elements are interleaved in an SEC table
- **THEN** their source ordinals and entry identities follow that mixed SEC table order without regrouping by kind, code, date, price, or amount

#### Scenario: One semantic field changes

- **WHEN** any retained Form 4 semantic or provenance fact changes at the same cutoff
- **THEN** canonical item content, Feed content digest, and run identity change while the accession-based filing identity and position-based entry identities remain stable

### Requirement: SEC v3 snapshot selection combines 13F state with current-window Form 4 events

A complete SEC contract-version-3 acquisition SHALL contain exactly one valid `form13f` filing item for every configured watched 13F company and no extra 13F company, together with exactly the complete set of valid `form4` filing items selected for configured watched issuers in the current advancing window. Validation SHALL dispatch subtype semantics explicitly, require exact configured 13F and Form 4 issuer membership, require unique accession-based identities across the SEC slice, and reject a legacy or unknown filing shape under v3.

The resulting mixed SEC slice SHALL remain a whole-Provider replacement. Equal identity sets with byte-identical canonical content MAY carry prior bytes under existing complete-state admission. Any added, removed, or changed 13F or Form 4 identity SHALL select the complete current SEC slice. In particular, Form 4 events from an earlier window SHALL not be unioned into a later slice when they are absent from the current complete event set. Failed or partial 13F or Form 4 acquisition SHALL remain `not_evaluated`, pipeline-failing and ineligible for prior-slice substitution. Genuine first-resource blocked exemption SHALL retain the existing no-prior-evidence degraded behavior.

#### Scenario: Current window adds a Form 4 event

- **WHEN** all 13F items are unchanged and a complete current Form 4 acquisition adds one eligible accession
- **THEN** the whole current SEC v3 slice containing all required 13F items and that event replaces the prior SEC slice

#### Scenario: Earlier Form 4 event leaves the current window

- **WHEN** the current complete SEC slice contains unchanged 13F state and no Form 4 event that appeared only in the preceding advancing window
- **THEN** the current slice replaces the prior slice without carrying or merging that earlier event

#### Scenario: Form 4 sub-acquisition fails

- **WHEN** every watched 13F company succeeds but one required Form 4 listing or selected filing is incomplete
- **THEN** SEC is incomplete, freshness is not evaluated, the Feed cannot publish, and prior SEC evidence does not convert the run into success

#### Scenario: Complete SEC v3 slice is byte-identical

- **WHEN** the exact 13F and Form 4 item identity sets and every canonical item are equal to the validated prior SEC v3 slice
- **THEN** existing whole-slice valid-unchanged carry-forward remains eligible without rewriting source-semantic times

### Requirement: SEC v4 selects a bounded watched-filer beneficial-ownership event set

The authoritative configuration SHALL contain a closed `watched_beneficial_ownership_filers` selection distinct from the watched 13F-company and Form 4-issuer selections, ordered by normalized CIK and embedded in the canonical Feed configuration snapshot. Shipped production SHALL select only Berkshire Hathaway reporting filer CIK `0001067983`. Unknown, duplicate, malformed, missing, or unordered selection data SHALL fail before Provider work or persistent mutation, and configured names SHALL NOT replace filing-supplied identity evidence.

For each configured filer, SEC contract version 4 SHALL validate the official submissions listing and select every unique exact `SCHEDULE 13D`, `SCHEDULE 13D/A`, `SCHEDULE 13G`, or `SCHEDULE 13G/A` whose precise acceptance time falls in `[window.start, evidence_cutoff_at)`. Selection SHALL use precise acceptance time rather than filing date, event date, retrieval time, or source row order. Accessions repeated across configured filers SHALL be fetched once and produce one event item. The manifest SHALL declare closed, statically validated current-filing, history-file, historical-candidate-document, reporting-person, structured-format, schema-version, and locator-prefix bounds. Unproved window coverage, bound excess, unsafe source location, omitted selected accession, unsupported current format, or malformed selected current document SHALL make SEC incomplete and prevent publication rather than truncate the event set.

#### Scenario: Current-window ownership filings are selected

- **WHEN** a configured filer's complete official listing contains supported exact Schedule 13D/G accessions accepted inside the half-open Feed window and all declared bounds hold
- **THEN** every unique selected accession is fetched and normalized in deterministic `(accepted_at, accession_number)` order

#### Scenario: Filing lies on a window boundary

- **WHEN** one supported filing is accepted exactly at `window.start` and another exactly at `evidence_cutoff_at`
- **THEN** the start-boundary filing is included and the cutoff-boundary filing is excluded

#### Scenario: Current event bound is exceeded

- **WHEN** the complete listing contains more eligible current-window Schedule 13D/G accessions than the manifest permits
- **THEN** SEC is incomplete and publishes neither a truncated subset nor prior SEC evidence

#### Scenario: Same accession is listed for multiple configured filers

- **WHEN** an identical accession is discovered through more than one configured filer
- **THEN** it is acquired once and produces one accession-identified Feed item without inferring a reporting group from duplicate discovery

#### Scenario: No ownership filing is eligible

- **WHEN** every configured listing proves complete window coverage and contains no eligible Schedule 13D/G accession
- **THEN** the beneficial-ownership sub-slice is complete and empty without fabricating an event

### Requirement: SEC v4 publishes closed structured beneficial-ownership evidence

Each selected accession SHALL produce exactly one `filing` item with `filing_subtype = beneficial_ownership`, accession-based item identity, exact SEC form, schedule family, filing and precise acceptance times, official raw structured-document URL, issuer identity, ownership-class identity, source-ordered reporting positions, and closed amendment metadata. Source publication and `knowledge_available_at` SHALL equal the precise SEC acceptance time. The Producer SHALL parse only manifest-declared verified SEC-native structured 13D and 13G shapes through form-specific contracts and SHALL NOT invoke a legacy prose, HTML, generic SEC, or heuristic parser.

Ownership-class identity SHALL prefer a normalized source CUSIP and otherwise use an exact normalized source class title. When neither is available, current evidence MAY remain publishable but comparison SHALL be unavailable with reason `ownership_class_identity_unavailable`. Each reporting position SHALL retain a zero-based source ordinal, source name, optional explicit source CIK, source-reported person type and group membership, required beneficially-owned-shares and ownership-percentage wrappers, and only those voting or dispositive power facts explicitly present in the source. A reporting-position identity SHALL use an explicit source CIK when available and otherwise exact normalized source name; configured aliases, fuzzy matching, and inferred CIK assignment are prohibited. A group identity or aggregate SHALL be published only when explicitly supported by the filing, and member values SHALL NOT be summed to invent group ownership.

The required shares and percentage wrappers SHALL contain a closed status, canonical value or null, unit, typed reason, and form-specific document-local source-field references. `reported` SHALL require a non-null source value; `unavailable` SHALL require null and a permitted reason. Shares and power values SHALL be nonnegative, and reported percentages SHALL be between zero and one hundred inclusive. Missing values SHALL NOT default to zero or be algebraically inferred from other filing facts. Source-field references SHALL resolve within their own current or previous filing snapshot to closed form/schema fields and source ordinals; arbitrary XPath, dangling references, credentials, filer CCC values, addresses, telephone numbers, and signatures SHALL NOT enter the Feed.

#### Scenario: Filing contains several reporting persons

- **WHEN** one supported filing contains multiple source reporting positions with distinct ownership values
- **THEN** one accession item preserves every position in source order with its own identity basis, measured facts, optional powers, and source-field support without collapsing the filing to one holder

#### Scenario: Reporting person has no source CIK

- **WHEN** a structured filing supplies a reporting-person name but no person CIK
- **THEN** the position retains `source_name` identity basis and no configured or inferred CIK is added

#### Scenario: CUSIP is absent

- **WHEN** the source supplies an ownership class title but no usable CUSIP
- **THEN** class identity uses exact deterministic normalized title matching and records `class_title` as its identity basis

#### Scenario: Required numeric value is not reported

- **WHEN** a supported structured source explicitly lacks a numeric shares or percentage value in an allowed shape
- **THEN** the required wrapper is retained with null value, `unavailable` status, and a closed source-supported reason rather than zero

#### Scenario: Group aggregate is not explicit

- **WHEN** several reporting persons jointly file but the structured source does not supply an explicit group aggregate
- **THEN** the item preserves the persons and group-membership evidence without summing their ownership facts or inventing a group aggregate

#### Scenario: Prohibited private or interpretive field is supplied

- **WHEN** an item contains filer credentials, CCC, contact details, signatures, arbitrary raw metadata, inferred identity, or investment interpretation
- **THEN** Feed validation rejects the item

### Requirement: Beneficial-ownership comparison is bounded, conservative, and reproducible

For each selected current filing, SEC v4 SHALL first resolve the nearest earlier filing comparable by official discovery filer CIK, issuer CIK, and ownership-class identity, without including schedule family or amendment status in that key. It SHALL then match reporting positions by explicit source CIK or, when absent, exact normalized source name. Schedule 13D and 13G forms MAY therefore compare across family transitions, but the Feed SHALL retain both exact forms and SHALL NOT interpret the transition. A previous filing SHALL precede current by precise acceptance time and have a distinct accession.

Resolution SHALL use a deterministic newest-first scan of official recent and declared historical submissions metadata. Historical candidate documents SHALL be fetched and parsed at most once per run and shared across all unresolved current keys. The scan SHALL stop when all keys resolve, official supported history is exhausted, or the closed total historical-candidate-document bound is reached. An unsupported nearest previous document SHALL be retained by accession, time, and source URL with reason `previous_format_unsupported`; it SHALL NOT be skipped in favor of an older parseable filing. A reached history or candidate bound SHALL produce typed unavailability rather than an initial-filing claim. Transport, source-validation, or parser failure for a document required within the supported acquisition contract SHALL keep SEC incomplete rather than masquerade as absent history.

A filing SHALL be classified `initial_filing` only after all official supported earlier metadata candidates have been exhausted with no prior filing matching its filer, issuer, and ownership class. When a prior filing exists but an internal reporting position cannot be matched, that position SHALL be unavailable with reason `reporting_identity_not_comparable`, not initial or new. Current and previous snapshots SHALL each retain their own accession, precise acceptance time, official URL, measured facts, and document-local source support.

For compatible reported facts, share delta SHALL equal exact current shares minus previous shares in `shares`, and percentage delta SHALL equal exact current percentage minus previous percentage in `percentage_points`. Arithmetic SHALL use the deterministic measured/derived numeric boundary and SHALL not round, truncate, use an LLM, or defer calculation to the Host Agent. Derived output SHALL carry the Provider-specific descriptor `current_minus_previous`; generic internal fact-object derivation metadata SHALL not be serialized. If either operand is unavailable, the corresponding delta SHALL be null and unavailable.

#### Scenario: Comparable filing changes schedule family

- **WHEN** the nearest earlier filing has the same filer, issuer and class but current and previous forms belong to different 13D/13G families
- **THEN** their explicitly reported compatible ownership facts are compared while both exact forms are retained without intent or market interpretation

#### Scenario: Supported previous facts are available

- **WHEN** current and nearest previous positions match and both report shares and percentages
- **THEN** share and percentage-point deltas equal exact current-minus-previous values and are reproducible from the two accession-supported snapshots

#### Scenario: Previous identity cannot be matched

- **WHEN** a previous comparable filing exists but a current name-based position cannot be matched exactly to a previous source identity
- **THEN** that position has comparison unavailable with reason `reporting_identity_not_comparable` and no initial or new-holder claim

#### Scenario: Nearest previous filing has an unsupported format

- **WHEN** the nearest metadata-comparable previous accession uses a legacy or otherwise unsupported document format
- **THEN** its filing reference is retained, comparison is unavailable with reason `previous_format_unsupported`, and no older filing is substituted

#### Scenario: Historical candidate bound is exhausted

- **WHEN** the shared reverse scan reaches its closed candidate-document bound before proving a previous filing or complete absence
- **THEN** unresolved comparisons use reason `history_candidate_bound_exhausted` without previous zero, delta, or initial-filing classification

#### Scenario: Complete history has no previous comparable filing

- **WHEN** all official supported earlier history is exhausted without any filing matching the current filer, issuer and ownership class
- **THEN** comparison is `initial_filing`, previous is null, and every delta is null rather than calculated from zero

#### Scenario: One operand is unavailable

- **WHEN** current or previous shares or percentage is unavailable
- **THEN** the corresponding delta remains null and unavailable without deriving the missing operand

### Requirement: Beneficial-ownership amendments remain independent evidence events

Exact `SCHEDULE 13D/A` and `SCHEDULE 13G/A` items SHALL retain `is_amendment = true`, their schedule family, and any source-supported amendment number. Non-amendment forms SHALL retain `is_amendment = false`. Every accession SHALL remain an independent event with its own provenance and canonical identity. The Producer SHALL NOT infer or publish an original accession, `amends_accession`, effective/latest version, merged filing, or amendment relationship from issuer, reporting persons, dates, ordering, similarity, or previous-comparable resolution unless the supported structured source explicitly supplies that accession linkage.

The payload and Host-Agent boundary SHALL remain evidence-only. They SHALL NOT add bullish, bearish, activist, takeover, control-change, accumulation, distribution, importance, confidence, signal, prediction, market-impact, recommendation, or trading semantics. Source-reported form transitions, ownership facts, amendment metadata, and exact changes MAY be expressed without interpretation.

#### Scenario: Amendment supplies only an amendment number

- **WHEN** a supported amendment identifies its amendment number but does not supply an original accession
- **THEN** the number and amendment status are retained while original-filing and `amends_accession` fields are absent

#### Scenario: Previous comparable is an earlier amendment

- **WHEN** the nearest earlier comparable filing is itself an amendment
- **THEN** it may support deterministic ownership comparison but is not relabeled as the original or effective filing

#### Scenario: Investment meaning is added

- **WHEN** a beneficial-ownership item adds intent, control, takeover, sentiment, signal, ranking, prediction, recommendation, or market-impact semantics not explicitly present as retained source evidence
- **THEN** Feed validation rejects the item

### Requirement: SEC v4 mixed slices remain complete, bounded, and deadline-admissible

A complete SEC contract-version-4 acquisition SHALL contain exactly one valid `form13f` item for every configured watched 13F company, exactly the selector-proven current-window `form4` accession set for configured watched issuers, and exactly the selector-proven deduplicated current-window `beneficial_ownership` accession set for configured watched beneficial-ownership filers. Validation SHALL dispatch every subtype explicitly, require exact configured membership and selector-produced accession sets, require unique accession-based identities across the SEC slice, and reject legacy or unknown filing shapes under v4.

The mixed SEC v4 slice SHALL remain one Provider outcome and one whole-Provider replacement. Historical filings fetched only for beneficial-ownership comparison SHALL remain nested references/snapshots and SHALL NOT become additional top-level events. A previous filing that is independently selected in the current window MAY be both its own top-level event and nested comparison evidence for a later event. Events absent from the next complete advancing-window slice SHALL not be unioned or carried from prior output. Failed or partial work in any SEC subtype SHALL remain `not_evaluated`, pipeline-failing, and ineligible for prior-slice substitution; genuine first-resource blocked exemption SHALL retain the existing no-prior-evidence degraded behavior.

Before production v4 activation, the configured pre-commit deadline SHALL be at least the verified complete SEC v4 successful-path managed-send floor plus explicit bounded network headroom and commit reserve. The calculation SHALL include all configured 13F sends, the existing maximum Form 4 listing/document sends, beneficial-ownership listing/current/history/candidate-document sends, the unchanged SEC minimum interval, and any reused request exactly once. Static resolution or regression verification SHALL fail when configuration, selections, manifest bounds, rate policy, or deadline no longer satisfy that inequality. ECO-132 SHALL NOT lower SEC rate safety or silently reduce evidence to fit the deadline.

#### Scenario: Complete SEC v4 event sets are produced

- **WHEN** all configured 13F, Form 4, and beneficial-ownership acquisition units complete under their closed contracts
- **THEN** the one SEC outcome contains the exact required mixed subtype sets and is eligible for whole-slice selection

#### Scenario: Historical enrichment filing is inspected

- **WHEN** a previous 13D/G document is fetched solely to support a current ownership event
- **THEN** it appears only in the current event's previous evidence and not as an extra top-level item unless independently selected in the current window

#### Scenario: Prior-window ownership event is absent now

- **WHEN** a beneficial-ownership accession appeared only in the prior advancing window and is absent from the complete current selector result
- **THEN** whole-slice replacement does not carry or union that prior top-level event

#### Scenario: Beneficial-ownership acquisition is incomplete

- **WHEN** 13F and Form 4 work succeeds but a required current beneficial-ownership listing, document, or supported historical request fails
- **THEN** SEC is incomplete, freshness is not evaluated, publication is forbidden, and prior SEC evidence does not convert the run into success

#### Scenario: Existing request-budget regression omits a subtype

- **WHEN** the successful-path send calculation excludes Form 4, beneficial-ownership, history, or another configured SEC v4 acquisition unit
- **THEN** production v4 activation fails verification rather than relying on an understated deadline floor

#### Scenario: Complete slices are byte-identical

- **WHEN** exact 13F, Form 4, and beneficial-ownership identity sets and every canonical item are equal to the validated prior SEC v4 slice
- **THEN** existing whole-slice valid-unchanged carry-forward remains eligible without changing source-semantic times

### Requirement: New News, Macro, and Policy evidence carries validated semantic context

Every newly acquired Feed v4 item whose payload discriminator is `news`, `macro_release`, or `policy` SHALL carry exactly one `semantic_context` matching that domain and the retained payload/source facts. The six currently emitting Provider paths SHALL be covered according to their existing output contracts: Federal Reserve and PBOC policy; BLS, NBS, SSE, and SZSE news; and NBS macro releases. Existing domain classification SHALL remain unchanged, including BLS releases and unstructured NBS releases remaining `news` unless a separate Provider-contract change authorizes another payload type.

Semantic enrichment SHALL run after existing source extraction and payload normalization and before item admission. It SHALL perform no Provider request, historical Feed lookup, credential access, orchestration, or payload reclassification. A required context construction or validation failure SHALL reject the item through the existing Provider outcome and publication boundary rather than publish evidence without its required context.

Positioning and filing items SHALL retain their existing typed payload semantics and SHALL NOT acquire `semantic_context` under this Change. Provider manifests, embedded Provider contract versions, payload-type declarations, coverage, freshness, and acquisition behavior SHALL remain unchanged.

A fully validated pre-ECO-130 v4 Provider slice MAY continue to omit context only when the existing snapshot contract carries that complete slice byte-for-byte and records its prior run in non-null `freshness.carried_forward_from_run_id`. The independently evaluated freshness status MAY be `valid_unchanged` or `stale` according to the existing cadence window. The Producer SHALL NOT rewrite carried item bytes merely to add context. The next complete current slice that replaces that legacy slice SHALL require context on every affected-domain item it contains; partial, failed, or blocked work SHALL NOT be used as a migration trigger or fallback.

#### Scenario: Newly generated affected-domain item is valid

- **WHEN** a supported Provider produces a valid new `news`, `macro_release`, or `policy` item
- **THEN** item admission and publication require its matching valid semantic context

#### Scenario: Required mapping fails

- **WHEN** an affected-domain item cannot produce a complete valid context from its normalized evidence and closed mapping
- **THEN** the item is rejected and existing Provider completeness and pipeline publication rules determine the failed or partial outcome

#### Scenario: Existing domain classification is preserved

- **WHEN** BLS or an unstructured NBS release is normalized under its current Provider contract
- **THEN** the item remains `news` and receives news context rather than being reclassified as `macro_release`

#### Scenario: Unaffected domain adds context

- **WHEN** a positioning or filing item contains `semantic_context`
- **THEN** validation rejects the item as outside the ECO-130 domain boundary

#### Scenario: Legacy slice is carried unchanged

- **WHEN** a fully validated pre-ECO-130 affected-domain slice remains eligible for existing whole-slice carry-forward and records non-null `carried_forward_from_run_id`
- **THEN** the Producer preserves its contextless item bytes and prior-run provenance rather than rewriting source evidence during migration

#### Scenario: Carried legacy slice ages to stale

- **WHEN** a contextless carried legacy slice from a scheduled or weekly Provider passes beyond its declared validity window while complete current acquisition still establishes no changed observation
- **THEN** the slice remains byte-identical with non-null `carried_forward_from_run_id`, its freshness becomes `stale`, and context omission alone does not change existing Provider completeness or pipeline publication status

#### Scenario: Current slice replaces a legacy slice

- **WHEN** complete current acquisition selects a new or changed affected-domain slice after a contextless legacy slice
- **THEN** every selected current item contains valid semantic context and the legacy omission is not propagated into the replacement

### Requirement: Semantic context participates in canonical Feed identity

The complete validated `semantic_context` SHALL participate in canonical item bytes, domain artifact bytes, the logical Feed semantic projection, `content_digest`, and cutoff-derived `run_id`. Repeated generation from identical validated evidence and mapping rules SHALL preserve identical context, canonical ordering, artifact bytes, digest, and run identity. Changing any retained semantic-context fact at the same cutoff SHALL change canonical item content and Feed identity while the existing source-derived item `id` remains unchanged.

No execution observation, mapping diagnostic, internal numeric-fact object, or non-published extraction state SHALL enter the semantic projection. Existing deterministic global item ordering by `(source.knowledge_available_at, id)`, domain artifact ordering, publication, snapshot selection, and carry-forward rules SHALL remain unchanged.

#### Scenario: Same evidence is regenerated

- **WHEN** identical Provider fixtures are processed repeatedly with the same cutoff and fixed mappings
- **THEN** semantic contexts, canonical item/artifact bytes, `content_digest`, and `run_id` are identical

#### Scenario: One context fact changes

- **WHEN** a source-supported subject, category, period, observation, revision, issuer, action, date, or scope fact changes at the same cutoff
- **THEN** the item ID remains source-derived while canonical item content, `content_digest`, and `run_id` reflect the changed evidence

#### Scenario: Only input order changes

- **WHEN** equivalent source maps, entity candidates, numeric facts, or affected scopes arrive in another order
- **THEN** total ordering and duplicate rules produce the same canonical Feed bytes and identity

### Requirement: Feed v4 retains bounded legacy reads across semantic-context activation

New production SHALL continue to emit Feed `schema_version = 4`. The current consumer SHALL accept an otherwise valid previously published v4 bundle whose `news`, `macro_release`, and `policy` items predate ECO-130 and omit `semantic_context`. When `semantic_context` is present on an affected legacy or current item, the consumer SHALL validate its entire closed shape and consistency with the item; it SHALL NOT ignore malformed, mismatched, unknown, or analytical context.

This bounded omission compatibility SHALL apply only to reading legacy v4 evidence and to the exact non-null `carried_forward_from_run_id` exception above, including carried `valid_unchanged` and `stale` slices. Newly acquired or replacement affected-domain items SHALL still require context before publication, and no Provider contract-version bump or hash-based behavior selection SHALL be introduced to distinguish old and new items.

#### Scenario: Legacy v4 item omits context

- **WHEN** the current consumer reads an otherwise valid previously published v4 bundle containing an affected-domain item without `semantic_context`
- **THEN** validation accepts the legacy omission under the bounded read path

#### Scenario: Present legacy context is malformed

- **WHEN** any v4 affected-domain item contains `semantic_context` with a mismatched domain, inconsistent payload fact, unknown member, or forbidden analytical meaning
- **THEN** validation rejects the bundle rather than treating context as optional untyped metadata

#### Scenario: New production omits context

- **WHEN** the current Producer attempts to publish a newly acquired or replacement affected-domain item without `semantic_context`
- **THEN** pre-publication validation fails even though the bounded consumer path can read a legacy omission

### Requirement: SEC source URLs use canonical CIK representation per locator

SEC EDGAR uses two distinct canonical CIK representations in its verified
locators. The submissions API URL SHALL use the ten-digit zero-padded CIK
(`https://data.sec.gov/submissions/CIK<ten-digit>.json`). Every Archive source
URL SHALL use the unpadded integer CIK in the path
(`https://www.sec.gov/Archives/edgar/data/<integer>/...`). A single
canonicalization helper SHALL derive the unpadded integer form from a normalized
ten-digit CIK, SHALL require a ten-digit input, and SHALL fail closed on malformed
input. The producer source-link contract and the Feed validator source-link
contract SHALL agree on the same canonical form for Archive URLs; neither side
SHALL independently accept the padded form in an Archive path. Submissions and
Archive URL construction SHALL NOT be duplicated across 13F, Form 4, and
Schedule 13D/G paths.

#### Scenario: Submissions URL uses padded CIK

- **WHEN** the SEC submissions API URL is constructed for a watched company
- **THEN** the URL is `https://data.sec.gov/submissions/CIK<ten-digit>.json` with
  the zero-padded CIK

#### Scenario: Archive URL uses unpadded integer CIK

- **WHEN** an SEC Archive source URL is constructed for a 13F complete submission,
  a Form 4 primary document, or a Schedule 13D/G current or historical document
- **THEN** the Archive path uses the unpadded integer CIK
  (`/Archives/edgar/data/<integer>/...`) and the URL is the SEC canonical locator,
  not a redirecting alias

#### Scenario: Producer and validator contracts agree

- **WHEN** a Form 4 or beneficial-ownership item is normalized and validated
- **THEN** both the producer-constructed source URL and the validator source-link
  regex require the unpadded integer CIK in the Archive path, and an item carrying a
  padded Archive URL fails validation

#### Scenario: Canonicalization helper rejects malformed CIK

- **WHEN** the canonicalization helper receives a CIK that is not a normalized
  ten-digit decimal string
- **THEN** it fails closed with a typed schema error and no Archive URL is emitted

#### Scenario: URL form change is reflected in digest identity

- **WHEN** an SEC Archive source URL changes from the padded form to the unpadded
  canonical form
- **THEN** the affected item's `DigestContext` projection and the Feed
  `content_digest` change by design, while `stable_item_id` (derived from
  `provider_id + accession`) and dedupe behavior remain stable
