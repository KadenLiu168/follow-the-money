## MODIFIED Requirements

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
- **THEN** the Feed makes zero Provider network requests, performs no normal collection work, does not create or mutate rate-registry state, and does not publish or replace `feeds/latest.json`

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
- **THEN** the Feed makes zero Provider network requests, performs no normal collection work, does not create or mutate rate-registry state, and does not publish or replace `feeds/latest.json`

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
- **THEN** the run acquires the runtime-state-root collection lock and durably debits and reconciles rate state exactly as a publishing run, while creating or replacing no `feeds/latest.json` product and not advancing the checkpoint

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
- **THEN** publication removes reversible staging files and fails typed `pre_commit_deadline_exceeded` before replacing `feeds/latest.json`

#### Scenario: Commit crosses the nominal deadline
- **WHEN** a candidate is fully staged and admitted by second 285 but durable replacement completes after second 300
- **THEN** commit finishes without cancellation or rollback and reports the overrun only outside the immutable Feed payload

### Requirement: Explicit degradation and coverage outcomes
One Provider failure SHALL NOT stop collection already planned for other Providers. The Feed SHALL record attempted, succeeded, empty, partially valid, failed, skipped, fetched, accepted, and rejected outcomes. Provider membership for completeness assessment SHALL derive only from the actual resolved run plan, and the resolved Provider contract SHALL be the sole authority for `empty_valid_for_window`; disabled Providers and unverified mappings excluded from that plan SHALL create no completeness obligation.

Every planned Provider SHALL have exactly one unambiguous terminal outcome matching its planned Provider identity. A planned Provider SHALL be complete only when its outcome is `healthy`, or when its outcome is `empty` and its resolved `empty_valid_for_window` contract is true. A `failed`, `partial`, or `skipped` outcome, a non-permitted `empty` outcome, or a missing, duplicate, ambiguous, or identity-mismatched terminal outcome SHALL be incomplete. Accepted and fetched item counts SHALL NOT determine Provider completeness.

Mandatory coverage SHALL count only complete planned Providers that belong to the configured group. A contract-permitted empty Provider SHALL count toward the configured minimum without contributing an evidence item; an incomplete Provider SHALL not count. Existing optional-group semantics SHALL remain unchanged. Any incomplete planned Provider or deficient mandatory coverage group SHALL produce `pipeline.status = failure` regardless of evidence returned by other Providers. A provider SHALL be `partial` when it retains accepted evidence but also has rejected items or incomplete later sub-request, role, or page work; retained valid evidence and outcome counters SHALL remain available for diagnostics but SHALL NOT make the failed run publishable.

The total accepted evidence count and final `items` length SHALL NOT independently determine pipeline health. When every planned Provider is complete, mandatory coverage is satisfied, and all existing non-source hard-failure boundaries succeed, the Feed SHALL remain eligible for the existing healthy or otherwise accepted non-source status even when `items` is empty. Planned source incompleteness SHALL NOT produce `degraded`; existing degraded semantics unrelated to source acquisition completeness SHALL remain available and no new degraded condition is introduced. Provider-specific and coverage-group warnings SHALL identify every source-completeness cause used to fail the pipeline.

#### Scenario: One provider fails and another succeeds
- **WHEN** one planned Provider fails or times out while another contributes valid evidence
- **THEN** the Feed run fails, exits non-zero, retains both Provider outcomes for diagnostics, and does not replace the previous valid `feeds/latest.json`

#### Scenario: Mandatory group is deficient with accepted evidence
- **WHEN** the pipeline accepts at least one valid item but fewer complete planned Provider outcomes contribute than a non-optional coverage group's minimum
- **THEN** the Feed run fails, exits non-zero, does not publish, and identifies the deficient coverage group

#### Scenario: Permitted empty contributes to coverage
- **WHEN** a provider returns no accepted item and its `empty_valid_for_window` contract is true
- **THEN** its `empty` outcome contributes to coverage without contributing an accepted evidence item

#### Scenario: Non-permitted empty does not contribute to coverage
- **WHEN** a planned Provider reaches `empty` and its `empty_valid_for_window` contract is false
- **THEN** the Provider is incomplete, contributes no coverage, and makes the Feed run fail regardless of evidence from other Providers

