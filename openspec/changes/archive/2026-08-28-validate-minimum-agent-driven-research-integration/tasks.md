## 1. Reconfirm the Accepted Phase 5 Boundary

- [x] 1.1 Re-read ECO-52 scope, `.openspec.yaml`, all six relevant living specs, active Changes, current worktree state, and the implemented Feed/Agent caller graph; confirm the prerequisite callers still exist and no overlap or blocker invalidates this acceptance-only Change.
- [x] 1.2 Confirm `agent-runtime-invocation-contract` already owns explicit independent invocation, no mandatory order or hidden chaining, optional omission, the exact version-1 operation set, typed fail-closed errors, bounded authority, and deferred capability status; keep `skip_specs: true`, create no delta spec, and stop for a separate scope decision if a genuine durable contract gap is found.
- [x] 1.3 Map existing focused evidence in `tests/test_agent_invocation_contract.py`, `tests/test_agent_invocation_runtime.py`, `tests/test_no_llm_contract.py`, and the Feed suites so the new Phase 5 module adds only missing integration acceptance rather than duplicating ECO-50/ECO-51 unit matrices.

## 2. Add Minimal Phase 5 Integration Acceptance

- [x] 2.1 Create `tests/test_phase5_agent_integration.py` with only private stateless test helpers: deterministic Feed fixture inputs, complete version-1 Agent requests, one real subprocess invocation helper, and an explicit sequence helper that iterates supplied requests without inference, result transformation, retry, state, or production reuse.
- [x] 2.2 Add the Feed-only acceptance case through `run_feed(..., providers_fn=_fixture_registry)`, validate schema and identity with existing validators, and assert a valid result is obtained without calling the Agent invocation boundary or requiring any post-Feed capability.
- [x] 2.3 Add independent Audit-only and Event-only cases through `python -m follow_the_money.agent_invocation`; assert each complete deterministic response while omitting Feed and the sibling operation.
- [x] 2.4 Preconstruct equivalent independent `audit.claims` and `event.structure` requests, execute `event.structure -> audit.claims` and `audit.claims -> event.structure`, and assert each capability-local response is identical across order with no result-to-request mapping.
- [x] 2.5 Assert the schema's request-operation constants are exactly `audit.text`, `audit.claims`, and `event.structure`; submit a representative deferred operation through the real process boundary and require the existing non-zero `unsupported_operation` error with no capability result.
- [x] 2.6 Add integration-level bounded-authority assertions for successful Audit/Event payloads, including preserved Agent evidence references and absence of semantic-grounding/factuality/admissibility proof fields; do not add a semantic evaluator.
- [x] 2.7 Submit one deterministic critical Audit case and assert process success, `passed: false`, and the unchanged applicable critical finding; verify the harness performs no rewrite, retry, or conversion to pass.
- [x] 2.8 Run `.venv/bin/python -m pytest tests/test_phase5_agent_integration.py tests/test_agent_invocation_contract.py tests/test_agent_invocation_runtime.py tests/test_no_llm_contract.py`; if an accepted production behavior fails, record the exact defect and stop rather than broadening ECO-52 into an unapproved runtime repair.

## 3. Align Only Demonstrably Stale Descriptions

- [x] 3.1 Re-audit `src/follow_the_money/__init__.py`, `AGENTS.md`, `pyproject.toml`, `README.md`, `README.zh-CN.md`, `SKILL.md`, and `docs/architecture.md` against the current schema, implementation, caller graph, and capability-status tests before editing any wording.
- [x] 3.2 Replace only the legacy package docstring claims in `src/follow_the_money/__init__.py` that describe a daily intelligence pipeline and removed `follow-the-money` console entry points; preserve imports, version, constants, and runtime behavior.
- [x] 3.3 Narrow the `AGENTS.md` architecture text so it includes the separate explicit on-demand Audit/Event boundary and limits the legal no-caller statement to Market, Confidence/Watchlist, and Scoring/Ranking; do not turn contributor guidance into a parallel runtime spec.
- [x] 3.4 Update only the `pyproject.toml` package description and the `README.md` / `README.zh-CN.md` repository-layout lines needed to acknowledge the live private Audit/Event surface; leave dependencies, build metadata, entry points, and already-truthful surrounding prose unchanged.
- [x] 3.5 Leave `SKILL.md` and `docs/architecture.md` unchanged if the re-audit confirms their independent on-demand topology, bounded authority, and deferred-family status are already truthful; correct only a newly demonstrated contradiction and record the evidence if one is found.
- [x] 3.6 Run scoped residue and parity checks over the seven audited files, confirming no current-facing claim still exposes the removed public console pipeline, calls Feed the only live production surface, marks Audit/Event retained without callers, or marks deferred families live.

## 4. Verify Scope and Closeout Evidence

- [x] 4.1 Run `uv sync --frozen --all-groups`, then rerun the focused Phase 5 acceptance and existing caller-graph regressions; do not run a real-network Feed dry run.
- [x] 4.2 Run `.venv/bin/python scripts/quality_gate.py` and record the actual complete result; do not substitute a smaller custom gate.
- [x] 4.3 Run `openspec doctor`, `openspec validate validate-minimum-agent-driven-research-integration --strict`, and `openspec validate --all --strict`; confirm the intentional zero-delta Change is accepted with `skip_specs: true`.
- [x] 4.4 Run `git diff --check` and inspect the complete diff against the allowlist: `tests/test_phase5_agent_integration.py`, only proven-stale files among the seven audited descriptions, and this Change's artifacts/task state. Confirm no production behavior, schema, living spec, archived Change, provider/configuration, dependency, workflow, Linear state, or unrelated file changed.
- [x] 4.5 Complete the Phase 5 acceptance review against all ECO-52 criteria, explicitly record unresolved conflicts or follow-up issues, and leave archive, commit, push, deployment, and Linear updates for separately authorized workflows.
