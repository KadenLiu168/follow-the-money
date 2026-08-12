## ADDED Requirements

### Requirement: Versioned golden-day dataset
The repository SHALL contain a versioned golden-day dataset of at least 30 unique, provenance-reviewed trading days with Feed inputs, recorded structured LLM outputs for offline replay, expected major events, expected full-event labels, canonical story-family member Event IDs plus exact unordered `distinct_material_development` Event-ID pairs, factual and causal claim labels, and versioned configuration. Golden labels SHALL reject response-local family labels, cross-family pairs, asymmetric aliases, and inferred transitive coexistence.

#### Scenario: Evaluation dataset is inspected
- **WHEN** the golden dataset is loaded
- **THEN** at least 30 unique-date independently identified day fixtures pass schema, provenance, cross-reference, uniqueness, and expectation validation

### Requirement: Required scenario coverage
Golden days SHALL cover ordinary sessions, CPI/PCE/payroll/FOMC releases, systemically important company events, major China policy, China-US policy shocks, geopolitics, abnormal equity/bond/volatility moves, and partial provider failure.

#### Scenario: Coverage validation runs
- **WHEN** the evaluation manifest is validated
- **THEN** every required scenario category has at least one associated golden day

### Requirement: Core evaluation metrics
The evaluation runner SHALL use one-to-one stable expected IDs or an explicit alias map and calculate: Major Event Recall@10 as matched expected-major events among the first ten selected divided by expected-major events; Top 3 Precision as matched expected full-event labels divided by the number actually selected in the up-to-three full-event set; Duplicate Story Rate as non-allowed excess selected events in a story family divided by selected events; Unsupported Claim Rate with every filled/rendered validated claim-inventory record whose script-owned `is_factual` flag is true as denominator and those records whose complete support check is unsupported as numerator; and Causal Overclaim Rate with every filled/rendered inventory record whose `is_causal` flag is true as denominator and those records carrying a validated `causal_overclaim` finding as numerator. Optional unfilled allocation slots are excluded. Stable claim slots and IDs, not sentence/clause tokenization or punctuation, SHALL define the claim units, and complete unique audit coverage of the rendered inventory SHALL be required before metrics are calculated.

#### Scenario: Evaluation completes
- **WHEN** all golden-day outputs and expected labels are valid
- **THEN** the runner reports each required metric with numerator, denominator, and aggregate value

#### Scenario: Metric denominator is zero
- **WHEN** a day has no applicable expected event or audited claim for one metric
- **THEN** the day reports `not_applicable` and `0/0`, while aggregate output reports summed counts and applicable/non-applicable day counts without silently dropping the day

### Requirement: Ranking stability
The offline evaluation runner SHALL use a versioned fixed permutation list and the same recorded semantic outputs to compare the identities and complete stable order of every selected full or compact event and separately report the full-event subset and order.

#### Scenario: Feed order changes only
- **WHEN** a golden Feed is evaluated under configured permutations without changing evidence
- **THEN** the report records selected-set inequality as identity drift, any complete ordered selected-ID difference as selection-order drift, and any full-event subset/order difference separately

#### Scenario: Deterministic correctness gate runs
- **WHEN** offline fixture evaluation completes
- **THEN** identity drift, order drift, Unsupported Claim Rate, and Causal Overclaim Rate are all zero or the evaluation exits non-zero

### Requirement: Offline deterministic execution
Deterministic unit and integration evaluations SHALL use fixed raw-provider, market, resolver, analyst, editor, and audit fixtures and SHALL NOT require live financial endpoints or an LLM call; replay SHALL consume saved structured outputs rather than re-invoke a model.

#### Scenario: CI has no external credentials
- **WHEN** tests and fixture-based evaluations run in CI without provider or LLM credentials
- **THEN** deterministic contracts, orchestration, scoring, selection, rendering, and audits remain executable

### Requirement: Regression dimensions
Every evaluation SHALL identify the mandatory application build fingerprint over package version, closed production runtime files, `pyproject.toml`, and `uv.lock`, plus prompt hashes, scoring configuration, provider contract/fixture set, schema versions, requested model configuration, model identifier reported by live responses, and supplementary Git revision/dirty state when available so applicable changes can be compared against a versioned baseline even outside Git.