#### Scenario: Every provider returns no accepted item
- **WHEN** every planned Provider reaches `healthy` or contract-permitted `empty`, mandatory coverage is satisfied, all other hard-failure boundaries succeed, and the final Feed has `items: []`
- **THEN** zero accepted evidence does not fail the run and the empty Feed remains eligible for normal successful publication

#### Scenario: An item is partially invalid
- **WHEN** a provider produces accepted items and rejects one or more other normalized items
- **THEN** accepted items and rejection counters are retained, the Provider is partial, and source incompleteness makes the Feed run fail rather than degrade

#### Scenario: Later provider work fails after valid evidence
- **WHEN** a provider retains accepted evidence from one sub-request, role, or page and later work fails or is incomplete
- **THEN** the retained evidence remains, the Provider is partial rather than healthy or wholly failed, and the Feed run fails without publication

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

#### Scenario: Partial provider cannot satisfy full coverage
- **WHEN** a partial provider belongs to a mandatory coverage group
- **THEN** it contributes no full mandatory coverage even though its accepted items remain usable in the failed Feed candidate

### Requirement: Durable monotonic publication
Before publication, only a healthy or degraded candidate SHALL be admitted and SHALL pass Feed schema, semantic, provenance, identity, digest, and canonical-byte validation. A failure candidate SHALL NOT be passed to the publication subsystem. Publication SHALL stage only the candidate for `feeds/latest.json` as an unpredictable same-parent file, use create-only staging, file and directory `fsync`, validate current ownership immediately before commit, atomically replace `feeds/latest.json`, and `fsync` its parent directory. It SHALL use the maximum `(evidence_cutoff_at, content_digest)` tuple for latest ownership independently of candidate submission order, SHALL accept an already-current matching semantic identity idempotently while retaining its existing valid canonical bytes, and SHALL reject stale or conflicting ownership without changing the current product. It SHALL NOT create a `feeds/daily/**` artifact. Publication failure or durability uncertainty SHALL remain an execution failure and SHALL NOT be reported as degraded success or fabricate rollback guarantees.

#### Scenario: Valid candidate publishes
- **WHEN** a healthy or degraded candidate passes validation and durable filesystem primitives are available
- **THEN** `feeds/latest.json` is atomically replaced with the candidate's canonical bytes and no `feeds/daily/**` artifact is created

#### Scenario: Failure candidate is not admitted
- **WHEN** pipeline assessment produces `failure`
- **THEN** orchestration does not call the publication subsystem and leaves the previous valid `feeds/latest.json` unchanged

#### Scenario: Latest replacement fails
- **WHEN** atomic replacement of `feeds/latest.json` fails
- **THEN** the previous valid latest remains unchanged, no other Feed product is created, and the run exits `1` as a publication failure

#### Scenario: Publication fails before commit
- **WHEN** a healthy or degraded candidate is admitted but publication fails before atomic replacement
- **THEN** the run exits `1`, removes reversible staging files, and leaves the previous valid `feeds/latest.json` unchanged

#### Scenario: Publication fails before replacement
- **WHEN** candidate staging, validation, ownership checking, commit admission, or rename fails before `feeds/latest.json` is replaced
- **THEN** the run exits `1`, removes reversible staging files, and leaves the previous valid `feeds/latest.json` unchanged

#### Scenario: Latest durability becomes uncertain after replacement
- **WHEN** atomic replacement succeeds but the required parent-directory `fsync` fails
- **THEN** the run exits `1`, does not claim rollback or durable success, and does not advance the checkpoint

#### Scenario: Stale candidate reaches publication
- **WHEN** an older valid externally prepared candidate is submitted after a newer `feeds/latest.json`
- **THEN** publication rejects it without changing `feeds/latest.json` or creating another Feed product

#### Scenario: Equal-cutoff variants arrive in either order
- **WHEN** two valid candidates have the same `evidence_cutoff_at`, different `content_digest` values, and are submitted in either order
- **THEN** `feeds/latest.json` deterministically contains the candidate with the lexicographically greater canonical `content_digest`, and the losing submission creates no Feed product

