## MODIFIED Requirements

### Requirement: Internal deterministic contracts and wiring status
Ledger entries, entity resolution, candidate Components, canonical Events, market analytics, Market State, watchlist, scoring, selection, and safety audit SHALL remain deterministic Python library contracts protected by typed interfaces, domain invariants, fail-closed validation where applicable, and focused tests. They SHALL NOT be represented as serialized external contracts unless an approved Change explicitly establishes a deliberately bounded mapping. After ECO-51, the private Agent invocation boundary SHALL be the only production caller of Deterministic Audit and canonical Event construction; its Event DTO SHALL expose only the accepted minimum projection and SHALL NOT serialize the full internal Ledger or Event Python layout. Post-Feed entity resolution, candidate preparation, market analytics, watchlist, scoring, and selection libraries SHALL remain retained without a production orchestration caller. Candidate preparation SHALL end at transport-neutral Components and SHALL NOT define a Resolver or Agent request envelope, request-local aliases, or batching contract.

#### Scenario: Internal structure is exercised
- **WHEN** a retained internal structure is constructed or transformed in focused tests
- **THEN** its type, ordering, numeric, identity, and domain invariants are enforced without requiring a standalone JSON Schema

#### Scenario: Production wiring is audited
- **WHEN** imports and entry paths are traced after ECO-51
- **THEN** Deterministic Audit and canonical Event construction are live only through the approved invocation adapter, while no other post-Feed research, scoring, or selection module is claimed as live without an actual caller

#### Scenario: Event boundary is inspected
- **WHEN** the Agent-facing Event DTO is compared with internal Ledger entries and Event dictionaries
- **THEN** the boundary maps only contracted fields explicitly and neither internal Python layout is promoted as the compatibility contract

#### Scenario: Candidate output is inspected
- **WHEN** candidate preparation groups seed facts
- **THEN** it produces deterministic Components without packaging them into bounded Resolver or Agent request batches

### Requirement: Immutable evidence ledger
The ledger SHALL store immutable typed `FACT`, `CLAIM`, `OBSERVATION`, and script-derived `INFERENCE` entries with stable fact IDs, evidence lineage, `knowledge_available_at`, effective time and precision, resolved or stable raw subject identity, canonical value and unit, corroboration families, and explicit conflicts. Canonical fact identity SHALL bind the complete semantic tuple while keeping provider/evidence lineage separate. Atomic Event seeds SHALL be exactly `FACT` or `CLAIM` entries from the supported event-like payload origins; market, calendar, observation, and inference entries SHALL NOT become atomic seeds. The `event.structure` adapter SHALL construct only accepted atomic Event-defining entries in an invocation-local Ledger, SHALL derive their fact IDs through this same implementation, and SHALL NOT expose other Ledger fields or state.

#### Scenario: Same fact has different lineage
- **WHEN** semantically identical facts arise from separate evidence records
- **THEN** they share the same canonical fact key while retaining distinct stable fact IDs and evidence lineage

#### Scenario: Observation is inspected for seeds
- **WHEN** a market or calendar observation is added to the ledger
- **THEN** it remains available as evidence but is absent from the atomic Event seed set

#### Scenario: Unknown fact is requested
- **WHEN** a caller references a fact ID absent from the frozen ledger
- **THEN** lookup fails closed rather than fabricating or silently dropping the fact

#### Scenario: Agent request constructs key facts
- **WHEN** `event.structure` accepts closed `FACT` or `CLAIM` inputs from a supported Event-like origin
- **THEN** the invocation-local entries use the existing canonical fact key and stable fact-ID semantics, preserve their evidence references, and expose only ordered `fact_id` / `evidence_id` projections

### Requirement: Canonical Event and family utilities
Canonical Event IDs SHALL derive from the versioned sorted evidence IDs, caller-supplied Event type, sorted resolved entity IDs, and sorted complete canonical keys of Event-defining facts. `key_fact_ids` SHALL be sorted and unique, `fully_known_at` SHALL be the latest knowledge time among those exact facts, and display labels SHALL be produced only by versioned templates over closed structured facts. Effective-time projections SHALL be ordered by canonical key-fact ID; the economic value and precision SHALL come from the same first ordered key fact, while `common_effective_time` SHALL be present only when all key facts have the same non-null value and precision. Story-family IDs SHALL derive from sorted canonical member Event IDs; unknown or one-member families SHALL use Event-specific singleton identity, and coexistence pairs SHALL be canonical unordered Event-ID pairs. The approved `event.structure` adapter SHALL invoke these existing utilities without duplicating their algorithms, while every other production pipeline or caller remains absent.

#### Scenario: Event inputs are reordered
- **WHEN** the same evidence IDs, entity IDs, and Event-defining facts are supplied in another order
- **THEN** fact IDs, Event ID, key-fact order, all effective-time projections, family identity, pair projection, and display label remain unchanged

#### Scenario: Key facts use different effective precisions
- **WHEN** a canonical Event contains multiple ordered key facts with different effective-time precisions
- **THEN** `economic_effective_time.value` and `precision` come from the same first ordered key fact, `common_effective_time` is null, and the result is stable across process hash seeds

#### Scenario: Family has one member
- **WHEN** a family is constructed from exactly one canonical Event ID
- **THEN** it receives that Event's `fam_single_<event_id>` identity rather than a shared label-derived identity

#### Scenario: Event references an unknown key fact
- **WHEN** Event construction requests a key fact absent from the frozen ledger
- **THEN** construction fails closed before producing an Event

#### Scenario: Agent-facing Event construction is invoked
- **WHEN** one valid `event.structure` request maps into canonical Event construction
- **THEN** the existing implementation remains the sole authority for fact/Event identity, ordering, knowledge/effective times, family identity, coexistence pairs, and deterministic display labels
