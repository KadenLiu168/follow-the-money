## 1. Contract Boundary Review

- [x] 1.1 Trace every `skill-agent-responsibility-boundary` requirement to the ECO-34 scope, confirming that Host Agent, Skill, and internal deterministic-engine responsibilities; result/information ownership; mutation/derivation ownership; and provenance/authority preservation are all normative and non-duplicative.
- [x] 1.2 Compare the `skill-capability-surface` MODIFIED delta with the accepted requirement, confirming that it retains the complete requirement block and exact inherited scenario names, changes only the ECO-34 deferral, and leaves the six-family taxonomy and execution statuses unchanged.
- [x] 1.3 Reconcile both deltas against `feed-evidence-pipeline`, `deterministic-research-engine`, and `deterministic-core-retention`, confirming that detailed domain rules remain authoritative there and that Feed provenance, identity, digest, verification, validation, fail-closed, ordering, coverage, and degradation semantics are unchanged.
- [x] 1.4 Confirm the responsibility boundary does not decide ECO-35 grounding sufficiency, final-output validation ownership, unsupported-claim emission/handling, acceptance/rejection, retry, rewrite, or recovery policy.

## 2. Current-Facing Documentation Alignment

- [x] 2.1 Update `SKILL.md` only where needed to replace stale ECO-34 deferral language with the accepted responsibility, mutation/derivation ownership, and provenance/authority boundary while preserving the Feed-only live path and retained-capability caller truth.
- [x] 2.2 Apply the same defined-versus-deferred distinction to `docs/architecture.md`, keeping the deterministic engine internal to the Skill and avoiding any call graph, facade, protocol, or Agent-callable claim.
- [x] 2.3 Align `README.md` and `README.zh-CN.md` with the accepted boundary while leaving ECO-35 policy and later Agent schema/invocation/orchestration/runtime decisions deferred.
- [x] 2.4 Inspect documentation changes for duplicated normative domain rules; keep OpenSpec living specs authoritative and remove any documentation claim that exceeds them.

## 3. Static Architecture and Scope Verification

- [x] 3.1 Review the attributable diff and confirm no production code, runtime test, configuration, Provider contract/adapter, dependency, financial formula, generated Feed data, workflow, or unrelated worktree content changed; specifically confirm `src/follow_the_money/boundary.py` is untouched.
- [x] 3.2 Inspect `schemas/` and confirm no Agent-facing DTO/schema, trust/confidence metadata, or post-Feed serialized contract was added and `feed.schema.json` remains the only current serialized external contract.
- [x] 3.3 Trace current entries, imports, and callers to confirm the Evidence Feed remains the only `live-production` family, all five post-Feed families remain `retained-no-production-caller`, and no retained capability is represented or wired as currently Agent-callable.
- [x] 3.4 Search runtime and configuration surfaces for a new facade, tool endpoint, MCP/RPC/HTTP contract, adapter, invocation protocol, orchestration, shared state/session/persistence contract, placeholder caller, Agent runtime, LLM/model/API-key coupling, trust enum, policy engine, or capability-status registry; fail the review if any is introduced.
- [x] 3.5 Perform a semantic mutation review confirming that consumer-derived values cannot be represented as unchanged Skill results, Agent-originated assertions remain Agent-owned, and deterministic processing does not silently upgrade their provenance or authority.

## 4. Canonical Verification

- [x] 4.1 Run `openspec doctor`, `openspec validate define-skill-agent-responsibility-boundary --strict`, and `openspec validate --all --strict`; resolve every in-scope structural or semantic failure.
- [x] 4.2 Run `.venv/bin/python scripts/quality_gate.py` and record the complete result without substituting a weaker custom gate or performing a networked Feed dry run.
- [x] 4.3 Perform a final requirement-to-artifact-to-caller-state review against all ECO-34 acceptance criteria, record any unresolved conflict or risk, and mark tasks complete only from fresh evidence.
