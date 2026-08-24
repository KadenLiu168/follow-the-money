## MODIFIED Requirements

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

#### Scenario: Brief-only configuration is supplied
- **WHEN** closed configuration contains a removed full/compact threshold, Brief count limit, or the superseded relevance-weight key
- **THEN** strict configuration loading rejects the unknown legacy key rather than accepting an alias or fallback

#### Scenario: Scoring is retained without a caller
- **WHEN** the repository exposes the typed deterministic scoring library after this change
- **THEN** no Feed or other production entry path invokes it and no Agent-owned or serialized scoring contract is introduced
