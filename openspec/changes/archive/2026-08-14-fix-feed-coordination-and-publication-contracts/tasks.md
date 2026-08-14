## 1. Establish Reproducible Contract Failures

- [x] 1.1 Add a production-registry `--dry-run` regression test that proves real sends acquire `CollectionLock`, durably debit/reconcile `RateRegistry`, and create no dated/latest Feed artifact; verify it fails against the current bypass.
- [x] 1.2 Strengthen the deadline regression test so injected staging or pre-commit `fsync` crosses second 285, then assert typed refusal, zero dated/latest rename, and no staging residue; verify it fails against the current caller-only check.
- [x] 1.3 Strengthen equal-cutoff/different-digest tests to assert identical latest bytes in both submission orders while retaining both dated artifacts; add older-candidate and incompatible-equal-owner cases and verify the current order-dependent implementation fails.

## 2. Repair Production Dry-Run Coordination

- [x] 2.1 Derive the coordination boundary from whether production adapters may send, and acquire the output-root lock before latest/cutoff planning for production `--dry-run` as well as publishing runs.
- [x] 2.2 Initialize and use durable per-scope rate state for production dry-run dispatch without changing dry-run's early return before publication.
- [x] 2.3 Run the focused dry-run, lock, concurrency, rate-state, and CLI tests; confirm fixture injection remains deterministic and no Feed artifact is published by any dry run.

## 3. Repair Pre-Commit Admission

- [x] 3.1 Pass the command's injected monotonic clock and absolute second-285 admission boundary into Feed publication rather than treating the pre-call check as final admission.
- [x] 3.2 After staging files and required pre-commit directory `fsync`, perform the final deadline check immediately before the first irreversible rename; on refusal remove staging and return typed `pre_commit_deadline_exceeded` with zero dated/latest rename.
- [x] 3.3 Apply the same admission boundary to idempotent recovery that must replace latest, and preserve non-cancellable rename/post-rename `fsync` behavior after admission.
- [x] 3.4 Run focused deadline, staging-cleanup, fsync-failure, durability-uncertainty, and commit-overrun tests.

## 4. Repair Monotonic Latest Ownership

- [x] 4.1 Derive candidate and current latest ownership from validated canonical `evidence_cutoff_at` and `content_digest` fields, failing closed when an ownership key is missing, malformed, or incompatible.
- [x] 4.2 Commit the create-only dated artifact as before, but replace latest only when the candidate ownership tuple is greater; retain latest for older candidates and accept equal ownership only as byte-identical idempotency.
- [x] 4.3 Preserve explicit stale/non-replacement and durability outcomes without deleting a durable dated artifact or changing CLI exit-category ownership.
- [x] 4.4 Run focused publication tests for both equal-cutoff digest orders, older/newer cutoffs, same-run recovery, ownership mismatch, no-replace dated commits, and stage cleanup.

## 5. Reconcile the Baseline Evidence

- [x] 5.1 Update `normalize-openspec-baseline/traceability.md` with the repaired implementation and focused-test evidence, removing only the three resolved Stage 3 blockers.
- [x] 5.2 Reclose `normalize-openspec-baseline` tasks 1.2, 4.3, and 5.1 only after every Feed requirement row has current implementation/test evidence and no production-wiring overclaim remains.
- [x] 5.3 Review the combined scoped diff and confirm no Feed schema, provider manifest, financial calculation, dependency, workflow, generated Feed, deployment, archive history, or unrelated worktree path changed.

## 6. Complete High-Risk Verification

- [x] 6.1 Run focused Feed CLI/provider/publication/deadline tests and mutation-check the three original failure modes against the repaired tests.
- [x] 6.2 Run `openspec doctor --json`, strict validation for both active Changes, and `openspec validate --all --strict --json`; report informational findings separately.
- [x] 6.3 After the final relevant code/test/spec edit, run `UV_CACHE_DIR=/tmp/follow-the-money-uv-cache uv run python scripts/quality_gate.py` once and require the complete gate to pass.
- [x] 6.4 Perform a fresh independent Stage 3 review of requirement → design → implementation → test → validation evidence, with no unresolved Blocker/High finding before either Change is recommended for archive.
