## ADDED Requirements

### Requirement: GitHub-hosted repository-native Feed deployment
The repository SHALL define an active credential-free Feed job on GitHub-hosted `ubuntu-latest` for `workflow_dispatch` and daily cron `20 0 * * *` (08:20 Asia/Shanghai). The job SHALL use the checked-out repository's `feeds/` directory as the Feed output root and the repository as the durable cross-run state authority, require only the built-in repository publication credential with `contents: write`, and use one non-cancelling concurrency group. It SHALL NOT require a self-hosted runner, external persistent filesystem, `FOLLOW_THE_MONEY_OUTPUT_ROOT`, or a custom mandatory default-off enable variable. The nominal schedule SHALL NOT determine `evidence_cutoff_at`; the existing Feed runtime SHALL capture the truthful cutoff after the job actually starts. The job SHALL generate and publish deterministic evidence only and SHALL NOT invoke Host-Agent reasoning, Audit, Event Structuring, or retained market/scoring capabilities.

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

### Requirement: Repository bootstrap and durable pre-network lease
After checkout and before normal network-capable execution, deployment preflight SHALL load the authoritative checked-in configuration and resolve enabled verified Provider contracts through the existing resolution boundary. Static resolution failure SHALL make zero Provider requests and SHALL NOT create or mutate normal deployment or rate state. A repository without an authoritative RateRegistry baseline SHALL use the existing RateRegistry first-use lifecycle to establish the registry, persistence marker, and every currently enabled scope, persist a bootstrap recovery boundary, fast-forward push that explicit state, perform zero Provider requests, and block collection until the configured crash-cooldown quiet boundary has elapsed.

For every later network-capable run, repository state SHALL contain a minimal versioned `in_progress` deployment lease and all newly required scope state before the first possible Provider request. The lease SHALL identify the deployment run and its arming/start/recovery bounds, but SHALL NOT contain token balances, cooldown values, last-dispatch values, policy fingerprints, Provider evidence, HTTP history, or Agent state. Provider work SHALL begin only after the allowlisted lease and state have been committed and fast-forward pushed to the remote branch and only within the lease's enforced Feed-start bound. A pre-network commit or push failure, non-fast-forward conflict, or missed Feed-start bound SHALL cause zero Provider requests; the workflow SHALL NOT force push or destructively reset the remote branch.

#### Scenario: Static deployment preflight fails
- **WHEN** authoritative configuration, enabled Provider resolution, deployment compatibility, repository RateRegistry, or lease validation fails before arming
- **THEN** the run performs zero Provider requests, does not enter normal Feed execution, and does not create or mutate normal rate or lease state

#### Scenario: Clean repository bootstrap
- **WHEN** valid resolved Provider contracts exist but the repository has no authoritative repository-backed RateRegistry baseline
- **THEN** the run durably establishes the existing registry, marker, current scope states, and bootstrap recovery boundary in the repository and exits without any Provider request

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

### Requirement: Conservative incomplete-run recovery envelope
An `in_progress` remote lease SHALL mean that the previous ephemeral runner may have sent Provider requests whose exact resulting local RateRegistry state was lost. Its deterministic `recovery_not_before` SHALL conservatively include the latest workflow-permitted Feed start, the existing configured Feed command deadline, and the configured RateRegistry crash cooldown; lease creation time plus crash cooldown alone or an unenforced Provider-time estimate SHALL NOT establish recovery safety. Before that boundary, a later run SHALL make zero Provider requests and SHALL NOT reset or weaken the last committed registry state.

After the boundary, the run MAY reuse the last committed exact RateRegistry state only when static validation of the authoritative currently enabled resolved Provider contracts proves, for every distinct rate scope, that the configured crash cooldown is at least both the scope's complete token-refill period and its minimum dispatch interval. The validation SHALL derive scopes and policies from resolved contracts without hard-coded Provider IDs. Existing RateRegistry refill, eligibility, migration, debit, refund, and reconcile behavior SHALL remain authoritative; recovery SHALL NOT synthesize token balances or introduce a second rate-state model. Missing, corrupt, unsupported, or incompatible registry or lease state SHALL fail closed.

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
- **WHEN** an established repository has a missing, corrupt, unknown-version, or internally inconsistent registry, scope state, or lease
- **THEN** hosted execution fails before Provider network without silently bootstrapping over the established state

