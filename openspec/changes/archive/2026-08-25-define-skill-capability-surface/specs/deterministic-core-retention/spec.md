## MODIFIED Requirements

### Requirement: OpenSpec living baseline matches the active architecture
Current specs together with active Changes SHALL form a non-contradictory source of
truth for the Agent-only Skill and deterministic financial engine. They SHALL NOT
positively require or imply an embedded LLM runtime, model SDK or request, model or
API-key configuration, prompts, token/retry/reasoning controls, standalone public
CLI, resolver/analyst/editor/language-audit pass, production Brief pipeline,
LLM-era Bundle or replay, or live model evaluation. They SHALL distinguish the one
live Feed path from retained deterministic libraries that have no production
orchestration caller. The living baseline MAY define an explicit semantic Skill
capability surface grounded in accepted deterministic behavior, but SHALL leave
Agent-facing objects and schemas, serialized Agent contracts, runtime invocation
protocols, adapters, orchestration topology, and production wiring for retained
libraries undefined until later Changes explicitly establish them. Historical
Changes under `openspec/changes/archive/` MAY preserve superseded requirements as
historical evidence and SHALL NOT be rewritten merely to match the current
architecture.

#### Scenario: Living source of truth is audited
- **WHEN** a reviewer reads all current specs and active Changes after normalization
- **THEN** every positive production requirement describes an existing current surface or an explicit negative architecture invariant, with no requirement to restore a removed runtime

#### Scenario: Historical Change is inspected
- **WHEN** an archived pre-removal Change describes the former internal-LLM or standalone architecture
- **THEN** it remains unchanged and is treated as history rather than a current requirement

#### Scenario: Future Agent workflow is searched
- **WHEN** the normalized baseline is inspected for `ResearchContext`, `AgentAnalysis`, `BriefContext`, Agent schemas, or Agent orchestration
- **THEN** those names appear only as explicitly deferred direction or non-goals and no current shape or runtime behavior is prescribed, even though the semantic Skill capability surface is now defined

