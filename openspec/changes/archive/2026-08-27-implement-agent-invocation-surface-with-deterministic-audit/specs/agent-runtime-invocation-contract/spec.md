## ADDED Requirements

### Requirement: Runtime classifies stdin as a request before dispatch
The invocation runtime SHALL parse stdin as exactly one UTF-8 JSON document and SHALL classify the parsed value as a supported request before dispatch. Validation against the root Agent invocation schema SHALL NOT by itself establish that a parsed value is a request because the root also accepts success and error responses. Classification SHALL be fail closed and SHALL apply this precedence without selecting categories from exception-message text: unparseable input as `invalid_json`; an explicitly supplied unsupported integer contract major as `unsupported_contract_version`; an explicitly named unsupported string operation as `unsupported_operation`; every other request-shape, field, type, identity, or supported-operation input failure as `invalid_request`; and an unexpected failure after a structurally valid supported request enters execution as `execution_failure`.

#### Scenario: Stdin is not exactly one JSON document
- **WHEN** stdin is empty, malformed, non-JSON, invalid UTF-8, or contains additional JSON values after the first document
- **THEN** the runtime emits one `invalid_json` error response and uses a non-zero process status

#### Scenario: Unsupported major takes precedence
- **WHEN** a parsed object explicitly supplies an integer `contract_version` other than `1`, including when another request field is missing or invalid
- **THEN** the runtime emits `unsupported_contract_version` without dispatching a capability

#### Scenario: Unsupported operation takes precedence after version
- **WHEN** a parsed object does not identify an unsupported major and explicitly names a string operation outside `audit.text` and `audit.claims`
- **THEN** the runtime emits `unsupported_operation` without dispatching a capability

#### Scenario: Parsed value is not a valid supported request
- **WHEN** the parsed value is response-shaped, error-response-shaped, missing request structure, contains unknown fields, mismatches operation and input, uses a wrong field type, contains a structurally invalid identity, or otherwise violates a supported operation's closed input contract
- **THEN** the runtime emits `invalid_request` and does not pass the invalid value into Deterministic Audit

#### Scenario: Accepted request fails during execution
- **WHEN** a structurally valid supported request enters the addressed Audit operation but execution unexpectedly cannot complete
- **THEN** the runtime emits one valid `execution_failure` response, claims no capability result, uses a non-zero process status, and emits no traceback on stdout

## MODIFIED Requirements

### Requirement: Phase 5 activation decisions do not change current runtime status
The Phase 5 activation matrix SHALL record: Evidence Feed remains live and unchanged; Deterministic Audit has the real production caller implemented by ECO-50 and therefore uses `live-production`; Evidence and Event Structuring remains approved for a later ECO-51 caller after Audit; Market Analytics and State, Confidence and Watchlist, and Scoring and Ranking remain deferred. An `activate` decision alone SHALL mean approval for a dedicated implementation Change rather than callability, runtime enablement, registry membership, or configuration. Execution status SHALL change only when the dedicated Change establishes and verifies a real production caller. After ECO-50, Audit SHALL be the only formerly retained family whose execution status changes.

#### Scenario: ECO-49 caller graph is inspected
- **WHEN** the implemented invocation boundary and production caller graph are traced
- **THEN** Evidence Feed and Deterministic Audit are `live-production`, the Host Agent can explicitly invoke only `audit.text` and `audit.claims` through the new boundary, and no Feed-to-Audit wiring exists

#### Scenario: Event Structuring remains deferred
- **WHEN** Evidence and Event Structuring is reviewed after ECO-50
- **THEN** it remains `retained-no-production-caller` with no Event operation, external Event payload, or production wiring and awaits its separate ECO-51 Change

#### Scenario: Deferred capability implementation is inspected
- **WHEN** Market, Confidence/Watchlist, or Scoring/Ranking libraries are reviewed after ECO-50
- **THEN** they remain valid retained implementations without being removed, fake-wired, exposed as operations, or marked live

### Requirement: Common invocation contract does not prescribe a research pipeline
Capability use SHALL remain explicitly selected and on demand by the Host Agent. The contract SHALL NOT require Feed as a first invocation step, automatic Audit invocation, automatic Feed-to-Event processing, operation order or count, retry or rewrite loops, narrative generation, automatic grounding or entailment judgment, investment recommendations, or trading execution. It SHALL NOT introduce HTTP, MCP, RPC, daemon, session, embedded LLM/model, credential, prompt, or fixed Resolver/Analyst/Editor/Brief pipeline machinery.

#### Scenario: Automatic capability sequence is sought
- **WHEN** a caller or implementation attempts to infer `Feed -> Audit`, `Feed -> Event`, or another mandatory capability sequence from this contract
- **THEN** no such sequence exists and each supported invocation remains an explicit Host-Agent choice

#### Scenario: Runtime implementation is inspected after ECO-50
- **WHEN** production code and entry paths are reviewed
- **THEN** exactly one private one-shot Agent invocation boundary statically dispatches only the two Audit operations, with no Event operation, registry, remote service, session framework, LLM runtime, automatic grounding system, retry, rewrite, or hidden capability chaining
