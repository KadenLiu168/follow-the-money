## Context

See `proposal.md` for motivation. The implementation already has two independent production surfaces: fixture-testable `follow_the_money.feed.cli.run_feed`, and the private one-shot `python -m follow_the_money.agent_invocation` boundary with static version-1 dispatch for exactly `audit.text`, `audit.claims`, and `event.structure`.

The living `agent-runtime-invocation-contract` already owns every durable integration semantic requested by ECO-52: explicit Host selection, operation independence, no mandatory order or implicit chaining, optional omission, closed dispatch, bounded authority, typed errors, and deferred capability status. This Change therefore uses `skip_specs: true`; acceptance mechanics and Phase 5 closeout evidence remain Change-local.

Existing ECO-50/ECO-51 tests already cover detailed schema variants, mapping, determinism, execution failures, and individual caller isolation. ECO-52 must add only the missing cross-surface acceptance evidence and must not turn test composition into production orchestration.

## Goals / Non-Goals

**Goals:**

- Exercise the real deterministic Feed execution function and the real subprocess Agent boundary in one Phase 5 acceptance module.
- Make every Host decision visible in test input, including two opposite explicit Audit/Event orders.
- Verify capability-local results are identical across order and omission, without transferring one result into the next request.
- Verify the closed operation surface, typed unsupported-operation failure, bounded result authority, and explicit `passed: false` critical Audit outcome.
- Reconfirm the deferred caller graph using the narrowest existing schema/source evidence.
- Correct only current-facing descriptions proven inconsistent with the implemented caller graph.

**Non-Goals:**

- Any production Host fixture, orchestration helper, workflow/session DTO, shared state, pipeline operation, capability discovery/registry, transport, model runtime, semantic evaluator, retry, rewrite, or automatic capability selection.
- Any change to Feed, Agent invocation, Audit, Event, Market, Watchlist, Confidence, Scoring, Ranking, schema, provider, configuration, dependency, or serialization behavior.
- Duplicating detailed ECO-50/ECO-51 unit matrices, changing living specs, modifying archived Changes, running a real-network Feed dry run, or delivering the Change.

## Decisions

### 1. Keep the Host fixture local to one acceptance test module

Create `tests/test_phase5_agent_integration.py` with a few private test helpers that accept already-complete requests or an explicit ordered request sequence. The helpers may reuse the established deterministic provider fixture (`CUTOFF` and `_fixture_registry`) and the existing subprocess invocation conventions, but they must not infer an operation, transform a prior result into a later input, keep session state, or become importable production code.

This is preferred over a production harness, generic orchestrator, reusable workflow object, or new fixture package because ECO-52 needs evidence only. A single test module is the smallest boundary that keeps the Host-owned decisions inspectable.

### 2. Exercise each production surface at its real acceptance seam

The Feed-only case calls `run_feed(output_root=tmp_path, cutoff=CUTOFF, providers_fn=_fixture_registry)` and validates the returned Feed through the existing schema and identity checks. It performs no Agent invocation.

Audit/Event cases start the existing `python -m follow_the_money.agent_invocation` process with one versioned JSON request and parse its one schema-valid JSON response. Direct `ClaimAuditor` or `build_event` calls are insufficient for these acceptance cases because they bypass the accepted Agent-facing classification, serialization, and failure boundary.

No network provider is used. The Feed fixture path is already the repository pattern for deterministic production-path testing.

### 3. Express independence through immutable Agent-owned requests

Construct one valid `audit.claims` request and one valid `event.structure` request before either sequence runs. Execute the exact same two request values in these explicit orders:

```text
event.structure -> audit.claims
audit.claims -> event.structure
```

Compare each operation's complete response with the same operation's response in the opposite order. The sequence helper only iterates over the supplied requests; it neither consumes a capability result nor creates the next request. Separate Audit-only and Event-only assertions prove optional omission without inventing an “optional capabilities” configuration mechanism.

