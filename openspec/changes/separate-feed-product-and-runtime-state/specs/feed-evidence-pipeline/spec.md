## ADDED Requirements

### Requirement: Versioned Feed continuity checkpoint
The repository-backed runtime-state root SHALL contain one closed, versioned `feed-checkpoint.json` whose only continuity value is `previous_success`. The supported version SHALL represent `previous_success` explicitly as either `null` or an object containing exactly the RFC 3339 UTC `evidence_cutoff_at` and successful Feed `run_id`. Unknown fields, unsupported versions, malformed JSON, invalid timestamps, invalid run identities, and missing checkpoints in an established runtime-state root SHALL fail closed before Provider network. The checkpoint SHALL NOT contain Feed items, Provider outcomes, coverage, diagnostics, configuration snapshots, RateRegistry data, HTTP history, or Agent state and SHALL NOT alter the consumer Feed schema or semantic Feed configuration snapshot.

After an accepted non-dry-run Feed publication has durably established both the dated artifact and `feeds/latest.json`, the run SHALL atomically advance the checkpoint to the successful Feed identity before releasing the runtime-state lock. The checkpoint SHALL NOT advance for dry-run, source incompleteness, typed execution failure, candidate validation failure, publication failure, durability uncertainty, or any result that did not establish latest ownership. If checkpoint persistence fails after Feed publication, execution SHALL fail without claiming rollback; the checkpoint MAY lag a published product but MUST NOT lead it.

#### Scenario: Runtime state has no previous successful Feed
- **WHEN** a genuine bootstrap or legacy migration without `feeds/latest.json` establishes the runtime-state root
- **THEN** it durably writes a supported checkpoint with `previous_success: null` before Provider work is permitted

#### Scenario: Successful Feed checkpoint is valid
- **WHEN** a checkpoint contains the supported version and exactly one valid prior successful cutoff and run identity
- **THEN** runtime planning accepts that previous-success state without reading a consumer Feed artifact

#### Scenario: Established checkpoint is unavailable or invalid
- **WHEN** an established runtime-state root has a missing checkpoint, partial or malformed JSON, an unknown field or version, a malformed timestamp, or a malformed run identity
- **THEN** execution fails closed before Provider network and does not reinterpret the state as a first Feed

#### Scenario: Accepted publication advances continuity
- **WHEN** a healthy or accepted degraded Feed durably publishes its dated artifact and successfully establishes `feeds/latest.json` ownership
- **THEN** the checkpoint advances atomically to exactly that Feed's `evidence_cutoff_at` and `run_id`

#### Scenario: Dry run does not advance continuity
- **WHEN** `--dry-run` completes with healthy or degraded assessment after any real Provider sends
- **THEN** RateRegistry state is reconciled normally but the checkpoint remains unchanged

#### Scenario: Failed or uncertain publication does not advance continuity
- **WHEN** execution fails before accepted latest ownership or publication durability is unknown
- **THEN** the checkpoint does not advance even if an immutable dated artifact may already exist

#### Scenario: Checkpoint persistence fails after Feed publication
- **WHEN** dated/latest Feed publication succeeds but atomic checkpoint persistence fails
- **THEN** execution fails, preserves the already committed product state, and leaves continuity conservatively lagging rather than claiming rollback or advancing without persistence

### Requirement: Deterministic legacy runtime-state migration
Before normal hosted arming, repository state SHALL be classified as a complete new layout, a complete legacy runtime layout with no new layout, no established layout, or mixed/partial/corrupt/unsupported state. A complete legacy layout SHALL enter a one-time zero-network migration that validates the existing persistence marker, RateRegistry registry, every registered scope, policy compatibility, deployment lease, and recovery information through their authoritative parsers and preserves exact token, refill-anchor, last-dispatch, cooldown, policy-fingerprint, scope-identity, lease-state, Feed-start, and recovery semantics. Only metadata explicitly bound to the old runtime root MAY be normalized to make relocated state truthful.

Migration SHALL move exact durable runtime files from `feeds/` to the runtime-state root, seed the checkpoint from a supported integrity-validated healthy or degraded `feeds/latest.json` when present or explicit `previous_success: null` when absent, leave consumer Feed products untouched, and SHALL NOT scan `feeds/daily/**` for another authority. It SHALL stage only the exact new durable additions and exact legacy runtime deletions, publish them through the existing non-force fast-forward boundary, make zero Provider requests, and end without arming or collecting. Mixed old/new authority, partial state, corrupt or missing registered state, invalid legacy latest when present, incompatible policy, and unsupported versions SHALL fail closed before Provider network without bootstrap, reset, force push, or destructive recovery.

