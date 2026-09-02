## Context

See `proposal.md` for motivation and `specs/feed-evidence-pipeline/spec.md` for the behavior delta. Current `run_feed()` binds `CollectionLock`, `plan_window(latest_path=...)`, `RateRegistry`, and `publish_feed()` to one root. Hosted deployment likewise passes `feeds/` to bootstrap, lease, collection, finalization, and Git staging. The persisted RateRegistry is already the sole rate-state model and includes a `root_identity` that is explicitly bound to the old root; the lease and scope records contain semantic state that must not be regenerated during relocation.

The accepted publisher already owns dated-before-latest durability and reports whether latest replacement succeeded or durability became unknown. The new checkpoint must follow that boundary, not alter it. ECO-73 transient diagnostics and `.feed-exit-code` authority remain downstream of safety-critical finalization.

## Goals / Non-Goals

**Goals:**

- Give product and runtime state separate, explicit path ownership throughout configuration, local orchestration, hosted deployment, validation, and staging.
- Make one minimal checkpoint the sole steady-state previous-success authority without changing window semantics or Feed identity.
- Relocate complete legacy repository state once, preserving exact rate and recovery semantics and making no Provider request.
- Keep every write and Git stage fail-closed and outcome-specific.

**Non-Goals:**

- Generalizing filesystem state, transactions, migration frameworks, or schema infrastructure.
- Changing the publisher, Feed fields/schema/semantic snapshot, RateRegistry algorithms, lease policy, completeness/coverage, diagnostics, or Host-Agent boundary.
- Removing dated history or changing latest publication; those remain ECO-75/ECO-76 work.

## Decisions

### 1. Resolve and pass two roots, never reinterpret one root

Add required `runtime_state_root: .feed-state` to the closed top-level configuration and `AppConfig`; retain required `output_root: feeds` as the product root. Loader validation materializes both values directly. The Feed semantic snapshot keeps its existing explicit projection and therefore excludes `runtime_state_root`.

`run_feed()` and the private deployment commands receive product and state roots as separate named values. The product root is used only by Feed validation/publication/status paths. The state root is used only by checkpoint, lock, RateRegistry, marker, scope, and lease operations. Rename local variables and private parameters where needed to retain that distinction; do not add a generic root abstraction.

Alternative rejected: derive `.feed-state` from `output_root` or keep one `--root` whose meaning changes by command. Either recreates hidden coupling and makes path-validation mistakes easy.

### 2. Use one small checkpoint module and keep window arithmetic pure

Add one internal checkpoint record/parser/writer shared by Feed orchestration and deployment. Its exact JSON keys are:

```json
{"previous_success": null, "version": "1"}
```

or `previous_success` with exactly `evidence_cutoff_at` and `run_id`. Parsing rejects non-objects, missing/unknown fields, unsupported versions, non-UTC or malformed timestamps, and run IDs outside the existing `<RFC3339 cutoff>::<32 lowercase hex>` semantic identity form or whose cutoff component disagrees with `evidence_cutoff_at`. It returns either no prior success or the two validated values. Atomic persistence reuses the repository's existing same-directory durable write primitive; no external JSON Schema or generic state codec is added.

`plan_window()` accepts validated prior cutoff state rather than a path or validation callback. It retains the exact bootstrap, strict advance, exact-threshold, over-threshold, coverage-gap, and half-open interval arithmetic. Normal planning has no code path to `latest.json`. Legacy migration alone validates latest with the existing Feed schema, semantic, digest, run-ID, embedded-contract, and accepted healthy/degraded checks before extracting checkpoint values.

Alternative rejected: store the full latest Feed or let planning load either checkpoint or latest. Both create duplicate continuity authorities.

### 3. Advance checkpoint after accepted product publication under the same lock

The collection lock moves to the state root and continues to enclose cutoff capture, planning, Provider work, candidate validation, dated/latest publication, and checkpoint advancement. After `publish_feed()` returns, orchestration first rejects `commit_durability_unknown` and `latest_replaced == false`; only then does it atomically write the successful Feed cutoff/run ID to the checkpoint. Dry-run and every earlier failure return without that write.

If the checkpoint write fails after product publication, return typed execution failure and keep the lock until failure propagation completes. Do not delete or roll back the already committed Feed. This deliberately permits conservative overlap on the next run but never skipped evidence from a leading checkpoint.

Alternative rejected: write before publication, roll back cross-directory product files, or add two-phase commit. The first can skip evidence; the others promise filesystem transactions the repository does not have.

### 4. Classify layout before bootstrap or arming

Deployment preflight examines exact authoritative indicators beneath both roots before any normal mutation:

- complete new: checkpoint, marker, registry, all registered scopes, and lease exist and validate; continue normal lifecycle;
- complete legacy with new absent: validate legacy through existing RateRegistry, scope, lease, policy, recovery, and Feed validators, then return migration mode;
- neither layout established: run genuine bootstrap;
- anything else: fail closed.

Scope completeness comes from the registry, not a glob-derived authority; globs are used only to detect orphan/partial files. A valid legacy latest seeds the checkpoint; absence seeds explicit null; dated history is never inspected. A present legacy latest that is not a supported, identity-valid healthy/degraded Feed blocks migration.

