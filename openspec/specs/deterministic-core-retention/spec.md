# deterministic-core-retention Specification

## Purpose
Define the retained post-removal contract: no embedded LLM runtime, a functional evidence-only Feed behind exactly one minimal internal invocation surface, deterministic rules with explicit caller boundaries, and credential-free fail-closed configuration.

## Requirements

### Requirement: No embedded LLM runtime
The repository SHALL NOT contain or invoke any LLM runtime: no OpenAI or other LLM SDK dependency, no LLM request adapter, no prompt files, no model or API-key configuration, no per-pass timeout/retry/token/reasoning controls, and no live LLM evaluation. The project SHALL NOT read any LLM credential, SHALL NOT know the model in use, and SHALL NOT execute any LLM request. Configuration loading SHALL succeed with no credential or model configured and SHALL fail closed only on deterministic contracts (providers, scoring, sessions, roles, safety lexicon).

#### Scenario: Repository audit finds no LLM surface
- **WHEN** a reviewer searches the repository for LLM couplings (LLM SDK imports, API-key environment variables, model configuration, prompt files, LLM request code)
- **THEN** none exist, and configuration loads and the Feed runs with no credential or model configured

#### Scenario: Legacy LLM artifacts are absent
- **WHEN** the repository state is inspected after this Change
- **THEN** no `llm` module, `prompts/` directory, LLM configuration section, or live-evaluation module exists, and the removed code is recoverable only from git history

### Requirement: Functional evidence-only Feed with one minimal internal invocation
The evidence-only Feed pipeline SHALL remain fully functional and SHALL remain invocable through exactly one minimal Feed entry used by the Agent/Skill. The public user-facing CLI product form with `brief`, `eval`, and `replay` subcommands and a `[project.scripts]` console entry SHALL NOT exist. A successful Feed run SHALL publish a Feed that validates against its schema, carries identity (run_id, evidence cutoff) and provider provenance, and requires no credential. The Feed entry SHALL preserve its accepted typed exit behavior independently of the separate private Agent invocation boundary. The Agent invocation boundary SHALL NOT wrap, replace, precede, or automatically invoke the Feed. The Feed entry SHALL return `0` for healthy or degraded success, `1` for planning, collection, runtime, schema, identity, integrity, deadline, rate-state, filesystem-execution, publication, or durability failure, and `2` for usage, configuration, invalid explicit invocation input, or startup-capability rejection. Expected exit categories SHALL be represented by explicit exception types or equivalent typed outcomes and SHALL NOT be inferred from exception-message text; parser-level invalid arguments SHALL retain `argparse` exit `2`.

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
- **THEN** they are deterministic, contain no LLM coupling, and preserve their accepted versioned behavior

#### Scenario: Approved Audit caller exists
- **WHEN** repository production callers are traced after ECO-50
- **THEN** only the private Agent invocation adapter calls `ClaimAuditor`, while scoring and ranking remain without a production orchestration caller

#### Scenario: No placeholder wiring exists
- **WHEN** the repository is inspected for calls into retained rules
- **THEN** no production caller supplies synthetic analysis inputs, no Feed or unrelated capability calls Audit, and no removed pipeline is reconstructed

### Requirement: Deterministic provenance, validation, and audit capability retained
The deterministic engine SHALL retain canonical digest utilities, Feed identity validation, Feed schema and semantic validation, and the safety audit as working capabilities. The serialized Feed SHALL be reproducible from the same inputs and validated against `feed.schema.json` together with its identity and digest invariants. Internal deterministic structures, including the ledger, candidate Components/grouping, market snapshot/state, watchlist, scoring intermediates, and ranking inputs, SHALL be protected by typed Python interfaces, domain invariants and validation, and deterministic tests; they SHALL NOT be required to have standalone JSON Schemas. Candidate Components/grouping SHALL remain transport-neutral and SHALL NOT retain or replace the removed semantic-Resolver request envelope.

#### Scenario: Feed identity and schema validation still gate publication
- **WHEN** a Feed is collected or a fixture Feed is loaded
- **THEN** `feed.schema.json` compliance, Feed semantic invariants, identity fields, and digest integrity are enforced by retained deterministic validation, with no credential and no dependency beyond the configured providers

#### Scenario: Internal structures use internal contracts
- **WHEN** the retained ledger, candidate, market, watchlist, scoring, or ranking structures are constructed or exercised
- **THEN** their correctness is enforced through their typed interfaces, applicable domain invariants and validation, and deterministic tests without requiring a standalone JSON Schema for each structure

