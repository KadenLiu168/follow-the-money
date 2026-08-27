## MODIFIED Requirements

### Requirement: Runtime classifies stdin as a request before dispatch
The invocation runtime SHALL parse stdin as exactly one UTF-8 JSON document and SHALL classify the parsed value as a supported request before dispatch. Validation against the root Agent invocation schema SHALL NOT by itself establish that a parsed value is a request because the root also accepts success and error responses. Classification SHALL be fail closed and SHALL apply this precedence without selecting categories from exception-message text: unparseable input as `invalid_json`; an explicitly supplied unsupported integer contract major as `unsupported_contract_version`; an explicitly named unsupported string operation as `unsupported_operation`; every other request-shape, field, type, identity, consistency, or supported-operation input failure as `invalid_request`; and an unexpected failure after a structurally valid supported request enters execution as `execution_failure`.

#### Scenario: Stdin is not exactly one JSON document
- **WHEN** stdin is empty, malformed, non-JSON, invalid UTF-8, or contains additional JSON values after the first document
- **THEN** the runtime emits one `invalid_json` error response and uses a non-zero process status

#### Scenario: Unsupported major takes precedence
- **WHEN** a parsed object explicitly supplies an integer `contract_version` other than `1`, including when another request field is missing or invalid
- **THEN** the runtime emits `unsupported_contract_version` without dispatching a capability

#### Scenario: Unsupported operation takes precedence after version
- **WHEN** a parsed object does not identify an unsupported major and explicitly names a string operation outside `audit.text`, `audit.claims`, and `event.structure`
- **THEN** the runtime emits `unsupported_operation` without dispatching a capability

#### Scenario: Parsed value is not a valid supported request
- **WHEN** the parsed value is response-shaped, error-response-shaped, missing request structure, contains unknown fields, mismatches operation and input, uses a wrong field type, contains a structurally invalid identity, violates Event provenance consistency, or otherwise violates a supported operation's closed input contract
- **THEN** the runtime emits `invalid_request` and does not pass the invalid value into Deterministic Audit or Event Structuring

#### Scenario: Accepted request fails during execution
- **WHEN** a structurally valid supported request enters the addressed Audit or Event Structuring operation but execution unexpectedly cannot complete
- **THEN** the runtime emits one valid `execution_failure` response, claims no capability result, uses a non-zero process status, and emits no traceback on stdout

### Requirement: Operation addressing is static and contract-governed
The version-1 operation set SHALL contain exactly `audit.text`, `audit.claims`, and `event.structure`. Operation identifiers SHALL describe stable Agent-facing semantics and SHALL NOT expose Python class, module, or method names as the compatibility boundary. The runtime SHALL use explicit static dispatch and SHALL NOT expose capability discovery, `list_capabilities`, a dynamic registry, or activation-matrix configuration. Adding another operation SHALL require an approved contract Change.

#### Scenario: Post-ECO-51 operation set is inspected
- **WHEN** the accepted Agent invocation contract is reviewed after ECO-51
- **THEN** only `audit.text`, `audit.claims`, and `event.structure` are defined and no Ledger, Feed, Market, Watchlist, Confidence, Scoring, or Ranking operation exists

#### Scenario: Initial operation set is inspected
- **WHEN** the version-1 operation set is inspected after ECO-51
- **THEN** its additive accepted set is exactly `audit.text`, `audit.claims`, and `event.structure`, with no operation for another capability

#### Scenario: Discovery is requested
- **WHEN** a caller requests runtime capability discovery or a registry snapshot
- **THEN** no discovery operation or dynamic registry is available and supported operations remain defined by accepted contract and truthful documentation

### Requirement: Phase 5 activation decisions change status only after verified callers
The Phase 5 activation matrix SHALL record: Evidence Feed remains live and unchanged; Deterministic Audit remains `live-production` through the real ECO-50 caller; Evidence and Event Structuring becomes on-demand `live-production` only after ECO-51 implements and verifies `event.structure`; and Market Analytics and State, Confidence and Watchlist, and Scoring and Ranking remain deferred. An `activate` decision alone SHALL mean approval for a dedicated implementation Change rather than callability, runtime enablement, registry membership, or configuration. Execution status SHALL change only when the dedicated Change establishes and verifies a real production caller.

#### Scenario: Post-ECO-51 caller graph is inspected
- **WHEN** the implemented invocation boundary and production caller graph are traced
- **THEN** Evidence Feed, Deterministic Audit, and Evidence/Event Structuring are independently `live-production`, the Host Agent can explicitly invoke only `audit.text`, `audit.claims`, or `event.structure` through the private boundary, and no capability invokes another implicitly

