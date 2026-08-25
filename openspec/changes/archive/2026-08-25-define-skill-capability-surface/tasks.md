## 1. Contract Boundary Review

- [x] 1.1 Reconcile the `skill-capability-surface` delta against the current `feed-evidence-pipeline` and `deterministic-research-engine` living requirements, confirming that all six semantic families are grounded in accepted behavior and no detailed formula, schema, or domain algorithm is duplicated.
- [x] 1.2 Verify the `deterministic-core-retention` delta changes only `OpenSpec living baseline matches the active architecture`, retains its complete inherited scenario set and exact scenario names, and leaves `Baseline acceptance uses semantic trace evidence` untouched.
- [x] 1.3 Confirm the catalog records Evidence Feed as `live-production`, all five post-Feed families as `retained-no-production-caller`, and capability ownership only as repository/Skill ownership of deterministic behavior and invariants.

## 2. Current-Facing Documentation Alignment

- [x] 2.1 Update `SKILL.md` to state that the semantic Skill capability surface is defined while responsibility, trust, grounding/validation, Agent schemas, invocation, orchestration, and runtime implementation remain deferred; preserve the current Feed-only live flow.
- [x] 2.2 Apply the same live-versus-retained and defined-versus-deferred distinction to `README.md` and `README.zh-CN.md` without adding a facade, workflow, or production capability claim.
- [x] 2.3 Update `docs/architecture.md` to present the six semantic capability families, their truthful execution status, and the internal-infrastructure exclusion while keeping detailed behavior owned by the existing living specs.
- [x] 2.4 Inspect `AGENTS.md` for a directly stale development gate; leave it unchanged unless a minimal factual synchronization is necessary, and do not turn it into a parallel product specification.

## 3. Static Architecture and Scope Verification

- [x] 3.1 Review the attributable diff and confirm no production code, tests, configuration, Provider contract/adapter, financial formula, dependency, workflow, generated Feed data, or unrelated worktree content changed.
- [x] 3.2 Inspect `schemas/` and confirm no Agent-facing or post-Feed schema was added and `feed.schema.json` remains the only current serialized external contract.
- [x] 3.3 Trace the minimal Feed entry and imports to confirm no runtime facade, Agent adapter, invocation protocol, orchestration layer, or post-Feed research import/caller was added and every retained family still lacks a production orchestration caller.
- [x] 3.4 Search current runtime/configuration surfaces for new LLM/model/API-key coupling, capability registry/status fields, placeholder wiring, and deferred Agent objects or protocols; fail the review if any appears outside explicit non-goal/deferred documentation.
- [x] 3.5 Confirm current-facing docs distinguish the semantic surface defined by ECO-33 from ECO-34 responsibility/mutation/trust decisions, ECO-35 grounding/validation/unsupported-claim decisions, and later runtime implementation.

## 4. Canonical Verification

- [x] 4.1 Run `.venv/bin/python scripts/quality_gate.py` and record the complete passing result without substituting a weaker custom test set.
- [x] 4.2 Run `openspec doctor`, `openspec validate define-skill-capability-surface --strict`, and `openspec validate --all --strict`; resolve any structural or semantic failure within ECO-33 scope.
- [x] 4.3 Perform a final requirement-to-artifact-to-caller-state review against all ECO-33 acceptance criteria, confirm no unresolved conflict or risk remains, and mark tasks complete only from fresh evidence.
