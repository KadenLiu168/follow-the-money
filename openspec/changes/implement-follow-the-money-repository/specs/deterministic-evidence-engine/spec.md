## ADDED Requirements

### Requirement: Latest Feed consumption and health assessment
The daily Skill SHALL consume only `feeds/latest.json`, validate its supported schema major version, canonical digest, half-open window, fixed cutoff, calendar horizon, and provider outcomes, calculate freshness from an injected clock, mark v1 lag over 30 minutes stale, refuse normal mode over 2 hours, and expose stale, coverage-gap, conflict, or degraded warnings before analysis.

#### Scenario: Feed is stale
- **WHEN** the injected current time minus `evidence_cutoff_at` exceeds the configured freshness limit
- **THEN** the run explicitly carries a stale warning through the final output and does not represent coverage as complete

#### Scenario: Feed exceeds the normal-mode maximum lag
- **WHEN** `brief_generated_at - evidence_cutoff_at` exceeds 2 hours
- **THEN** normal Brief generation fails before LLM calls instead of using an arbitrarily old Feed

#### Scenario: Brief clock precedes Feed knowledge or generation
- **WHEN** `brief_generated_at` is earlier than `evidence_cutoff_at` or the Feed's `generated_at`
- **THEN** the run fails closed with `clock_before_feed` before freshness arithmetic or any LLM call

#### Scenario: Historical daily Feeds exist
- **WHEN** files exist under `feeds/daily/`
- **THEN** the normal daily Skill does not read them

#### Scenario: Feed digest or version is incompatible
- **WHEN** the Feed digest does not match its canonical payload or its major schema version is unsupported
- **THEN** the Skill fails closed before constructing runtime objects

### Requirement: Deterministic normalization and entity resolution
The evidence engine SHALL normalize timestamps, URLs, titles, markets, categories, and configured entity aliases through scripts and an entity registry.

#### Scenario: Known Fed aliases appear
- **WHEN** evidence contains `Federal Reserve`, `Fed`, or `FOMC`
- **THEN** the relevant references resolve to the configured Federal Reserve entity identity without an LLM

#### Scenario: Entity is unknown
- **WHEN** no registry entry or deterministic identifier supports an entity match
- **THEN** the engine preserves the raw label and does not invent a canonical entity

### Requirement: High-recall filtering and candidate blocking
The engine SHALL construct the design-defined seed-mention graph before any semantic-resolution call. Scripts SHALL designate roots from every candidate ledger entry whose type is `FACT` or `CLAIM` and whose origin payload is exactly `news`, `macro_release`, `policy`, `filing`, `flow`, or `positioning`, without a predicate allowlist; a node SHALL be `(evidence_id, seed_fact_id, normalized subject-or-unresolved-subject key)`. `market_data`, `calendar`, `OBSERVATION`, `INFERENCE`, and all entries outside that exact type-plus-origin rule SHALL NOT form nodes or consume resolver capacity; a non-seed fact MAY be a bounded supporting ref only inside a seed component sharing its exact evidence ID, while unattached non-seeds remain solely in deterministic downstream stores. Using each seed fact's `knowledge_available_at`, an edge SHALL exist only for equal complete fact keys excluding source lineage; or shared exact entity within 48 hours plus exact predicate/category or title similarity `>=0.45`; or two entity-less mentions with exact market/category within 12 hours and similarity `>=0.85`. V1 title similarity SHALL be the exact NFC/casefold/remove-punctuation-separator-control/code-point-trigram Jaccard algorithm, with short strings exact-only. Distinct non-empty entity sets SHALL NOT join only through title/time, and seed mentions from one bridge evidence SHALL NOT join merely because they share that evidence. Each component resolver projection SHALL contain only its allowed seed/supporting facts and sorted projected evidence records, so one bridge MAY appear in multiple components without leaking cross-component fact membership. The engine SHALL preserve components and create blocks within the v1 20-projected-record/24-seed/32-KiB canonical dynamic-data limits without silently discarding seed evidence or splitting a component. V1 SHALL hash each component's sorted seed-mention-node IDs as its stable key; hash each packed block's ordered component IDs, projected `(evidence_id, allowed_fact_ids)` records, and boundaries; sort components by stable key; and apply non-reordering next-fit packing. Packed requests SHALL preserve component aliases/boundaries without cross-component deduplication, and every resolver proposal/unresolved group SHALL name exactly one component and use only its references; no tokenizer estimate participates.

