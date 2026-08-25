## MODIFIED Requirements

### Requirement: Baseline acceptance uses semantic trace evidence
Pre-Agent Baseline Acceptance SHALL maintain a fresh requirement-to-disposition-to-evidence trace for every current Requirement in `deterministic-core-retention`, `feed-evidence-pipeline`, and `deterministic-research-engine`. Each trace entry SHALL identify the current implementation or negative invariant, production caller status where architecture claims depend on wiring, focused executable or static-audit evidence, and an acceptance result. Every removed or superseded Requirement carried by the historical baseline trace or a subsequent baseline-changing Change SHALL retain an explicit current historical disposition, and historical trace material SHALL count as current evidence only after reconciliation with the current living specs, implementation, tests, subsequent Changes, and caller graph.

The baseline SHALL be accepted only when the complete current semantic trace is consistent with Production Feed regression evidence, retained deterministic-library regression evidence, no-LLM and architecture-boundary evidence, the canonical repository quality gate, `openspec doctor`, strict validation of the acceptance Change, strict validation of all OpenSpec artifacts, and a final semantic review across the governing issue scope, living requirements, implementation, tests, and current architecture documentation. Structural validity alone SHALL NOT constitute semantic acceptance. A positive production-stage claim SHALL have a verified real caller; a retained deterministic capability with no production orchestration caller SHALL be recorded as such and SHALL NOT be fake-wired for acceptance.

The accepted Change SHALL alter no production code, tests, configuration, schema, provider behavior, financial formula, workflow, dependency, generated Feed data, deployment state, CI behavior, or unrelated worktree content merely to make the gate pass. It SHALL NOT define a future Agent contract, Agent-facing schema, runtime, invocation protocol, or fixed orchestration topology. If the fresh trace exposes missing evidence or a semantic contradiction outside this acceptance-only boundary, acceptance SHALL stop and record the unresolved scope decision rather than expanding the Change silently.

#### Scenario: Structural validation passes with stale semantics
- **WHEN** an OpenSpec artifact is structurally valid but requires a module or path absent from current production
- **THEN** semantic tracing rejects it from the living baseline despite the structural pass

#### Scenario: Requirement trace is complete
- **WHEN** final acceptance reviews a living requirement
- **THEN** the trace identifies current implementation and focused test evidence or marks it as an explicit negative invariant with a corresponding audit

#### Scenario: Change scope is reviewed
- **WHEN** the Apply diff is compared with its explicit allowlist
- **THEN** only the authorized OpenSpec baseline, Change artifacts, and trace evidence differ, while production and unrelated files remain untouched

#### Scenario: Complete Pre-Agent baseline is evaluated
- **WHEN** the final Phase-3 acceptance decision is made
- **THEN** every current Requirement across all three living capabilities has one current trace entry with disposition, implementation or negative invariant, caller status where applicable, focused evidence, and an acceptance result
- **THEN** Production Feed, retained deterministic-library, no-LLM and architecture-boundary regressions pass through existing evidence, the canonical repository quality gate succeeds, required OpenSpec structural checks succeed, and final semantic review finds no contradiction

#### Scenario: Production and retained caller states are distinguished
- **WHEN** the trace evaluates a claimed production stage or a retained deterministic capability
- **THEN** each positive production-stage claim identifies a verified real caller and each intentionally retained no-caller capability is recorded without placeholder or automatic production wiring

#### Scenario: Historical trace evidence is reused
- **WHEN** an archived trace or removed or superseded requirement disposition is considered during current acceptance
- **THEN** it is retained as historical seed evidence only after its facts are reconciled with the current living specs, implementation, tests, subsequent Changes, and caller graph

#### Scenario: Acceptance evidence reveals a gap
- **WHEN** a current Requirement lacks sufficient executable or static-audit evidence or contradicts the architecture under evaluation
- **THEN** acceptance stops with an explicit unresolved scope decision and does not change production behavior, tests, or future Agent architecture merely to obtain a passing result

#### Scenario: Future Skill-Agent contract remains deferred
- **WHEN** the accepted baseline and its trace are inspected for Phase-4 architecture
- **THEN** no Agent-facing object, serialized schema, runtime, invocation protocol, or fixed orchestration topology has been introduced by the acceptance Change