#### Scenario: Event Structuring activation is inspected
- **WHEN** ECO-51 has implemented and verified the `event.structure` caller
- **THEN** Evidence and Event Structuring changes from `retained-no-production-caller` to on-demand `live-production` without creating Feed-to-Event wiring, persistent Ledger state, or another Event operation

#### Scenario: Deferred capability implementation is inspected
- **WHEN** Market, Confidence/Watchlist, or Scoring/Ranking libraries are reviewed after ECO-51
- **THEN** they remain valid retained implementations without being removed, fake-wired, exposed as operations, or marked live

### Requirement: Common invocation contract does not prescribe a research pipeline
Capability use SHALL remain explicitly selected and on demand by the Host Agent. The contract SHALL NOT require Feed as a first invocation step, automatic Audit or Event invocation, automatic Feed-to-Event processing, Event-to-Audit chaining, operation order or count, retry or rewrite loops, narrative generation, automatic grounding or entailment judgment, investment recommendations, or trading execution. It SHALL NOT introduce HTTP, MCP, RPC, daemon, session, embedded LLM/model, credential, prompt, or fixed Resolver/Analyst/Editor/Brief pipeline machinery.

#### Scenario: Automatic capability sequence is sought
- **WHEN** a caller or implementation attempts to infer `Feed -> Event`, `Event -> Audit`, `Feed -> Audit`, or another mandatory capability sequence from this contract
- **THEN** no such sequence exists and each supported invocation remains an explicit Host-Agent choice

#### Scenario: Runtime implementation is inspected after ECO-51
- **WHEN** production code and entry paths are reviewed
- **THEN** exactly one private one-shot Agent invocation boundary statically dispatches only the two Audit operations and `event.structure`, with no Ledger API, registry, remote service, session framework, LLM runtime, automatic grounding system, retry, rewrite, or hidden capability chaining

#### Scenario: Runtime implementation is inspected after ECO-50
- **WHEN** the ECO-50 runtime baseline is compared with the additive ECO-51 implementation
- **THEN** the same private boundary and two Audit branches remain backward compatible and only the literal `event.structure` branch has been added

## ADDED Requirements

### Requirement: Event Structuring input is minimal closed and structured
The `event.structure` input SHALL be a closed object containing non-empty `event_type`, non-empty `evidence_ids`, non-empty `entity_ids`, one or more `key_facts`, and non-empty `subject_zh`; it MAY contain filing-only `company` and `form`, `story_family_peer_event_ids`, and `coexisting_event_ids`. Each key fact SHALL be a closed object containing `entry_type` equal to `FACT` or `CLAIM`; `origin_payload` equal to one of `news`, `macro_release`, `policy`, `filing`, `flow`, or `positioning`; non-empty `evidence_id`, `subject`, and `predicate`; nullable string `effective_time`, nullable string `value`, nullable string `unit`; `effective_precision` equal to `instant`, `date`, `month`, or `year`; and valid `knowledge_available_at`. The serialized contract SHALL NOT accept caller-supplied fact IDs, Event IDs, family IDs, display labels, complete Ledger entries, corroboration bookkeeping, confidence, conflicts, candidate/component state, parent/inference state, resolver state, authority/proof fields, narrative, or arbitrary internal fields.

#### Scenario: Minimal Event request validates
- **WHEN** `event.structure` receives only the contracted Event values and one or more valid Event-defining key facts
- **THEN** the request validates without an external Ledger, Agent-managed fact IDs, internal Python serialization, or another capability input

#### Scenario: Event request is not closed
- **WHEN** the envelope, Event input, key fact, or optional structured sub-object contains an unknown field, missing field, wrong type, malformed identity/time/precision, unsupported entry/origin type, or a forbidden authority/proof or internal bookkeeping field
- **THEN** the request fails closed as `invalid_request` before Event construction

#### Scenario: Filing display inputs are supplied
- **WHEN** `event_type` is `filing`
- **THEN** non-empty `form` is required, optional non-empty `company` is accepted, and the existing deterministic filing template remains authoritative

#### Scenario: Non-filing request supplies filing-only inputs
- **WHEN** an Event type other than `filing` supplies `company` or `form`
- **THEN** the request fails closed rather than enlarging the display-label contract

