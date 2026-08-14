## ADDED Requirements

### Requirement: Verified-packet financial analysis
The financial analyst SHALL process only shortlisted verified event packets and SHALL return a closed `analyst-output.schema.json` containing only its owned explanations, impact chains, asset mappings (whose closed `horizon` is the per-mapping horizon), market-reaction interpretation, exactly one Event-level price-in assessment, indirect money-flow indication, watch points, alternative interpretations, categorical features (including the distinct closed `structural_horizon` feature), and existing references without adding to the frozen Evidence Ledger; there is no additional free-standing time-horizon field. Scripts SHALL validate and merge those fields with script-owned values into authoritative `analysis.schema.json` objects.

#### Scenario: Raw Feed is offered to analyst
- **WHEN** analysis is requested without a valid verified event packet
- **THEN** the analysis pass refuses to run

#### Scenario: Analyst returns an authoritative score or event fact
- **WHEN** `analyst-output` attempts to supply a script-owned numeric score, final status, or replacement Event/ledger field
- **THEN** its strict schema or ownership validation rejects the output before any Analysis object is assembled

### Requirement: Fact, mechanism, and implication separation
Every impact chain SHALL distinguish sourced facts from mechanisms and implications, and non-factual steps SHALL be worded as interpretations rather than certainties.

#### Scenario: Lower inflation chain is analyzed
- **WHEN** the analyst connects a sourced inflation release to rates and long-duration assets
- **THEN** the release remains a fact while the rates and asset effects are typed as mechanism or implication with uncertainty

### Requirement: Bounded reaction attribution
Market-reaction attribution SHALL use only `direct`, `likely`, `concurrent`, or `unclear` and SHALL reference script-generated market observations.

#### Scenario: Price move shares only the same date
- **WHEN** no stronger timing or corroborating evidence links an event and a price move
- **THEN** attribution is `concurrent` or `unclear`, not stated as direct causality

### Requirement: Evidence-bound price-in assessment
Price-in status SHALL be one of `not_priced`, `partial`, `mostly_priced`, or `unclear`, and any non-unclear status SHALL reference valid expectation or reaction evidence.

#### Scenario: No expectations evidence exists
- **WHEN** the verified packet contains no consensus, futures, options, prior positioning, relevant price reaction, or equivalent expectation evidence
- **THEN** `price_in` is `unclear`

### Requirement: Money-flow classification
Scripts SHALL own final money-flow status `confirmed | indicated | no_evidence`: direct typed Flow or Positioning evidence assigns `confirmed`; otherwise a validated analyst `indirect_indication` with referenced non-price evidence may assign `indicated`; otherwise status is `no_evidence`. The analyst SHALL NOT assign `confirmed`, and price movement alone SHALL produce `no_evidence`.

#### Scenario: ETF net-flow item exists
- **WHEN** a valid typed Flow item directly measures ETF net flow
- **THEN** scripts can classify the corresponding flow as `confirmed` with its evidence ID

#### Scenario: Asset price rises without flow data
- **WHEN** the only supporting observation is positive price movement
- **THEN** money-flow status is `no_evidence` and the analysis does not state that money flowed into the asset

#### Scenario: Analyst claims confirmed flow
- **WHEN** analyst output attempts to assign `confirmed`
- **THEN** analysis validation rejects that field ownership violation

### Requirement: Safe asset mapping
An Event SHALL contain at most one analyst asset mapping for each of the design-defined nine groups; duplicate groups SHALL reject the analyst result rather than merge. Each mapping SHALL contain exactly one `positive | negative | mixed | unclear` direction, `high | medium | low | unknown` confidence, `intraday | next_session | days | weeks | months | years_plus | unknown` horizon, one non-empty at-most-192-byte mechanism, 1..8 existing packet references, and the required nullable at-most-192-byte audit reason whose nullability follows the design's uncertain-value rule. It SHALL NOT contain trading instructions. Scripts SHALL own the group-to-dashboard reaction proxies, one-group-one-count breadth rule, and final Repricing/Systemic-Breadth arithmetic.

