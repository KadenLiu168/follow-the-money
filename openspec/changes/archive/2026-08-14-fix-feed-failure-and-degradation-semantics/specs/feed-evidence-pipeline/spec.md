## MODIFIED Requirements

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
coverage. With at least one accepted item, any enabled-provider degradation or
deficient non-optional coverage group SHALL produce `degraded`; otherwise complete
mandatory coverage and no enabled-provider degradation SHALL produce `healthy`.
Zero accepted items SHALL produce `failure` regardless of permitted-empty outcomes,
and a failure candidate SHALL NOT be published or replace the last valid latest
Feed. Provider-specific and coverage-group warnings SHALL identify every cause used
to degrade the pipeline.

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

## ADDED Requirements

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
