# deterministic-research-engine Specification

## Purpose
Define the retained deterministic Python library contracts for evidence preparation, canonical Events, market analytics, scoring, selection, watchlist, and safety rules, with honest production-caller status.

## Requirements

### Requirement: Internal deterministic contracts and wiring status
Ledger entries, entity resolution, candidate components and blocks, canonical Events,
market analytics, Market State, watchlist, scoring, selection, and safety audit SHALL
remain deterministic Python library contracts protected by typed interfaces, domain
invariants, fail-closed validation where applicable, and focused tests. They SHALL NOT
be represented as current serialized external contracts unless a later Change
explicitly establishes such a boundary. The living baseline SHALL identify the
current caller status honestly: only modules imported by the minimal Feed path MAY be
described as production-wired; post-Feed preparation, scoring, selection, and safety
libraries SHALL be described as retained without a production orchestration caller.

#### Scenario: Internal structure is exercised
- **WHEN** a retained internal structure is constructed or transformed in focused tests
- **THEN** its type, ordering, numeric, identity, and domain invariants are enforced without requiring a standalone JSON Schema

#### Scenario: Production wiring is audited
- **WHEN** imports and entry paths are traced from the minimal Feed entry
- **THEN** no post-Feed research, scoring, selection, or safety module is claimed as a live production stage without an actual caller

### Requirement: Immutable evidence ledger
The ledger SHALL store immutable typed `FACT`, `CLAIM`, `OBSERVATION`, and
script-derived `INFERENCE` entries with stable fact IDs, evidence lineage,
`knowledge_available_at`, effective time and precision, resolved or stable raw
subject identity, canonical value and unit, corroboration families, and explicit
conflicts. Canonical fact identity SHALL bind the complete semantic tuple while
keeping provider/evidence lineage separate. Atomic Event seeds SHALL be exactly
`FACT` or `CLAIM` entries from the supported event-like payload origins; market,
calendar, observation, and inference entries SHALL NOT become atomic seeds.

#### Scenario: Same fact has different lineage
- **WHEN** semantically identical facts arise from separate evidence records
- **THEN** they share the same canonical fact key while retaining distinct stable fact IDs and evidence lineage

#### Scenario: Observation is inspected for seeds
- **WHEN** a market or calendar observation is added to the ledger
- **THEN** it remains available as evidence but is absent from the atomic Event seed set

#### Scenario: Unknown fact is requested
- **WHEN** a caller references a fact ID absent from the frozen ledger
- **THEN** lookup fails closed rather than fabricating or silently dropping the fact

### Requirement: Deterministic entity resolution and candidate grouping
Entity aliases SHALL resolve only through the closed configured map and unknown
subjects SHALL retain stable normalized raw identity. Candidate construction SHALL
derive deterministic mention nodes and undirected edges only from the implemented
canonical-fact and exact-entity/time/predicate rules. Connected components and their packed blocks SHALL
use stable canonical ordering and the implemented per-component, per-block, byte,
seed, record, and total-block limits; oversized input SHALL fail with typed capacity
errors. Candidate blocks SHALL NOT imply that a resolver or Agent currently consumes
them in production.

#### Scenario: Feed order changes
- **WHEN** equivalent seed entries arrive in another input order
- **THEN** mention IDs, component membership, component order, aliases, and packed block contents remain deterministic

#### Scenario: One component exceeds a bound
- **WHEN** a connected component exceeds an implemented record, seed, or canonical-byte limit
- **THEN** block construction fails typed `candidate_group_too_large` without splitting the component or invoking semantic analysis

#### Scenario: Too many blocks are required
- **WHEN** canonical next-fit packing would produce more than the implemented maximum block count
- **THEN** block construction fails typed `capacity_exceeded`

### Requirement: Canonical Event and family utilities
Canonical Event IDs SHALL derive from the versioned sorted evidence IDs, caller-supplied
Event type, sorted resolved entity IDs, and sorted complete canonical keys of Event-defining
facts. `key_fact_ids` SHALL be sorted and unique, `fully_known_at` SHALL be the latest
knowledge time among those exact facts, and display labels SHALL be produced only by
versioned templates over closed structured facts. Story-family IDs SHALL derive from
sorted canonical member Event IDs; unknown or one-member families SHALL use
Event-specific singleton identity, and coexistence pairs SHALL be canonical unordered
Event-ID pairs. These pure utilities SHALL NOT be described as consuming resolver
proposals or as part of a current live/replay pipeline.

