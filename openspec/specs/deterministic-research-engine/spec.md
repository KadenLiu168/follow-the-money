# deterministic-research-engine Specification

## Purpose
Define the retained deterministic Python library contracts for evidence preparation, canonical Events, market analytics, scoring, selection, watchlist, and safety rules, with honest production-caller status.

## Requirements

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
absolute z-score threshold. An unverified configured mapping SHALL remain explicitly
unknown with reason `unverified_mapping` even if a matching Feed item is present.
Other ineligible, stale, post-cutoff, wrong-unit, session-incompatible, or insufficient
observations SHALL remain explicitly unknown instead of being filled. This retained
deterministic capability SHALL NOT gain a production orchestration caller through
market-mapping enforcement.

#### Scenario: Price role has sufficient history
- **WHEN** a price-like role has 22 eligible consecutive closes with non-zero reference standard deviation
- **THEN** the snapshot computes 21 simple returns, compares the last with the preceding 20, and retains Decimal precision until output quantization

#### Scenario: Yield role has sufficient history
- **WHEN** a yield role has 22 eligible percent-unit closes with non-zero reference standard deviation
- **THEN** the snapshot computes basis-point changes and exposes the result through `yield_change_zs` without mislabelling the raw level as a return

#### Scenario: Mapping remains unverified
- **WHEN** the configured role has `mapping_verified` false, including when a matching canonical-role Feed item is present
- **THEN** the role remains present in canonical order with unknown reason `unverified_mapping` and no calculated metric

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
configured 30/20/20/20/10 significance weights, missing-data policy, component
coverage, freshness, China/Hong Kong exposure, US next-session exposure, catalyst
inputs, configured 40/25/20/15 relevance weights, and configured 0.70/0.30 base-
priority formula in versioned configuration. For equivalent semantic inputs and
configuration, neutral scoring names SHALL preserve the same scoring formulas,
configured weights, categorical mappings, surprise bins, missing-data behavior, and
operation order.
Systemic Breadth SHALL remain `affected_groups / 9 * 100`. All normative financial
arithmetic SHALL use the repository-owned high-precision Decimal context, and that
context SHALL determine numerical results independently of ambient process Decimal
precision or rounding. Unknown components SHALL contribute zero without denominator
renormalization, and rankable inputs SHALL require the configured minimum known-
weight coverage. Scoring inputs SHALL remain caller-supplied typed Python values
until a future Agent Contract defines how analysis reaches this boundary. Scoring
SHALL remain a retained deterministic library with no production orchestration
caller or standalone external scoring schema.

#### Scenario: One significance component is unknown
- **WHEN** an input component lacks the evidence required by its closed mapping
- **THEN** it contributes zero under the full denominator and reduces component coverage instead of being imputed or reweighted

#### Scenario: Process Decimal context is hostile
- **WHEN** the ambient process Decimal precision or rounding differs from the normative configuration
- **THEN** scoring produces the same deterministic result under its owned Decimal context

#### Scenario: Categorical value is unmapped
- **WHEN** a scoring input uses a non-unknown value absent from its closed configured map
- **THEN** scoring fails closed rather than assigning a default score

#### Scenario: Neutral scoring names receive an equivalent vector
- **WHEN** equivalent semantic scoring inputs and configuration are evaluated through the neutral scoring contract under materially different ambient Decimal precision and rounding settings
- **THEN** they use the same formulas, configured weights, categorical mappings, surprise bins, missing-data behavior, and operation order
- **THEN** Systemic Breadth and downstream Event Significance produce the same result determined by the repository-owned normative Decimal context

#### Scenario: Significance components ignore hostile ambient Decimal context
- **WHEN** equivalent valid scoring vectors use `sector` scope, `headline` fundamental depth, `medium` reversibility, `months` structural horizon, three affected groups, a known surprise, and observable repricing z of `-0.4999`, and are evaluated under materially different ambient Decimal precision and rounding settings
- **THEN** Fundamental Magnitude is exactly `37.5`, Persistence is exactly `62.5`, Systemic Breadth is exactly `33.333333333333333333333333333333333333333333333333`, and Repricing Magnitude is exactly `0` in every ambient context
- **THEN** all five significance component values, downstream Event Significance, and component coverage are identical across those ambient contexts and are determined by the repository-owned normative Decimal context
- **THEN** the absolute repricing magnitude `0.4999` remains below the configured `0.5` boundary without tolerance, quantization, or bin-policy changes

