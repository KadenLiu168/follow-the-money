## MODIFIED Requirements

### Requirement: Internal deterministic contracts and wiring status
Ledger entries, entity resolution, candidate Components, canonical Events,
market analytics, Market State, watchlist, scoring, selection, and safety audit SHALL
remain deterministic Python library contracts protected by typed interfaces, domain
invariants, fail-closed validation where applicable, and focused tests. They SHALL NOT
be represented as current serialized external contracts unless a later Change
explicitly establishes such a boundary. The living baseline SHALL identify the
current caller status honestly: only modules imported by the minimal Feed path MAY be
described as production-wired; post-Feed preparation, scoring, selection, and safety
libraries SHALL be described as retained without a production orchestration caller.
Candidate preparation SHALL end at transport-neutral Components and SHALL NOT define
a Resolver or Agent request envelope, request-local aliases, or batching contract.

#### Scenario: Internal structure is exercised
- **WHEN** a retained internal structure is constructed or transformed in focused tests
- **THEN** its type, ordering, numeric, identity, and domain invariants are enforced without requiring a standalone JSON Schema

#### Scenario: Production wiring is audited
- **WHEN** imports and entry paths are traced from the minimal Feed entry
- **THEN** no post-Feed research, scoring, selection, or safety module is claimed as a live production stage without an actual caller

#### Scenario: Candidate output is inspected
- **WHEN** candidate preparation groups seed facts
- **THEN** it produces deterministic Components without packaging them into bounded Resolver or Agent request batches

### Requirement: Deterministic entity resolution and candidate grouping
Entity aliases SHALL resolve only through the closed configured map and unknown
subjects SHALL retain stable normalized raw identity. Candidate construction SHALL
use `LedgerEntry.subject` as the authoritative stored resolved-or-raw subject identity
and SHALL recognize it as a canonical entity for exact-entity matching only when that
exact ID is present in the closed configured entity registry. Text prefixes or other
naming conventions SHALL NOT determine canonical-entity status, and `raw_subject`
SHALL NOT substitute for the authoritative subject identity.

Candidate construction SHALL derive deterministic mention nodes and undirected edges
only through: equality of the complete canonical fact key; the same registry-recognized
canonical entity within 48 hours by absolute `knowledge_available_at` difference plus
either the same predicate or evidence-title Jaccard similarity of at least 0.45; or,
when neither subject is a registry-recognized
canonical entity, the same origin-payload type and predicate within 12 hours by absolute
`knowledge_available_at` difference plus evidence-title Jaccard similarity of at least
0.85. Title similarity SHALL use actual
evidence title metadata associated by `evidence_id` and the existing closed title
normalization and Jaccard semantics. A missing or empty title SHALL create no
title-derived edge and SHALL NOT trigger recovery from `raw_subject` or any synthetic
title. Equal complete canonical fact keys and exact-predicate paths SHALL remain
independent of title availability.

Connected Components SHALL preserve deterministic membership, identity, and canonical
ordering under equivalent input permutations. Candidate preparation SHALL NOT pack
Components into Blocks, assign request-local aliases, impose Resolver-request record,
seed, byte, or total-block capacities, or introduce an equivalent renamed batching
abstraction. Candidate preparation SHALL remain a retained deterministic library with
no current production orchestration caller.

#### Scenario: Feed order changes
- **WHEN** equivalent seed facts and evidence-title associations arrive in different input orders
- **THEN** mention IDs, edge set, Component membership, Component IDs, and Component order remain identical

#### Scenario: Canonical entity ID has no conventional prefix
- **WHEN** two seed facts use the same subject ID that exists exactly in the closed entity registry, the ID has no `ent_` prefix, and the facts satisfy the existing entity/time/predicate rule
- **THEN** candidate grouping treats both subjects as the same canonical entity

#### Scenario: Canonical-looking subject is unregistered
- **WHEN** a subject begins with `ent_` but its exact ID is absent from the closed entity registry
- **THEN** candidate grouping does not treat it as a canonical entity on the basis of that prefix

#### Scenario: Prefix does not override registry membership
- **WHEN** an exact configured canonical entity ID begins with `raw_` or `unresolved`
- **THEN** candidate grouping recognizes it as canonical despite its prefix

#### Scenario: Same canonical entity joins through evidence titles
- **WHEN** two facts for the same registry-recognized canonical entity are within 48 hours, have different predicates, and their associated evidence titles have Jaccard similarity at least 0.45
- **THEN** candidate grouping creates an edge using the evidence titles

#### Scenario: Same canonical entity has insufficient title similarity
- **WHEN** two facts for the same registry-recognized canonical entity are within 48 hours, have different predicates, and their associated evidence titles have Jaccard similarity below 0.45
- **THEN** candidate grouping creates no title-derived edge

#### Scenario: Evidence title is missing
- **WHEN** one or both evidence IDs have no non-empty associated title and no title-independent edge rule applies
- **THEN** candidate grouping creates no title-derived edge, invents no title, and does not read `raw_subject` as a fallback

#### Scenario: Entity-less facts join through evidence titles
- **WHEN** neither fact subject is recognized by the registry, the facts share origin-payload type and predicate within 12 hours, and their associated evidence titles have Jaccard similarity at least 0.85
- **THEN** candidate grouping creates an edge using the evidence titles

#### Scenario: Entity-less title rule is not satisfied
- **WHEN** neither fact subject is recognized by the registry but the origin-payload type, predicate, time-window, title-availability, or 0.85 title-similarity condition is not satisfied
- **THEN** candidate grouping creates no edge through the entity-less rule

#### Scenario: One component exceeds a bound
- **WHEN** a valid connected Component would have exceeded a former Resolver request record, seed, or canonical-byte bound
- **THEN** candidate grouping retains the complete Component without splitting it or raising a transport-capacity failure

#### Scenario: Too many blocks are required
- **WHEN** valid deterministic inputs would formerly have required more than the maximum Resolver request Block count
- **THEN** candidate grouping returns all Components in canonical order without packing Blocks or raising `capacity_exceeded`