#### Scenario: Event inputs are reordered
- **WHEN** the same evidence IDs, entity IDs, and Event-defining facts are supplied in another order
- **THEN** the Event ID, key-fact order, family identity, pair projection, and display label remain unchanged

#### Scenario: Family has one member
- **WHEN** a family is constructed from exactly one canonical Event ID
- **THEN** it receives that Event's `fam_single_<event_id>` identity rather than a shared label-derived identity

#### Scenario: Event references an unknown key fact
- **WHEN** Event construction requests a key fact absent from the frozen ledger
- **THEN** construction fails closed before producing an Event

### Requirement: Deterministic market snapshot
Given a validated Feed and closed role configuration, `build_market_snapshot` SHALL
produce one immutable snapshot in configured role order with dashboard rows, current
moves, current-excluded z-scores, anomaly flags, classifier input maps, equity
breadth, macro-surprise votes, missing or unknown reasons, and contributing evidence
IDs. Price, index, FX, commodity, and crypto roles SHALL use simple returns; yield
roles SHALL use basis-point changes. Each available z-score SHALL compare the current
change with exactly the preceding 20 eligible changes through the precision-50
`ROUND_HALF_EVEN` Decimal formulas, and the anomaly boundary SHALL be the configured
absolute z-score threshold. Ineligible, stale, post-cutoff, wrong-unit,
session-incompatible, or insufficient observations SHALL remain explicitly unknown
instead of being filled.

#### Scenario: Price role has sufficient history
- **WHEN** a price-like role has 22 eligible consecutive closes with non-zero reference standard deviation
- **THEN** the snapshot computes 21 simple returns, compares the last with the preceding 20, and retains Decimal precision until output quantization

#### Scenario: Yield role has sufficient history
- **WHEN** a yield role has 22 eligible percent-unit closes with non-zero reference standard deviation
- **THEN** the snapshot computes basis-point changes and exposes the result through `yield_change_zs` without mislabelling the raw level as a return

#### Scenario: Observation is incompatible
- **WHEN** required history is missing, stale, post-cutoff, wrong-unit, session-incompatible, or has zero reference standard deviation
- **THEN** the role remains present in canonical order with an explicit unknown reason and no invented metric

### Requirement: Deterministic breadth, surprise, and Market State
The snapshot SHALL calculate equity breadth from the observable current simple
returns of the configured fixed equity universe, counting zero in the denominator but
in neither sign count. For each exact configured macro series it SHALL select at most
the latest cutoff-eligible release with the stable evidence-ID tie-break, calculate
the versioned normalized surprise, map the exact vote boundaries, and apply the
configured Inflation-direction inversion. `classify_market_state` SHALL derive the
five-dimension vector, known-dimension count, missing-role accounting, and
`risk_on`, `neutral`, `risk_off`, or `unknown` regime solely from deterministic
inputs. These functions SHALL NOT claim current editor, Brief, Bundle, replay, or
production orchestration wiring.

#### Scenario: Classification coverage is sufficient
- **WHEN** Risk Appetite and the required number of dimensions are known
- **THEN** classification returns the deterministic configured regime and vector

#### Scenario: Classification coverage is insufficient
- **WHEN** Risk Appetite is unknown or too few dimensions are known
- **THEN** classification returns `unknown` while preserving independently known dimensions and deterministic missing-role order

#### Scenario: Surprise release is incompatible
- **WHEN** a release lacks actual or consensus, uses an incompatible unit or series identity, or becomes known after cutoff
- **THEN** it contributes no surprise vote and is absent from Market State support

### Requirement: Deterministic confidence and watchlist rules
Evidence confidence SHALL derive from source tiers, independent source families,
and explicit conflicts; Event confidence SHALL be the lowest
confidence of its exact key facts, and unresolved key facts SHALL keep the Event
unresolved. Watchlist construction SHALL select only eligible future calendar
evidence inside the configured horizon, use stable deterministic ordering and bounds,
and preserve missing or sparse outcomes without inventing catalysts. Neither result
SHALL be described as automatically entering a production Brief.

