## MODIFIED Requirements

### Requirement: Typed Feed bundle has one authoritative manifest

Every newly generated Feed SHALL consist of canonical `feed-manifest.json` bytes and exactly one canonical domain artifact for each supported Feed payload discriminator, in this deterministic order: `news`, `macro_release`, `policy`, `positioning`, `filing`, and `social`. Each item SHALL occur in exactly one artifact selected solely by its `payload.type`; each required artifact SHALL exist even when its `items` array is empty. `market_data`, `flow`, `calendar`, and any unknown payload or artifact domain SHALL be rejected. Grouping SHALL NOT depend on Provider identity or introduce another evidence category.

The manifest SHALL be the only authoritative bundle entry point and SHALL contain bundle identity, window and cutoff, truthful generation metadata, producer/configuration/Provider contracts, Provider outcomes, pipeline result, schema descriptors, and a complete six-domain artifact inventory. It SHALL contain no evidence item, duplicated evidence payload, analysis, ranking, signal, regime, impact, or recommendation. A domain artifact SHALL contain only its artifact schema version, bundle `run_id`, domain discriminator, and evidence items.

#### Scenario: Mixed evidence is routed

- **WHEN** normalized evidence contains different supported payload types
- **THEN** each item appears once in its matching artifact in the closed six-domain inventory

#### Scenario: A domain has no evidence

- **WHEN** a valid run produces no item for a supported payload type
- **THEN** the manifest inventories the corresponding required empty artifact

#### Scenario: Removed evidence type is supplied

- **WHEN** normalized evidence or an inventory entry uses `market_data`, `flow`, or `calendar`
- **THEN** validation rejects the candidate before publication or consumption

#### Scenario: Consumer discovers available evidence

- **WHEN** a consumer reads a valid manifest
- **THEN** its closed inventory identifies all six required domains, canonical paths, item counts, byte sizes, and digests without inspecting payloads

#### Scenario: Intelligence enters the bundle

- **WHEN** the manifest or a domain item contains prohibited financial interpretation or investment intelligence
- **THEN** bundle validation rejects the candidate before publication or consumption

### Requirement: Credential-free verified provider contracts

The Feed SHALL strictly compose required activation and coverage policy with each of the eight required core manifests and the approved optional Weibo manifest before execution. Each manifest SHALL remain authoritative for Provider identity/version, verification and evidence metadata, authentication/protocol, fetch/redirect/source-link rules, charset/content type, request/response limits, rate policy, pagination, empty-window semantics, implemented payload types, cadence, and fixture provenance. The one resolved contract SHALL drive adapter behavior, rate handling, planning, coverage, and the embedded `provider_contracts` snapshot. All eight core Providers SHALL require no paid data credential, and every accepted URL SHALL be HTTPS, credential-free, canonicalized under its owning policy, and validated before identity or publication.

Only the approved optional `weibo_social` acquisition SHALL require a session Cookie. Its absence SHALL NOT prevent static configuration or package import; no secret value SHALL enter the manifest or embedded contract. The eight core contracts SHALL retain authentication `none`. Static invalidity of any declared manifest, including Social, SHALL fail startup rather than degrade. Valid contract with unavailable backend installation SHALL instead be a Social acquisition failure.

#### Scenario: Default providers run without credentials

- **WHEN** shipped configuration loads without a paid data credential
- **THEN** all eight required verified Providers initialize for planning without reading an API key

#### Scenario: Enabled Provider contract cannot be resolved

- **WHEN** any required manifest is missing, invalid, unsupported, mismatched, unverified, or outside the six-domain contract
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

#### Scenario: Optional acquisition secret is absent
- **WHEN** all declared contracts are valid and `WEIBO_COOKIE` is absent
- **THEN** configuration resolves without reading that secret and only attempted Social acquisition becomes unavailable

### Requirement: Feed bundle is the serialized external contract

Every published bundle SHALL validate against the six-domain manifest, artifact, and logical Feed schema majors and their semantic invariants. New production SHALL emit logical Feed and bundle major 6 while retaining the six-domain physical artifact layout at artifact major 3. Logical and bundle major 5 MAY remain read-compatible only as the immediately preceding bounded migration input; major 4 and every older major SHALL be rejected. New production SHALL NOT emit major 5, and normal current-Feed consumption SHALL use major 6. The bundle SHALL retain fixed acquisition window, truthful lifecycle timestamps, Provider outcomes with freshness and availability, canonical redacted Feed configuration snapshot, eight required core Provider contract snapshots plus the declared optional Social contract, producer descriptor, canonical logical `content_digest`, cutoff-derived `run_id`, pipeline semantics, and exactly one supported payload per item. Consumers SHALL validate from embedded producer contracts without requiring equality with the consumer build.

#### Scenario: Producer and consumer builds differ

- **WHEN** another build produced a valid supported major-6 six-domain bundle
- **THEN** the consumer validates it from embedded descriptors without requiring current build hashes to match

#### Scenario: Payload type and artifact domain disagree

- **WHEN** an item is stored outside the artifact matching its retained payload discriminator
- **THEN** validation rejects the bundle

#### Scenario: Previous-major active bundle is read

- **WHEN** a complete major-5 bundle enters the explicit bounded migration path
- **THEN** it may seed only a newly validated major-6 six-domain candidate and is not exposed as the normal current product after migration

#### Scenario: Version 3 bundle is supplied

- **WHEN** a consumer or migration caller receives a logical Feed or bundle with major 4 or older
- **THEN** validation rejects it rather than retaining two previous-major compatibility paths

