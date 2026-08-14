## ADDED Requirements

### Requirement: OpenSpec living baseline matches the active architecture
Current specs together with active Changes SHALL form a non-contradictory source of
truth for the Agent-only Skill and deterministic financial engine. They SHALL NOT
positively require or imply an embedded LLM runtime, model SDK or request, model or
API-key configuration, prompts, token/retry/reasoning controls, standalone public
CLI, resolver/analyst/editor/language-audit pass, production Brief pipeline,
LLM-era Bundle or replay, or live model evaluation. They SHALL distinguish the one
live Feed path from retained deterministic libraries that have no production
orchestration caller, and SHALL leave the future Agent Contract undefined.
Historical Changes under `openspec/changes/archive/` MAY preserve superseded
requirements as historical evidence and SHALL NOT be rewritten merely to match the
current architecture.

#### Scenario: Living source of truth is audited
- **WHEN** a reviewer reads all current specs and active Changes after normalization
- **THEN** every positive production requirement describes an existing current surface or an explicit negative architecture invariant, with no requirement to restore a removed runtime

#### Scenario: Historical Change is inspected
- **WHEN** an archived pre-removal Change describes the former internal-LLM or standalone architecture
- **THEN** it remains unchanged and is treated as history rather than a current requirement

#### Scenario: Future Agent workflow is searched
- **WHEN** the normalized baseline is inspected for `ResearchContext`, `AgentAnalysis`, `BriefContext`, Agent schemas, or Agent orchestration
- **THEN** those names appear only as explicitly deferred direction or non-goals and no current shape or runtime behavior is prescribed

### Requirement: Baseline acceptance uses semantic trace evidence
Normalization SHALL maintain a requirement-to-implementation-to-test trace for every
living requirement, including verified caller status for every claimed production
stage and explicit disposition for every removed or superseded requirement.
`openspec doctor` and strict validation SHALL remain mandatory structural gates but
SHALL NOT alone constitute semantic acceptance. The accepted Change SHALL alter no
production code, tests, configuration, schema, provider behavior, financial formula,
workflow, generated Feed data, deployment state, or unrelated worktree content.

#### Scenario: Structural validation passes with stale semantics
- **WHEN** an OpenSpec artifact is structurally valid but requires a module or path absent from current production
- **THEN** semantic tracing rejects it from the living baseline despite the structural pass

#### Scenario: Requirement trace is complete
- **WHEN** final acceptance reviews a living requirement
- **THEN** the trace identifies current implementation and focused test evidence or marks it as an explicit negative invariant with a corresponding audit

#### Scenario: Change scope is reviewed
- **WHEN** the Apply diff is compared with its explicit allowlist
- **THEN** only the authorized OpenSpec baseline, Change artifacts, and trace evidence differ, while production and unrelated files remain untouched
