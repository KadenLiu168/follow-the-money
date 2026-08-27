## MODIFIED Requirements

### Requirement: Functional evidence-only Feed with one minimal internal invocation
The evidence-only Feed pipeline SHALL remain fully functional and SHALL remain invocable through exactly one minimal Feed entry used by the Agent/Skill. The public user-facing CLI product form with `brief`, `eval`, and `replay` subcommands and a `[project.scripts]` console entry SHALL NOT exist. A successful Feed run SHALL publish a Feed that validates against its schema, carries identity and provider provenance, and requires no credential. The Feed entry SHALL preserve its accepted typed exit behavior independently of the separate private Agent invocation boundary. The Agent invocation boundary SHALL NOT wrap, replace, precede, or automatically invoke the Feed.

#### Scenario: The Feed is collected by the Skill
- **WHEN** the minimal internal Feed entry runs against enabled verified providers and completes with healthy or degraded status
- **THEN** it publishes the evidence-only Feed to the output root with run identity, evidence cutoff, and per-item source provenance, and exits `0` with warnings on stderr

#### Scenario: Input or startup rejection has a typed exit
- **WHEN** the Feed invocation, explicit cutoff or window, configuration, enabled-provider set, or required startup capability is invalid before Feed execution can proceed
- **THEN** the Feed entry reports the typed failure without an uncaught traceback and exits `2` without inspecting the error message

#### Scenario: Valid invocation fails during execution
- **WHEN** a valid Feed invocation fails during planning, collection, runtime, validation, integrity checking, deadline enforcement, rate-state handling, filesystem execution, publication, or durability handling
- **THEN** the Feed entry reports the typed failure and exits `1` without inspecting the error message

#### Scenario: Error wording does not select the exit category
- **WHEN** an input-category error and an execution-category error contain arbitrary or misleading words such as `config`, `invalid`, `provider`, or `non_advancing`
- **THEN** each Feed exit code is determined only by its explicit type or typed outcome and remains respectively `2` or `1`

#### Scenario: Only the Feed entry is exposed
- **WHEN** repository entry paths are traced after ECO-50
- **THEN** exactly one minimal Feed entry and one separate private one-shot Audit invocation boundary exist, neither calls the other, and no removed public CLI subcommand or console script has returned

### Requirement: Deterministic domain rules retain explicit caller boundaries
The deterministic rules that remain valuable SHALL remain pure and tested. Scoring and ranking SHALL continue to have no production orchestration caller. `ClaimAuditor` safety-lexicon and trading-instruction rules SHALL gain exactly one approved production caller through the private Host-Agent invocation boundary. No production caller SHALL supply synthetic analysis inputs, fake a removed pipeline, or wire Feed, Event, Market, Watchlist, Confidence, Scoring, or Ranking into Audit.

#### Scenario: Retained rules stay pure and tested
- **WHEN** the retained scoring, ranking, and audit modules are imported
- **THEN** they remain deterministic, contain no LLM coupling, and preserve their accepted versioned behavior

#### Scenario: Approved Audit caller exists
- **WHEN** repository production callers are traced after ECO-50
- **THEN** only the private Agent invocation adapter calls `ClaimAuditor`, while scoring and ranking remain without a production orchestration caller

#### Scenario: No placeholder wiring exists
- **WHEN** the repository is inspected for calls into retained rules
- **THEN** no production caller supplies synthetic analysis inputs, no Feed or unrelated capability calls Audit, and no removed pipeline is reconstructed

### Requirement: OpenSpec living baseline matches the active architecture
Current specs together with active Changes SHALL form a non-contradictory source of truth for the Agent-driven Skill and deterministic financial engine. They SHALL NOT positively require or imply an embedded LLM runtime, model SDK or request, model or API-key configuration, prompts, token/retry/reasoning controls, standalone public CLI, resolver/analyst/editor/language-audit pass, production Brief pipeline, LLM-era Bundle or replay, or live model evaluation. They SHALL distinguish the live Evidence Feed, the live on-demand Deterministic Audit boundary, and retained deterministic libraries that still have no production orchestration caller. The living baseline SHALL recognize the accepted Agent-facing schema and private one-shot Audit runtime while leaving Event Structuring and every other deferred capability's serialized contract, adapter, and production wiring undefined until a later approved Change. Historical Changes under `openspec/changes/archive/` MAY preserve superseded requirements as historical evidence and SHALL NOT be rewritten merely to match the current architecture.

#### Scenario: Living source of truth is audited
- **WHEN** a reviewer reads all current specs and active Changes after ECO-50
- **THEN** every positive production requirement describes the existing Feed or approved Audit surface, or an explicit negative architecture invariant, with no requirement to restore a removed runtime or invent a deferred capability caller

#### Scenario: Historical Change is inspected
- **WHEN** an archived pre-removal or pre-ECO-50 Change describes a superseded architecture or caller status
- **THEN** it remains unchanged and is treated as history rather than a current requirement

#### Scenario: Future Agent workflow is searched
- **WHEN** the living baseline is inspected for Agent-facing schemas, runtime, adapters, or orchestration
- **THEN** only the accepted version-1 private Audit invocation boundary is concretely defined and implemented, while no fixed Agent pipeline, Event operation, generic registry, shared state, remote service, or deferred-capability wiring is prescribed

## RENAMED Requirements

- FROM: `### Requirement: Deterministic domain rules retained without production wiring`
- TO: `### Requirement: Deterministic domain rules retain explicit caller boundaries`