#### Scenario: New production attempts the preceding major

- **WHEN** a producer candidate declares major 5
- **THEN** new-production validation rejects it before publication

#### Scenario: Current artifact version is checked
- **WHEN** a new major-6 bundle is produced
- **THEN** its manifest has major 6 and inventories exactly six major-3 artifacts in fixed domain order, including Social when empty

### Requirement: Provenance tiers and payload-specific time semantics

Every Feed item SHALL retain Provider identity, source name, tier, kind, canonical URL, supplied publication/update time, `source.knowledge_available_at`, and the retained payload's source-semantic effective/reference time and selection basis. Provider `retrieved_at` and Feed `generated_at` SHALL remain execution observations and SHALL NOT be copied into evidence or treated as source time. Newly acquired `news`, `macro_release`, `policy`, and Provider-contract-version-1 `filing` evidence SHALL be selected by knowledge time in the half-open window; SEC contract-version-2 exact `13F-HR` current-state evidence SHALL instead select the latest precise acceptance timestamp strictly before the cutoff for each configured watched CIK and MAY predate `window.start`; current `positioning` and validation-gated carried slices MAY contain earlier source times only under declared cadence contracts. Social evidence SHALL use verified source publication time for half-open membership under its explicit content-availability rules and SHALL remain Tier 3. Retrieval time SHALL NOT establish cutoff eligibility or freshness.

#### Scenario: Evidence becomes known after cutoff

- **WHEN** retained evidence has an earlier effective time but source availability at or after the cutoff
- **THEN** it is excluded from the run rather than admitted from effective time alone

#### Scenario: SEC v2 current state predates the window

- **WHEN** the latest eligible exact `13F-HR` for a configured watched CIK was accepted before `window.start` and no later exact filing was accepted before the cutoff
- **THEN** the filing MAY be retained as cutoff-bounded current state with its original acceptance, filing, report-period, and source provenance

#### Scenario: Calendar evidence was announced earlier

- **WHEN** previously announced calendar evidence is encountered during migration or collection
- **THEN** it is excluded from the six-domain candidate rather than retained through a future-horizon exception

#### Scenario: Tier 3 evidence is normalized

- **WHEN** a supported commentary source emits an otherwise valid retained-domain item
- **THEN** it remains explicitly Tier 3 and is not promoted

#### Scenario: Unchanged evidence is checked again

- **WHEN** a complete core Provider check allows a prior slice to be carried
- **THEN** current retrieval time records the check while carried evidence retains original source-semantic times

### Requirement: Provider availability is explicit and evidence-based

The Feed SHALL classify Provider availability independently from pipeline status using the closed states `success`, `blocked`, `failed`, and `disabled`. A concrete upstream HTTP 401 or HTTP 403 response SHALL classify the affected Provider as `blocked`; no timeout, transport error, parser error, schema error, unexpected status, missing outcome, or other unconfirmed failure SHALL be inferred to be `blocked`. `degraded` SHALL remain reserved for future Provider partial-data availability and SHALL NOT be produced as a Provider availability state. A disabled Provider SHALL remain outside the actual run plan and SHALL NOT create a synthetic Provider outcome or completeness obligation.

Every serialized planned-Provider outcome in the new production schema major SHALL expose its Provider identity, availability, bounded reason or null, and affected configured coverage groups in deterministic order. Availability SHALL agree with the underlying terminal evidence: completed healthy or contract-permitted-empty work is `success`; confirmed access denial is `blocked`; all other incomplete or unexpected work is `failed`. A confirmed access denial after accepted evidence or incomplete sub-request, role, or page work SHALL remain partial and non-exempt rather than making partial-data publication acceptable. For optional Social only, approved acquisition incompleteness SHALL permit degraded publication after discarding the entire Social candidate slice; it SHALL NOT permit partial-data publication.

#### Scenario: HTTP 403 is blocked

- **WHEN** an enabled planned core Provider returns a concrete HTTP 403 response before any evidence is accepted
- **THEN** its availability is `blocked`, its bounded reason identifies HTTP 403, and no Provider-specific exception is required

#### Scenario: HTTP 401 is blocked

- **WHEN** an enabled planned core Provider returns a concrete HTTP 401 response before any evidence is accepted
- **THEN** its availability is `blocked` and its bounded reason identifies HTTP 401

#### Scenario: Timeout remains failed

- **WHEN** Provider work ends in a timeout without a concrete HTTP 401 or HTTP 403 response
- **THEN** its availability is `failed` and it is ineligible for blocked exemption

#### Scenario: Parser error remains failed

- **WHEN** a Provider response cannot be parsed or normalized under its verified contract
- **THEN** its availability is `failed` and it is ineligible for blocked exemption

#### Scenario: Access denial follows accepted evidence

- **WHEN** a core Provider accepts evidence from one sub-request, role, or page and later receives HTTP 401 or HTTP 403 before completing its planned work
- **THEN** diagnostics preserve the access-denial reason but the Provider remains partial, non-exempt, and pipeline-failing

#### Scenario: Disabled Provider is not synthesized

- **WHEN** authoritative registry policy disables a Provider before run planning
- **THEN** its availability is `disabled` in planning semantics but no Provider outcome, coverage obligation, or synthetic warning is emitted

#### Scenario: Optional Social fails after partial acquisition
- **WHEN** a Social account or page fails after earlier acquisition progress
- **THEN** availability remains truthfully blocked or failed, no Social items are published, and only the approved optional acquisition exception can make the otherwise valid Feed degraded

### Requirement: Explicit degradation and coverage outcomes