### Requirement: Minimal internal Feed entry outcomes
Exactly one minimal internal Feed entry SHALL expose configuration, explicit Feed product root, explicit runtime-state root, deterministic clock/window injection, status output, and `--dry-run`. Healthy or degraded success, including a source-complete Feed with zero accepted evidence, SHALL exit `0`. Planned source incompleteness and typed planning, collection, runtime, checkpoint, migration, validation, integrity, deadline, rate-state, filesystem, publication, or durability failure SHALL exit `1`; usage, configuration, invalid explicit input, or startup-capability rejection SHALL exit `2`. Expected exit categories SHALL derive from explicit types or typed outcomes, never message text. Dry-run SHALL execute the same fetch, normalize, validation, coverage, source-completeness, and pipeline-health decision as publication mode while omitting `feeds/latest.json` publication and checkpoint advancement.

For a source-completeness failure, existing transient status, command output, and workflow logs SHALL expose the responsible Provider's `provider_id`, terminal `state`, existing error or message when present, and relevant warnings by reusing the existing Provider outcome. A transient deployment status for a completed failed Feed SHALL preserve the existing result `message` and `warnings` plus the existing serialized Provider outcomes in their deterministic order, including `provider_id`, `state`, `error`, `attempted`, `fetched`, `accepted`, and `rejected` when available. A typed input or execution failure without completed Provider outcomes SHALL expose its existing message and deterministic warnings, if any, and SHALL NOT fabricate or infer Provider facts. This reporting SHALL NOT parse message or warning text to reconstruct structured outcomes, introduce a second Provider-failure domain model, add a Feed schema field, create a new tracked failure artifact, or add a transient path to the repository generated-state allowlist.

#### Scenario: Degraded Feed succeeds
- **WHEN** a degraded candidate remains valid for an existing condition unrelated to planned source acquisition completeness and dry-run or publication completes
- **THEN** the entry exits `0` while machine-readable status and stderr identify the degradation

#### Scenario: Failure dry run exits nonzero
- **WHEN** dry-run completes assessment with an incomplete planned Provider or deficient mandatory coverage and pipeline status `failure`
- **THEN** the entry exits `1`, reports the failure status, responsible Provider outcomes, and warnings, and creates or replaces no `feeds/latest.json`

#### Scenario: Failure publication run exits nonzero
- **WHEN** publication mode completes assessment with pipeline status `failure`
- **THEN** the entry exits `1` without invoking publication or exposing a success product path

#### Scenario: Input and execution errors use misleading words
- **WHEN** typed input and execution failures contain arbitrary words associated with the opposite category
- **THEN** their exits remain respectively `2` and `1` based only on type or typed outcome

#### Scenario: Dry run is requested for usable evidence
- **WHEN** `--dry-run` is set and assessment produces healthy or degraded status
- **THEN** the entry validates and reports the candidate with exit `0` without changing `feeds/latest.json` or checkpoint state, while any real Provider sends still obey lock and durable rate-state contracts

#### Scenario: Source-complete empty Feed publishes normally
- **WHEN** every planned Provider is complete, mandatory coverage and existing hard-failure checks succeed, publication mode produces `items: []`, and durable publication succeeds
- **THEN** the entry exits `0`, atomically replaces `feeds/latest.json`, advances the matching checkpoint, and retains the current cutoff, Provider outcomes, and normal deterministic identity metadata

#### Scenario: Source failure diagnostics are transient
- **WHEN** source completeness fails with Provider error details or warnings available in existing outcomes
- **THEN** transient status preserves the existing failure message, warnings, and serialized Provider outcomes for command and hosted presentation without adding a repository-persisted failure or status artifact

#### Scenario: Typed failure has no completed Provider outcomes
- **WHEN** a typed input or execution failure occurs before a completed failed Feed result exists
- **THEN** transient status preserves only the failure status, existing message, and deterministic warnings available at that boundary without fabricating Provider identity or outcomes

### Requirement: Canonical serializer owns published Feed bytes
Every `feeds/latest.json` byte sequence passed to publication SHALL equal the shared `canonical_bytes()` serialization of its validated Feed object. Feed-producing modules SHALL NOT use independent JSON serializer settings for published Feed bytes.