### Requirement: Event Structuring derives identities and enforces provenance consistency
The boundary SHALL generate every fact ID from the accepted structured key-fact values through the existing canonical fact identity semantics and SHALL generate the Event ID through the existing canonical Event semantics. Each key fact's `evidence_id` MUST occur in the request's `evidence_ids`; duplicate evidence/entity/peer inputs MAY be canonically collapsed by existing set semantics, but two key facts that generate the same canonical fact ID SHALL fail closed rather than being silently dropped. The request SHALL NOT supply a second authoritative copy of generated fact IDs, key-fact IDs, Event ID, family ID, coexistence pairs, or deterministic display label. The current generated Event ID SHALL be deterministically included with supplied story-family peers and paired with each supplied coexisting Event ID.

#### Scenario: Key fact provenance is traceable
- **WHEN** every key fact references an evidence identity present in `evidence_ids`
- **THEN** the accepted reference is preserved into the generated fact and the ordered result projection without gaining verification or grounding authority

#### Scenario: Key fact references absent evidence
- **WHEN** a key fact names an evidence identity absent from the request's `evidence_ids`
- **THEN** the request fails closed as `invalid_request` and no Event result is emitted

#### Scenario: Canonical fact identity collides within one request
- **WHEN** two supplied key facts produce the same canonical fact ID
- **THEN** the request fails closed rather than silently deduplicating, overwriting, or repairing the invocation-local Ledger

#### Scenario: Optional peer inputs are reordered
- **WHEN** equivalent story-family peers or coexisting Event identities are supplied in another order or with duplicates
- **THEN** the current Event is included exactly once and the existing family and unordered-pair semantics produce the same canonical result

### Requirement: Event Structuring uses invocation-local deterministic state only
Each accepted `event.structure` request SHALL construct only the request's key facts in an invocation-local Ledger, invoke the existing canonical Event behavior once for that request, and discard the Ledger when the one-shot process ends. The operation SHALL NOT expose or persist Ledger state, create cross-call handles, accept Agent-managed Ledger mutations, serialize internal Python dataclasses directly, invoke Feed, Audit, Market, Watchlist, Confidence, Scoring, or Ranking, or establish a workflow sequence.

#### Scenario: Event is structured successfully
- **WHEN** the Host Agent explicitly submits one valid `event.structure` request
- **THEN** only Event Structuring executes against request-local deterministic state and returns one successful Event result

#### Scenario: Invalid Event input is submitted
- **WHEN** validation or consistency checks reject an `event.structure` request
- **THEN** no key fact, Ledger, Event, or sibling capability construction is entered

#### Scenario: Stateful continuation is sought
- **WHEN** a caller attempts to reuse a Ledger, fact handle, Event session, or other state across invocations
- **THEN** the contract provides no such identity or state mechanism

### Requirement: Event Structuring result is closed canonical and bounded
A successful `event.structure` response SHALL use the common version-1 success envelope and SHALL contain a closed result with canonical `event_id`, caller-supplied `event_type`, canonically ordered `evidence_ids`, canonically ordered `key_fact_ids`, `fully_known_at`, `story_family_id`, canonical ordered `coexistence_pair_ids`, deterministic `display_label`, `economic_effective_time`, nullable `common_effective_time`, `multiple_effective_times`, ordered `key_fact_effective_times`, and ordered `key_fact_references`. Each key-fact reference SHALL contain exactly `fact_id` and `evidence_id` and SHALL be ordered by `fact_id`. The result SHALL omit internal `schema_version`, complete Ledger entries, entity/display inputs already owned by the caller, proof/authority fields, narrative, and unrelated capability results.

#### Scenario: Canonical Event result is returned
- **WHEN** a valid Event request completes
- **THEN** the response contains exactly the contracted Event projection and each identity, time, family, pair, and label value comes from the existing deterministic semantics

#### Scenario: Equivalent semantic input is permuted
- **WHEN** key facts, evidence identities, entity identities, family peers, or coexisting identities are reordered without changing their semantic values
- **THEN** generated fact IDs, Event ID, all canonical arrays, all effective-time projections, family identity, coexistence pairs, display label, key-fact references, and serialized result remain stable

#### Scenario: Result authority is inspected
- **WHEN** Agent-supplied classifications, selections, evidence references, hypotheses, or display inputs appear through deterministic Event processing
- **THEN** they remain Agent-owned and the result contains no `verified`, `grounded`, `factually_correct`, `entailed`, `answer_valid`, `admissible`, or equivalent claim

#### Scenario: Result mapping cannot complete
- **WHEN** an accepted Event execution or result mapping unexpectedly fails or would emit a schema-invalid result
- **THEN** the runtime emits `execution_failure`, no partial Event result, and a non-zero process status