### Requirement: Exact allowlisted repository finalization
The workflow SHALL execute safety-state finalization after any controlled Feed outcome and SHALL stage only explicitly resolved generated-state paths. On Feed success, one final non-force fast-forward commit SHALL contain the exact resulting RateRegistry registry and per-scope files, persistence marker when required, terminal success lease, successful run-scoped dated Feed, and `feeds/latest.json`. On controlled Feed failure after Provider work, finalization SHALL commit the exact resulting RateRegistry files and terminal failure lease but SHALL NOT fabricate or promote a successful Feed; the Feed failure SHALL remain the workflow result even when safety-state persistence succeeds.

Ephemeral collection locks, temporary and staging files, `feed-status.json`, local run bundles, debug/failure workspaces, and unrelated repository paths SHALL remain outside the generated-state allowlist. If final commit or push fails, conflicts, or the runner disappears, the remote `in_progress` lease SHALL remain the conservative recovery signal; the workflow SHALL NOT force push, destructively reset, or claim rollback of possibly sent requests.

#### Scenario: Successful Feed finalization
- **WHEN** Feed execution succeeds and exact local state can be fast-forward published
- **THEN** one allowlisted final commit contains terminal success, exact RateRegistry state, the successful dated artifact, and `feeds/latest.json`

#### Scenario: Controlled Feed failure after Provider work
- **WHEN** Feed execution fails after Provider work and the runner remains able to finalize
- **THEN** one allowlisted final commit persists exact RateRegistry state and terminal failure without adding or promoting a successful Feed, and the workflow remains failed

#### Scenario: Final publication fails or conflicts
- **WHEN** the final generated-state commit cannot be fast-forward pushed
- **THEN** the workflow fails and remote `in_progress` remains authoritative for conservative recovery

#### Scenario: Runner disappears before finalization
- **WHEN** the runner terminates after the durable lease and before terminal state reaches the remote repository
- **THEN** the next invocation treats the remote lease as incomplete and follows its recovery boundary

#### Scenario: Unrelated or transient files exist
- **WHEN** finalization finds transient generated files or unrelated worktree changes
- **THEN** it stages none of them and publishes only the explicit generated-state allowlist for that outcome

### Requirement: Generated-state commits avoid recursive full CI
The normal CI workflow SHALL exclude pushes whose changed paths consist only of the accepted generated Feed, RateRegistry, persistence-marker, and deployment-lease allowlist. A push containing any other path, including code, configuration, Provider contracts, schemas, tests, workflows, OpenSpec, or documentation, SHALL remain eligible for the full normal CI suite. This distinction SHALL be path-based and SHALL NOT rely solely on commit-message conventions.

#### Scenario: Generated-state-only push
- **WHEN** a workflow commit changes only accepted generated Feed, rate, marker, and lease paths
- **THEN** that push does not recursively invoke the full normal CI workflow

#### Scenario: Mixed generated and source push
- **WHEN** a push changes an accepted generated-state path and any non-generated path
- **THEN** the full normal CI workflow remains eligible to run

## MODIFIED Requirements

### Requirement: Feed deployment workflow acceptance includes Actions semantics
The accepted Feed deployment workflow SHALL be valid under GitHub Actions workflow-definition and expression/context semantics. The authoritative pre-merge path SHALL evaluate the repository's real workflows with an established Actions-aware validator in addition to repository-specific hosted deployment, state ordering, explicit staging, failure-finalization, Git safety, and generated-commit CI checks. Hosted Feed runner selection SHALL remain scheduler-enforced through `runs-on: ubuntu-latest`, without an unavailable workflow-level context or redundant runtime runner guard.

#### Scenario: Accepted Feed deployment workflow
- **WHEN** the repository's real GitHub Actions workflows are evaluated by the authoritative Actions-aware validator
- **THEN** they pass workflow-definition and expression/context validation while the project-specific hosted Feed deployment and generated-commit CI invariants also pass

#### Scenario: Unavailable context is used
- **WHEN** a workflow uses a GitHub Actions context at a workflow key where that context is unavailable
- **THEN** authoritative pre-merge workflow validation fails and the invalid workflow cannot satisfy repository acceptance

#### Scenario: Dedicated Feed runner is selected
- **WHEN** GitHub Actions schedules a Feed generation job
- **THEN** the job is assigned through `runs-on: ubuntu-latest` without requiring self-hosted labels or a later runtime label check