#### Scenario: Scoring weight changes
- **WHEN** an evaluation is run with modified scoring weights
- **THEN** the report records the configuration difference and resulting metric and ranking deltas

### Requirement: Explicit credentialed prompt and model evaluation
An opt-in live evaluation mode SHALL run the same golden inputs through the four configured LLM passes using declared repetition, request-attempt, monotonic-time, and Decimal USD cost budgets that cover the entire invocation plus an explicit local versioned/fingerprinted exact-model price table containing source/effective date, allowed returned canonical model IDs/aliases, and input/output USD-per-million-token rates. V1 SHALL use LLM concurrency 1 and stable day/date, repetition, pass, resolver-block/analyst-Event, then per-logical-invocation attempt order, so reactive retry eligibility cannot let completion order choose a budget winner. Before each attempt it SHALL atomically debit worst-case cost from the pass's one-token-per-complete-request-byte reservation plus maximum output tokens and SHALL not send when committed spend plus reservation exceeds the budget (equality allowed); every dispatched retry SHALL consume request budget. Only a failure proven pre-send MAY release the reservation. Once dispatch may have reached the service, a timeout, connection failure, or any HTTP error envelope SHALL retain the full reservation; usage-like HTTP-error fields SHALL never be trusted, while retryable errors MAY follow the normal retry matrix only when remaining global request/time/cost budgets admit them. Every received Responses API response object SHALL return an allowed exact model ID, provide trustworthy usage within the reservation, and report zero reasoning tokens before the reservation is atomically replaced with actual declared-rate spend without cache discounts; model mismatch, nonzero/missing reasoning detail, or missing/invalid/over-reservation usage SHALL retain the full reservation and become `budget_integrity_failure`. The evaluator SHALL validate and store every structured outcome and compare per-run and aggregate metrics with a selected baseline; it SHALL NOT fetch pricing at runtime, run in credential-free CI, or claim bit-for-bit reproducibility.

#### Scenario: Prompt or model comparison is requested
- **WHEN** a credentialed evaluator selects a baseline and candidate prompt/model configuration
- **THEN** the report includes every run outcome, refusal/failure count, model and prompt fingerprints, cost/usage metadata, metric distributions, and per-day deltas

#### Scenario: Live budget is exhausted
- **WHEN** the declared request, monotonic-time, or reserved Decimal USD cost budget cannot admit the next attempt, or reported usage fails budget integrity, before all planned repetitions complete
- **THEN** evaluation stops, reports machine-readable `incomplete` evidence, exits 1, and does not silently compute a complete comparison

### Requirement: Machine-readable and human-readable reports
The evaluation runner SHALL emit a machine-readable result and a concise human-readable evidence summary containing failures, baseline deltas, numerator/denominator details, applicable-day counts, and per-day drill-down references. The shipped v1 offline gate SHALL allow zero Recall@10 or Top 3 Precision decrease and zero Duplicate Story Rate increase versus the selected versioned baseline; a baseline/tolerance change SHALL be explicit and SHALL NOT be auto-accepted. Credentialed repeated live comparisons SHALL remain evidence reports rather than deterministic release gates, and no metric SHALL be treated as proof merely because evaluation ran.

#### Scenario: Unsupported claim regression occurs
- **WHEN** a day produces a claim absent from its expected evidence ledger
- **THEN** both reports identify the day, claim, evidence failure, and affected aggregate metric

#### Scenario: Offline quality metric regresses
- **WHEN** Recall@10 or Top 3 Precision decreases, or Duplicate Story Rate increases, by any positive amount versus the selected v1 baseline
- **THEN** offline evaluation exits non-zero unless an explicit reviewed versioned baseline/tolerance update is supplied

### Requirement: Validation before scoring
Invalid raw-provider, Feed, expected-label, resolver, verified-packet, analysis, editor, audit, Brief, degraded-report, or run-manifest fixtures SHALL fail evaluation setup rather than being silently excluded from metric denominators.

#### Scenario: Golden fixture violates schema
- **WHEN** one golden-day Feed is invalid
- **THEN** the evaluation fails with the fixture path and validation error before aggregate metrics are calculated
