## MODIFIED Requirements

### Requirement: Explicit degradation and coverage outcomes
One Provider failure SHALL NOT stop collection already planned for other Providers. The Feed SHALL record attempted, succeeded, empty, partially valid, failed, skipped, fetched, accepted, and rejected outcomes. Provider membership for completeness assessment SHALL derive only from the actual resolved run plan, and the resolved Provider contract SHALL be the sole authority for `empty_valid_for_window`; disabled Providers and unverified mappings excluded from that plan SHALL create no completeness obligation.

Every planned Provider SHALL have exactly one unambiguous terminal outcome matching its planned Provider identity. A planned Provider SHALL be complete only when its outcome is `healthy`, or when its outcome is `empty` and its resolved `empty_valid_for_window` contract is true. A `failed`, `partial`, or `skipped` outcome, a non-permitted `empty` outcome, or a missing, duplicate, ambiguous, or identity-mismatched terminal outcome SHALL be incomplete. Accepted and fetched item counts SHALL NOT determine Provider completeness.

Mandatory coverage SHALL count only complete planned Providers that belong to the configured group. A contract-permitted empty Provider SHALL count toward the configured minimum without contributing an evidence item; an incomplete Provider SHALL not count. Existing optional-group semantics SHALL remain unchanged. Any incomplete planned Provider or deficient mandatory coverage group SHALL produce `pipeline.status = failure` regardless of evidence returned by other Providers. A provider SHALL be `partial` when it retains accepted evidence but also has rejected items or incomplete later sub-request, role, or page work; retained valid evidence and outcome counters SHALL remain available for diagnostics but SHALL NOT make the failed run publishable.

The total accepted evidence count and final `items` length SHALL NOT independently determine pipeline health. When every planned Provider is complete, mandatory coverage is satisfied, and all existing non-source hard-failure boundaries succeed, the Feed SHALL remain eligible for the existing healthy or otherwise accepted non-source status even when `items` is empty. Planned source incompleteness SHALL NOT produce `degraded`; existing degraded semantics unrelated to source acquisition completeness SHALL remain available and no new degraded condition is introduced. Provider-specific and coverage-group warnings SHALL identify every source-completeness cause used to fail the pipeline.

#### Scenario: One provider fails and another succeeds
- **WHEN** one planned Provider fails or times out while another contributes valid evidence
- **THEN** the Feed run fails, exits non-zero, retains both Provider outcomes for diagnostics, and does not publish a dated Feed or replace the previous valid latest Feed

#### Scenario: Mandatory group is deficient with accepted evidence
- **WHEN** the pipeline accepts at least one valid item but fewer complete planned Provider outcomes contribute than a non-optional coverage group's minimum
- **THEN** the Feed run fails, exits non-zero, does not publish, and identifies the deficient coverage group

#### Scenario: Permitted empty contributes to coverage
- **WHEN** a planned Provider returns no accepted item, reaches `empty`, and its resolved `empty_valid_for_window` contract is true
- **THEN** that complete Provider contributes to every configured coverage group it belongs to without contributing an accepted evidence item

#### Scenario: Non-permitted empty does not contribute to coverage
- **WHEN** a planned Provider reaches `empty` and its resolved `empty_valid_for_window` contract is false
- **THEN** the Provider is incomplete, contributes no coverage, and makes the Feed run fail regardless of evidence from other Providers

#### Scenario: Every provider returns no accepted item
- **WHEN** every planned Provider reaches `healthy` or contract-permitted `empty`, mandatory coverage is satisfied, all other hard-failure boundaries succeed, and the final Feed has `items: []`
- **THEN** zero accepted evidence does not fail the run and the empty Feed remains eligible for normal successful publication

#### Scenario: An item is partially invalid
- **WHEN** a planned Provider produces accepted items and rejects one or more other normalized items
- **THEN** accepted items and rejection counters are retained, the Provider is partial, and source incompleteness makes the Feed run fail rather than degrade

#### Scenario: Later provider work fails after valid evidence
- **WHEN** a planned Provider retains accepted evidence from one sub-request, role, or page and later work fails or is incomplete
- **THEN** the retained evidence remains, the Provider is partial rather than healthy or wholly failed, and the Feed run fails without publication

#### Scenario: Partial provider cannot satisfy full coverage
- **WHEN** a partial planned Provider belongs to a mandatory coverage group
- **THEN** it contributes no mandatory coverage even though its accepted items and outcome remain available in the failed candidate for diagnostics

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

