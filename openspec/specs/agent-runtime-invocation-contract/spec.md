# agent-runtime-invocation-contract Specification

## Purpose
Define the minimum private Host-Agent process boundary for invoking selected deterministic Skill operations while preserving compatibility, failure, ownership, provenance, and bounded-authority semantics.

## Requirements

### Requirement: Invocation uses a private local one-shot JSON process boundary
The Host Agent SHALL invoke the boundary by starting a local process, writing exactly one UTF-8 JSON request to stdin, and receiving exactly one machine-readable UTF-8 JSON response on stdout. Stdout SHALL contain only the contract response, while operational diagnostics SHALL be written only to stderr. Each process SHALL handle one request without session state, conversational state, streaming, multiplexing, a long-lived daemon, shared mutable Agent/Skill workspace, or hidden capability chaining. The boundary SHALL be a private Host-Agent integration surface rather than a public end-user CLI product, and executable naming SHALL remain outside this stable semantic contract.

#### Scenario: One request executes successfully
- **WHEN** the Host Agent submits one valid supported request to the one-shot process
- **THEN** the process emits exactly one successful contract response on stdout, uses process-success status, and performs only the explicitly addressed operation

#### Scenario: Diagnostics are produced
- **WHEN** the invocation emits operational diagnostics
- **THEN** the diagnostics appear on stderr and do not contaminate the JSON response on stdout

#### Scenario: Stateful behavior is sought
- **WHEN** session continuation, conversation state, streaming, multiplexing, shared mutable workspace, or implicit operation chaining is requested
- **THEN** the invocation contract provides no such behavior

### Requirement: Requests use one closed versioned envelope
Every request SHALL be a closed JSON object containing exactly `contract_version`, `operation`, and `input`. The initial supported major `contract_version` SHALL be integer `1`. `operation` SHALL be one of the statically contracted namespaced operation identifiers, and `input` SHALL satisfy the addressed operation's closed input contract. Unknown fields, missing fields, malformed JSON, unsupported versions, unsupported operations, and inputs that fail the addressed operation contract SHALL fail closed as invocation errors.

#### Scenario: Supported request validates
- **WHEN** a request contains `contract_version: 1`, a supported operation, and a valid closed input for that operation
- **THEN** it validates as an invocation request

#### Scenario: Request contains an unknown field
- **WHEN** any request-envelope or operation-input object contains a field not defined by the contract
- **THEN** the request is rejected as an invocation error

#### Scenario: Unsupported major is submitted
- **WHEN** a request identifies a `contract_version` other than integer `1`
- **THEN** it fails closed with an `unsupported_contract_version` invocation error

#### Scenario: Unsupported operation is submitted
- **WHEN** a request names an operation not statically defined by the accepted contract
- **THEN** it fails closed with an `unsupported_operation` invocation error

### Requirement: Operation addressing is static and contract-governed
The initial operation set SHALL contain exactly `audit.text` and `audit.claims`. Operation identifiers SHALL describe stable Agent-facing semantics and SHALL NOT expose Python class, module, or method names as the compatibility boundary. The runtime SHALL NOT expose capability discovery, `list_capabilities`, a dynamic registry, or activation-matrix configuration. Adding another operation SHALL require an approved contract Change.

#### Scenario: Initial operation set is inspected
- **WHEN** the accepted Agent invocation contract is reviewed after ECO-49
- **THEN** only `audit.text` and `audit.claims` are defined and no Event, Market, Watchlist, Confidence, Scoring, or Ranking operation exists

#### Scenario: Discovery is requested
- **WHEN** a caller requests runtime capability discovery or a registry snapshot
- **THEN** no discovery operation or dynamic registry is available and supported operations remain defined by accepted contract and truthful documentation

### Requirement: Audit text input is minimal and closed
The `audit.text` input SHALL be a closed object containing required non-empty string `text` and optional non-empty string `claim_id`. The input SHALL expose no Host-Agent override for the Skill-owned Audit safety policy or lexicon.

#### Scenario: Text Audit request is valid
- **WHEN** `audit.text` receives non-empty `text` and, if present, a non-empty `claim_id`, with no other fields
- **THEN** the input validates for deterministic text auditing under Skill-owned policy

#### Scenario: Caller supplies Audit policy
- **WHEN** an `audit.text` request attempts to supply prohibited terms, exceptions, policy, lexicon, or equivalent configuration
- **THEN** the closed input rejects the request as an invocation error