#### Scenario: Feed is serialized for publication
- **WHEN** a valid healthy or degraded Feed is admitted to publication
- **THEN** its latest candidate bytes are produced by the shared canonical serializer and are byte-identical to `canonical_bytes(feed)`

### Requirement: Publication is idempotent by semantic identity
When `feeds/latest.json` already contains a valid canonical Feed with the candidate's semantic `run_id`, `content_digest`, and cutoff, publication SHALL retain the existing latest bytes and report accepted idempotent ownership even when excluded execution-audit metadata makes the candidate bytes differ. A byte-identical duplicate SHALL follow the same idempotent path. An invalid current latest, conflicting bytes under equal ownership, stale ownership, or a different semantic identity SHALL fail closed or follow deterministic monotonic ownership as applicable without creating another Feed product. Existing atomic latest replacement, monotonic ownership, canonical-byte, and `fsync` durability requirements SHALL remain unchanged.

#### Scenario: Same semantic Feed runs with different audit timing
- **WHEN** a later execution has the same semantic `run_id`, `content_digest`, and cutoff as the current valid `feeds/latest.json` but different truthful audit timestamps
- **THEN** publication retains the current valid latest bytes and reports idempotent accepted ownership

#### Scenario: Byte-identical Feed is submitted again
- **WHEN** the exact canonical bytes already stored in `feeds/latest.json` are submitted again
- **THEN** publication performs no replacement, reports idempotent accepted ownership, and creates no additional product

#### Scenario: Idempotent recovery repairs latest
- **WHEN** a duplicate semantic candidate reaches publication while the current valid `feeds/latest.json` already carries that identity
- **THEN** publication accepts the existing latest as the recovered product owner without reading or creating a dated artifact

#### Scenario: Same path carries different semantic identity
- **WHEN** `feeds/latest.json` is invalid or claims the candidate's ownership tuple with incompatible semantic identity
- **THEN** publication fails closed without overwriting the current file

#### Scenario: Current latest has incompatible equal ownership
- **WHEN** `feeds/latest.json` is invalid or claims the candidate's ownership tuple with incompatible semantic identity
- **THEN** publication fails closed without overwriting the current file

### Requirement: Exact allowlisted repository finalization
The workflow SHALL execute safety-state finalization after any controlled Feed outcome and SHALL stage only explicitly resolved generated-state paths under the separately resolved roots. Runtime safety state SHALL consist only of the persistence marker, RateRegistry registry, registered scope files, and deployment lease; the checkpoint SHALL be separate successful-continuity state, and `feeds/latest.json` SHALL be the only successful Feed product state. On Feed success, finalization SHALL validate the successful status and `feeds/latest.json`, require checkpoint `previous_success.run_id` and `evidence_cutoff_at` to exactly match both, and make one non-force fast-forward commit containing exact resulting runtime safety state, terminal success lease, matching checkpoint, and `feeds/latest.json`. On controlled Feed failure after Provider work, finalization SHALL commit exact resulting RateRegistry files and terminal failure lease but SHALL NOT stage a changed checkpoint or any Feed product; the Feed failure SHALL remain the workflow result even when safety-state persistence succeeds.

Ephemeral collection locks, temporary and staging files, `feed-status.json`, local run bundles, debug/failure workspaces, `feeds/daily/**`, and unrelated repository paths SHALL remain outside every generated-state allowlist. If final commit or push fails, conflicts, or the runner disappears, the remote `in_progress` lease SHALL remain the conservative recovery signal; the workflow SHALL NOT force push, destructively reset, or claim rollback of possibly sent requests or locally committed product/checkpoint state.

#### Scenario: Successful Feed finalization
- **WHEN** Feed execution succeeds, checkpoint and status identity/cutoff match the valid `feeds/latest.json`, and exact local state can be fast-forward published
- **THEN** one allowlisted final commit contains terminal success, exact RateRegistry state, the matching checkpoint, and `feeds/latest.json`, with no `feeds/daily/**` path staged

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
- **WHEN** finalization finds transient generated files, `feeds/daily/**`, or unrelated worktree changes
- **THEN** it stages none of them and publishes only the explicit generated-state allowlist for that outcome

