## MODIFIED Requirements

### Requirement: Canonical Event and family utilities
Canonical Event IDs SHALL derive from the versioned sorted evidence IDs, caller-supplied
Event type, sorted resolved entity IDs, and sorted complete canonical keys of Event-defining
facts. `key_fact_ids` SHALL be sorted and unique, `fully_known_at` SHALL be the latest
knowledge time among those exact facts, and display labels SHALL be produced only by
versioned templates over closed structured facts. Story-family IDs SHALL derive from
sorted canonical member Event IDs; unknown or one-member families SHALL use
Event-specific singleton identity, and coexistence pairs SHALL be canonical unordered
Event-ID pairs. Effective-time projections SHALL be ordered by canonical key-fact ID; the
economic value and precision SHALL come from the same first ordered key fact, while
`common_effective_time` SHALL be present only when all key facts have the same non-null
value and precision. The approved `event.structure` adapter SHALL invoke these existing
utilities without duplicating their algorithms, while every other production pipeline or
caller remains absent.

#### Scenario: Event inputs are reordered
- **WHEN** the same evidence IDs, entity IDs, and Event-defining facts are supplied in another order
- **THEN** fact IDs, Event ID, key-fact order, all effective-time projections, family identity, pair projection, and display label remain unchanged

#### Scenario: Key facts use different effective precisions
- **WHEN** a canonical Event contains multiple ordered key facts with different effective-time precisions
- **THEN** `economic_effective_time.value` and `precision` come from the same first ordered key fact, `common_effective_time` is null, and the result is stable across process hash seeds

#### Scenario: First canonical key fact has no effective-time value
- **WHEN** the first canonical key fact has a null effective-time value and a later canonical key fact has a non-null effective-time value
- **THEN** `economic_effective_time.value` is null, its precision is the first canonical key fact's exact precision, and the later fact does not replace that projection

#### Scenario: Effective times are all unknown
- **WHEN** all key facts have null effective-time values
- **THEN** `economic_effective_time` is derived from the first canonical key fact, `common_effective_time` is null, and no synthetic precision is introduced

#### Scenario: Effective time is only partially known
- **WHEN** at least one key fact has a null effective-time value and another key fact has a non-null effective-time value
- **THEN** `common_effective_time` is null even when all known values and all declared precisions are otherwise identical

#### Scenario: Family has one member
- **WHEN** a family is constructed from exactly one canonical Event ID
- **THEN** it receives that Event's `fam_single_<event_id>` identity rather than a shared label-derived identity

#### Scenario: Event references an unknown key fact
- **WHEN** Event construction requests a key fact absent from the frozen ledger
- **THEN** construction fails closed before producing an Event

#### Scenario: Agent-facing Event construction is invoked
- **WHEN** one valid `event.structure` request maps into canonical Event construction
- **THEN** the existing implementation remains the sole authority for fact/Event identity, ordering, knowledge/effective times, family identity, coexistence pairs, and deterministic display labels