#### Scenario: Complete legacy state migrates
- **WHEN** the new runtime-state layout is absent and every authoritative legacy runtime file is complete, valid, and mutually consistent
- **THEN** migration relocates the exact durable state, removes only the exact legacy runtime paths, publishes the explicit migration allowlist, performs zero Provider requests, and exits before arming

#### Scenario: Legacy latest seeds previous success
- **WHEN** complete legacy runtime state includes a valid supported healthy or degraded `feeds/latest.json`
- **THEN** migration seeds the checkpoint from exactly that Feed's `evidence_cutoff_at` and `run_id` while leaving latest and dated Feed products untouched

#### Scenario: Legacy latest is absent
- **WHEN** complete legacy runtime state has no `feeds/latest.json`
- **THEN** migration seeds `previous_success: null` and does not scan dated history for another cutoff

#### Scenario: Legacy rate and recovery semantics are preserved
- **WHEN** valid legacy state carries token, dispatch, cooldown, policy, scope, bootstrap, or in-progress lease and recovery values
- **THEN** migration preserves those semantic values and the next invocation remains subject to the original recovery boundary

#### Scenario: Mixed or partial layouts fail closed
- **WHEN** old and new authoritative state coexist unexpectedly or either layout is partial, corrupt, unsupported, incompatible, or internally inconsistent
- **THEN** preflight performs zero Provider requests and does not bootstrap, migrate a subset, reset rate state, or arm collection

#### Scenario: Migration stages exact paths only
- **WHEN** migration completes while transient or unrelated worktree files also exist
- **THEN** only exact new durable runtime-state additions and exact legacy runtime-state deletions are staged, with Feed products and unrelated files left untouched

## MODIFIED Requirements

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
- **THEN** the run acquires the runtime-state-root collection lock and durably debits and reconciles rate state exactly as a publishing run, while creating no dated or latest Feed artifact and not advancing the checkpoint

#### Scenario: Product and runtime roots are distinct
- **WHEN** production orchestration resolves configuration
- **THEN** it explicitly materializes the Feed product root and runtime-state root independently so product validation cannot target runtime state and runtime-state validation cannot target Feed products

### Requirement: Fixed advancing Feed window
After acquiring the runtime-state collection lock, the run SHALL load and validate previous-success state exclusively from the runtime checkpoint, capture one `evidence_cutoff_at` before Provider requests, and publish a strictly advancing half-open `[window.start, evidence_cutoff_at)` interval. Explicit null previous success SHALL use the bounded bootstrap lookback; later runs SHALL advance from the checkpoint cutoff subject to the configured maximum gap, including when the corresponding prior successful Feed contained `items: []`. Equal or earlier cutoffs, missing or invalid established checkpoint state, look-ahead evidence, and invalid timestamp ordering SHALL fail closed before Provider calls or publication as their phase requires. Exact-threshold and over-threshold gap handling and coverage-gap reporting SHALL remain unchanged. Deadlines SHALL use monotonic time while persisted instants use RFC 3339 UTC with Asia/Shanghai schedule metadata. Steady-state planning SHALL NOT read or validate `feeds/latest.json` as continuity authority.

#### Scenario: Existing latest Feed is invalid
- **WHEN** steady-state planning has a valid checkpoint while `feeds/latest.json` is absent or fails product integrity validation
- **THEN** planning still derives its window from the checkpoint and leaves product integrity rejection to the existing publication or consumption boundary

#### Scenario: Cutoff does not advance
- **WHEN** the captured cutoff is equal to or earlier than the current valid checkpoint cutoff
- **THEN** planning returns typed `non_advancing_cutoff` before any provider call or artifact write

#### Scenario: Collection finishes after cutoff
- **WHEN** collection completes several minutes after the fixed cutoff
- **THEN** the Feed preserves the original cutoff and records later collection timestamps without claiming later evidence coverage

