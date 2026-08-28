## Why

ECO-49 through ECO-51 established the minimum Phase 5 caller graph, but the repository has no single acceptance layer proving that the deterministic Feed and the independently selected Audit/Event operations behave together exactly as accepted. ECO-52 closes that evidence gap now that the prerequisite callers exist, without extending the runtime architecture.

## What Changes

- Add one small deterministic Phase 5 acceptance suite with a test-only Host-Agent fixture that explicitly drives the existing fixture-controlled Feed path and the existing private one-shot Agent invocation process.
- Prove Feed-only, Audit-only, Event-only, both explicit Audit/Event orders, optional omission, exact version-1 operation closure, typed fail-closed rejection, bounded authority, explicit critical Audit failure state, and absence of hidden downstream activation.
- Reuse existing focused ECO-50/ECO-51 tests and caller-graph evidence instead of duplicating their detailed unit coverage or adding production instrumentation.
- Audit `src/follow_the_money/__init__.py`, `AGENTS.md`, `pyproject.toml`, `README.md`, `README.zh-CN.md`, `SKILL.md`, and `docs/architecture.md`; correct only demonstrated contradictions with the implemented caller graph.
- Keep all production behavior, schemas, capability statuses, dependencies, Feed contracts, and private invocation version unchanged. Add no production harness, pipeline, registry, state, transport, model runtime, semantic evaluator, retry, rewrite, or deferred capability caller.

## Capabilities

### New Capabilities

None. Phase 5 acceptance is evidence for existing capabilities, not a new capability family.

### Modified Capabilities

None. `agent-runtime-invocation-contract` already requires the exact version-1 operation set, independent explicit invocation, no mandatory order or hidden chaining, optional use, typed fail-closed unsupported operations, bounded authority, and deferred capability status. This Change therefore declares `skip_specs: true` rather than duplicating accepted requirements.

## Impact

- Tests: one test-boundary Phase 5 integration acceptance module, reusing the existing deterministic Feed fixture path and invoking `python -m follow_the_money.agent_invocation` for Agent-facing scenarios.
- Current-facing descriptions: only files in the required truthfulness audit whose wording is demonstrably stale; confirmed candidates include the legacy package docstring in `src/follow_the_money/__init__.py` and the blanket no-caller statement in `AGENTS.md`.
- OpenSpec: proposal, design, and tasks only; no delta spec, living-spec edit, archived Change rewrite, or new capability.
- Runtime/API/dependencies: no intended change to production code behavior, JSON schemas, operation names, Feed behavior, provider/configuration contracts, dependencies, or caller graph.
