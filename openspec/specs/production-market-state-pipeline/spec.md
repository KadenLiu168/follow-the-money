# production-market-state-pipeline Specification

## Purpose
TBD - created by syncing change activate-production-market-state-pipeline. Update Purpose after archive.
## Requirements
### Requirement: Verified bounded daily market history
The production market provider SHALL use an explicit cutoff-bounded 90-calendar-day daily-history request for each of the 13 configured dashboard roles, sufficient under v1 to seek at least 22 consecutive eligible completed-session closes while retaining no more than the configured 260-observation Feed bound. A role SHALL contribute only when its provider symbol, unit, daily-close semantics, availability policy, and fixture provenance are verified for that exact role; a superficially similar proxy or unverified mapping SHALL NOT be substituted.

#### Scenario: Sufficient verified daily history is collected
- **WHEN** a configured role has a verified mapping and the provider returns at least 22 eligible consecutive completed-session closes at or before `evidence_cutoff_at`
- **THEN** the normalized Feed preserves the bounded chronological observations needed for the current change plus 20 current-excluded reference changes

#### Scenario: A role mapping is unverified or mismatched
- **WHEN** the configured symbol, unit, or daily-close semantics cannot be verified for the named dashboard role
- **THEN** that role is unavailable with an explicit reason and no alternate instrument is silently used

### Requirement: Explicit role session ownership and completed-observation eligibility
Every dashboard role SHALL reference one explicit configured session policy. Exchange-traded roles SHALL align provider bars to that policy's expected sessions; continuous 24/5 and 24/7 roles SHALL use their explicit configured daily boundaries. A daily observation SHALL become eligible only after its session close plus the verified conservative availability lag and no later than `evidence_cutoff_at`; current partial sessions, post-cutoff observations, duplicate session labels, unit mismatches, and missing required sessions SHALL NOT be skipped, filled, or treated as completed data.

#### Scenario: Current provider bar is still partial
- **WHEN** a provider returns a bar for a session whose close plus availability lag is after `evidence_cutoff_at`
- **THEN** the snapshot excludes that bar from the current and reference windows

#### Scenario: A required reference session is missing
- **WHEN** the 22-close window contains a missing expected session or duplicate session label
- **THEN** the dependent return or yield-change z-score is unknown with a deterministic reason rather than being calculated over a compressed or filled window

#### Scenario: Role session configuration is invalid
- **WHEN** a role has no session policy, references an unknown policy, or its role/session classes conflict
- **THEN** startup fails before provider collection or Brief generation

### Requirement: Single deterministic market snapshot
Scripts SHALL build one immutable market snapshot from the validated Feed and configuration exactly once before editor projection. In configured role order, the snapshot SHALL contain all 13 dashboard rows, current moves, current-excluded z-scores, anomaly flags, classifier input maps, equity breadth, missing or unknown reasons, and contributing evidence IDs. Price/index/FX/commodity/crypto roles SHALL use simple returns; yield roles SHALL use basis-point changes; each z-score SHALL compare the current change with exactly the preceding 20 eligible changes through the existing precision-50 `ROUND_HALF_EVEN` Decimal formulas. A dashboard anomaly SHALL be true exactly when the absolute available z-score is at least the configured `2.0` boundary.

#### Scenario: Complete price history produces a current-excluded z-score
- **WHEN** a price-like role has 22 consecutive eligible closes with non-zero reference standard deviation
- **THEN** scripts compute 21 simple returns, use the last as current, use the preceding 20 as the reference window, and expose the resulting z-score without output-first quantization

#### Scenario: Complete yield history produces a yield-change z-score
- **WHEN** a yield role has 22 consecutive eligible percent-unit closes with non-zero reference standard deviation
- **THEN** scripts compute 21 basis-point changes and compare the current change with exactly the preceding 20 changes

#### Scenario: Dashboard is assembled from the snapshot
- **WHEN** the snapshot is projected into the Brief dashboard
- **THEN** all 13 configured roles remain in canonical order, available price-like roles show the calculated current return, available yield roles show the calculated basis-point change, and unavailable roles remain visible with no raw level mislabeled as a percentage return