#### Scenario: Success identity or cutoff does not match
- **WHEN** successful status, checkpoint previous-success, or `feeds/latest.json` differ by `run_id` or `evidence_cutoff_at`
- **THEN** finalization fails closed without publishing a success commit

### Requirement: Generated-state commits avoid recursive full CI
The normal CI workflow SHALL exclude pushes whose changed paths consist only of accepted `.feed-state/` durable generated state and `feeds/latest.json`. `feeds/daily/**/*.json` and legacy runtime paths under `feeds/` SHALL NOT remain steady-state CI exclusions. A push containing any other path, including code, configuration, Provider contracts, schemas, tests, workflows, OpenSpec, documentation, dated Feed paths, or unexpected runtime/transient state, SHALL remain eligible for the full normal CI suite. This distinction SHALL be path-based and SHALL NOT rely solely on commit-message conventions.

#### Scenario: Generated-state-only push
- **WHEN** a workflow commit changes only accepted `.feed-state/` durable files and `feeds/latest.json`
- **THEN** that push does not recursively invoke the full normal CI workflow

#### Scenario: Mixed generated and source push
- **WHEN** a push changes an accepted generated-state path and any non-generated path
- **THEN** the full normal CI workflow remains eligible to run

#### Scenario: Dated Feed path changes
- **WHEN** a push adds, changes, or removes a path under `feeds/daily/**`
- **THEN** the path is not treated as accepted steady-state generated output and the full normal CI workflow remains eligible to run

#### Scenario: Legacy runtime paths change during migration
- **WHEN** the one-time migration commit deletes legacy runtime files beneath `feeds/`
- **THEN** normal CI may run because steady-state exclusions describe only the accepted post-migration architecture

### Requirement: Versioned Feed continuity checkpoint
The repository-backed runtime-state root SHALL contain one closed, versioned `feed-checkpoint.json` whose only continuity value is `previous_success`. The supported version SHALL represent `previous_success` explicitly as either `null` or an object containing exactly the RFC 3339 UTC `evidence_cutoff_at` and successful Feed `run_id`. Unknown fields, unsupported versions, malformed JSON, invalid timestamps, invalid run identities, and missing checkpoints in an established runtime-state root SHALL fail closed before Provider network. The checkpoint SHALL NOT contain Feed items, Provider outcomes, coverage, diagnostics, configuration snapshots, RateRegistry data, HTTP history, or Agent state and SHALL NOT alter the consumer Feed schema or semantic Feed configuration snapshot.

After an accepted non-dry-run Feed publication has durably established `feeds/latest.json` ownership, the run SHALL atomically advance the checkpoint to the successful Feed identity before releasing the runtime-state lock. The checkpoint SHALL NOT advance for dry-run, source incompleteness, typed execution failure, candidate validation failure, publication failure, durability uncertainty, stale ownership, or any result that did not establish accepted latest ownership. If checkpoint persistence fails after Feed publication, execution SHALL fail without claiming rollback; the checkpoint MAY lag a published product but MUST NOT lead it.

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
- **WHEN** a healthy or accepted degraded Feed durably establishes accepted `feeds/latest.json` ownership
- **THEN** the checkpoint advances atomically to exactly that Feed's `evidence_cutoff_at` and `run_id`

#### Scenario: Dry run does not advance continuity
- **WHEN** `--dry-run` completes with healthy or degraded assessment after any real Provider sends
- **THEN** RateRegistry state is reconciled normally but the checkpoint remains unchanged

#### Scenario: Failed or uncertain publication does not advance continuity
- **WHEN** execution fails before accepted latest ownership, a stale candidate is rejected, or publication durability is unknown
- **THEN** the checkpoint does not advance

#### Scenario: Checkpoint persistence fails after Feed publication
- **WHEN** `feeds/latest.json` publication succeeds but atomic checkpoint persistence fails
- **THEN** execution fails, preserves the already committed product state, and leaves continuity conservatively lagging rather than claiming rollback or advancing without persistence
