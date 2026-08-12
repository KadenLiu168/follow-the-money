# Evaluation

## Golden-day dataset

`evals/dataset/manifest.json` defines at least 30 unique, provenance-reviewed
trading days covering: ordinary sessions, CPI/PCE/payroll/FOMC releases,
systemically important company events, major China policy, China-US policy
shocks, geopolitics, abnormal cross-asset moves, and partial provider
failure. Each fixture has a Feed input, recorded four-pass outputs, expected
major events, expected full-event labels, canonical story-family member
Event IDs plus exact unordered `distinct_material_development` pairs, and
factual/causal claim labels. Invalid fixtures fail setup before scoring.
Each Feed item points to a checked-in source response metadata/body pair whose
status, size, and SHA-256 are revalidated before scoring. Each recorded pass is
also stored in a separate `evals/dataset/pass_outputs/<date>/` file; the inline
projection and referenced file must match exactly, so missing or tampered pass
artifacts fail setup. The evaluator re-derives a bounded visible excerpt from
each saved source body, validates source-specific structured fields such as
Yahoo observations and SEC form/date/accession values, and requires recorded
analyst/editor prose to carry that source-derived fragment in addition to its
Feed evidence aliases.

## Metrics

| Metric | Definition |
| --- | --- |
| Major Event Recall@10 | matched expected-major events in the first ten selected / expected-major events |
| Top 3 Precision | matched expected full-event labels / number actually selected in the up-to-three full set |
| Duplicate Story Rate | non-allowed excess selected events in a story family / selected events |
| Unsupported Claim Rate | claim-inventory records with `is_factual=true` whose support check is unsupported / all such records |
| Causal Overclaim Rate | inventory records with `is_causal=true` carrying a validated `causal_overclaim` finding / all such records |

Claim units are validated claim-inventory records (not sentences/clauses);
complete unique claim-audit coverage is required before scoring. Zero
denominators are `not_applicable` with `0/0`, never silently dropped;
aggregates report summed numerators/denominators and applicable/non-applicable
day counts.

## Ranking stability

A fixed, versioned permutation list plus recorded semantic outputs drives:
identity drift (selected-set inequality), selection-order drift (complete
stable ordered ID list), and separately the full-event subset/order. Every
drift value must be zero for the deterministic correctness gate.

## Offline gates (v1)

- Zero Recall@10 / Top-3 Precision decrease and zero Duplicate Story Rate
  increase versus the selected versioned baseline.
- Zero Unsupported Claim Rate and Causal Overclaim Rate for fixture-backed
  normal outputs.
- Changing a baseline/tolerance requires an explicit versioned update; it is
  never auto-accepted.

## Live evaluation

An opt-in credentialed mode re-runs the same golden inputs through the four
configured passes under declared repetition, request-attempt, monotonic-time,
and Decimal USD cost budgets covering the entire invocation. It requires an
explicit local versioned/fingerprinted exact-model price table and never
fetches pricing at runtime. V1 uses LLM concurrency 1 and stable
day/repetition/pass/object/logical-attempt admission. Budget and integrity
rules:

- Before every attempt, atomically debit a worst-case reservation
  (one-token-per-complete-request-byte plus max output tokens); do not send
  when committed + reservation would exceed the budget (equality allowed).
- A failure proven pre-send releases the reservation; post-dispatch
  connection loss/timeout/HTTP error retains it.
- A received Responses object must return an allowed exact model, valid
  usage within the reservation, and zero reasoning tokens; only then does
  actual spend (declared rates, no cache discounts) replace the reservation.
- Model mismatch, nonzero/missing reasoning, or invalid/over-reservation
  usage retains the reservation and becomes `budget_integrity_failure`.
- Early exhaustion reports machine-readable `incomplete` status and exits 1.

Live evaluation is an evidence report, not a release gate: it never claims
bit-for-bit model repeatability and is absent from credential-free CI.