### Requirement: Structured Audit input promotes only necessary Agent-facing values
The `audit.claims` input SHALL be a closed object containing `claims`, `submitted_claim_ids`, and optional `flows`. Each claim SHALL be a closed object containing non-empty string `claim_id`, string `text`, boolean `requires_direct_evidence`, and an array of non-empty string `evidence_ids`. Each flow SHALL be a closed object containing boolean `confirmed` and `owning_event_id`, where `owning_event_id` is either a non-empty string or null. The arrays MAY be empty so capability-local rules such as `empty_inventory` remain deterministic findings. These fields SHALL be a separate Agent-facing representation mapped by ECO-50 and SHALL NOT promote internal Python structure layout or expose Skill-owned Audit configuration.

#### Scenario: Structured Audit request is valid
- **WHEN** `audit.claims` receives only the contracted claim inventory, submitted identities, and optional flow ownership values with valid field types
- **THEN** the input validates without requiring a Brief, Editor, Agent object, workflow object, or internal Python serialization

#### Scenario: Empty inventory is submitted
- **WHEN** `audit.claims` receives an empty `claims` array in an otherwise valid input
- **THEN** invocation validation succeeds and the Audit capability may return its deterministic critical `empty_inventory` finding

#### Scenario: Required identity is structurally invalid
- **WHEN** a claim, submitted claim, evidence reference, or non-null owning Event identity is missing, empty, whitespace-only, or has the wrong JSON type
- **THEN** the operation input fails closed as an invocation error rather than entering the deterministic capability

#### Scenario: Evidence references are supplied
- **WHEN** Agent-owned evidence identifiers cross the invocation boundary
- **THEN** they remain Agent-supplied references and their presence does not establish semantic support, entailment, or verified grounding

### Requirement: Successful responses carry bounded Audit results
A successful response SHALL be a closed object containing `contract_version: 1`, the executed `operation`, and `result`. For both Audit operations, `result` SHALL be a closed object containing boolean `passed` and ordered `findings`. Each finding SHALL be a closed object containing nullable `claim_id`, a contracted Audit `category`, non-empty `detail`, and `severity` equal to `critical` or `warning`. The initial categories SHALL be `trading_instruction`, `empty_inventory`, `invalid_claim_id`, `duplicate_claim_id`, `outside_inventory`, `missing_evidence`, and `flow_ownership`. The response SHALL preserve the exact deterministic result and stable finding order produced through the governing Audit semantics.

#### Scenario: Audit passes
- **WHEN** a supported Audit operation executes and returns no applicable critical finding
- **THEN** stdout contains a successful capability response with `passed: true` and the process uses process-success status

#### Scenario: Audit returns a critical finding
- **WHEN** a supported Audit operation executes and returns an applicable critical finding
- **THEN** stdout contains a successful capability response with `passed: false`, the critical finding remains explicit with its category and severity, and the process still uses process-success status

#### Scenario: Audit result would be silently changed
- **WHEN** an integration layer would suppress a finding, alter its severity or category, or rewrite `passed: false` as a pass
- **THEN** the integration violates the invocation contract

### Requirement: Invocation errors are typed and separate from capability results
An invocation failure SHALL emit a closed response containing `contract_version: 1` and an `error` object with non-empty `code` and `message`, and SHALL use process-failure status. Initial error codes SHALL be `invalid_json`, `unsupported_contract_version`, `unsupported_operation`, `invalid_request`, and `execution_failure`. An error response SHALL NOT contain a capability `result`, and a successful capability response SHALL NOT contain `error`. Process status SHALL NOT substitute for the Audit result's `passed` state. Exact non-zero numeric exit-code taxonomy SHALL remain outside the stable contract.

#### Scenario: Malformed JSON is submitted
- **WHEN** stdin does not contain one parseable JSON request
- **THEN** stdout contains one version-1 `invalid_json` error response and the process uses a non-zero status

#### Scenario: Operation input is out of contract
- **WHEN** a supported operation receives input that fails its closed input contract
- **THEN** stdout contains one `invalid_request` error response, no Audit result is claimed, and the process uses a non-zero status

#### Scenario: Requested operation cannot execute
- **WHEN** the boundary cannot execute an otherwise accepted operation according to the invocation contract
- **THEN** stdout contains one `execution_failure` error response and the process uses a non-zero status

