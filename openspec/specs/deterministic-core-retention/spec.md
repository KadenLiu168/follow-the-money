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
The evidence-only Feed pipeline SHALL remain fully functional and SHALL be invocable through exactly one minimal internal entry used by the Agent/Skill. The public user-facing CLI product form (with `brief`, `eval`, and `replay` subcommands and a `[project.scripts]` console entry) SHALL NOT exist. A successful Feed run SHALL publish a Feed that validates against its schema, carries identity (run_id, evidence cutoff) and provider provenance, and requires no credential.

#### Scenario: The Feed is collected by the Skill
- **WHEN** the minimal internal Feed entry runs against enabled verified providers
- **THEN** it publishes the evidence-only Feed to the output root with run identity, evidence cutoff, and per-item source provenance, and exits 0 with warnings on stderr

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
The deterministic engine SHALL retain canonical digest utilities, Feed identity validation, schema validation, and the safety audit as working capabilities. Every artifact the retained engine produces (Feed, ledger, candidate blocks, market snapshot, watchlist) SHALL be reproducible from the same inputs and validated against its schema.

#### Scenario: Feed identity and schema validation still gate publication
- **WHEN** a Feed is collected or a fixture Feed is loaded
- **THEN** identity fields and schema compliance are enforced by the retained deterministic validation, with no credential and no dependency beyond the configured providers

#### Scenario: Safety audit applies to any submitted text
- **WHEN** the retained `ClaimAuditor` receives text containing prohibited trading instructions
- **THEN** it flags the violation using the configured safety lexicon and its descriptive exceptions