One Provider failure SHALL NOT stop collection already planned for other Providers. The Feed SHALL record attempted, succeeded, empty, partially valid, failed, skipped, fetched, accepted, and rejected outcomes together with explicit availability diagnostics. Provider membership for completeness assessment SHALL derive only from the actual resolved run plan, and the resolved Provider contract SHALL be the sole authority for `empty_valid_for_window`; disabled Providers and unverified mappings excluded from that plan SHALL create no completeness obligation.

Every planned Provider SHALL have exactly one unambiguous terminal outcome matching its planned Provider identity. The existing core completeness and first-resource HTTP 401/403 blocked-exemption behavior SHALL remain unchanged. Only the approved `weibo_social` Provider SHALL be eligible for optional acquisition degradation; declaring an arbitrary coverage row optional SHALL NOT suppress execution, contract or integrity failures. A planned Provider SHALL be complete only when its outcome is `healthy`, or when its outcome is `empty` and its resolved `empty_valid_for_window` contract is true. A `failed`, `partial`, or `skipped` outcome, a non-permitted `empty` outcome, or a missing, duplicate, ambiguous, or identity-mismatched terminal outcome SHALL be incomplete. Accepted and fetched item counts SHALL NOT determine Provider completeness. A Provider SHALL be blocked-exempt only when a concrete HTTP 401 or HTTP 403 establishes `availability = blocked`, no evidence was accepted, and no partial sub-request, role, or page result exists.

Mandatory coverage SHALL count only complete planned Providers that belong to the configured group. A contract-permitted empty Provider SHALL count toward the configured minimum without contributing an evidence item; an incomplete Provider SHALL not count. For each non-optional group, the effective minimum SHALL equal `max(0, configured minimum - blocked-exempt planned members in that group)`. This exemption SHALL NOT alter configured membership or minimum values, and every exempt member and affected group SHALL remain visible in deterministic diagnostics. A non-exempt incomplete core Provider, an unapproved or internal Social failure, or a group below its effective minimum SHALL produce `pipeline.status = failure` regardless of evidence returned by other Providers. A core Provider SHALL be `partial` when it retains accepted evidence but also has rejected items or incomplete later sub-request, role, or page work; retained valid evidence and outcome counters SHALL remain available for diagnostics but SHALL NOT make the failed run publishable. Social SHALL retain truthful partial-progress outcome semantics but discard candidate items before applying its approved optional acquisition exception.

Core partial outcomes retain existing diagnostics. Social upstream incompleteness SHALL discard every candidate item; normalized Social contract invalidity SHALL fail the Feed.

The total accepted evidence count and final `items` length SHALL NOT independently determine pipeline health. When every planned Provider is complete, blocked-exempt, or an approved unavailable optional Social Provider, every mandatory group meets its effective minimum, and all existing non-source hard-failure boundaries succeed, the Feed SHALL be `degraded` if at least one Provider is blocked-exempt or optional Social acquisition is unavailable and otherwise SHALL remain eligible for the existing healthy or otherwise accepted non-source status even when `items` is empty. Unknown or non-exempt core source incompleteness SHALL NOT produce `degraded`. Approved optional Social acquisition failures SHALL produce `degraded` only after the entire Social slice is discarded and every core and hard non-source gate succeeds. Missing, duplicate, ambiguous or identity-mismatched Social outcomes, invalid normalized items, serialization defects and hard execution failures SHALL remain fatal. Provider-specific and coverage-group diagnostics SHALL identify every blocked exemption or source-completeness cause used to determine pipeline status.

#### Scenario: Blocked Provider is published with warnings

- **WHEN** a planned Provider is blocked-exempt, all other planned Providers are complete, every mandatory group meets its effective minimum, and all non-source hard boundaries pass
- **THEN** the Feed is `degraded`, exits successfully, remains eligible for publication, and identifies the unavailable Provider and affected coverage groups

#### Scenario: Every member of a group is blocked

- **WHEN** every planned member of a mandatory coverage group is blocked-exempt and no other hard failure exists
- **THEN** that group's effective minimum is zero, the Feed is `degraded`, and diagnostics truthfully report the complete unavailable coverage

#### Scenario: One provider fails and another succeeds

- **WHEN** one planned core Provider fails or times out without blocked exemption while another contributes valid evidence
- **THEN** the Feed run fails, exits non-zero, retains both Provider outcomes for diagnostics, and does not replace the active bundle

#### Scenario: Mandatory group is deficient with accepted evidence

- **WHEN** the pipeline accepts at least one valid item but fewer complete planned Provider outcomes contribute than a non-optional coverage group's effective minimum
- **THEN** the Feed run fails, exits non-zero, does not publish, and identifies the deficient coverage group

#### Scenario: Permitted empty contributes to coverage

- **WHEN** a Provider returns no accepted item and its `empty_valid_for_window` contract is true
- **THEN** its `empty` outcome contributes to coverage without contributing an accepted evidence item

#### Scenario: Non-permitted empty does not contribute to coverage

- **WHEN** a planned core Provider reaches `empty` and its `empty_valid_for_window` contract is false
- **THEN** the Provider is incomplete, contributes no coverage, and makes the Feed run fail regardless of evidence from other Providers

#### Scenario: Every provider returns no accepted item

- **WHEN** every planned Provider reaches `healthy` or contract-permitted `empty`, mandatory coverage is satisfied, all other hard-failure boundaries succeed, and the final Feed has `items: []`
- **THEN** zero accepted evidence does not fail the run and the empty Feed remains eligible for normal successful publication

#### Scenario: An item is partially invalid