#### Scenario: Successful empty Feed advances the next window
- **WHEN** a source-complete empty Feed is successfully published as `latest.json` and recorded in the checkpoint
- **THEN** the next run derives `window.start` from that checkpoint's newer `evidence_cutoff_at` rather than reusing the preceding older cutoff

#### Scenario: No previous success uses bounded bootstrap
- **WHEN** a valid checkpoint explicitly contains `previous_success: null`
- **THEN** planning uses the existing bounded bootstrap lookback without reading latest or dated Feed products

#### Scenario: Gap reaches or exceeds the configured threshold
- **WHEN** the checkpoint cutoff produces a gap exactly at or beyond the configured maximum
- **THEN** planning preserves the existing exact-threshold, bounded-gap/bootstrap, and coverage-gap behavior

### Requirement: Minimal internal Feed entry outcomes
Exactly one minimal internal Feed entry SHALL expose configuration, explicit Feed product root, explicit runtime-state root, deterministic clock/window injection, status output, and `--dry-run`. Healthy or degraded success, including a source-complete Feed with zero accepted evidence, SHALL exit `0`. Planned source incompleteness and typed planning, collection, runtime, checkpoint, migration, validation, integrity, deadline, rate-state, filesystem, publication, or durability failure SHALL exit `1`; usage, configuration, invalid explicit input, or startup-capability rejection SHALL exit `2`. Expected exit categories SHALL derive from explicit types or typed outcomes, never message text. Dry-run SHALL execute the same fetch, normalize, validation, coverage, source-completeness, and pipeline-health decision as publication mode while omitting dated/latest Feed publication and checkpoint advancement.

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
- **THEN** the entry validates and reports the candidate with exit `0` without changing dated/latest Feed artifacts or checkpoint state, while any real Provider sends still obey lock and durable rate-state contracts

#### Scenario: Source-complete empty Feed publishes normally
- **WHEN** every planned Provider is complete, mandatory coverage and existing hard-failure checks succeed, publication mode produces `items: []`, and durable publication succeeds
- **THEN** the entry exits `0`, publishes a schema-valid dated Feed, replaces `latest.json`, advances the matching checkpoint, and retains the current cutoff, Provider outcomes, and normal deterministic identity metadata

#### Scenario: Source failure diagnostics are transient
- **WHEN** source completeness fails with Provider error details or warnings available in existing outcomes
- **THEN** transient status preserves the existing failure message, warnings, and serialized Provider outcomes for command and hosted presentation without adding a repository-persisted failure or status artifact

#### Scenario: Typed failure has no completed Provider outcomes
- **WHEN** a typed input or execution failure occurs before a completed failed Feed result exists
- **THEN** transient status preserves only the failure status, existing message, and deterministic warnings available at that boundary without fabricating Provider identity or outcomes

### Requirement: GitHub-hosted repository-native Feed deployment
The repository SHALL define an active credential-free Feed job on GitHub-hosted `ubuntu-latest` for `workflow_dispatch` and daily cron `20 0 * * *` (08:20 Asia/Shanghai). The job SHALL use the checked-out repository's explicit `feeds/` Feed product root and `.feed-state/` runtime-state root, with the repository as durable cross-run authority, require only the built-in repository publication credential with `contents: write`, and use one non-cancelling concurrency group. It SHALL NOT require a self-hosted runner, external persistent filesystem, `FOLLOW_THE_MONEY_OUTPUT_ROOT`, or a custom mandatory default-off enable variable. The nominal schedule SHALL NOT determine `evidence_cutoff_at`; the existing Feed runtime SHALL capture the truthful cutoff after the job actually starts. Prepare, migration or arming publication, collection, finalization, diagnostics, and original-failure restoration SHALL remain explicitly ordered; migration-only mode SHALL end without collection. The job SHALL generate and publish deterministic evidence only and SHALL NOT invoke Host-Agent reasoning, Audit, Event Structuring, or retained market/scoring capabilities.

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
An `in_progress` remote lease in either a validated legacy layout being migrated or the established runtime-state root SHALL mean that the previous ephemeral runner may have sent Provider requests whose exact resulting local RateRegistry state was lost. Its deterministic `recovery_not_before` SHALL conservatively include the latest workflow-permitted Feed start, the existing configured Feed command deadline, and the configured RateRegistry crash cooldown; lease creation time plus crash cooldown alone or an unenforced Provider-time estimate SHALL NOT establish recovery safety. Migration SHALL preserve the original lease state and bounds and SHALL NOT arm Provider work. Before that boundary, a later run SHALL make zero Provider requests and SHALL NOT reset or weaken the last committed registry state.

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

