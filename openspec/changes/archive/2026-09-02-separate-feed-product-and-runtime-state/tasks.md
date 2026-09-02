## 1. Baseline and Configuration Contract

- [x] 1.1 Record the clean active-Change/worktree baseline, inspect current legacy generated state without mutating it, and run `uv sync --frozen --all-groups` plus focused existing config/Feed/deployment/workflow tests.
- [x] 1.2 Add failing strict-config regressions for required `runtime_state_root`, unknown/missing fields, and explicit `output_root`/`runtime_state_root` resolution while proving the Feed semantic config snapshot excludes runtime layout.
- [x] 1.3 Add `runtime_state_root: .feed-state` to the authoritative closed YAML/model/loader contract with no implicit derivation, default fallback, Feed schema field, or dependency.

## 2. Checkpoint and Window Planning

- [x] 2.1 Add focused failing checkpoint tests for explicit null and valid success records plus missing established state, unknown/missing fields/version, malformed UTC timestamp/run identity, mismatch, partial JSON, and atomic-write failure.
- [x] 2.2 Implement the minimal closed/versioned internal checkpoint parser and atomic writer by reusing existing repository primitives; add no external JSON Schema or generic state framework.
- [x] 2.3 Add failing pure-planning regressions for null bootstrap, checkpoint advancement, equal/earlier cutoff rejection, exact/over-threshold gaps, coverage-gap reporting, and proof that steady-state planning never opens `feeds/latest.json`.
- [x] 2.4 Change `plan_window()` to consume validated prior-success state while preserving the existing half-open window, bootstrap lookback, strictly advancing cutoff, threshold, and gap semantics.

## 3. Dual-Root Feed Orchestration

- [x] 3.1 Add failing Feed orchestration tests proving lock/RateRegistry/checkpoint ownership under the runtime-state root and dated/latest publication exclusively under the product root, using temporary roots and deterministic Provider fixtures.
- [x] 3.2 Thread explicit product and runtime-state roots through the minimal Feed entry; move lock and RateRegistry ownership to state while retaining publisher ownership under product.
- [x] 3.3 Add failing ordering regressions for healthy and accepted degraded checkpoint advancement and non-advancement on dry-run, source failure, candidate validation failure, publication failure, durability unknown, or latest-not-replaced outcomes.
- [x] 3.4 Advance the checkpoint only after accepted dated/latest publication and before lock release; surface checkpoint persistence failure as execution failure without rollback claims.
- [x] 3.5 Run focused Feed CLI/pipeline/determinism/publication tests and confirm schema bytes, Feed fields, semantic snapshot, completeness/coverage, canonical serialization, dated/latest idempotence, and ECO-73 diagnostics remain unchanged.

## 4. Bootstrap, Layout Classification, and Legacy Migration

- [x] 4.1 Add failing deployment tests for complete new layout, complete legacy/new-absent layout, genuinely empty layout, and every mixed/partial/corrupt/unsupported/incompatible case before Provider network.
- [x] 4.2 Implement exact preflight layout classification using the existing RateRegistry, scope, lease, policy, recovery, and Feed integrity validators; use registered scopes as authority and globs only to detect orphans.
- [x] 4.3 Extend genuine zero-network bootstrap to persist marker, registry, current scopes, explicit null checkpoint, and bootstrap lease under `.feed-state/`; established state with a missing checkpoint must fail closed.
- [x] 4.4 Add failing migration regressions proving exact tokens/refill anchors/dispatch/cooldown/policy/scope preservation, root-identity-only normalization, healthy/degraded latest seeding, absent-latest null seeding, and no dated-history scan.
- [x] 4.5 Implement one migration-only operation that validates/copies durable legacy state, rewrites only RateRegistry `root_identity`, validates the new copy, deletes exact legacy runtime paths, returns an explicit additions/deletions allowlist, and performs zero Provider requests.
- [x] 4.6 Add and pass recovery regressions proving legacy `bootstrap`/`in_progress` lease identity, Feed-start bound, and `recovery_not_before` survive relocation and migration never arms collection.
- [x] 4.7 Add Git-runner regressions proving migration stages only exact new additions and legacy deletions, leaves products/transients/unrelated files unstaged, uses one non-force fast-forward publication, and exits before collection.

## 5. Hosted Finalization and Workflow Paths

- [x] 5.1 Add failing finalization tests for success checkpoint/status cutoff and run-ID parity, success path composition, failure checkpoint/product exclusion, locally modified checkpoint exclusion, and unrelated/transient files remaining unstaged.
- [x] 5.2 Separate runtime-safety, success-continuity, and success-product path construction; ordinary pre-network publication excludes checkpoint, success includes matching checkpoint/products, and failure includes safety state only.
- [x] 5.3 Update private deployment commands and `generate-feed.yml` to pass explicit product/state roots and preserve prepare → migration/bootstrap/armed publish → armed-only collect → finalization → ECO-73 diagnostics → original-failure restoration ordering.
- [x] 5.4 Update `.gitignore` so `feeds/` tracks only accepted Feed products and `.feed-state/` tracks only exact durable marker/checkpoint/lease/registry/scope files while lock/status/temp/staging/debug/failure artifacts remain ignored.
- [x] 5.5 Replace steady-state CI generated-path exclusions with accepted `.feed-state/` durable paths plus `feeds/latest.json` and `feeds/daily/**/*.json`; retain no legacy runtime exclusions solely for migration.
- [x] 5.6 Extend project workflow tests/validator for explicit roots, migration-only zero-collection control flow, exact outcome staging, no force/reset, final CI paths, existing failure propagation, and authoritative Actions semantics.

## 6. Documentation and Contract Truth

- [x] 6.1 Update only documentation and runbooks that currently describe the single-root Feed/deployment boundary so they distinguish consumer `feeds/`, runtime `.feed-state/`, checkpoint authority, migration-only first invocation, recovery, and outcome-specific staging.
- [x] 6.2 Confirm `README.md`, `README.zh-CN.md`, `SKILL.md`, Feed contract, architecture, configuration, and relevant runbooks make no claim that runtime paths enter Feed output or that dated/latest publication has changed; modify only files with stale claims.
- [x] 6.3 Review the delta against `feed-evidence-pipeline` and verify no Agent, deterministic-research-engine, scoring, grounding, capability-surface, Provider policy, ECO-75, or ECO-76 contract was added or changed.

## 7. Verification and Operational Migration

- [x] 7.1 Run focused checkpoint, config, Feed pipeline/CLI/deployment/workflow tests with temporary state roots, then run the complete relevant existing RateRegistry, Feed schema/determinism/publication, completeness/coverage, and ECO-73 diagnostics regressions.
- [x] 7.2 Run `.venv/bin/python scripts/quality_gate.py`, `openspec doctor`, `openspec validate separate-feed-product-and-runtime-state --strict`, `openspec validate --all --strict`, and `git diff --check`; record only checks actually executed.
- [x] 7.3 Inspect the final diff for exact scope, unchanged `schemas/feed.schema.json`, no runtime fields in Feed products, no persistent-database/repository-state mutation from tests, and no unrelated edits.
- [x] 7.4 After separately authorized delivery places the implementation on `main`, run one hosted invocation and verify the exact zero-Provider migration commit adds durable `.feed-state/` files, deletes exact legacy runtime files under `feeds/`, leaves Feed products untouched, preserves rate/lease/recovery values, and exits without arming or collection.
- [x] 7.5 On a later hosted invocation after the preserved recovery boundary permits work, verify normal pre-network arming and success/failure finalization use the new exact path sets and that remote continuity comes solely from the checkpoint; retain evidence needed before declaring ECO-74 operationally complete.
