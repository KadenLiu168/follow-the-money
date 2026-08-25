## 1. Reconfirm the ECO-31 Baseline

- [x] 1.1 Re-read the ECO-31 issue boundary, all three living specs, active Changes, and the current worktree; confirm no new blocker, overlap, or semantic contradiction invalidates the zero-delta `skip_specs: true` decision before editing documentation.
- [x] 1.2 Trace the minimal Feed entry through current imports/callers and record that only Feed/Provider infrastructure is production-reachable, while ledger, candidate/event, market/state, watchlist, scoring, selection, and audit remain retained no-caller libraries.
- [x] 1.3 Reuse existing architectural tests as evidence for the absent LLM/model/credential surface, single minimal Feed entry, unchanged Feed contracts, and independently tested retained libraries; if a genuinely stale test assertion is found, stop and surface it before expanding scope.
- [x] 1.4 Search current-facing documentation for concrete future Agent object/pipeline definitions and ambiguous production-wiring claims, excluding archived Changes and dated historical evidence from remediation.

## 2. Align the Architecture Document

- [x] 2.1 Replace the concrete future topology in `docs/architecture.md` with the only live production topology: Evidence Providers -> deterministic evidence Feed -> Host Agent reasoning and narrative -> grounded research output.
- [x] 2.2 Present ledger, candidate/event utilities, market snapshot/state, watchlist, scoring/ranking, and `ClaimAuditor` as a non-sequential retained capability inventory that is typed, deterministic, reproducible, tested, reusable, and intentionally allowed to have no production orchestration caller.
- [x] 2.3 Replace positive future object names, schemas, stages, call counts, and ordering with the boundary-only statement that a future Skill-Agent Contract remains undefined until the Pre-Agent Baseline Acceptance gate passes.
- [x] 2.4 Review module and trust-boundary wording so it does not imply that the Feed invokes every deterministic object, while preserving the evidence-only Feed, Host Agent ownership, and all deterministic/fail-closed/provenance invariants.

## 3. Align Skill and README Claims

- [x] 3.1 Update `SKILL.md` so the minimal entry owns network access and deterministic Feed processing only, the Host Agent owns analysis and narrative, and retained post-Feed libraries are not claimed as entry-orchestrated.
- [x] 3.2 Update `README.md` to distinguish the live and tested Feed production path from tested retained libraries without a current production orchestration caller.
- [x] 3.3 Apply the same Live / Retained / Future distinction to `README.zh-CN.md` without changing capability meaning between languages.
- [x] 3.4 Repeat the scoped current-facing documentation search and correct only another proven equivalent inconsistency; leave archived Changes and historical validation records unchanged.

## 4. Verify the Aligned Baseline

- [x] 4.1 Inspect the final diff against the explicit allowlist (`docs/architecture.md`, `SKILL.md`, `README.md`, `README.zh-CN.md`, the `pyproject.toml` package description only, and this Change's planning/task state); confirm no runtime code, tests, living specs, configuration, Providers, schemas, formulas, dependencies or other build metadata, workflows, deployment files, archived Changes, or dated evidence changed.
- [x] 4.2 Verify by scoped searches and caller tracing that no current-facing artifact positively defines `ResearchContext`, `AgentAnalysis`, `BriefContext`, an equivalent future schema, or a fixed Agent pipeline, and that no retained library is newly described or wired as a live production stage.
- [x] 4.3 Run the focused existing architecture regressions: `.venv/bin/python -m pytest tests/test_no_llm_contract.py tests/test_workflows.py tests/test_neutralize_selection_and_scoring_contract.py tests/test_audit.py`.
- [x] 4.4 Run `openspec doctor`, `openspec validate align-pre-agent-living-baseline --strict`, and `openspec validate --all --strict`; confirm the Change is accepted with zero deltas because `skip_specs: true` is intentional.
- [x] 4.5 Run `.venv/bin/python scripts/quality_gate.py` and record the actual result; do not run a real-network Feed dry run for this documentation-only Change.
- [x] 4.6 Complete a final semantic review against all ECO-31 acceptance criteria, record any unresolved conflict or follow-up as future work, and leave ECO-32 implementation, archive, commit, and push for separately authorized workflows.