- **WHEN** a core Provider produces accepted items and rejects one or more other normalized items
- **THEN** accepted items and rejection counters are retained, the Provider is partial, and core source incompleteness makes the Feed run fail rather than degrade

#### Scenario: Later provider work fails after valid evidence

- **WHEN** a core Provider retains accepted evidence from one sub-request, role, or page and later work fails or is incomplete
- **THEN** the retained evidence remains, the Provider is partial rather than healthy or wholly failed, and the Feed run fails without publication

#### Scenario: Later provider work is access denied after valid evidence

- **WHEN** a core Provider retains accepted evidence from one sub-request, role, or page and later work receives HTTP 401 or HTTP 403
- **THEN** the retained evidence and access-denial diagnostics remain, the Provider is partial and non-exempt, and the Feed run fails without publication

#### Scenario: Planned Provider is skipped

- **WHEN** a core Provider exists in the actual run plan but its terminal outcome is `skipped`
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

Social SHALL receive this same window and SHALL NOT add a per-account cursor, checkpoint, historical merge or recovery window. Accepted degraded publication with unavailable Social SHALL advance the one checkpoint normally; the missed Social interval SHALL not be automatically backfilled. Newly enabled accounts SHALL use the current global window, not receive an independent 72-hour bootstrap.

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

#### Scenario: Failed Social window is followed by success
- **WHEN** core publishes at T1 with Social unavailable for `[T0,T1)` and Social succeeds at T2
- **THEN** the next Social acquisition covers `[T1,T2)`, does not backfill `[T0,T1)`, and does not claim recovered historical coverage

### Requirement: Provider snapshot freshness is explicit and deterministic

For Social, a complete nonempty current-window slice SHALL be `fresh`, complete empty SHALL be `no_snapshot`, and unavailable acquisition SHALL be `not_evaluated`; carry provenance SHALL always be null. No age-based Social validity or `valid_unchanged` carry-forward SHALL be used.

Every newly generated Feed SHALL record exactly one semantic freshness result beside each planned Provider outcome in ascending `provider_id` order. The result SHALL use the resolved cadence and exactly one status: `fresh` for a current Provider slice within its cadence window, `valid_unchanged` for an unchanged carried slice that remains valid, `stale` for a current or carried slice beyond an age-bounded cadence window, `no_snapshot` for complete no-observation acquisition with no prior slice, or `not_evaluated` for incomplete acquisition. It SHALL record the originating embedded Provider-contract hash for a present slice and the immediately preceding validated `run_id` only when bytes were carried forward.

For weekly and scheduled cadence, evaluation SHALL compare `evidence_cutoff_at` with the latest authoritative payload-specific observation/effective time in the Provider slice and the declared validity window. For event-driven core cadence, a complete current check SHALL keep an unchanged carried slice valid without rewriting its source time. Invalid, missing, future, or ambiguous time authority SHALL fail validation rather than select a convenient timestamp. Freshness status SHALL be part of semantic Feed identity, but SHALL NOT independently rewrite Provider completeness or pipeline status.

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

- **WHEN** a complete event-driven core check finds no new observation and a validated prior slice exists
- **THEN** the prior slice remains `valid_unchanged` because the current successful check, not an invented age limit, establishes unchanged validity

#### Scenario: No prior snapshot exists

- **WHEN** acquisition is complete and contract-permitted empty but no validated prior Provider slice exists
- **THEN** the Provider freshness status is `no_snapshot` and no evidence is invented

### Requirement: Snapshot carry-forward is validation-gated and failure-isolated

The Feed MAY carry a core Provider slice only after complete current acquisition establishes that every accepted current item has an exact canonical semantic match under the same identity in the prior slice and the current active bundle has passed full schema, integrity, semantic identity, provenance, pipeline-consumability, and item validation. Carry-forward SHALL reuse the prior Provider items byte-for-byte in semantic form, including stable IDs, payloads, original source publication/update and knowledge times, provenance, and source lineage; it SHALL preserve the originating embedded Provider-contract hash and SHALL NOT merge successive slices into unbounded history. A current slice containing a new identity or changed canonical semantic content under an existing identity SHALL replace, rather than merge with, the prior slice.

Failed, partial, blocked, skipped, missing, duplicate, ambiguous, identity-mismatched, or non-permitted-empty current acquisition SHALL set freshness to `not_evaluated` and SHALL NOT consult retained evidence as a substitute. A blocked-exempt acquisition MAY produce a degraded publishable Feed without that Provider's prior slice; every other listed core condition SHALL retain source-incomplete pipeline failure and no-publication behavior. Absence or invalidity of the active bundle SHALL disable carry-forward without weakening current Provider outcome, availability, or coverage rules.

Social SHALL never carry a prior slice, including after a successful complete-empty check. Optional acquisition failure SHALL publish no Social evidence rather than consulting a previous bundle.

#### Scenario: Valid prior slice is carried

- **WHEN** current core Provider acquisition is complete with no new observation and the active bundle plus that Provider slice validate fully
- **THEN** the new candidate carries exactly the prior semantic items, records the prior `run_id`, and preserves their originating Provider-contract hash

#### Scenario: Prior bundle is invalid

- **WHEN** the active manifest, inventory, artifact, semantic identity, pipeline consumability, or prior Provider slice fails validation
- **THEN** no prior item is carried and current acquisition is evaluated without fallback

#### Scenario: Current acquisition fails with a previous snapshot

- **WHEN** current core Provider acquisition fails without blocked exemption while a prior valid Provider slice exists
- **THEN** the Provider remains failed with freshness `not_evaluated`, the pipeline remains source-incomplete, and the prior slice cannot convert the run into success or publication