### Requirement: One major version governs the Agent-facing boundary
Requests and responses SHALL identify major contract version `1`. Breaking changes to the common envelope, operation meaning, or an existing operation's accepted input/result semantics SHALL require a new major version. Compatible clarifications or additions that do not invalidate version-1 messages MAY remain within major version `1`. Internal Python refactoring that preserves the serialized Agent-facing contract SHALL NOT require a contract-version change. ECO-49 SHALL NOT create per-field, per-capability, or per-operation version systems.

#### Scenario: Internal implementation is refactored
- **WHEN** internal Python structures or mappings change while every version-1 serialized behavior remains compatible
- **THEN** the Agent contract version remains `1`

#### Scenario: Existing operation meaning would break
- **WHEN** a later Change would make a valid version-1 request invalid or change the contracted meaning of its result
- **THEN** that breaking Agent-boundary change requires a new major contract version

### Requirement: Invocation preserves ownership provenance and bounded authority
Agent-originated assertions, interpretations, classifications, hypotheses, research selections, narrative text, and identifiers SHALL remain Agent-owned after boundary crossing and deterministic processing. The Skill SHALL own only the deterministic transformation or finding and the exact invariants guaranteed by the operation's governing living spec. Boundary crossing or deterministic success SHALL NOT upgrade provenance, verification status, factual status, grounding, semantic support, entailment, complete answer correctness, or final-output admissibility. The serialized result SHALL NOT expose or imply `grounded`, `factually_correct`, `entailed`, `answer_valid`, or equivalent proof fields.

#### Scenario: Agent assertion passes Audit
- **WHEN** an Agent-originated assertion passes every deterministic Audit rule exercised by the requested operation
- **THEN** the assertion remains Agent-owned and the pass proves only those bounded Audit rules, not grounding, factuality, entailment, answer correctness, or admissibility

#### Scenario: Skill result crosses the boundary
- **WHEN** an Audit result is returned to the Host Agent
- **THEN** the Skill owns the deterministic finding within `deterministic-research-engine`, while the Host Agent retains recovery and constrained final-emission ownership under `agent-grounding-validation-contract`

### Requirement: Phase 5 activation decisions do not change current runtime status
The Phase 5 activation matrix SHALL record: Evidence Feed remains live and unchanged; Deterministic Audit is approved to receive a production caller in ECO-50; Evidence and Event Structuring is approved to receive a production caller after Audit in ECO-51; Market Analytics and State, Confidence and Watchlist, and Scoring and Ranking are deferred. `activate` SHALL mean approval for a later dedicated implementation Change, not immediate callability, `live-production` status, runtime enablement, registry membership, or configuration. After ECO-49, Audit and Event Structuring SHALL remain `retained-no-production-caller`.

#### Scenario: ECO-49 caller graph is inspected
- **WHEN** this contract-first Change is complete
- **THEN** Feed remains the only `live-production` family, Audit and Event Structuring remain `retained-no-production-caller`, and no Feed-to-retained or Agent-to-retained production wiring exists

#### Scenario: Deferred capability implementation is inspected
- **WHEN** Market, Confidence/Watchlist, or Scoring/Ranking libraries are reviewed after ECO-49
- **THEN** they remain valid retained implementations without being removed, fake-wired, exposed as operations, or marked live

### Requirement: Common invocation contract does not prescribe a research pipeline
Capability use SHALL remain explicitly selected and on demand by the Host Agent. The contract SHALL NOT require Feed as a first invocation step, automatic Audit invocation, automatic Feed-to-Event processing, operation order or count, retry or rewrite loops, narrative generation, automatic grounding or entailment judgment, investment recommendations, or trading execution. It SHALL NOT introduce HTTP, MCP, RPC, daemon, session, embedded LLM/model, credential, prompt, or fixed Resolver/Analyst/Editor/Brief pipeline machinery.

#### Scenario: Automatic capability sequence is sought
- **WHEN** a caller or implementation attempts to infer `Feed -> Audit`, `Feed -> Event`, or another mandatory capability sequence from this contract
- **THEN** no such sequence exists and each supported invocation remains an explicit Host-Agent choice

#### Scenario: Runtime implementation is inspected after ECO-49
- **WHEN** production code and entry paths are reviewed
- **THEN** no invocation executable, adapter, caller, registry, remote service, session framework, LLM runtime, automatic grounding system, or Event operation has been introduced