#### Scenario: Candidate grouping stays transport-neutral
- **WHEN** the retained candidate library is inspected or exercised
- **THEN** it exposes deterministic candidate Components/grouping without a Resolver request Block, request-local alias, transport capacity, replacement batching abstraction, or standalone external candidate schema

#### Scenario: Safety audit applies to any submitted text
- **WHEN** the retained `ClaimAuditor` receives text containing prohibited trading instructions
- **THEN** it flags the violation using the configured safety lexicon and its descriptive exceptions

### Requirement: OpenSpec living baseline matches the active architecture
Current specs together with active Changes SHALL form a non-contradictory source of
truth for the Agent-driven Skill and deterministic financial engine. They SHALL NOT
positively require or imply an embedded LLM runtime, model SDK or request, model or
API-key configuration, prompts, token/retry/reasoning controls, standalone public
CLI, resolver/analyst/editor/language-audit pass, production Brief pipeline,
LLM-era Bundle or replay, or live model evaluation. They SHALL distinguish the live
Evidence Feed, the live on-demand Deterministic Audit boundary, and retained
deterministic libraries that still have no production orchestration caller. The
living baseline SHALL recognize the accepted Agent-facing schema and private
one-shot Audit runtime while leaving Event Structuring and every other deferred
capability's serialized contract, adapter, and production wiring undefined until a
later approved Change. Historical Changes under `openspec/changes/archive/` MAY preserve superseded requirements as
historical evidence and SHALL NOT be rewritten merely to match the current
architecture.

#### Scenario: Living source of truth is audited
- **WHEN** a reviewer reads all current specs and active Changes after ECO-50
- **THEN** every positive production requirement describes the existing Feed or approved Audit surface, or an explicit negative architecture invariant, with no requirement to restore a removed runtime or invent a deferred capability caller

#### Scenario: Historical Change is inspected
- **WHEN** an archived pre-removal or pre-ECO-50 Change describes a superseded architecture or caller status
- **THEN** it remains unchanged and is treated as history rather than a current requirement

#### Scenario: Future Agent workflow is searched
- **WHEN** the living baseline is inspected for Agent-facing schemas, runtime, adapters, or orchestration
- **THEN** only the accepted version-1 private Audit invocation boundary is concretely defined and implemented, while no fixed Agent pipeline, Event operation, generic registry, shared state, remote service, or deferred-capability wiring is prescribed

### Requirement: Baseline acceptance uses semantic trace evidence
Pre-Agent Baseline Acceptance SHALL maintain a fresh requirement-to-disposition-to-evidence trace for every current Requirement in `deterministic-core-retention`, `feed-evidence-pipeline`, and `deterministic-research-engine`. Each trace entry SHALL identify the current implementation or negative invariant, production caller status where architecture claims depend on wiring, focused executable or static-audit evidence, and an acceptance result. Every removed or superseded Requirement carried by the historical baseline trace or a subsequent baseline-changing Change SHALL retain an explicit current historical disposition, and historical trace material SHALL count as current evidence only after reconciliation with the current living specs, implementation, tests, subsequent Changes, and caller graph.

The baseline SHALL be accepted only when the complete current semantic trace is consistent with Production Feed regression evidence, retained deterministic-library regression evidence, no-LLM and architecture-boundary evidence, the canonical repository quality gate, `openspec doctor`, strict validation of the acceptance Change, strict validation of all OpenSpec artifacts, and a final semantic review across the governing issue scope, living requirements, implementation, tests, and current architecture documentation. Structural validity alone SHALL NOT constitute semantic acceptance. A positive production-stage claim SHALL have a verified real caller; a retained deterministic capability with no production orchestration caller SHALL be recorded as such and SHALL NOT be fake-wired for acceptance.

The Pre-Agent Baseline Acceptance Change SHALL alter no production code, tests, configuration, schema, provider behavior, financial formula, workflow, dependency, generated Feed data, deployment state, CI behavior, or unrelated worktree content merely to make its gate pass. It SHALL NOT define a future Agent contract, Agent-facing schema, runtime, invocation protocol, or fixed orchestration topology. Later implementation Changes MAY establish explicitly accepted bounded callers such as the ECO-50 Audit boundary; if a fresh baseline trace exposes missing evidence or a semantic contradiction outside its acceptance-only boundary, acceptance SHALL stop and record the unresolved scope decision rather than expanding that baseline Change silently.

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