#### Scenario: Current acquisition is blocked with a previous snapshot

- **WHEN** current Provider acquisition is blocked-exempt while a prior valid Provider slice exists
- **THEN** freshness is `not_evaluated`, no prior item is carried for that Provider, and the degraded Feed reports the current coverage unavailability

#### Scenario: New slice replaces prior slice

- **WHEN** complete acquisition returns an identity absent from the prior Provider slice or different canonical semantic content under an existing identity
- **THEN** the current Provider slice becomes the snapshot without unioning prior items into Feed history

#### Scenario: Social becomes empty after a prior nonempty window
- **WHEN** complete current Social acquisition has no eligible posts while a previous bundle has Social evidence
- **THEN** the current Social artifact is empty with no_snapshot and null carry provenance

### Requirement: GitHub-hosted repository-native Feed deployment

The repository SHALL define an active Feed job with credential-free core acquisition and optional session-authenticated Social acquisition on GitHub-hosted `ubuntu-latest` for `workflow_dispatch` and daily cron `20 0 * * *` (08:20 Asia/Shanghai). The job SHALL use the checked-out repository's explicit `feeds/` Feed product root and `.feed-state/` runtime-state root, with the repository as durable cross-run authority, require only the built-in repository publication credential with `contents: write` for core operation, and pass optional `WEIBO_COOKIE` only to the collection step, and use one non-cancelling concurrency group. It SHALL NOT require a self-hosted runner, external persistent filesystem, `FOLLOW_THE_MONEY_OUTPUT_ROOT`, or a custom mandatory default-off enable variable. The nominal schedule SHALL NOT determine `evidence_cutoff_at`; the existing Feed runtime SHALL capture the truthful cutoff after the job actually starts. Prepare, migration or arming publication, collection, finalization, diagnostics, and original-failure restoration SHALL remain explicitly ordered; bounded previous-bundle migration SHALL end without collection. The job SHALL generate and publish deterministic evidence only and SHALL NOT invoke Host-Agent reasoning, Audit, Event Structuring, or retained market/scoring capabilities.

After exact deployment finalization, a failed Feed step SHALL trigger an `always()` diagnostics presentation before the existing original-failure restoration remains final authority. The presentation SHALL select only known fields from transient Feed status, preserve existing Provider-outcome order, safely represent control characters, newlines, and Markdown-sensitive text, and bound human-facing message, warning, and error output. It SHALL write a concise failure report to Actions logs and `$GITHUB_STEP_SUMMARY` without re-evaluating completeness, coverage, health, publication, or exit category. Missing or corrupt transient status, unavailable summary output, or renderer failure SHALL produce at most a bounded diagnostics-unavailable notice and SHALL be non-gating: it SHALL NOT skip or alter finalization, turn a successful Feed into failure, replace an underlying Feed failure, or change the existing `.feed-exit-code` category `0`, `1`, or `2`. Transient diagnostics SHALL NOT be committed, added to durable Feed output, RateRegistry state, checkpoint, or deployment lease.

Backend absence or dependency provisioning failure SHALL become bounded Social unavailability inside the normal collection lifecycle, not abort the workflow before core collection. Backend execution SHALL not access repository publication credentials. No separate Social schedule or alert workflow SHALL be added. Current-digest limitations, not Actions job failure or an external channel, SHALL notify readers of accepted Social degradation.

#### Scenario: Daily hosted invocation

- **WHEN** GitHub schedules the repository Feed workflow from cron `20 0 * * *`
- **THEN** a non-cancelling `ubuntu-latest` job is eligible to establish repository state and run the Feed with credential-free core acquisition without a custom opt-in or external output root

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

#### Scenario: Optional backend cannot be provisioned
- **WHEN** core dependencies are ready but the approved external Social backend is unavailable
- **THEN** core collection and exact finalization remain eligible, Social is unavailable, and an accepted degraded Feed contains the facts required for current-digest disclosure

### Requirement: Production Provider set is closed and required

The shipped production Feed SHALL plan exactly Federal Reserve, BLS, PBOC, NBS, SSE, SZSE, SEC EDGAR, and CFTC as required credential-free core Providers, with `weibo_social` as the only approved optional credentialed extension. Provider manifests SHALL declare only payload types that their current adapters can emit within the six-domain contract. Yahoo Market and every `market_data`, `flow`, or `calendar` Provider declaration, activation, coverage claim, mapping, and acquisition path SHALL be absent.

#### Scenario: Shipped Provider plan is resolved

- **WHEN** production configuration and verified manifests are resolved
- **THEN** the eight required core Providers are planned, optional Weibo is planned exactly when enabled, and no Yahoo or other optional Provider path exists

#### Scenario: Provider declaration exceeds its adapter

- **WHEN** a manifest declares a payload type outside the adapter's implemented six-domain output
- **THEN** static resolution fails closed before Provider requests or runtime-state mutation

#### Scenario: Removed Provider is configured

- **WHEN** activation or coverage configuration names Yahoo Market or another removed Provider
- **THEN** startup rejects the configuration instead of ignoring it or restoring `market_data`

#### Scenario: Another credentialed Provider is declared
- **WHEN** a manifest or activation row introduces a credentialed Provider other than approved Weibo
- **THEN** startup rejects it rather than generalizing the Social exception

### Requirement: Five-domain migration is explicit and atomic

