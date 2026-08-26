## 1. Contract Boundary Review

- [x] 1.1 Trace every `agent-grounding-validation-contract` requirement and scenario to the ECO-35 scope, confirming coverage of grounded factual assertions, evidence-reference versus semantic-support distinction, Host-Agent support assessment, bounded authority, deterministic findings, output admissibility, unsupported assertions, and semantic recovery.
- [x] 1.2 Reconcile the new contract against `feed-evidence-pipeline`, `deterministic-research-engine`, `skill-capability-surface`, and `skill-agent-responsibility-boundary`, confirming that detailed source and deterministic semantics remain authoritative in their governing living specs and are not duplicated or broadened.
- [x] 1.3 Compare each `MODIFIED` delta with its accepted living requirement, confirming complete requirement blocks and exact inherited scenario names are retained and only the ECO-35 deferrals and necessary cross-references change.
- [x] 1.4 Review the contract for false authority upgrades: evidence-reference presence is not semantic support, deterministic processing is not entailment, a deterministic pass is not complete answer validity, and Agent interpretation or conclusions do not become Skill-verified facts.
- [x] 1.5 Confirm admissibility and recovery remain semantic constraints only and define no retry count, automatic retry, rewrite loop, invocation order, call count, validator invocation, or recovery topology.

## 2. Current-Facing Documentation Alignment

- [x] 2.1 Update `docs/architecture.md` only where needed to replace ECO-35 deferrals with the accepted grounding, validation-authority, admissibility, unsupported-assertion, and semantic-recovery contract while keeping concrete Skill-Agent integration deferred.
- [x] 2.2 Update `SKILL.md` with the same defined-versus-deferred distinction while preserving Host-Agent reasoning/narrative ownership, the Feed-only live path, and retained-capability caller truth.
- [x] 2.3 Align `README.md` and `README.zh-CN.md` with `agent-grounding-validation-contract` without claiming automatic semantic validation, a final-answer validator, a runtime pipeline, or a new callable capability.
- [x] 2.4 Inspect documentation changes for duplicated normative domain rules or presentation-specific policy; keep living specs authoritative and introduce no Brief, fixed section, or prose-format requirement.

## 3. Behavioral and Architecture Regression

- [x] 3.1 Run the focused retained-audit regressions in `tests/test_audit.py` and `tests/test_no_llm_contract.py`, confirming deterministic stability, critical-finding semantics, no silent rewrite, and no Agent/Brief/Editor runtime dependency.
- [x] 3.2 Inspect `schemas/` and the attributable diff, confirming `feed.schema.json` is unchanged and remains the only current serialized external contract, with no Agent-facing Claim, audit, or final-output schema added.
- [x] 3.3 Trace Feed entries, imports, and retained-audit callers, confirming Feed remains evidence-only, Deterministic Audit remains `retained-no-production-caller`, and no Feed-to-retained-library or Agent-validation production wiring was introduced.
- [x] 3.4 Search the attributable changes and runtime/configuration surfaces for `ResearchContext`, `AgentAnalysis`, `BriefContext`, replacement Agent DTOs, promoted internal audit structures, validator services/facades, Agent adapters, MCP/RPC/HTTP interfaces, orchestration, shared runtime state, prompt/model/API-key coupling, or placeholder callers; fail the review if any prohibited construct was introduced.
- [x] 3.5 Review the attributable diff and confirm no production code, runtime behavior, dependency, provider, configuration, schema, generated Feed data, archived Change, or unrelated worktree content changed.

## 4. Canonical Verification

- [x] 4.1 Run `openspec doctor`, `openspec validate define-agent-grounding-validation-contract --strict`, and `openspec validate --all --strict`; resolve every in-scope structural or semantic failure.
- [x] 4.2 Run `.venv/bin/python scripts/quality_gate.py` and record the complete result without substituting a weaker custom gate or performing a networked Feed dry run.
- [x] 4.3 Perform a final requirement-to-delta-to-documentation-to-caller-state review against all ECO-35 acceptance criteria, record any unresolved conflict or risk, and mark tasks complete only from fresh evidence.