### Requirement: Fixed advancing Feed window
After acquiring the collection lock, the run SHALL read and validate the current latest Feed, capture one `evidence_cutoff_at` before provider requests, and publish a strictly advancing half-open `[window.start, evidence_cutoff_at)` interval. The first run SHALL use the bounded bootstrap lookback; later runs SHALL advance from the prior valid cutoff subject to the configured maximum gap, including when that prior valid Feed contains `items: []`. Equal or earlier cutoffs, unreadable or invalid existing latest state, look-ahead evidence, and invalid timestamp ordering SHALL fail closed before provider calls or publication as their phase requires. Deadlines SHALL use monotonic time while persisted instants use RFC 3339 UTC with Asia/Shanghai schedule metadata.

#### Scenario: Existing latest Feed is invalid
- **WHEN** `feeds/latest.json` exists but fails schema, semantic, digest, run-ID, or embedded-contract validation
- **THEN** planning fails typed `invalid_latest_integrity` with zero provider calls and no new dated or latest artifact

#### Scenario: Cutoff does not advance
- **WHEN** the captured cutoff is equal to or earlier than the current valid latest cutoff
- **THEN** planning returns typed `non_advancing_cutoff` before any provider call or artifact write

#### Scenario: Collection finishes after cutoff
- **WHEN** collection completes several minutes after the fixed cutoff
- **THEN** the Feed preserves the original cutoff and records later collection timestamps without claiming later evidence coverage

#### Scenario: Successful empty Feed advances the next window
- **WHEN** a source-complete empty Feed is successfully published as `latest.json`
- **THEN** the next run derives `window.start` from that Feed's newer `evidence_cutoff_at` rather than reusing the preceding older cutoff

### Requirement: Minimal internal Feed entry outcomes
Exactly one minimal internal Feed entry SHALL expose configuration, explicit output root, deterministic clock/window injection, status output, and `--dry-run`. Healthy or degraded success, including a source-complete Feed with zero accepted evidence, SHALL exit `0`. Planned source incompleteness and typed planning, collection, runtime, validation, integrity, deadline, rate-state, filesystem, publication, or durability failure SHALL exit `1`; usage, configuration, invalid explicit input, or startup-capability rejection SHALL exit `2`. Expected exit categories SHALL derive from explicit types or typed outcomes, never message text. Dry-run SHALL execute the same fetch, normalize, validation, coverage, source-completeness, and pipeline-health decision as publication mode while omitting dated and latest Feed publication.

For a source-completeness failure, existing transient status, command output, and workflow logs SHALL expose the responsible Provider's `provider_id`, terminal `state`, existing error or message when present, and relevant warnings by reusing the existing Provider outcome. This reporting SHALL NOT introduce a second Provider-failure domain model, a new tracked failure artifact, or a transient path in the repository generated-state allowlist.

#### Scenario: Degraded Feed succeeds
- **WHEN** a degraded candidate remains valid for an existing condition unrelated to planned source acquisition completeness and dry-run or publication completes
- **THEN** the entry exits `0` while machine-readable status and stderr identify the degradation

#### Scenario: Failure dry run exits nonzero
- **WHEN** dry-run completes assessment with an incomplete planned Provider or deficient mandatory coverage and pipeline status `failure`
- **THEN** the entry exits `1`, reports the failure status, responsible Provider outcomes, and warnings, and creates no dated or latest Feed artifact

#### Scenario: Failure publication run exits nonzero
- **WHEN** publication mode completes assessment with pipeline status `failure`
- **THEN** the entry exits `1` without invoking publication or exposing success artifact paths

#### Scenario: Input and execution errors use misleading words
- **WHEN** typed input and execution failures contain arbitrary words associated with the opposite category
- **THEN** their exits remain respectively `2` and `1` based only on type or typed outcome

#### Scenario: Dry run is requested for usable evidence
- **WHEN** `--dry-run` is set and assessment produces healthy or degraded status
- **THEN** the entry validates and reports the candidate with exit `0` without changing dated or latest Feed artifacts, while any real provider sends still obey lock and durable rate-state contracts

#### Scenario: Source-complete empty Feed publishes normally
- **WHEN** every planned Provider is complete, mandatory coverage and existing hard-failure checks succeed, publication mode produces `items: []`, and durable publication succeeds
- **THEN** the entry exits `0`, publishes a schema-valid dated Feed, replaces `latest.json`, and retains the current cutoff, Provider outcomes, and normal deterministic identity metadata

#### Scenario: Source failure diagnostics are transient
- **WHEN** source completeness fails with Provider error details or warnings available in existing outcomes
- **THEN** command status and logs identify the responsible Provider and cause without adding a repository-persisted failure or status artifact