#### Scenario: Unrelated evidence arrives together
- **WHEN** evidence has no material time, market, entity, category, or title overlap
- **THEN** it is not placed in the same candidate component; capacity packing MAY place its components in one resolver request only with explicit boundaries that forbid cross-component proposals

#### Scenario: Bridge article mentions two independent events
- **WHEN** one article overlaps two otherwise distinct event clusters
- **THEN** its distinct fact-mention projections may appear in both candidate components, but the evidence identity alone creates no edge and does not merge the components or their fact allowlists

#### Scenario: Disconnected candidate components fit only in separate blocks
- **WHEN** packing whole graph components together would exceed the 20-projected-record or 32-KiB dynamic-data limit but each component fits independently
- **THEN** the v1 stable-key next-fit packer emits the uniquely ordered separate blocks, preserves every evidence ID, and records their component lineage

#### Scenario: Connected candidate component exceeds a configured bound
- **WHEN** one connected component itself exceeds the 20-projected-record, 24-seed, or 32-KiB dynamic-data limit
- **THEN** normal mode fails typed `candidate_group_too_large` before resolver calls rather than splitting a possible semantic relationship, truncating evidence, or claiming completeness

#### Scenario: Resolver block capacity is exceeded
- **WHEN** deterministic splitting produces more than 40 resolver blocks
- **THEN** normal mode fails with `capacity_exceeded` before any block is silently dropped

#### Scenario: Feed contains only dashboard and calendar facts
- **WHEN** a valid Feed has many market observations/calendar entries but no atomic-event seed fact
- **THEN** it produces zero resolver components/blocks, retains those facts for deterministic dashboard/watchlist use, and may continue to the explicitly sparse normal path without consuming resolver capacity

### Requirement: Evidence Ledger construction
Before financial analysis, the engine SHALL construct and freeze an immutable ledger whose source-derived entries are typed `FACT`, `CLAIM`, or `OBSERVATION` and whose script-derived calculations may be typed `INFERENCE`; every entry SHALL reference existing Feed evidence or deterministic parent ledger IDs. Every source fact SHALL retain a script-derived `knowledge_available_at` following the Feed payload time table, with date-only knowledge mapped to its end-of-source-local-date eligibility instant. For each canonical Event, scripts SHALL set `fully_known_at` to the maximum knowledge instant over the exact `key_fact_ids`, keep it distinct from economic effective/reference time, reject a missing or post-cutoff knowledge instant, and reject LLM mutation of either time. LLM mechanisms and implications SHALL remain in the separate Analysis object and SHALL NOT mutate or append to the ledger.

#### Scenario: Numeric fact enters the ledger
- **WHEN** a normalized macro item supplies an actual value
- **THEN** the ledger fact stores the value, unit, and originating evidence ID

#### Scenario: Unknown evidence is referenced
- **WHEN** a runtime object refers to an evidence ID absent from the input Feed
- **THEN** validation rejects the object

#### Scenario: Analyst attempts to append an inference
- **WHEN** an LLM analysis output attempts to add or modify a ledger entry
- **THEN** semantic validation rejects the analysis and the frozen ledger remains unchanged

#### Scenario: Event-defining facts become known at different times
- **WHEN** a multi-key-fact Event has valid knowledge instants from staggered releases
- **THEN** scripts set `fully_known_at` to the latest key-fact knowledge instant while preserving each fact's separate economic effective/reference time