#### Scenario: Brief-only configuration is supplied
- **WHEN** closed configuration contains a removed full/compact threshold, Brief count limit, or the superseded relevance-weight key
- **THEN** strict configuration loading rejects the unknown legacy key rather than accepting an alias or fallback

#### Scenario: Scoring is retained without a caller
- **WHEN** the repository exposes the typed deterministic scoring library after this change
- **THEN** no Feed or other production entry path invokes it and no Agent-owned or serialized scoring contract is introduced

### Requirement: Deterministic ranking and family penalty
Ranking SHALL accept caller-supplied typed event identity, `fully_known_at`, base
priority, deterministic confidence, component coverage, story-family identity, and
canonical coexistence-pair information. It SHALL reject an Event when confidence is
`unresolved` or component coverage is below the configured minimum; resolved
`high`, `medium`, and `low` confidence values SHALL otherwise be rankable without
analysis-presence, packet, Editor conflict, or breaking-label state. A confidence
value outside the closed `high`, `medium`, `low`, and `unresolved` set SHALL fail
closed before eligibility or ranking. Ranking SHALL
freeze base order by base priority descending, `fully_known_at` descending, and
Event ID ascending. It SHALL apply the configured routine-family penalty to every
later family member unless its canonical unordered pair with the frozen first member
exists, and SHALL compute final priority as
`max(0, base_priority - applicable_family_penalty)`. The pair exemption SHALL be
first-to-later, pairwise, and non-transitive. Ranking SHALL return the complete
eligible set in final-priority descending, `fully_known_at` descending, and Event ID
ascending order, together with base priority, final priority, and deterministic
ineligibility reasons; it SHALL NOT truncate results or assign presentation formats,
tiers, Breaking/Unconfirmed state, or sparse-output state. It SHALL derive pair
exemption from canonical pair membership rather than accept an authoritative caller
boolean, but SHALL NOT claim that a production pipeline currently supplies those
pairs. Ranking SHALL remain a retained deterministic library with no production
orchestration caller or standalone external ranking schema.

#### Scenario: Confidence is unresolved
- **WHEN** a ranking input has `unresolved` deterministic confidence
- **THEN** the Event is ineligible with the unresolved-confidence reason

#### Scenario: Component coverage is insufficient
- **WHEN** a ranking input has component coverage below the configured minimum
- **THEN** the Event is ineligible with the below-coverage reason

#### Scenario: Resolved confidence has no legacy workflow state
- **WHEN** otherwise equivalent `high`, `medium`, and `low` confidence inputs satisfy minimum component coverage
- **THEN** all three Events participate in ranking without analysis, packet, Editor-conflict, or breaking-label fields or gates

#### Scenario: Confidence is outside the closed set
- **WHEN** a ranking input supplies a confidence value other than `high`, `medium`, `low`, or `unresolved`
- **THEN** ranking fails closed before the Event can enter eligibility or ordering

#### Scenario: Routine later family member is penalized
- **WHEN** two eligible Events share a non-singleton family and have no canonical coexistence pair
- **THEN** the first Event in frozen base order is unpenalized and the later Event loses exactly the configured family penalty with a final-priority floor of zero

#### Scenario: Exact first-to-later pair exists
- **WHEN** a later family member has a canonical unordered pair with the frozen first member
- **THEN** that later member receives the pair exemption without changing any other member's comparison

#### Scenario: Only later members form a pair
- **WHEN** two later members have a canonical coexistence pair but a later member lacks a pair with the frozen first member
- **THEN** that later member remains penalized because the exemption is pairwise and non-transitive

#### Scenario: Equivalent inputs are reordered
- **WHEN** equivalent ranking inputs arrive in another order
- **THEN** ineligibility reasons, penalties, base and final priorities, ranked IDs, and final output order remain identical

#### Scenario: Eligible set exceeds historical Brief limits
- **WHEN** more eligible Events exist than the removed Brief target or hard maximum
- **THEN** ranking returns every eligible Event in deterministic final order without format, tier, Breaking/Unconfirmed, or sparse-warning state

#### Scenario: Ranking is retained without a caller
- **WHEN** the repository exposes the typed deterministic ranking library after this change
- **THEN** no Feed or other production entry path invokes it and no Agent-owned or serialized ranking contract is introduced

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
