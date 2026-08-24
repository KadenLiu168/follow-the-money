## MODIFIED Requirements

### Requirement: Versioned deterministic scoring
Scoring SHALL keep its closed categorical maps, five significance components,
configured 30/20/20/20/10 significance weights, missing-data policy, component
coverage, freshness, China/Hong Kong exposure, US next-session exposure, catalyst
inputs, configured 40/25/20/15 relevance weights, and configured 0.70/0.30 base-
priority formula in versioned configuration. For equivalent semantic inputs and
configuration, neutral scoring names SHALL produce exactly the same significance,
coverage, relevance, and base-priority values as the superseded Morning Relevance
and Brief Priority names, using the same bins, mappings, missing-data behavior,
operation order, precision, and rounding. Financial arithmetic SHALL use the
normative high-precision Decimal context; unknown components SHALL contribute zero
without denominator renormalization, and rankable inputs SHALL require the
configured minimum known-weight coverage. Scoring inputs SHALL remain caller-
supplied typed Python values until a future Agent Contract defines how analysis
reaches this boundary. Scoring SHALL remain a retained deterministic library with
no production orchestration caller or standalone external scoring schema.

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
- **WHEN** neutral relevance and base-priority operations receive semantic inputs and configuration equivalent to a pre-change scoring vector
- **THEN** significance, component coverage, relevance, and base priority are exactly equal to the pre-change Decimal results

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

## RENAMED Requirements

- FROM: `### Requirement: Deterministic selection and family penalty`
- TO: `### Requirement: Deterministic ranking and family penalty`
