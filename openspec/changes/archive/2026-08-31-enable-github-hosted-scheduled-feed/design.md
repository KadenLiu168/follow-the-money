## Context

See `proposal.md` for motivation and `specs/feed-evidence-pipeline/spec.md` for behavior. The existing Feed already loads and resolves checked-in Provider contracts before normal execution, coordinates one output root, persists exact RateRegistry state before each possible send, publishes directly beneath its output root, and reports the successful Asia/Shanghai dated path in `feed-status.json`. The remaining failure window is outside that process: an ephemeral hosted runner can disappear after a Provider send but before Git publishes the locally updated registry.

The repository currently ignores Feed artifacts and contains no repository-backed RateRegistry baseline. The existing workflow instead guards an external persistent root before checkout, copies successful artifacts into `feeds/`, and stages only those two artifacts. ECO-62 must change this deployment boundary without changing Feed bytes, Provider dispatch, RateRegistry serialization, or Agent behavior.

## Goals / Non-Goals

**Goals:**

- Make `feeds/` the single runtime and publication root for the hosted job.
- Add the smallest repository-level state machine that conservatively encloses ephemeral-runner loss.
- Make every network-capable run remotely visible as uncertain before Provider work and exact again after controlled completion.
- Keep Git operations optimistic, non-force, auditable, and restricted to generated-state paths.
- Make bootstrap, recovery, conflicts, controlled failure, and publication failure testable without live Provider network.

**Non-Goals:**

- Changing RateRegistry state or transitions, Feed deadlines/schema/identity, Provider contracts, or publication algorithms.
- Importing arbitrary external/self-hosted state or keeping two output trees synchronized.
- Providing a general workflow framework, distributed lock, transaction log, Provider-request Git commit, or public CLI.
- Invoking Host-Agent, Audit, Event Structuring, Market Analytics and State, Confidence and Watchlist, or Scoring and Ranking.

## Decisions

### 1. Use `feeds/` directly and track only cross-run truth

The hosted job passes `--output-root feeds` to the existing Feed. This removes the external-root copy step and lets the Feed's current atomic publication and Asia/Shanghai dated-path behavior remain authoritative.

The durable tree is limited to:

- `feeds/.follow-the-money-persistent`
- `feeds/rate-registry.json`
- the exact `feeds/scope-<digest>.json` files named by the registry
- `feeds/feed-run-lease.json`
- `feeds/latest.json` and, on success, the exact `dated_relative_path` reported by `feed-status.json`

`.gitignore` will continue to exclude `.collection.lock`, temporary/staging files, status files, run bundles, and failure/debug workspaces while allowing the durable paths above. The deployment helper resolves a concrete path list for each commit; neither `git add .`, `git add -A`, nor a broad `feeds/**` stage is permitted.

Alternative rejected: keep an external runtime root and copy into `feeds/`. It preserves the ephemeral-state loss window and maintains two trees for one contract.

### 2. Add one private, deployment-specific helper

Add one internal module under `follow_the_money.feed` for bootstrap, lease validation/transitions, recovery-envelope validation, direct invocation of the existing Feed entry, and allowlisted Git publication. It is invoked only by the workflow through `python -m`; it receives no console-script entry point and is not a user-facing Feed CLI.

The helper reuses the existing application configuration/Provider resolution path and RateRegistry first-use/load APIs. If a tiny shared query is needed to enumerate an existing scope path or validate an existing state against a resolved policy, expose only that query from `providers/rate.py`; do not change serialization or transition ownership.

Keeping state decisions and Git staging in one narrow helper makes push failures injectable in tests and avoids duplicating lease rules across YAML shell fragments. Git itself remains the native coordination mechanism, invoked with explicit arguments and normal non-force push behavior.

Alternative rejected: encode the state machine entirely in workflow shell. It would duplicate JSON validation and RateRegistry policy interpretation and would be harder to test at the trust boundary.

### 3. Keep the lease minimal and separate from RateRegistry

`feeds/feed-run-lease.json` is a closed versioned record with only:

- `version`
- `deployment_run_id` derived from GitHub run ID and attempt
- `state`: `bootstrap`, `in_progress`, `success`, or `failure`
- truthful UTC `armed_at` and, for terminal state, `finished_at`
- `feed_start_not_after` when the run is armed
- `recovery_not_before`

The lease stores no scope list or rate values. RateRegistry remains authoritative for scopes, balances, anchors, dispatch times, cooldowns, and fingerprints. A closed parser rejects missing fields, unknown fields/version/state, invalid UTC ordering, a reused deployment identity, or inconsistent terminal values.

Alternative rejected: copy rate summaries into the lease. That creates a second rate authority and makes disagreement recovery ambiguous.

### 4. Bootstrap is a zero-network cutover, not migration

Static configuration and Provider resolution, including hosted recovery compatibility, run before deployment-state mutation. The helper distinguishes exactly two initial shapes:

- neither lease nor RateRegistry baseline exists: clean bootstrap;
- any partial combination exists: fail closed as corrupt established state.

Clean bootstrap calls the existing RateRegistry creation and first-use scope initialization for every distinct enabled resolved scope, writes a `bootstrap` lease, and commits/pushes the explicit state allowlist. Its `recovery_not_before` is the bootstrap instant plus configured crash cooldown. The workflow then exits without invoking Feed. The previous external/local scheduler must already be stopped; after the quiet boundary, unknown earlier state may be conservatively forgotten. No importer or legacy-state probing is added.

An established terminal state may initialize a newly resolved scope with existing first-use semantics, but that new state must be included in the same remote pre-network commit as the next `in_progress` lease.

Alternative rejected: initialize and collect in the first hosted run. That would treat absence of repository state as evidence that no external request was recently sent.

### 5. Arm remotely before entering the existing Feed deadline

For an established eligible state, the helper creates `in_progress` locally and commits/pushes the concrete rate/marker/lease paths to `HEAD:main`. Before preparation it fast-forward refreshes from `origin/main`; after preparation it makes exactly one non-force push attempt. Any fetch/merge, commit, or push conflict fails before Feed invocation and is not repaired by reset or force push.

The arming instant sets `feed_start_not_after` to one configured Feed command-deadline duration later. The same helper operation that validates the durable local/remote lease admits and directly enters the existing Feed call; if current time is later than that bound, it performs no Provider work. This removes an unbounded workflow-step gap without adding another Provider execution deadline.

`recovery_not_before` is computed as:

```text
feed_start_not_after
+ configured Feed command deadline (300 seconds today)
+ configured RateRegistry crash cooldown (24 hours today)
```

The first duration is only the bounded lease-publication/start window. Once admitted, the Feed's existing command-start monotonic deadline and exact 15-second commit reserve remain the sole execution deadline. Using the full configured 300 seconds in recovery is conservative even though Provider admission ends before the reserve.

Alternative rejected: `armed_at + crash_cooldown`. The lease is created before its remote push, and that formula does not cover a later permitted Feed start plus request admissions inside the Feed deadline.

### 6. Recover only when resolved policy proves forgetting is conservative

`bootstrap` before its boundary and `in_progress` before `recovery_not_before` block before Provider network. At or after the boundary, the helper groups currently enabled resolved Provider contracts by `scope_id` and requires:

```text
crash_cooldown_seconds >= refill_period_seconds
crash_cooldown_seconds >= minimum_interval_seconds
```

for every scope. Configuration resolution already rejects inconsistent declarations for a shared scope, so the helper does not build another policy registry. A future contract outside this envelope fails closed. If compatible, the helper leaves the last committed RateRegistry bytes untouched except for normal new-scope establishment and lets existing refill/eligibility logic decide the next dispatch.

Alternative rejected: reset each recovered scope to zero tokens. That invents state outside RateRegistry, changes its contract, and still needs a migration story.

### 7. Finalize exact safety state without masking Feed failure