Migration writes the new marker, registry, scopes, lease, and checkpoint without changing semantic values. Scope and lease bytes are preserved. Only the registry's `root_identity` is rewritten from the validated old resolved root to the new resolved root; version, scope map, statuses, and policy fingerprints remain identical. After validating the complete new copy, migration deletes only the exact legacy marker, registry, registered scope files, and lease. A crash can leave a mixed layout, which the next invocation rejects rather than guessing. The explicit Git allowlist includes exactly those new additions and old deletions. Migration is fast-forward published and exits; no lease is refreshed and no collection command runs.

Alternative rejected: filesystem-directory rename, rate-state regeneration, or bootstrap when `.feed-state/` is absent. A rename cannot normalize truthful root metadata, while regeneration or bootstrap discards safety history.

### 5. Keep bootstrap, safety state, continuity state, and product state distinct

Genuine bootstrap creates the RateRegistry through its existing first-use lifecycle, current scopes, persistence marker, null checkpoint, and bootstrap lease under `.feed-state/` before the existing pre-network push. Ordinary arming validates the checkpoint but stages only runtime safety state: marker, registry, registered scopes, and lease. The generic safety allowlist never includes the checkpoint.

Collection receives both roots. A successful run has already advanced the local checkpoint after accepted product publication. Success finalization reads the transient successful status, validates dated/latest product paths beneath `feeds/`, validates the checkpoint beneath `.feed-state/`, requires exact cutoff/run-ID parity, writes terminal success lease, and stages safety state + checkpoint + products. Failure finalization writes terminal failure lease and stages safety state only, even if a checkpoint is locally modified. This outcome-specific construction prevents accidental checkpoint promotion.

Alternative rejected: one union allowlist filtered after staging. Constructing the exact path set before `git add --` is smaller and fail-closed.

### 6. Update repository path policy to the final architecture

`.gitignore` keeps only `feeds/latest.json` and `feeds/daily/*/*.json` trackable beneath the product root. `.feed-state/*` is ignored by default, with only the marker, checkpoint, lease, registry, and registered `scope-*.json` patterns trackable; `.collection.lock`, temp/staging/status/debug/failure paths stay ignored. Runtime legacy paths under `feeds/` are not retained as accepted exceptions.

The workflow passes explicit product/state roots through prepare, publish, collect, and finalize; prepare exposes migration mode, pre-network publication accepts migration but collection accepts only armed mode. `test.yml` path exclusions describe only accepted `.feed-state/` durable paths plus latest/dated products. Project workflow validation checks root explicitness, migration-only ordering, exact outcome staging, no force/reset, ECO-73 diagnostics ordering, and Actions semantics.

Alternative rejected: permanent legacy ignore/CI exceptions. They would preserve the obsolete architecture to hide one migration commit.

### 7. Prove boundaries with focused no-network regressions

Add checkpoint contract and pure planning tests first, then dual-root local orchestration and publication ordering tests. Extend deployment tests with layout classification, exact migration semantic preservation, mixed/corrupt failures, incomplete-lease preservation, success parity, failure checkpoint exclusion, and exact Git path sets. Workflow/config tests cover required configuration, explicit command roots, migration-only control flow, final CI paths, and Actions-aware validation. Existing Feed schema/determinism, publisher idempotence, RateRegistry, completeness/coverage, and ECO-73 diagnostics tests remain regression authorities rather than being duplicated.

No test uses repository `feeds/` or `.feed-state/` as mutable state; all state tests use temporary roots and deterministic fixtures. No Feed dry-run with real Providers is required for this Change.

## Risks / Trade-offs

- [Feed product publishes but checkpoint write fails] → Report execution failure and allow checkpoint lag; never roll back product files or advance optimistically.
- [Migration crashes between new writes and old deletions] → Leave detectable mixed state and fail closed on the next invocation; operator repairs only through an explicit reviewed state action.
- [Legacy `root_identity` contains runner-specific absolute path] → Require it to match the authoritative legacy root expected by existing validation, then rewrite only that field to the resolved new root.
- [Failure finalization sees a locally advanced or tampered checkpoint] → Build the failure allowlist without checkpoint or product paths and verify the staged set exactly.
- [Path-ignore rules conceal source changes] → Ignore only exact accepted generated patterns; mixed commits remain CI-eligible.
- [Large migration surface tempts a generic framework] → Keep one layout classifier and one migration operation for the known v1 files; unsupported future versions fail closed.

## Migration Plan

1. Land configuration, checkpoint/planning, dual-root orchestration, deployment migration/finalization, path policy, tests, docs, and living-spec alignment together; do not alter archived Changes.
2. On the first hosted invocation, refresh by fast-forward, statically resolve configuration/providers, classify complete legacy state, validate legacy latest if present, relocate exact runtime state, normalize only registry `root_identity`, create the checkpoint, and publish the explicit additions/deletions with zero Provider requests.
3. End that invocation after migration. On a later invocation, validate complete `.feed-state/`, preserve any migrated bootstrap/in-progress recovery bound, and only arm when the existing recovery contract permits.
4. On normal success, verify remote final state contains matching safety state, checkpoint, dated Feed, and latest Feed. On controlled failure, verify checkpoint/products were not included and the original Feed failure remains authoritative.

Rollback after migration is a reviewed source-and-state migration, not a code-only revert: disabling the workflow is safe, but restoring the old code requires relocating the exact runtime state and continuity authority back without resetting RateRegistry or lease history. Do not force push, delete `.feed-state/`, or infer continuity from dated history.