#### Scenario: Analysis proposes an entry
- **WHEN** analyst output includes buy, sell, position size, entry, exit, or equivalent instruction
- **THEN** output validation rejects the analysis

### Requirement: Categorical semantic scoring features
The analyst SHALL return only the closed values `scope = single_entity | sector | single_market | cross_market | unknown`, `fundamental_depth = headline | operating_or_policy | balance_sheet_or_liquidity | systemic | unknown`, `reversibility = high | medium | low | effectively_irreversible | unknown`, and `structural_horizon = intraday | days | weeks | months | years_plus | unknown`, plus short audit reasons; scripts SHALL use the fixed versioned mappings in `scoring.yaml` to produce `0..100` Fundamental Magnitude and Persistence components.

#### Scenario: Analyst lacks persistence evidence
- **WHEN** the verified packet does not support a persistence judgment
- **THEN** the analyst can return `unknown` and the script follows the configured missing-data policy

### Requirement: Versioned v1 scoring contract
The shipped v1 scoring configuration SHALL match the design's fixed category maps, exact three surprise scales, maximum-absolute available `key_fact_ids` Surprise aggregation with all-unavailable unknown, whole-component known/unknown rules, weight-based coverage formula, surprise/repricing bins and unavailable rules, exact nine asset groups/proxy mappings and `/9` Systemic Breadth ratio including only-`unclear` unknown behavior, 30/20/20/20/10 significance weights, `evidence_cutoff_at - fully_known_at` freshness boundaries, 40/25/20/15 Morning Relevance weights, `0.70/0.30` Brief Priority formula, 60% minimum component coverage for every normal full or compact selection, 60/40 full/compact priority thresholds, and 15-point routine same-family penalty, and SHALL reject missing or inconsistent mappings instead of supplying hidden defaults.

#### Scenario: Shipped v1 oracle is evaluated
- **WHEN** the normative hand-calculated component vector and v1 configuration are loaded
- **THEN** every component, coverage value, final score, threshold decision, and penalty matches the documented Decimal result

#### Scenario: Scoring configuration is incomplete
- **WHEN** an enum mapping, feature bin, weight, threshold, precision, or tie-break rule is absent or invalid
- **THEN** configuration validation fails before any event is scored

### Requirement: Deterministic event significance
Scripts SHALL calculate a `0..100` Event Significance separately from confidence using Decimal arithmetic and exhaustive configured component mappings for Fundamental Magnitude, Surprise, Systemic Breadth, Repricing Magnitude, and Persistence, initially weighted 30%, 20%, 20%, 20%, and 10%; unknown components SHALL contribute zero without weight redistribution and SHALL reduce reported component coverage.

#### Scenario: Significance is calculated
- **WHEN** component values and configured missing-data rules are available
- **THEN** the same input and configuration always produce the same significance score and component audit trail

#### Scenario: Component is unknown
- **WHEN** one significance component is unknown
- **THEN** its contribution is zero, the full configured denominator remains, and the score reports the reduced coverage rather than silently reweighting other components

### Requirement: Deterministic morning relevance
Scripts SHALL calculate a `0..100` Morning Relevance separately from Event Significance using freshness age `evidence_cutoff_at - fully_known_at` with the fixed bins, never the economic effective/reference time, plus required analyst-output categories `cn_hk_exposure` and `us_next_session_exposure` from the closed enum `direct | indirect | none | unknown`, mapping to `100 | 50 | 0 | 0`, and `catalyst_calendar_ids` restricted to existing IDs in the deterministic up-to-six critical/high next-24-hour watchlist, mapping non-empty to 100 and empty to 0. Scripts SHALL validate categories/references, reject a missing or post-cutoff `fully_known_at`, and SHALL NOT infer these features from prose.

