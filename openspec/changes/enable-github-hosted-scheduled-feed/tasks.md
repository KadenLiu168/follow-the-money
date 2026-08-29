## 1. Lock the Deployment Contract with Failing Tests

- [x] 1.1 Replace the self-hosted/template expectations in `tests/test_workflows.py` and `scripts/validate_workflows.py` with failing assertions for `ubuntu-latest`, cron `20 0 * * *`, `contents: write`, no opt-in/external root, non-cancelling concurrency, direct `feeds/` execution, static preflight and durable lease-push ordering, explicit generated-state staging, no force/reset, `always()` finalization, Feed-failure propagation, and generated-only CI recursion avoidance.
- [x] 1.2 Add focused no-network deployment-state tests for closed lease validation, clean zero-send bootstrap, early bootstrap blocking, valid established state, missing/corrupt registry or lease, new-scope establishment, and resolved-policy recovery-envelope rejection without hard-coded Provider IDs.
- [x] 1.3 Add focused state-transition/Git tests for pre-network push failure and conflict, missed Feed-start bound, incomplete lease before/after recovery, controlled pre-network and post-network failure, successful finalization, final push failure, and exact staging that excludes transient and unrelated paths.

## 2. Implement the Minimal Repository State Boundary

- [x] 2.1 Add one private `follow_the_money.feed` deployment helper with a closed versioned `feeds/feed-run-lease.json` parser/writer and deterministic `bootstrap`, `in_progress`, `success`, and `failure` transitions; keep all exact rate facts solely in RateRegistry.
- [x] 2.2 Reuse the authoritative configuration/Provider resolution path to group enabled rate scopes, validate `crash_cooldown >= refill_period` and `crash_cooldown >= minimum_interval`, fail closed on partial/corrupt established state, and establish clean bootstrap or newly introduced scopes through existing RateRegistry first-use semantics.
- [x] 2.3 Implement remote arming with one explicit non-force fast-forward Git update, a Feed-start bound equal to the configured command-deadline duration, and `recovery_not_before = feed_start_not_after + command deadline + crash cooldown`; ensure push failure/conflict or late admission returns before the existing Feed can run.
- [x] 2.4 Invoke the existing Feed directly against `feeds/` only after durable arming, then implement success/failure finalization that reads the existing Asia/Shanghai `dated_relative_path`, persists exact rate state, stages Feed artifacts only on success, and preserves the original Feed failure result.
- [x] 2.5 Expose only a minimal existing RateRegistry scope-path/state query if the helper cannot safely enumerate its exact allowlist through current APIs; do not change RateRegistry serialization, debit, cooldown, refill, refund, reconcile, or migration behavior.

## 3. Activate the Hosted Workflows

- [x] 3.1 Update `.gitignore` so only the persistence marker, registry, exact scope states, lease, latest Feed, and successful dated Feed can be tracked under `feeds/`, while locks, status, staging, temporary, bundle, and debug/failure state remain ignored.
- [x] 3.2 Replace `.github/workflows/generate-feed.yml` with the active `ubuntu-latest` scheduled/manual flow: checkout and install, static state preparation, zero-send bootstrap/block handling, durable pre-network lease publication, bounded Feed admission, `always()` exact finalization, and explicit failure propagation using only normal fast-forward pushes.
- [x] 3.3 Add the exact generated-state `push.paths-ignore` boundary to `.github/workflows/test.yml` while leaving pull requests and any mixed/non-generated push eligible for the full existing CI suite.
- [x] 3.4 Keep actionlint as the Actions syntax/context authority and complete the repository-specific behavioral workflow validator/tests, including the existing invalid-context fixture.

## 4. Synchronize Contract and Documentation Truth

- [x] 4.1 Update `README.md`, `README.zh-CN.md`, `SKILL.md`, and both deployment runbooks to state active 08:20 Asia/Shanghai GitHub-hosted Feed generation, runtime-derived cutoff, repository-backed state/bootstrap/recovery, and the separate later Host-Agent consumption boundary.
- [x] 4.2 Remove stale 08:30, self-hosted, opt-in, external-root, and automatic-Agent implications without changing Feed schema/evidence claims or describing retained capabilities as activated.
- [x] 4.3 Document the first bootstrap/manual recovery procedure, native workflow-disable rollback, generated-state allowlist, non-force conflict behavior, and the requirement to verify Actions write permission and branch policy before declaring operational completion.

## 5. Verify Locally and Preserve Existing Invariants

- [x] 5.1 Run the focused deployment/workflow/RateRegistry tests and workflow validator/actionlint, then retain the existing invalid-workflow fixture failure and all deterministic rate, deadline, lock, publication, Shanghai-date, schema/provenance/digest/run-ID, coverage, degradation, and failure regressions.
- [x] 5.2 Run the full credential-free pytest suite and `.venv/bin/python scripts/quality_gate.py`, including the repository-authoritative Ruff, format, mypy, workflow, entry-point, build, and offline checks; do not run a real Provider dry run for ordinary verification.
- [x] 5.3 Run `openspec doctor`, `openspec validate enable-github-hosted-scheduled-feed --strict`, `openspec validate --all --strict`, and `git diff --check`; confirm only ECO-62 implementation, tests, docs, and planning paths changed.

## 6. Verify the External Deployment Prerequisite

- [ ] 6.1 Before claiming ECO-62 operational, verify repository Actions `contents: write` and branch policy permit the workflow identity's ordinary fast-forward commits to `main`; record any setting that remains unavailable as an explicit deployment blocker rather than changing it without authorization.
- [ ] 6.2 After separately authorized deployment, disable any prior external scheduler, dispatch the zero-network bootstrap, verify its allowlisted remote state commit, wait through `recovery_not_before`, and verify a later manual run publishes remote `in_progress` before Provider work and terminal exact state afterward without force push.