### Requirement: Exact allowlisted repository finalization
The workflow SHALL execute safety-state finalization after any controlled Feed outcome and SHALL stage only explicitly resolved generated-state paths under the separately resolved roots. Runtime safety state SHALL consist only of the persistence marker, RateRegistry registry, registered scope files, and deployment lease; the checkpoint SHALL be separate successful-continuity state, and dated/latest Feed files SHALL be successful product state. On Feed success, finalization SHALL validate the successful status and checkpoint, require checkpoint `previous_success.run_id` and `evidence_cutoff_at` to exactly match the successful Feed status, and make one non-force fast-forward commit containing exact resulting runtime safety state, terminal success lease, matching checkpoint, successful run-scoped dated Feed, and `feeds/latest.json`. On controlled Feed failure after Provider work, finalization SHALL commit exact resulting RateRegistry files and terminal failure lease but SHALL NOT stage a changed checkpoint or any Feed product; the Feed failure SHALL remain the workflow result even when safety-state persistence succeeds.

Ephemeral collection locks, temporary and staging files, `feed-status.json`, local run bundles, debug/failure workspaces, and unrelated repository paths SHALL remain outside every generated-state allowlist. If final commit or push fails, conflicts, or the runner disappears, the remote `in_progress` lease SHALL remain the conservative recovery signal; the workflow SHALL NOT force push, destructively reset, or claim rollback of possibly sent requests or locally committed product/checkpoint state.

#### Scenario: Successful Feed finalization
- **WHEN** Feed execution succeeds, checkpoint and status identity/cutoff match, and exact local state can be fast-forward published
- **THEN** one allowlisted final commit contains terminal success, exact RateRegistry state, the matching checkpoint, successful dated artifact, and `feeds/latest.json`

#### Scenario: Controlled Feed failure after Provider work
- **WHEN** Feed execution fails after Provider work and the runner remains able to finalize
- **THEN** one allowlisted final commit persists exact RateRegistry state and terminal failure without staging a locally changed checkpoint or adding or promoting a Feed product, and the workflow remains failed

#### Scenario: Final publication fails or conflicts
- **WHEN** the final generated-state commit cannot be fast-forward pushed
- **THEN** the workflow fails and remote `in_progress` remains authoritative for conservative recovery

#### Scenario: Runner disappears before finalization
- **WHEN** the runner terminates after the durable lease and before terminal state reaches the remote repository
- **THEN** the next invocation treats the remote lease as incomplete and follows its recovery boundary

#### Scenario: Unrelated or transient files exist
- **WHEN** finalization finds transient generated files or unrelated worktree changes
- **THEN** it stages none of them and publishes only the explicit generated-state allowlist for that outcome

#### Scenario: Success identity or cutoff does not match
- **WHEN** successful status and checkpoint previous-success `run_id` or `evidence_cutoff_at` differ
- **THEN** finalization fails closed without publishing a success commit

### Requirement: Generated-state commits avoid recursive full CI
The normal CI workflow SHALL exclude pushes whose changed paths consist only of accepted `.feed-state/` durable generated state, `feeds/latest.json`, and `feeds/daily/**/*.json`. Legacy runtime paths under `feeds/` SHALL NOT remain steady-state CI exclusions solely for migration compatibility. A push containing any other path, including code, configuration, Provider contracts, schemas, tests, workflows, OpenSpec, documentation, or unexpected runtime/transient state, SHALL remain eligible for the full normal CI suite. This distinction SHALL be path-based and SHALL NOT rely solely on commit-message conventions.

#### Scenario: Generated-state-only push
- **WHEN** a workflow commit changes only accepted `.feed-state/` durable files and accepted latest or dated Feed products
- **THEN** that push does not recursively invoke the full normal CI workflow

#### Scenario: Mixed generated and source push
- **WHEN** a push changes an accepted generated-state path and any non-generated path
- **THEN** the full normal CI workflow remains eligible to run

#### Scenario: Legacy runtime paths change during migration
- **WHEN** the one-time migration commit deletes legacy runtime files beneath `feeds/`
- **THEN** normal CI may run because steady-state exclusions describe only the accepted post-migration architecture
