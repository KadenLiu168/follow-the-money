## MODIFIED Requirements

### Requirement: Minimal internal Feed entry outcomes
Exactly one minimal internal Feed entry SHALL expose configuration, explicit output root, deterministic clock/window injection, status output, and `--dry-run`. Healthy or degraded success, including a source-complete Feed with zero accepted evidence, SHALL exit `0`. Planned source incompleteness and typed planning, collection, runtime, validation, integrity, deadline, rate-state, filesystem, publication, or durability failure SHALL exit `1`; usage, configuration, invalid explicit input, or startup-capability rejection SHALL exit `2`. Expected exit categories SHALL derive from explicit types or typed outcomes, never message text. Dry-run SHALL execute the same fetch, normalize, validation, coverage, source-completeness, and pipeline-health decision as publication mode while omitting dated and latest Feed publication.

For a source-completeness failure, existing transient status, command output, and workflow logs SHALL expose the responsible Provider's `provider_id`, terminal `state`, existing error or message when present, and relevant warnings by reusing the existing Provider outcome. A transient deployment status for a completed failed Feed SHALL preserve the existing result `message` and `warnings` plus the existing serialized Provider outcomes in their deterministic order, including `provider_id`, `state`, `error`, `attempted`, `fetched`, `accepted`, and `rejected` when available. A typed input or execution failure without completed Provider outcomes SHALL expose its existing message and deterministic warnings, if any, and SHALL NOT fabricate or infer Provider facts. This reporting SHALL NOT parse message or warning text to reconstruct structured outcomes, introduce a second Provider-failure domain model, add a Feed schema field, create a new tracked failure artifact, or add a transient path to the repository generated-state allowlist.

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
- **THEN** transient status preserves the existing failure message, warnings, and serialized Provider outcomes for command and hosted presentation without adding a repository-persisted failure or status artifact

#### Scenario: Typed failure has no completed Provider outcomes
- **WHEN** a typed input or execution failure occurs before a completed failed Feed result exists
- **THEN** transient status preserves only the failure status, existing message, and deterministic warnings available at that boundary without fabricating Provider identity or outcomes

### Requirement: GitHub-hosted repository-native Feed deployment
The repository SHALL define an active credential-free Feed job on GitHub-hosted `ubuntu-latest` for `workflow_dispatch` and daily cron `20 0 * * *` (08:20 Asia/Shanghai). The job SHALL use the checked-out repository's `feeds/` directory as the Feed output root and the repository as the durable cross-run state authority, require only the built-in repository publication credential with `contents: write`, and use one non-cancelling concurrency group. It SHALL NOT require a self-hosted runner, external persistent filesystem, `FOLLOW_THE_MONEY_OUTPUT_ROOT`, or a custom mandatory default-off enable variable. The nominal schedule SHALL NOT determine `evidence_cutoff_at`; the existing Feed runtime SHALL capture the truthful cutoff after the job actually starts. The job SHALL generate and publish deterministic evidence only and SHALL NOT invoke Host-Agent reasoning, Audit, Event Structuring, or retained market/scoring capabilities.

After exact deployment finalization, a failed Feed step SHALL trigger an `always()` diagnostics presentation before the existing original-failure restoration remains final authority. The presentation SHALL select only known fields from transient Feed status, preserve existing Provider-outcome order, safely represent control characters, newlines, and Markdown-sensitive text, and bound human-facing message, warning, and error output. It SHALL write a concise failure report to Actions logs and `$GITHUB_STEP_SUMMARY` without re-evaluating completeness, coverage, health, publication, or exit category. Missing or corrupt transient status, unavailable summary output, or renderer failure SHALL produce at most a bounded diagnostics-unavailable notice and SHALL be non-gating: it SHALL NOT skip or alter finalization, turn a successful Feed into failure, replace an underlying Feed failure, or change the existing `.feed-exit-code` category `0`, `1`, or `2`. Transient diagnostics SHALL NOT be committed, added to durable Feed output, RateRegistry state, or the deployment lease.

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

#### Scenario: Failed hosted collection exposes existing facts
- **WHEN** the hosted Feed step fails after producing a transient status with an existing message, warnings, and Provider outcomes
- **THEN** exact finalization runs first and an always-run diagnostics presentation exposes the selected bounded facts in Actions logs and `$GITHUB_STEP_SUMMARY` before original Feed failure restoration

#### Scenario: Hosted diagnostics are unavailable
- **WHEN** transient status is missing or corrupt, summary output is unavailable, or diagnostics rendering otherwise cannot produce full detail
- **THEN** diagnostics remains non-gating, emits at most a bounded unavailable notice, and neither hides nor replaces the Feed or finalization result

#### Scenario: Successful hosted Feed needs no failure report
- **WHEN** the hosted Feed step succeeds as healthy or degraded accepted output
- **THEN** failure diagnostics do not change the successful path, publication, finalization, or exit `0`