### Requirement: Deterministic breadth and macro-surprise inputs
The snapshot SHALL calculate equity breadth from the observable current simple returns of exactly S&P 500, CSI 300, and Hang Seng as `(positive - negative) / observable`, counting zero returns in the observable denominator but in neither sign count. For each exact v1 CPI, core PCE, and PPI series, scripts SHALL select at most the latest release whose knowledge time is no later than `evidence_cutoff_at`, breaking equal-time ties by evidence ID, calculate its versioned normalized surprise, map it through the exact `-0.5/+0.5` vote boundaries, and invert the vote before providing it to the Inflation dimension. Unknown, incompatible, or absent releases SHALL contribute no vote.

#### Scenario: Cross-market equity returns are observable
- **WHEN** at least one of the three configured equity roles has an eligible current return
- **THEN** scripts calculate breadth from only the observable members in the fixed three-role universe

#### Scenario: Multiple releases for one surprise series are in the Feed
- **WHEN** two cutoff-eligible releases share the same exact v1 series identity
- **THEN** only the latest knowledge-time release, with evidence-ID tie-break, contributes its inverted deterministic vote

#### Scenario: Surprise data is incompatible
- **WHEN** a release lacks actual or consensus, uses an incompatible unit, has a non-v1 series identity, or becomes known after the cutoff
- **THEN** it contributes no Inflation vote and is not cited as Market State support

### Requirement: Production classification before narrative explanation
The normal production pipeline SHALL pass the snapshot's `role_zs`, `role_return_zs`, `yield_change_zs`, `equity_breadth`, and inverted surprise votes to `classify_market_state` exactly once before allocating the editor slots. The resulting regime, five-dimension vector, known-dimension count, and missing-role accounting SHALL be script-owned. Missing-role accounting SHALL consider price/return z inputs and yield-change z inputs, SHALL remain deterministic in configured role order, and SHALL NOT report an available yield role as missing merely because it is carried in `yield_change_zs`.

#### Scenario: Sufficient observations classify a regime
- **WHEN** the Feed yields known Risk Appetite and at least four known dimensions
- **THEN** the production Brief carries the classifier's deterministic `risk_on`, `neutral`, or `risk_off` regime and vector instead of a literal all-`unknown` placeholder

#### Scenario: Classification coverage is insufficient
- **WHEN** Risk Appetite is unknown or fewer than four dimensions are known
- **THEN** the production Brief carries regime `unknown`, preserves every independently known vector dimension, and reports the unavailable role inputs rather than forcing `neutral`

### Requirement: Evidence-bounded editor explanation and authoritative merge
Scripts SHALL append the Market State's deduplicated contributing evidence IDs to the request-local evidence alias map after the existing selected-event aliases, preserving existing selected-event alias stability. The required `market_state_explanation` slot SHALL expose at most eight of those allowed evidence aliases and a bounded source view containing only the script-owned regime, vector, missing roles, and cutoff. Merge SHALL copy the editor's validated wording into only `market_state.explanation`, SHALL retain the script-owned regime/vector/missing roles unchanged, and SHALL mark the resulting explanation claim factual with its validated evidence references. The rendered Market State explanation and claim inventory text SHALL be the same merged wording.

#### Scenario: Editor explains a classified state
- **WHEN** the editor fills the allocated Market State slot with allowed references
- **THEN** its wording becomes the Brief's Market State explanation while every classification field remains byte-for-byte script-owned

#### Scenario: Editor attempts to alter or cite outside the state projection
- **WHEN** editor output injects a regime, vector, missing role, unexposed alias, URL, score, or other authoritative field
- **THEN** the normal pipeline fails closed and publishes no Brief

### Requirement: Informational non-effect and production-path regression proof
Activating Market State SHALL NOT add an LLM pass or change event significance, Morning Relevance, confidence, eligibility, family penalties, selected event IDs, formats, or ordering. Deterministic replay of the same validated Feed, configuration, prompts, and recorded four-pass outputs SHALL reproduce the same market snapshot, Market State, Brief, and evidence projection without provider or model calls. Production-path tests SHALL include complete `risk_on`, `neutral`, and `risk_off` fixtures plus insufficient-history, missing-session, stale/post-cutoff, wrong-unit, zero-reference-standard-deviation, and missing-role cases.

#### Scenario: Market State is activated for an existing event fixture
- **WHEN** the same event inputs are run before and after Market State activation with sufficient market observations
- **THEN** event scores, selected IDs, formats, and ordering are unchanged while the Brief gains the deterministic non-placeholder Market State

#### Scenario: A recorded run is replayed
- **WHEN** replay consumes the stored Feed and recorded four LLM outputs
- **THEN** it reproduces the original market snapshot, classification, editor projection, and rendered Brief with zero external calls