Migration SHALL accept only a fully validated immediate-previous logical/manifest major-5, artifact-major-2 five-domain bundle, and atomically activate a newly validated major-6, artifact-major-3 six-domain bundle through the existing manifest-led path. Major 4 and older SHALL no longer be migration inputs. Valid core evidence SHALL retain source semantics and stable item IDs; a structural empty Social artifact SHALL NOT fabricate evidence, acquisition success or current Social coverage. Pure migration SHALL occur only with `weibo_social` disabled for that operation, embedded truthfully as disabled, and SHALL perform zero Provider requests. It SHALL end before collection; enabled production Social SHALL require a subsequent real acquisition run. Product, checkpoint identity, durable rate state, lease and generated-state allowlists SHALL remain coherent under existing migration safety. Normal current consumption SHALL reject major 5.

#### Scenario: Existing eight-domain bundle is migrated
- **WHEN** an old eight-domain bundle is supplied to the current migration path
- **THEN** migration rejects it as older than the immediate-previous supported major rather than reviving removed domains

#### Scenario: Existing five-domain bundle is migrated
- **WHEN** a complete valid major-5 bundle enters migration with Social disabled
- **THEN** valid core evidence is projected into major 6, Social is structurally empty and not_configured, and no Social success is invented

#### Scenario: Social is enabled during pure migration
- **WHEN** a migration operation would label Social enabled without acquisition
- **THEN** it fails before activation instead of claiming an empty successful Social check

#### Scenario: Mixed domain generations are presented
- **WHEN** a six-domain manifest is combined with an old or different-generation artifact
- **THEN** bundle validation rejects the whole product

#### Scenario: Normal consumer receives the previous major
- **WHEN** normal current consumption receives logical or manifest major 5
- **THEN** it rejects the bundle rather than running migration implicitly

### Requirement: Multi-request failures preserve typed lifecycle and blocked-exemption evidence

The managed transport and bounded fetch helper SHALL preserve typed fetch-error retryability, concrete HTTP status, Retry-After, and actual response-observation metadata. Durable rate-state failures SHALL remain hard execution failures rather than ordinary Provider failures or retries. Each Provider outcome's `retrieved_at` SHALL reflect its last concrete response observation across requests, retries and acquisition units, or null if none occurred; a later no-response failure SHALL NOT advance or erase that observation. Response observations SHALL NOT become source time.

A terminal HTTP 401/403 after a successful terminal resource response in an unresolved acquisition unit or after accepted evidence from another unit SHALL be partial and non-exempt, even when normalization has not produced items. The outcome SHALL serialize existing `state = partial`, `availability = blocked`, the concrete HTTP status/reason, and `freshness.status = not_evaluated`; for core Providers pipeline status SHALL be failure and publication SHALL be forbidden. For Social, an approved optional acquisition failure SHALL instead discard the complete Provider candidate slice and permit only otherwise-valid degraded publication; durable-state or FTM integrity failures SHALL never use this exception. Successful resource progress SHALL survive unsuccessful retries of that unit until a complete retry resolves it. Counters SHALL NOT be fabricated to encode progress. A terminal incomplete company unit SHALL NOT be erased by later company success.

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

### Requirement: Feed v5 carries bounded official source content

New production SHALL emit logical Feed `schema_version = 6`. A `news`, `macro_release`, or `policy` payload MAY contain one closed `source_content` object with exactly non-empty `text`, `format`, `extraction_method`, `truncated`, and `document_sha256` fields. `format` SHALL be `plain_text`; `extraction_method` SHALL be `official_html_text_v1`; `truncated` SHALL be boolean; and `document_sha256` SHALL be the lowercase SHA-256 of the admitted raw detail-response body bytes without HTTP headers, retrieval time, execution metadata, or another runtime observation. The text SHALL be NFC-normalized deterministic plain text of at most 12,000 Unicode code points. Social, positioning, filing, `raw_metadata`, and `semantic_context` SHALL NOT carry source content.

Every serialized source-content field SHALL remain part of the item and therefore part of the canonical Feed semantic projection. Source content SHALL NOT create a new artifact, cache, checkpoint, or evidence authority.

#### Scenario: Official HTML content is admitted

- **WHEN** a supported Provider produces valid bounded official detail-document text
- **THEN** Feed v6 retains it in the matching payload's closed `source_content` object with its deterministic extraction provenance and raw-document digest

#### Scenario: Source content is placed outside its contract

- **WHEN** source content appears in `raw_metadata`, `semantic_context`, a social, positioning or filing payload, or another undeclared location
- **THEN** Feed validation rejects the candidate rather than treating it as reader evidence

#### Scenario: Source content exceeds its closed shape

- **WHEN** source content is empty, over 12,000 Unicode code points, non-NFC, uses an unknown format or extraction method, or carries a malformed document digest
- **THEN** Feed validation rejects the item before publication or consumption

### Requirement: Bounded canonical evidence and conservative deduplication

Normalized text SHALL use strict manifest-declared decoding, Unicode scalar values, NFC normalization, and bounded UTF-8 fields. A verified first-party official Provider MAY retain its schema-permitted bounded official document text as `source_content`; news-like items SHALL NOT retain full third-party copyrighted article bodies or text outside the closed source-content contract. Social SHALL retain only authorized attributed post and bounded reference text under its closed payload contract, not arbitrary linked article bodies. Distinct Social post identities SHALL NOT be collapsed by text similarity, and repeated same-ID captures with conflicting semantic contents SHALL fail acquisition rather than select an arbitrary survivor. Raw numeric tokens SHALL satisfy the existing lexical, digit, exponent, magnitude, sign, and unit-domain bounds before `Decimal` construction, and persisted financial values SHALL be canonical plain decimal strings without exponent or negative zero. Stable IDs and canonical URLs SHALL remove exact duplicates; existing core same-source near-deduplication SHALL remain unchanged while retaining independently originated cross-source reports and their source-lineage provenance. Social SHALL use only exact source post identity deduplication.