### Requirement: Deterministic market analytics
The engine SHALL accept only the design-bounded canonical decimal-string grammar and calculate session simple returns `(current / previous - 1)`, yield basis-point changes `(current_percent - previous_percent) * 100`, volume changes `(current / previous - 1)`, sample rolling volatility over the preceding 20 consecutive completed-session returns annualized by the v1 session-class factor, price abnormal-move z-scores against those preceding 20 simple returns, yield abnormal-move z-scores against the preceding 20 consecutive completed-session basis-point changes, and directional breadth `(positive - negative) / observable` from raw observations aligned to completed configured sessions. Every operation SHALL use a fresh design-defined precision-50 `ROUND_HALF_EVEN` Decimal context with its exact traps/range and normative stable-order mean/variance/`Decimal.sqrt`/z operation order, independent of the ambient context. Both z-score references SHALL exclude the current change, a missing required session SHALL make the dependent window unknown without skipping or filling, and equity/ETF return inputs SHALL use a verified adjusted-close contract.

#### Scenario: Sufficient history is available
- **WHEN** an instrument has the configured valid lookback and a current observation
- **THEN** its metrics are calculated reproducibly using configured formulas

#### Scenario: History is insufficient
- **WHEN** an instrument lacks enough valid observations
- **THEN** dependent metrics are `unknown` with an insufficiency reason and no forward-fill or guessed values

#### Scenario: Numeric input is invalid
- **WHEN** an input is non-finite, boolean, unit-incompatible, has a non-positive ratio denominator, a zero reference standard deviation, or a zero breadth denominator
- **THEN** the dependent metric is rejected or `unknown` with the exact reason and no float coercion, divide-by-zero substitution, or imputation

#### Scenario: Metric is serialized
- **WHEN** a calculation succeeds from finite decimal inputs
- **THEN** the canonical precision-50 local-context value drives every bin/gate/sort and only the output boundary applies documented round-half-even quantization

#### Scenario: Process Decimal context is hostile
- **WHEN** a caller changes global precision/rounding or supplies values immediately around a score threshold
- **THEN** the fresh normative local context and operation order produce the same canonical value and threshold decision as the hand-calculated oracle

### Requirement: Deterministic surprise calculation
The engine SHALL calculate raw surprise as `actual - consensus` only from compatible facts and SHALL calculate normalized surprise as `raw_surprise / configured_positive_scale` only when a versioned per-series scale exists. Shipped v1 SHALL use a `0.1` percentage-point scale only for exact US all-items SA CPI MoM, US core PCE price-index MoM, and US PPI final-demand SA MoM series identities; every other identity/frequency/adjustment SHALL remain `unknown` until a versioned scale and oracle are added.

#### Scenario: Actual and consensus exist
- **WHEN** actual and consensus use the same compatible unit
- **THEN** raw surprise equals their deterministic difference

#### Scenario: Consensus is missing
- **WHEN** a release has no consensus evidence
- **THEN** surprise is `unknown` and the LLM is not asked to estimate it

### Requirement: Reaction observability
The engine SHALL determine `observable` or `not_observable` for each event/asset pair from the Event's script-owned `fully_known_at` information-release anchor, asset session policy, exchange calendar, session open/closed state, and observation timestamps using the v1 first-completed-session-strictly-after-knowledge versus immediately-prior-close contract; knowledge at or after close SHALL roll to the next completed session and both values SHALL have been source-available before cutoff. Economic effective/reference time SHALL remain separate metadata and SHALL NOT anchor reaction. The later `risk_on | neutral | risk_off | unknown` market-regime classification SHALL NOT affect observability.

#### Scenario: Announcement occurs after cash close
- **WHEN** an event occurs after the affected cash market closes and no later session observation exists
- **THEN** cash-market reaction and Repricing Magnitude are `not_observable`/`unknown`, the missing component contributes zero and reduces component coverage under the scoring contract, and it is never misrepresented as an observed zero reaction or causal evidence

#### Scenario: Session has completed with data
- **WHEN** the relevant post-event session has completed and valid before/after observations exist
- **THEN** the reaction is `observable` with its measurement resolution and timestamps