#### Scenario: Key fact has no support
- **WHEN** confidence evaluation receives no qualifying evidence support
- **THEN** it returns `unresolved` with the applicable reason

#### Scenario: Event contains an unresolved key fact
- **WHEN** any exact Event key fact is unresolved
- **THEN** the Event confidence remains unresolved and cannot qualify through another fact's stronger support

#### Scenario: Calendar items tie
- **WHEN** multiple eligible calendar items have equal schedule and relevance keys
- **THEN** the watchlist uses its stable evidence identity tie-break and configured maximum count

### Requirement: Versioned deterministic scoring
Scoring SHALL keep its closed categorical maps, five significance components,
weights, missing-data policy, component coverage, Morning Relevance inputs, and base
priority formula in versioned configuration. Financial arithmetic SHALL use the
normative high-precision Decimal context; unknown components SHALL contribute zero
without denominator renormalization, and normally selected inputs SHALL require the
configured minimum known-weight coverage. Scoring inputs SHALL remain caller-supplied
typed Python values until a future Agent Contract defines how analysis reaches this
boundary.

#### Scenario: One significance component is unknown
- **WHEN** an input component lacks the evidence required by its closed mapping
- **THEN** it contributes zero under the full denominator and reduces component coverage instead of being imputed or reweighted

#### Scenario: Process Decimal context is hostile
- **WHEN** the ambient process Decimal precision or rounding differs from the normative configuration
- **THEN** scoring produces the same deterministic result under its owned Decimal context

#### Scenario: Categorical value is unmapped
- **WHEN** a scoring input uses a non-unknown value absent from its closed configured map
- **THEN** scoring fails closed rather than assigning a default score

### Requirement: Deterministic selection and family penalty
Selection SHALL reject unresolved, analysis-absent, or below-coverage inputs; derive
full and compact capability from confidence, packet, conflict, and breaking-label
fields; freeze base order by priority descending, `fully_known_at` descending, and
Event ID ascending; and apply the configured routine-family penalty to every later
member unless its canonical unordered pair with the frozen first member exists.
Selection SHALL reapply thresholds, deterministically order final results, enforce the
configured total and full-format limits, and report sparse output. It SHALL compute
the pair exemption from canonical pair membership rather than accept an authoritative
caller boolean, but SHALL NOT claim that resolver output or a production pipeline
currently supplies those pairs.

#### Scenario: Routine later family member is penalized
- **WHEN** two eligible Events share a non-singleton family and have no canonical coexistence pair
- **THEN** the first Event in frozen base order is unpenalized and the later Event loses exactly the configured family penalty before thresholds are reapplied

#### Scenario: Exact first-to-later pair exists
- **WHEN** a later family member has a canonical unordered pair with the frozen first member
- **THEN** that later member receives the pair exemption without changing any other member's comparison

#### Scenario: Equivalent inputs are reordered
- **WHEN** equivalent selection inputs arrive in another order
- **THEN** eligibility reasons, penalties, final priorities, formats, selected IDs, and output order remain identical

### Requirement: Deterministic safety audit retained without orchestration
`ClaimAuditor` SHALL remain a deterministic library that rejects duplicate or missing
claim inventory identity, rendered assertions outside the inventory, factual claims
without required evidence references, unsupported confirmed-flow ownership, and
prohibited Chinese or English trading instructions subject to configured descriptive
exceptions. It SHALL block the submitted candidate rather than silently rewriting
text. The baseline SHALL state that no production Brief or Agent validation caller
exists yet and SHALL NOT treat the old Brief dictionary shape as a future Agent
Contract.

#### Scenario: Trading instruction is submitted
- **WHEN** submitted text contains a configured buy, sell, add, reduce, position-size, entry, exit, stop-loss, or target-price instruction without a descriptive exception
- **THEN** the audit produces a critical `trading_instruction` finding and fails the candidate

#### Scenario: Factual claim lacks evidence
- **WHEN** a non-dashboard factual claim in the submitted candidate has no evidence references
- **THEN** the audit fails with `missing_evidence` rather than inventing references or editing the claim

#### Scenario: Auditor caller status is inspected
- **WHEN** production entry paths are traced
- **THEN** `ClaimAuditor` is identified as retained tested library code with no current production Brief or Agent caller