### 4. Prove closure and bounded authority from observable contracts

Read the existing Agent invocation schema to assert that the request-operation constants are exactly `audit.text`, `audit.claims`, and `event.structure`. Submit one representative deferred operation, such as `market.state`, through the process boundary and require the existing non-zero `unsupported_operation` response with no `result`.

For successful Audit/Event responses, recursively inspect serialized field names and require the absence of `grounded`, `verified`, `entailed`, `factually_correct`, `answer_valid`, `admissible`, or equivalent authority upgrades already prohibited by the living contract. Preserve Agent-supplied evidence IDs only as references. Submit one deterministic critical Audit request and require process success, `passed: false`, and the unchanged critical finding.

This observable approach is preferred over a semantic judge because ECO-52 verifies bounded authority; it does not decide truth or entailment.

### 5. Reuse existing caller-graph checks and add only one missing closeout assertion

Existing tests already establish that Feed does not call the Agent boundary, `event.structure` has only the approved `build_event` caller and does not call Audit, Audit does not call Event, the invocation module contains no deferred capability/runtime machinery, and the architecture table retains the three deferred families. Keep those tests authoritative and include them in focused verification.

The new acceptance module should add only the integration-level closure assertion: the schema exposes exactly the three supported operations, a deferred operation fails through the real process boundary, and the two-order run produces only the two explicitly requested results. Do not add production instrumentation or repeat every source scan.

### 6. Apply a current-facing truthfulness allowlist

Audit the seven required files before editing. The initial trace establishes these contradictions:

- `src/follow_the_money/__init__.py` still calls the package a daily financial-intelligence pipeline and claims removed `follow-the-money` console entry points.
- `AGENTS.md` presents only the Feed topology and says Post-Feed deterministic libraries have no production caller, which is too broad now that Audit and Event Structuring have private on-demand callers.
- `pyproject.toml` describes only the Feed plus no-caller retained libraries and omits the live private Audit/Event surface.
- `README.md` and `README.zh-CN.md` label `src/follow_the_money/` as live Feed/Audit code while omitting the live Event boundary.

Correct only those exact statements with the shortest truthful wording. `SKILL.md` and `docs/architecture.md` currently describe independent on-demand Audit/Event use and deferred families accurately; leave them unchanged unless the Apply-time re-audit finds a concrete contradiction. Do not normalize tone or terminology elsewhere.

### 7. Preserve zero durable contract delta

Create no file under this Change's `specs/` directory and do not edit `openspec/specs/`. If Apply discovers a genuine externally meaningful contract defect rather than missing acceptance evidence, stop and report it for a separate scope decision instead of silently turning ECO-52 into a runtime-contract Change.

## Risks / Trade-offs

- [Risk] A test helper could look like a new orchestration abstraction. → Keep it private, stateless, test-local, and driven only by explicit complete requests.
- [Risk] Cross-module test fixture reuse can couple acceptance to test internals. → Reuse only stable repository fixtures already shared by tests; copy the minimal subprocess helper locally if importing it would cause pytest collection or unclear ownership.
- [Risk] Order-independence assertions could accidentally encode a pipeline. → Build both requests first and forbid result-to-request transformation.
- [Risk] Negative caller-graph checks can become brittle. → Reuse the existing focused caller/source checks and add no broad repository-wide import framework.
- [Risk] Documentation cleanup could expand into rewriting truthful files. → Use the explicit contradiction list and leave `SKILL.md`/`docs/architecture.md` untouched unless new evidence requires a narrow correction.
- [Risk] `skip_specs: true` could hide a real contract change. → Re-read the living invocation, grounding, responsibility, capability, Feed, and deterministic-engine specs during Apply; stop if acceptance requires behavior not already specified.

## Migration Plan

No runtime migration or deployment is required. Apply adds test evidence and current-facing wording only. Rollback is removal of the new acceptance module and reversal of attributable wording edits; production behavior and serialized contracts remain unchanged.
