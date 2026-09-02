## Context

See `proposal.md` for motivation. Publication currently stages and commits an immutable dated Feed before replacing `feeds/latest.json`; CLI status, checkpoint advancement, hosted finalization, CI path exclusions, tests, and docs all encode that sequence. ECO-74 already moved continuity to `.feed-state/feed-checkpoint.json`, so dated products no longer participate in window planning.

The latest replacement remains a trust and durability boundary: candidate bytes must be canonical and validated, ownership must remain monotonic, and a rename that already committed cannot be truthfully rolled back if the following directory `fsync` fails.

## Goals / Non-Goals

**Goals:**

- Make `feeds/latest.json` the only Feed product created and staged by successful runs.
- Preserve deterministic ownership, semantic idempotence, atomic replacement, deadline admission, filesystem durability, and fail-closed checkpoint ordering.
- Keep hosted finalization's status/product/checkpoint identity checks while narrowing its product allowlist to latest only.

**Non-Goals:**

- Add archive storage, historical lookup, snapshot retention, or Git-history runtime access.
- Delete arbitrary untracked or externally retained `feeds/daily/**` trees at runtime.
- Change Feed bytes, schema, identity projection, evidence, provenance, or provider behavior.

## Decisions

### 1. Collapse publication to one same-directory atomic replacement

Publication will validate canonical candidate bytes and ownership, create one unpredictable create-only staging file directly under the product root, `fsync` the file and product directory, admit commit before the deadline reserve, atomically replace `latest.json`, then `fsync` the product directory. No daily directory or dated staging file will be created.

Alternative: retain dated staging as an internal recovery journal. Rejected because it preserves the storage contract being removed and duplicates checkpoint/Git responsibilities.

### 2. Preserve monotonic ownership and make current semantic ownership the idempotence source

The valid current `latest.json` replaces the dated artifact as the comparison source. A newer ownership tuple replaces it; an older tuple is rejected without writes; equal semantic `run_id`, digest, and cutoff is accepted idempotently while retaining existing latest bytes, including when truthful execution-audit timestamps make candidate bytes differ. Equal ownership with incompatible identity fails closed.

Alternative: overwrite equal semantic ownership with the latest execution envelope. Rejected because completion order would choose audit bytes and weaken deterministic duplicate execution behavior.

### 3. Advance checkpoint only after accepted durable latest ownership

A newly replaced latest advances the checkpoint only after replacement and required directory `fsync` succeed. An idempotent candidate that already owns a valid latest may also advance/confirm the same checkpoint identity. Stale rejection, pre-replacement failure, and post-replacement durability uncertainty do not advance it.

Alternative: advance from candidate validation alone. Rejected because checkpoint state could lead product state.

### 4. Narrow status and hosted finalization to latest only

Successful transient status will retain `run_id`, `evidence_cutoff_at`, and fixed `latest_relative_path: latest.json`, and remove `dated_relative_path`. Finalization will validate only that latest is inside the product root, canonical, schema/identity valid, and matches both status and checkpoint before adding it to the exact generated-state allowlist. Failure finalization remains runtime-safety-state only.

Alternative: infer the product path from `run_id`. Rejected because the latest-only path is fixed and inference adds no value.

### 5. Remove dated paths from active repository state without adding cleanup machinery

The currently tracked `feeds/daily/**` artifact will be removed from the active tree, and dated paths will be removed from CI generated-state exclusions and workflow validators. Existing legacy migration continues to derive checkpoint state only from `latest.json` and never scans dated history. Runtime publication/finalization will neither create nor stage arbitrary dated files.

Alternative: add a migration that recursively deletes all dated files. Rejected because snapshot retention/cleanup policy is out of scope and destructive cleanup is unnecessary for latest-only publication.

## Risks / Trade-offs

- [A post-replace directory `fsync` failure may leave new latest bytes visible while durability is uncertain] → Preserve the existing execution failure, no-rollback claim, and no-checkpoint-advance semantics.
- [Removing dated artifacts eliminates filesystem repair from an immutable copy] → Validate current latest directly; continuity remains checkpoint-owned and repository history remains available operationally through Git only.
- [A stale candidate no longer leaves an audit artifact] → Reject it without writes; historical product querying is explicitly out of scope.
- [Documentation or workflow checks may retain dual-output claims] → Search dated-path/status-field references and run focused tests, workflow validation, strict OpenSpec validation, and the canonical quality gate.

## Migration Plan

1. Update focused tests to express latest-only publication and preserve failure/durability/idempotence invariants.
2. Simplify publication, CLI status, hosted finalization, generated-state allowlists, and CI exclusions.
3. Remove the currently tracked dated Feed artifact and update contract documentation; do not add runtime historical cleanup.
4. Run focused publication/deployment/workflow tests, then the repository quality gate and strict OpenSpec checks.

Rollback requires reverting the code, contract, workflow, documentation, and tracked-product changes together. It must not reconstruct missing dated artifacts from checkpoint state or treat Git history as a runtime source.