#### Scenario: Old or future-effective fact is newly disclosed
- **WHEN** news reports an older occurrence, a policy is announced before its future effective date, or an old flow/positioning `as_of` value is published now
- **THEN** reaction begins strictly after `fully_known_at`, never from the older or future economic effective/reference time

#### Scenario: Source knowledge has only date precision
- **WHEN** a key fact supplies only a valid source-local knowledge date
- **THEN** scripts use the already normalized end-of-source-local-date eligibility instant in `fully_known_at` for session ordering; only a missing or invalid knowledge eligibility instant rejects the Event rather than silently making reaction observable or unknown

### Requirement: Evidence confidence and conflicts
The engine SHALL define each canonical Event's script-owned `key_fact_ids` as exactly its sorted deduplicated existing `event_defining_fact_ids`, calculate confidence independently for each such key fact by source family, and assign the Event the lowest key-fact confidence: at least one non-conflicting Tier 1 source or two independently originated Tier 2 families is High, exactly one Tier 2 family is Medium, Tier 3-only support is Low, and no support is unresolved; any unresolved key fact SHALL exclude the Event, and a material conflict SHALL cap the affected key fact and Event at Medium until explicitly resolved.

#### Scenario: Tier 1 evidence supports an event
- **WHEN** a primary official source supports the event facts without material conflict
- **THEN** the event can receive High evidence confidence

#### Scenario: Tier 3 is the only support
- **WHEN** only Tier 3 evidence supports a material claim
- **THEN** confidence is Low and the claim cannot be treated as a confirmed full-event fact

#### Scenario: Sources conflict
- **WHEN** valid sources provide incompatible values for the same fact
- **THEN** the conflict is retained in the verified packet and confidence is not silently upgraded

#### Scenario: Mirrored reports share one origin
- **WHEN** multiple URLs trace to one original publisher or wire story
- **THEN** they count as one source family and cannot create independent Tier 2 corroboration

### Requirement: Targeted verification packet
After canonical event construction and before financial analysis, the system SHALL assemble a verified event packet containing only validated in-Feed event facts with their `knowledge_available_at`, the Event's recomputed `fully_known_at`, the frozen ledger, market observations, provider-bound canonical source URLs, conflicts, derived deterministic analytics, and the stable ordered `eligible_catalyst_calendar_ids` from the already computed deterministic up-to-six next-24-hour watchlist; every catalyst ID SHALL resolve to the packet's exact input Feed/calendar snapshot. Packet verification SHALL perform no network fetch and SHALL record a deterministic completeness status.

#### Scenario: Event enters the shortlist
- **WHEN** the post-resolution key of confidence, maximum available absolute normalized surprise over `key_fact_ids` with unknown last, `fully_known_at`, and stable Event ID places a verified packet in the bounded analyst shortlist
- **THEN** only its verified packet, not the raw global Feed, is supplied to the financial analyst

#### Scenario: Verification cannot support a key fact
- **WHEN** in-Feed packet completeness checks cannot substantiate one of the Event's declared `key_fact_ids`
- **THEN** the packet marks the key fact and packet unresolved, excludes the event from analysis, and never asks the analyst to complete or remove the fact

#### Scenario: Medium-confidence packet passes full-event completeness
- **WHEN** every declared `key_fact_id` has valid in-Feed provenance, owning-provider-bound canonical URL, and knowledge instant, `fully_known_at` recomputes exactly, numeric units agree, and no material conflict remains unresolved
- **THEN** the packet records `verification_status = passed` without changing its Medium confidence

#### Scenario: Analyst-call bound is applied
- **WHEN** more than 20 packets pass verification
- **THEN** the analyst shortlist takes the first 20 by confidence, maximum available absolute normalized surprise across each Event's `key_fact_ids` with unknown last, `fully_known_at`, and stable ID, while retaining every non-shortlisted packet in the audit trace; pre-analyst reaction z-scores are not used