#### Scenario: Verified official document content is returned

- **WHEN** a Provider contract explicitly permits bounded first-party official source content and the detail document satisfies that contract
- **THEN** the Feed may retain only the closed normalized source-content evidence in addition to its existing typed fields

#### Scenario: Full article content is returned

- **WHEN** a Provider response contains a third-party copyrighted article body or text outside its applicable closed official source-content or authorized Social post contract
- **THEN** the Feed does not retain that body and rejects any payload that attempts to serialize it outside existing bounded evidence fields

#### Scenario: Numeric input is adversarial

- **WHEN** a raw numeric token exceeds the configured byte, significant-digit, exponent, magnitude, sign, or unit-domain bounds
- **THEN** it is rejected before `Decimal` arithmetic, hashing, or Feed publication

#### Scenario: Independent sources report one event

- **WHEN** two independent sources publish similar evidence at distinct canonical URLs
- **THEN** both items remain available for later corroboration rather than being collapsed as one origin

### Requirement: Feed v4 supports bounded Provider semantic contract evolution

New production SHALL emit Feed `schema_version = 6`. The checked-in SEC EDGAR manifest SHALL publish Provider `contract_version = 4`, the checked-in CFTC manifest SHALL publish Provider `contract_version = 2`, and Federal Reserve, PBOC, SSE and SZSE SHALL retain contract version 2, and BLS and NBS SHALL retain contract version 1. Manifest resolution and embedded-contract validation SHALL use an explicit Provider-specific supported-version set rather than a global maximum, a manifest hash, or implicit acceptance of arbitrary versions.

No major-4 bundle SHALL be accepted by current consumption or migration. Only Provider semantic compatibility already supported by a fully validated major-5 migration input SHALL be retained. A current consumer SHALL retain bounded read compatibility for structurally and semantically valid current items preserved through the bounded major-5 migration path carrying SEC Provider contract versions 1, 2, or 3 and CFTC Provider contract version 1. SEC contract version 2 items SHALL retain the complete required 13F semantic structure. SEC contract version 3 items SHALL retain the complete required `form13f` or `form4` subtype structure. SEC contract version 4 items SHALL carry a required closed filing subtype and satisfy the complete `form13f`, `form4`, or `beneficial_ownership` subtype contract. CFTC contract version 2 items SHALL contain the complete required COT semantic structure. Unknown fields, unsupported Provider/version combinations, malformed version declarations, and versioned items missing required semantics SHALL fail closed. New production SHALL NOT emit a legacy SEC v1/v2/v3 or CFTC v1 contract after the corresponding working manifest activation. Each checked-in manifest bump SHALL be atomic with its working semantic adapters, configuration, validation, verified fixtures, request bounds, and compatibility path.

#### Scenario: Existing v4 Provider-v1 bundle is read

- **WHEN** a valid previous-major-5 bundle entering explicit migration embeds SEC or CFTC Provider contract version 1 and uses the bounded legacy payload shape
- **THEN** the current consumer validates it without requiring newer semantic fields

#### Scenario: Existing SEC v2 bundle is read

- **WHEN** a valid previous-major-5 bundle entering explicit migration embeds SEC Provider contract version 2 with the complete existing 13F semantic structure
- **THEN** the current consumer validates it without requiring a filing subtype or Form 4 fields

#### Scenario: Existing SEC v3 bundle is read

- **WHEN** a valid previous-major-5 bundle entering explicit migration embeds SEC Provider contract version 3 with a complete `form13f` or `form4` payload
- **THEN** the current consumer validates it without requiring beneficial-ownership fields or SEC-v4 configuration

#### Scenario: SEC v2 semantics are absent

- **WHEN** a supported migrated item belongs to an embedded SEC contract version 2 but omits any required 13F semantic structure
- **THEN** Feed validation rejects the bundle

#### Scenario: SEC v3 subtype semantics are absent

- **WHEN** a supported migrated item belongs to an embedded SEC contract version 3 but omits its filing subtype or the complete semantics required by that subtype
- **THEN** Feed validation rejects the bundle

#### Scenario: SEC v4 subtype semantics are absent

- **WHEN** a supported migrated item belongs to an embedded SEC contract version 4 but omits its filing subtype or the complete semantics required by that subtype
- **THEN** Feed validation rejects the bundle

#### Scenario: CFTC v2 semantics are absent

- **WHEN** a supported migrated item belongs to an embedded CFTC contract version 2 but omits any required COT semantic structure
- **THEN** Feed validation rejects the bundle

#### Scenario: Versioned semantic item is complete

- **WHEN** a supported migrated SEC or CFTC item matches its embedded supported contract version and all required typed semantic and provenance fields
- **THEN** Feed validation accepts the item without requiring a Feed major-version change

#### Scenario: Unknown semantic field is supplied

- **WHEN** a versioned semantic payload contains a field outside its closed schema
- **THEN** Feed validation rejects the item rather than treating the field as untyped metadata

#### Scenario: Unsupported Provider version is embedded

- **WHEN** a bundle or checked-in manifest declares a Provider contract version outside the explicit supported set for that Provider
- **THEN** resolution or consumption fails closed without using the contract hash to select behavior

### Requirement: New News, Macro, and Policy evidence carries validated semantic context

