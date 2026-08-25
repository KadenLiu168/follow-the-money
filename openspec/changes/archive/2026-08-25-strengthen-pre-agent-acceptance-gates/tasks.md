## 1. Freeze the Current Acceptance Inventory

- [x] 1.1 Re-read the supplied ECO-32 scope and, if current Linear read access is available, verify ECO-31 completion plus ECO-32 `blockedBy` / `blocks`, milestone, and status without updating Linear; stop and record any dependency or scope conflict.
- [x] 1.2 Record the inspected revision, initial worktree state, active Change set, and exact living capability directories in Change-local `traceability.md`; preserve every pre-existing unrelated change.
- [x] 1.3 Extract every exact current Requirement heading from `deterministic-core-retention`, `feed-evidence-pipeline`, and `deterministic-research-engine`, and prove the trace inventory has one row per heading with no duplicate, omitted, or invented Requirement.
- [x] 1.4 Compare the Change-local `MODIFIED` requirement with the current `Baseline acceptance uses semantic trace evidence` block; verify the Requirement name and every inherited scenario name/content are preserved before evaluating the added acceptance behavior.

## 2. Build the Fresh Semantic Trace

- [x] 2.1 Define the trace legend and columns for disposition, current implementation or negative invariant, caller status, focused executable/static evidence, and result; distinguish `live-production`, `retained-no-caller`, `negative-invariant`, `historical-superseded`, and non-applicable states without creating runtime metadata.
- [x] 2.2 Trace every `deterministic-core-retention` Requirement to current repository surfaces, no-LLM/architecture audits, caller evidence where applicable, and existing focused tests; leave no row accepted from structural validity alone.
- [x] 2.3 Trace every `feed-evidence-pipeline` Requirement to the actual Provider-to-Feed call path and existing evidence for startup authority, verified provenance/mappings, coverage, deterministic generation, schema/identity/digest, degradation, timing/rate discipline, publication/recovery, and invocation/workflow boundaries.
- [x] 2.4 Trace every `deterministic-research-engine` Requirement to its typed implementation and focused ledger, entity/candidate, Event/family, market/state, watchlist, scoring, ranking, and audit evidence; record the expected production caller status for each retained capability.
- [x] 2.5 Audit the minimal Feed entry and real call sites, proving every positive production-stage claim has a caller and that retained ledger, candidate/event, market/state, watchlist, scoring/ranking, and `ClaimAuditor` capabilities are not automatically or synthetically wired into production.
- [x] 2.6 Reconcile the archived `normalize-openspec-baseline/traceability.md` removed/superseded dispositions against current living specs, source, tests, all subsequent archived Changes, and the current caller graph; record only still-valid conclusions as `historical-superseded` and leave archived files unchanged.
- [x] 2.7 Audit current-facing `AGENTS.md`, `SKILL.md`, README files, and architecture docs against the completed trace, separating historical archive hits from current claims and rejecting any contradiction or positive Phase-4 Agent contract/topology.

## 3. Establish Existing Executable Evidence

- [x] 3.1 Map Production Feed rows to existing focused suites, including `tests/test_gate_13_1.py`, `tests/test_gate_13_2.py`, `tests/test_feed_determinism.py`, `tests/test_feed_boundary.py`, `tests/test_feed_pipeline.py`, `tests/test_feed_cli.py`, `tests/test_provider_contract.py`, and `tests/test_workflows.py`; run the necessary fixture-backed tests and record exact commands/results in the trace.
- [x] 3.2 Map retained-library rows to existing focused suites, including `tests/test_engine.py`, `tests/test_events.py`, `tests/test_market.py`, `tests/test_market_snapshot.py`, `tests/test_state.py`, `tests/test_scoring.py`, `tests/test_neutralize_selection_and_scoring_contract.py`, and `tests/test_audit.py`; run the necessary tests and record deterministic, fail-closed, and no-caller evidence.
- [x] 3.3 Run `tests/test_no_llm_contract.py` with any supporting current architecture tests needed by the trace, and record evidence for no LLM SDK/runtime/request, prompt/model/API-key configuration, legacy fixed pipeline, credential dependency, or removed public product surface.
- [x] 3.4 For any Requirement without sufficient current executable or static-audit evidence, mark the row and overall acceptance blocked and surface the exact coverage/scope decision; do not add replacement tests, alter existing expectations, or change production behavior within ECO-32.

## 4. Run Canonical and Structural Gates

- [x] 4.1 Run `.venv/bin/python scripts/quality_gate.py` as the only repository-wide executable orchestrator and record its complete fresh outcome; do not add an ECO-32 runner, duplicate matrix, CI change, or real-network Feed dry run.
- [x] 4.2 Run `openspec doctor`, `openspec validate strengthen-pre-agent-acceptance-gates --strict`, and `openspec validate --all --strict`; record actual results while treating these structural checks as necessary but not sufficient.
- [x] 4.3 Review the final diff against the Change-artifact-only allowlist and verify that living specs, production code, tests, configuration, Providers, schemas, financial behavior, workflows, dependencies, CI/deployment, generated Feed data, archived Changes, and unrelated worktree state are unchanged.

## 5. Make the Phase-3 Acceptance Decision

- [x] 5.1 Complete every trace result only from fresh evidence and verify the matrix covers every current Requirement, every applicable caller state, every reused historical disposition, and every required regression category.
- [x] 5.2 Perform the final semantic review across ECO-32 scope, all living requirements, current implementation, tests, caller graph, `AGENTS.md`, `SKILL.md`, README files, and architecture docs; record every conflict, risk, or follow-up without silently expanding scope.
- [x] 5.3 Declare Phase 3 Pre-Agent Baseline Acceptance complete only if every row is accepted, all executable and structural gates pass, no architecture contradiction remains, and no production or future Agent behavior was introduced; otherwise record the exact blocked decision.
- [x] 5.4 Leave living-spec synchronization, Linear status changes, archive, commit, push, and all Phase-4 Skill-Agent Contract work untouched pending separate explicit authorization.
