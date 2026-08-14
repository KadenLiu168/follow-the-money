# deterministic-core-retention Specification

## Purpose
Define the retained post-removal contract: no embedded LLM runtime, a functional evidence-only Feed behind exactly one minimal internal invocation surface, retained deterministic rules with tests and no production wiring, and credential-free fail-closed configuration.

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
The evidence-only Feed pipeline SHALL remain fully functional and SHALL be invocable through exactly one minimal internal entry used by the Agent/Skill. The public user-facing CLI product form (with `brief`, `eval`, and `replay` subcommands and a `[project.scripts]` console entry) SHALL NOT exist. A successful Feed run SHALL publish a Feed that validates against its schema, carries identity (run_id, evidence cutoff) and provider provenance, and requires no credential. The internal entry SHALL return `0` for healthy or degraded success, `1` for planning, collection, runtime, schema, identity, integrity, deadline, rate-state, filesystem-execution, publication, or durability failure, and `2` for usage, configuration, invalid explicit invocation input, or startup-capability rejection. Expected exit categories SHALL be represented by explicit exception types or equivalent typed outcomes and SHALL NOT be inferred from exception-message text; parser-level invalid arguments SHALL retain `argparse` exit `2`.

#### Scenario: The Feed is collected by the Skill
- **WHEN** the minimal internal Feed entry runs against enabled verified providers and completes with healthy or degraded status
- **THEN** it publishes the evidence-only Feed to the output root with run identity, evidence cutoff, and per-item source provenance, and exits `0` with warnings on stderr

#### Scenario: Input or startup rejection has a typed exit
- **WHEN** the invocation, explicit cutoff or window, configuration, enabled-provider set, or required startup capability is invalid before Feed execution can proceed
- **THEN** the internal entry reports the typed failure without an uncaught traceback and exits `2` without inspecting the error message

#### Scenario: Valid invocation fails during execution
- **WHEN** a valid invocation fails during planning, collection, runtime, validation, integrity checking, deadline enforcement, rate-state handling, filesystem execution, publication, or durability handling
- **THEN** the internal entry reports the typed failure and exits `1` without inspecting the error message

#### Scenario: Error wording does not select the exit category
- **WHEN** an input-category error and an execution-category error contain arbitrary or misleading words such as `config`, `invalid`, `provider`, or `non_advancing`
- **THEN** each exit code is determined only by its explicit type or typed outcome and remains respectively `2` or `1`

#### Scenario: Only the Feed entry is exposed
- **WHEN** the invocation surface is inspected
- **THEN** exactly the minimal Feed entry exists; the `brief`, `eval`, and `replay` subcommands and the standalone console script are absent

### Requirement: Deterministic domain rules retained without production wiring
The deterministic rules that remain valuable SHALL be retained as pure tested functions with no production pipeline caller: scoring (significance, morning relevance, priority), selection (eligibility, formats, family penalty, coexistence), and the `ClaimAuditor` safety lexicon and trading-instruction audit. This Change SHALL NOT introduce placeholder architecture that fakes analysis inputs or re-wires these functions to make a removed pipeline appear functional.

#### Scenario: Retained rules stay pure and tested
- **WHEN** the retained scoring, selection, and audit modules are imported
- **THEN** they are deterministic, contain no LLM coupling, and their tests pass unchanged in behavior

#### Scenario: No placeholder wiring exists
- **WHEN** the repository is inspected for calls into the retained rules
- **THEN** no production caller supplies synthetic analysis inputs; the rules exist as library code awaiting the future Agent contract

### Requirement: Deterministic provenance, validation, and audit capability retained
The deterministic engine SHALL retain canonical digest utilities, Feed identity validation, Feed schema and semantic validation, and the safety audit as working capabilities. The serialized Feed SHALL be reproducible from the same inputs and validated against `feed.schema.json` together with its identity and digest invariants. Internal deterministic structures, including the ledger, candidate blocks, market snapshot/state, watchlist, scoring intermediates, and selection inputs, SHALL be protected by typed Python interfaces, domain invariants and validation, and deterministic tests; they SHALL NOT be required to have standalone JSON Schemas.

#### Scenario: Feed identity and schema validation still gate publication
- **WHEN** a Feed is collected or a fixture Feed is loaded
- **THEN** `feed.schema.json` compliance, Feed semantic invariants, identity fields, and digest integrity are enforced by retained deterministic validation, with no credential and no dependency beyond the configured providers

#### Scenario: Internal structures use internal contracts
- **WHEN** the retained ledger, candidate, market, watchlist, scoring, or selection structures are constructed or exercised
- **THEN** their correctness is enforced through their typed interfaces, applicable domain invariants and validation, and deterministic tests without requiring a standalone JSON Schema for each structure

#### Scenario: Safety audit applies to any submitted text
- **WHEN** the retained `ClaimAuditor` receives text containing prohibited trading instructions
- **THEN** it flags the violation using the configured safety lexicon and its descriptive exceptions

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