The workflow records the Feed step outcome without allowing it to skip finalization. An `always()` finalization invokes the helper while the same checkout still contains the exact locally fsynced RateRegistry state.

- Success transitions the lease to `success`, reads `dated_relative_path` and `latest_relative_path` from the successful status file, validates both beneath `feeds/`, and publishes them with the exact durable rate paths.
- Controlled failure transitions the lease to `failure` and publishes only the exact durable rate paths plus lease; it does not stage Feed artifacts.
- After finalization, an explicit workflow step re-emits the original Feed failure so state bookkeeping cannot turn failure into success.

The final push is one non-force fast-forward attempt. If it fails or the runner vanishes, no terminal lease reaches remote; remote `in_progress` intentionally drives later recovery. The helper never promises rollback of a Provider send or a locally committed Feed artifact.

Alternative rejected: publish only after success. Controlled failures may already have changed exact rate state and must not discard it.

### 8. Use path-based CI recursion control

`test.yml` uses a narrow `push.paths-ignore` set matching only the durable generated paths. GitHub still runs the workflow when any changed path falls outside that set, so a mixed commit containing source, config, Provider, schema, workflow, test, OpenSpec, or documentation changes remains gated. Pull requests remain unchanged. Commit messages are descriptive only and do not control CI.

Repository workflow validation continues to use actionlint for GitHub syntax/context semantics and `scripts/validate_workflows.py` for project invariants. The project validator will check hosted runner/schedule/permission/concurrency, state-validation and lease-push ordering, direct `feeds/` execution, explicit staging, non-force Git, failure finalization, failure propagation, and the exact CI ignore boundary.

Alternative rejected: `[skip ci]`. It describes author intent rather than the changed-path contract and can hide mixed changes.

## Risks / Trade-offs

- [Branch policy rejects bot writes] → Verify Actions write permission and a real non-force manual bootstrap/state push before declaring ECO-62 operational; local validation alone is insufficient.
- [A normal source push races with lease or final publication] → Fail the single optimistic push. Before network this is zero-send; after network remote `in_progress` forces conservative recovery.
- [The first cutover overlaps an old scheduler] → Disable any prior external invocation before bootstrap and wait the recorded crash-cooldown boundary; do not import unverifiable legacy state.
- [GitHub delays the scheduled job] → Preserve runtime-derived cutoff and existing freshness/deadline failures; document 08:20 as schedule, not evidence time.
- [Daily state commits grow repository history] → Accept one pre-network and one final commit per network-capable run as the cost of repository authority; add compaction only if measured repository growth becomes operationally material.
- [Rate policy later exceeds 24-hour recovery support] → Fail hosted recovery from resolved contracts before network and require a deliberate contract change instead of silently weakening safety.
- [Generated-path ignore rules become too broad] → Keep the list identical to the staging allowlist and test generated-only and mixed pushes separately.

## Migration Plan

1. Merge the implementation and documentation without altering archived Changes or enabling another state authority. Stop any prior external/self-hosted Feed scheduler before repository bootstrap.
2. Verify repository Actions `contents: write` and branch policy permit the workflow identity to make ordinary fast-forward commits to `main`; do not change policy implicitly as part of Apply.
3. Run `workflow_dispatch` once. It must statically resolve current contracts, create and push only bootstrap RateRegistry/marker/scope/lease state, make zero Provider requests, and exit without a Feed.
4. Confirm the bootstrap commit and wait until its recorded recovery boundary.
5. Run `workflow_dispatch` again. Confirm the remote pre-network `in_progress` commit precedes Feed execution and that the final commit contains exact rate/terminal state plus the reported dated/latest Feed on success.
6. Leave cron `20 0 * * *` active and monitor the first scheduled result. Operational completion requires repository-side evidence that both required fast-forward writes are accepted.

Rollback is GitHub's native workflow disable control. Preserve the last remote lease and RateRegistry state; do not force push, reset generated state, or restart an external scheduler from an unverified state. A later code revert follows the normal reviewed source workflow and must retain conservative state until a separate migration is designed.