Every newly acquired Feed v6 item whose payload discriminator is `news`, `macro_release`, or `policy` SHALL carry exactly one `semantic_context` matching that domain and the retained payload/source facts. The six currently emitting Provider paths SHALL be covered according to their existing output contracts: Federal Reserve and PBOC policy; BLS, NBS, SSE, and SZSE news; and NBS macro releases. Existing domain classification SHALL remain unchanged, including BLS releases and unstructured NBS releases remaining `news` unless a separate Provider-contract change authorizes another payload type.

Semantic enrichment SHALL run after existing source extraction and payload normalization and before item admission. It SHALL perform no Provider request, historical Feed lookup, credential access, orchestration, or payload reclassification. A required context construction or validation failure SHALL reject the item through the existing Provider outcome and publication boundary rather than publish evidence without its required context.

Positioning and filing items SHALL retain their existing typed payload semantics; Social SHALL use its separately declared closed payload. None SHALL acquire `semantic_context`. Existing core Provider manifests, embedded Provider contract versions, payload-type declarations, coverage, freshness, and acquisition behavior SHALL remain unchanged by this Social extension.

A fully validated legacy Provider slice preserved through a fully validated major-5 migration input MAY continue to omit context only when the existing snapshot contract carries that complete slice byte-for-byte and records its prior run in non-null `freshness.carried_forward_from_run_id`. The independently evaluated freshness status MAY be `valid_unchanged` or `stale` according to the existing cadence window. The Producer SHALL NOT rewrite carried item bytes merely to add context. The next complete current slice that replaces that legacy slice SHALL require context on every affected-domain item it contains; partial, failed, or blocked work SHALL NOT be used as a migration trigger or fallback.

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

- **WHEN** a social, positioning or filing item contains `semantic_context`
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

### Requirement: Feed v4 retains bounded legacy reads across semantic-context activation

New production SHALL emit Feed `schema_version = 6`. The current consumer SHALL accept an otherwise valid major-6 bundle migrated from a fully validated major-5 input whose `news`, `macro_release`, and `policy` items predate ECO-130 and omit `semantic_context`. When `semantic_context` is present on an affected legacy or current item, the consumer SHALL validate its entire closed shape and consistency with the item; it SHALL NOT ignore malformed, mismatched, unknown, or analytical context.

This bounded omission compatibility SHALL apply only to reading legacy evidence preserved by that bounded major-5 migration and to the exact non-null `carried_forward_from_run_id` exception above, including carried `valid_unchanged` and `stale` slices. Newly acquired or replacement affected-domain items SHALL still require context before publication, and no Provider contract-version bump or hash-based behavior selection SHALL be introduced to distinguish old and new items.

#### Scenario: Legacy v4 item omits context

- **WHEN** the current consumer reads an otherwise valid major-6 bundle migrated from a fully validated major-5 input containing an affected-domain item without `semantic_context`
- **THEN** validation accepts the legacy omission under the bounded read path

#### Scenario: Present legacy context is malformed

- **WHEN** any current or migrated affected-domain item contains `semantic_context` with a mismatched domain, inconsistent payload fact, unknown member, or forbidden analytical meaning
- **THEN** validation rejects the bundle rather than treating context as optional untyped metadata

#### Scenario: New production omits context

- **WHEN** the current Producer attempts to publish a newly acquired or replacement affected-domain item without `semantic_context`
- **THEN** pre-publication validation fails even though the bounded consumer path can read a legacy omission

#### Scenario: Old bundle is supplied outside migration
- **WHEN** a major-4 bundle or a major-5 bundle outside the explicit migration path is presented
- **THEN** version validation rejects it before any legacy semantic-context omission exception is considered

## ADDED Requirements

### Requirement: Optional Social failures use a closed externally validated taxonomy

Approved Social acquisition unavailability SHALL use one of `credential_unavailable`, `credential_rejected`, `backend_unavailable`, `upstream_blocked`, `account_unavailable`, `acquisition_incomplete`, or `deadline_exceeded` as its sanitized availability reason. Credential rejection and upstream blocking SHALL require corresponding source observations; an unclassified upstream acquisition failure SHALL use `acquisition_incomplete`, not a guessed diagnosis. Unexpected internal exceptions SHALL remain hard failures and SHALL NOT be caught as upstream acquisition failures. Social failure SHALL retain truthful availability (`blocked` only with observed HTTP 401/403, otherwise `failed`), no published Social items, and `not_evaluated` freshness. The embedded Feed contract SHALL record the no-automatic-backfill policy so downstream disclosure is Feed-derived. Successful Social outcomes SHALL have a null failure reason and valid complete or complete-empty evidence. Provider outcome counters SHALL remain truthful observations, never copy the backend's undercounted request statistic or imply that discarded candidates were published.

Normal consumers SHALL validate the same approved optional-failure distinctions as producers from embedded contracts. A reason string alone SHALL NOT authorize degradation of a malformed outcome, missing identity, invalid canonical evidence or hard execution failure. Core Providers SHALL retain their existing reason and blocked-exemption semantics.

#### Scenario: Optional acquisition fails with a supported reason
- **WHEN** core gates pass and valid Social outcome evidence supports an approved failure classification
- **THEN** producer and consumer agree that the zero-Social-slice Feed is degraded and that its missing window will not be automatically backfilled

#### Scenario: Internal defect is disguised as optional failure
- **WHEN** a Social candidate has invalid normalized evidence, inconsistent identity or missing required outcome data despite an allowed reason string
- **THEN** producer and consumer reject it rather than trusting the reason string