#### Scenario: Old resolved event remains in the window
- **WHEN** an event is less fresh and has no unresolved next-session catalyst
- **THEN** its morning relevance is lower according to configuration without modifying its intrinsic significance

#### Scenario: Economic and knowledge times differ
- **WHEN** an older occurrence or measurement is newly published, or an announced policy has a future effective date
- **THEN** freshness uses the Event's recomputed `fully_known_at` and does not become older or future merely because its economic time differs

### Requirement: Confidence gates
High-confidence and packet-passed conflict-free Medium-confidence events SHALL be both full-capable and compact-capable; Low-confidence events SHALL be compact-capable only with an explicit Breaking/Unconfirmed label; unresolved events and events without valid analysis SHALL be ineligible. Full-capable events SHALL still meet final priority 60, compact-capable events SHALL meet final priority 40, and every normal selection SHALL meet 60% significance-component coverage.

#### Scenario: Major low-confidence breaking report
- **WHEN** a material report has only Low confidence
- **THEN** it may appear only in a clearly marked Breaking/Unconfirmed treatment and not as a confirmed Top 3 event

### Requirement: Deterministic final selection
Scripts SHALL apply the design's single normative pipeline: calculate base priority; remove unresolved/no-analysis/below-60%-coverage events; classify full/compact capability from confidence; stable-sort by base priority/`fully_known_at`/ID; identify the first member of each script-derived canonical story family; apply the one-time 15-point non-first-member penalty except when that later Event has a validated canonical `distinct_material_development` pair with the frozen first member; floor final priority at zero; reapply the 60 full/40 compact thresholds; stable-sort by final priority/`fully_known_at`/ID; take at most twelve; and assign full format to the first up to three selected full-capable events while rendering other selected compact-capable events compactly. The target of ten SHALL be informational only and SHALL NOT alter selection.

#### Scenario: Feed item order is shuffled
- **WHEN** identical evidence and the same validated semantic outputs are supplied in a different array order
- **THEN** final full-event and ordered selected event IDs remain stable

#### Scenario: Only seven events pass quality threshold
- **WHEN** fewer than the normal target of ten events satisfy quality and confidence gates
- **THEN** the Brief includes only the qualifying events rather than lowering thresholds

#### Scenario: Fewer than three events qualify in total
- **WHEN** zero, one, or two events survive the complete selection pipeline
- **THEN** exactly those events are selected in their eligible full or compact format and the Brief records a sparse-result warning without promotion or invention

#### Scenario: Thirteen events qualify
- **WHEN** thirteen events pass all gates
- **THEN** final stable order selects exactly the first twelve and the thirteenth remains only in the audit trace

### Requirement: Story-family redundancy control
Scripts SHALL freeze the base-priority order before assigning each non-singleton canonical story family's unpenalized first member, SHALL derive that family ID from sorted member Event IDs, SHALL treat unknown or singleton families as event-ID-specific singletons, SHALL subtract the v1 15-point penalty exactly once from every later member unless the exact unordered Event-ID pair between it and the frozen first member carries validated `distinct_material_development`, and SHALL reapply thresholds and final sorting after penalty without enforcing category diversity. Coexistence SHALL be pairwise and non-transitive; a pair between two later members SHALL NOT exempt either from the first-member comparison.

#### Scenario: Fed statement, press conference, and projections overlap
- **WHEN** three related events belong to the same story family
- **THEN** their post-penalty priority prevents routine duplication from automatically filling Top 3

#### Scenario: Systemic crisis has distinct material developments
- **WHEN** related events remain independently material after the redundancy penalty
- **THEN** more than one can enter Top 3 regardless of category concentration

#### Scenario: Pairwise coexistence does not become transitive
- **WHEN** a three-Event family contains validated coexistence pairs A-B and B-C but no A-C pair and A is the frozen first member
- **THEN** B is exempt from the routine penalty, C is penalized exactly once, and no implementation infers an A-C exemption
