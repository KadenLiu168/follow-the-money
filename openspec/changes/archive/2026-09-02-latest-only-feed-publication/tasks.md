## 1. Publication Contract Tests

- [x] 1.1 Rewrite focused publication tests for latest-only canonical atomic replacement, semantic idempotence, stale/equal-cutoff ownership, staging cleanup, and absence of `feeds/daily/**`; verify the updated publication tests fail against the dual-output implementation for the intended reasons.
- [x] 1.2 Update orchestration/checkpoint tests for successful latest-only publication, unchanged previous latest on pre-replacement failure, no checkpoint advance on failure or durability uncertainty, and deterministic duplicate execution; verify the focused CLI and determinism tests expose the current dated assumptions.

## 2. Latest-Only Publication

- [x] 2.1 Simplify `src/follow_the_money/feed/publish.py` to validate and stage one latest candidate, preserve monotonic ownership and semantic idempotence, atomically replace `latest.json`, retain existing `fsync`/deadline/fail-closed semantics, and verify the focused publication tests pass with no daily path created.
- [x] 2.2 Update Feed orchestration and successful status serialization to treat accepted durable latest ownership as publication success, remove dated path fields/messages, and advance checkpoint only after accepted latest ownership; verify focused CLI, checkpoint, and determinism tests pass.

## 3. Hosted Deployment and Repository State

- [x] 3.1 Update deployment status validation and finalization to validate/stage only fixed `latest.json` plus matching checkpoint/runtime state, reject dated paths from success allowlists, and verify deployment and product/runtime separation tests pass.
- [x] 3.2 Remove `feeds/daily/**/*.json` from CI generated-state exclusions and repository workflow validators while preserving all existing hosted ordering, credentials, diagnostics, and Git-safety checks; verify workflow and gate tests pass.
- [x] 3.3 Remove the currently tracked dated Feed artifact without adding runtime cleanup or retention machinery, and verify the active `feeds/` tree contains only `latest.json` as product state.

## 4. Contract Documentation

- [x] 4.1 Update `README.md`, `README.zh-CN.md`, `SKILL.md`, `docs/feed-contract.md`, architecture/runbook references, and any other current capability claims found by dated-path search to describe latest-only product state, checkpoint runtime continuity, and Git-only repository history; verify no current documentation claims new dated publication or a historical query capability.

## 5. Verification

- [x] 5.1 Run the focused publication, CLI, deployment, determinism, workflow, and no-LLM/architecture-boundary tests and verify all latest-only acceptance scenarios pass without changing Feed schema, evidence, provenance, or Agent boundaries.
- [x] 5.2 Run `.venv/bin/python scripts/quality_gate.py` and verify the canonical repository quality gate passes.
- [x] 5.3 Run `openspec doctor`, `openspec validate latest-only-feed-publication --strict`, and `openspec validate --all --strict`; verify all OpenSpec checks pass and review remaining `feeds/daily`, `dated_relative_path`, and dual-output references as historical-only or remove them from current surfaces.
