## MODIFIED Requirements

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

### Requirement: Deterministic provenance, validation, and audit capability retained
The deterministic engine SHALL retain canonical digest utilities, Feed identity validation, Feed schema and semantic validation, and the safety audit as working capabilities. Persisted external artifacts SHALL be validated at their explicit contract boundaries. The retained Feed SHALL be reproducible from the same inputs and SHALL validate against `feed.schema.json` together with its semantic, identity, and digest invariants. Internal deterministic structures, including the ledger, candidate blocks, market snapshot, market state, watchlist, scoring intermediates, and selection inputs, SHALL be protected by typed Python interfaces, domain invariants and validation, and deterministic tests; they SHALL NOT be required to have standalone JSON Schemas.

#### Scenario: Feed identity and schema validation still gate publication
- **WHEN** a Feed is collected or a fixture Feed is loaded
- **THEN** `feed.schema.json` compliance, Feed semantic invariants, identity fields, and digest integrity are enforced by retained deterministic validation, with no credential and no dependency beyond the configured providers

#### Scenario: Internal structures use internal contracts
- **WHEN** the retained ledger, candidate, market, watchlist, scoring, or selection structures are constructed or exercised
- **THEN** their correctness is enforced through their typed interfaces, applicable domain invariants and validation, and deterministic tests without requiring a standalone JSON Schema for each structure

#### Scenario: Safety audit applies to any submitted text
- **WHEN** the retained `ClaimAuditor` receives text containing prohibited trading instructions
- **THEN** it flags the violation using the configured safety lexicon and its descriptive exceptions
