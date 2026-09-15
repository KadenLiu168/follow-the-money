## Context

See `proposal.md` for motivation and `specs/feed-evidence-pipeline/spec.md` for observable requirements.

The Provider protocol is intentionally small: `fetch(window, client)` followed by `normalize(raw, window)`. Today `feed/cli.py` wraps the complete `adapter.fetch()` call with one durable rate transition and one pair of concurrency gates. That implementation assumes one fetch equals one upstream request. SEC 13F current/change acquisition requires submissions plus two complete submissions per watched company, while deterministic CFTC acquisition requires date discovery and sequentially paged rows. The rate transition therefore has to move to the actual-send seam without changing the Provider protocol or creating a semantic framework.

`_production_adapters()` already supports multiple adapter instances per logical Provider, and `_run_adapter()` already accumulates them into one `ProviderOutcome`. `feed/snapshot.py` already selects or carries whole Provider slices. Those seams are retained: eight SEC company acquisition units remain one `sec_edgar` Provider, and no per-company snapshot merge is introduced.

The logical Feed is schema major v4 with five domains and eight required Providers. Provider contract versions are embedded in canonical contract snapshots, but the current manifest loader accepts only version 1 and semantic validation does not yet dispatch payload requirements by embedded Provider contract version. The current configuration snapshot also omits the watched-company selection, so a consumer cannot independently prove SEC slice completeness.

## Goals / Non-Goals

**Goals:**

- Make every actual Provider request, including redirect hops and pages, pass the existing durable transport guarantees exactly once.
- Produce complete, deterministic SEC 13F and CFTC COT current/change evidence that a Host Agent can express from the current validated Feed alone.
- Preserve exact cutoff, official provenance, canonical numeric, deterministic identity, coverage, freshness, and fail-closed behavior.
- Keep old supported v4/provider-v1 bundles readable while requiring version-2 semantics from the new SEC and CFTC producers.
- Reuse the existing Provider outcome, bundle, identity, freshness, snapshot, and publication machinery.

**Non-Goals:**

- A generic semantic enrichment, comparator, derivation, pagination, or Provider-acquisition framework.
- Form 4, 13D, 13G, `13F-HR/A` merging, or deeper 8-K/10-Q/10-K semantics.
- Changes to news, macro release, policy, Digest editorial presentation, or snapshot database/storage semantics. The narrow SEC/CFTC-v2 complete-state carry-forward admission correction in Decision 10 is in scope; legacy event-list and empty-check selection rules are not changed.
- Historical Feed lookup, Provider access by the Host Agent, model/LLM runtime, ranking, market direction, prediction, recommendation, or trading execution.
- Publication of previous-only CFTC markets as synthetic current positioning items.

## Decisions

### 1. Move rate, deadline, and concurrency management to a per-send client

Add a narrow `ManagedProviderClient` used only as the production transport passed to the unchanged adapter `fetch(window, client)` interface. It owns the underlying HTTP client and receives the resolved Provider contract, shared `RateRegistry`, scope lock, global semaphore, host semaphore map, deadline/cancellation state, deterministic wall and monotonic clocks, and sleep function.

For each actual send it performs, in order:

1. validate cancellation, remaining deadline budget, requested timeout, Provider fetch/redirect host policy, and exact Provider user-agent;
2. acquire the shared rate-scope lock;
3. load/refill the sole durable scope state and wait only when eligibility fits before the deadline;
4. durably debit and install provisional crash cooldown;
5. acquire global then normalized target-host concurrency;
6. recheck cancellation/deadline, invoke one underlying send, and mark it dispatched;
7. inspect a returned response for a valid `Retry-After` and reconcile exactly once;
8. on an exception after dispatch may have begun, reconcile exactly once; on a confirmed failure before dispatch, refund the provisional debit;
9. release host/global semaphores and the scope lock in reverse order.

No rate transition remains in `_run_adapter()`. It continues to own Provider-level attempt count, retry admission, normalization, item validation, accepted/rejected counters, availability, and final outcome. A successful multi-request acquisition increments the existing Provider-level `fetched` count once; it does not redefine that field as an HTTP request counter.

The managed client records the actual injected-clock timestamp of each concrete response, including redirect/error responses, independently of domain acceptance. Orchestration preserves the latest observed timestamp across requests, retries, and company units as `retrieved_at`. A later timeout, cancellation, URL rejection, parse error, or rate failure must not invent a newer response time or erase the prior observation; no response means null. This is execution metadata, never source time.

`bounded_fetch()` must pass through existing `FetchError` and `RateStateError` without losing their typed meaning. A managed transport exception is translated once into `FetchError` retaining retryability, HTTP status when actually observed, Retry-After, and observation/progress metadata. Durable rate read/write/reconciliation failures remain `RateStateError` and take the existing hard execution-failure path, not Provider retry or blocked exemption. Neither wrapping nor retry handling performs a second rate transition. HTTP-date Retry-After parsing uses the same injected clock and produces one delay reused by the send boundary and orchestration.

Track successful terminal 2xx resource responses for the pending acquisition unit separately from item counters; redirect hops and 401/403 themselves are observations, not successful partial resources. Carry that progress through a typed fetch failure, including a failure on a later retry after an earlier successful resource response. If a pending unit ends in 401/403 after resource progress or any previously accepted company evidence, serialize `state = partial`, `availability = blocked`, the concrete status/reason, and freshness `not_evaluated`, even when accepted and rejected are both zero. Existing serialized partial-state rules already prevent exemption; no new public outcome field or fake counter increment is needed. Without such progress, accepted/rejected evidence, or another incompleteness cause, a first-resource 401/403 retains the existing failed/blocked exemption. A redirect followed by denial, with no successful resource body, remains eligible for that same exemption.

Progress accumulates across unsuccessful retries of one unit; a fully successful retry resolves that unit's transient failures. A terminal failed unit cannot be erased by later company success. Stop that Provider's remaining units on terminal incomplete work, preserving earlier accepted evidence for diagnostics. Other Providers continue as today. SEC and CFTC adapters propagate progress in direct fixture-client tests as well as production managed-client execution; do not derive partial-resource progress from `fetched` or `accepted`.

The owning resolved Provider contract remains the single identity authority. The managed client removes any case-insensitive caller `User-Agent` and sends exactly the resolved value. Existing adapter header plumbing may retain the same value for fixture-level direct tests, but it cannot override production transport authority.

Alternative considered: keep rate management around `adapter.fetch()`. Rejected because multi-request acquisition would undercount sends and weaken crash recovery and shared-scope policy.

Alternative considered: make adapters call orchestration callbacks instead of a client. Rejected because it changes the Provider interface and couples domain code to Feed orchestration.

### 2. Follow redirects manually through the managed boundary

The underlying HTTP client always sends with automatic redirects disabled. `ManagedProviderClient.get(..., follow_redirects=True)` implements a small bounded redirect loop. Every hop resolves the `Location` against the preceding URL, validates it under the owning redirect policy, rejects credentials, fragments, IP literals, cycles, missing/invalid locations, and an implementation constant maximum redirect count, then invokes the complete per-send path again using the redirected target host semaphore.

The final response is returned with enough URL history/final URL behavior for `bounded_fetch()` to retain its response admission and source policy checks. `follow_redirects=False` returns the first response without following it. Redirect limits are implementation safety constants rather than Provider semantic configuration because all Providers share the same closed HTTP safety boundary.

Alternative considered: let `httpx` follow redirects internally. Rejected because hidden redirect requests would not receive independent debit, deadline, or concurrency management.

### 3. Keep one logical SEC Provider with one acquisition unit per watched company

Production construction creates one `SecEdgarAdapter` per resolved `WatchCompany`, in deterministic CIK order. Every instance has `provider_id = sec_edgar`, uses the same resolved Provider contract and rate scope, and contributes to the pre-existing single SEC `ProviderOutcome`. Units execute sequentially under the existing per-Provider loop; concurrency between companies is not added.

A company acquisition attempt performs at most:

1. `GET submissions/CIKxxxxxxxxxx.json`;
2. `GET` the selected current accession's official complete submission `.txt`;
3. `GET` the selected previous accession's official complete submission `.txt`, when one exists.

Provider-level retries may repeat a failed acquisition attempt; the bound is at most three logical resource GET operations per attempt, not three total wire sends. Each permitted redirect hop is an additional independently managed send under the redirect bound. Every resource GET uses the managed client. The submissions response must itself contain enough precise metadata to select current and previous; ECO-124 does not add historical submissions-file traversal. If that bounded source cannot establish the required current selection, the company acquisition fails closed.

The adapter returns a company-specific raw acquisition object, and normalization delegates only deterministic selection/parsing/comparison to `sec_13f.py`. A missing previous filing is represented as unavailable comparison and avoids the third request. Missing or ambiguous current filing or INFORMATION TABLE raises a typed failure rather than returning an empty company result.

Alternative considered: one adapter loops all eight companies. Rejected because existing multi-adapter outcome accumulation already expresses acquisition units and makes partial company failure explicit.

Alternative considered: eight logical Providers or per-company snapshot merge. Rejected because Provider identity, coverage, rate scope, and accepted snapshot replacement are all `sec_edgar`-scoped.

### 4. Treat SEC v2 as cutoff-bounded current state, not a window-only event list

For each configured CIK, selection uses precise `acceptanceDateTime` and chooses:

```text
current  = latest exact 13F-HR with accepted_at < evidence_cutoff_at
previous = nearest earlier exact 13F-HR whose report_period differs
```

The current filing may predate `window.start`; this is the deliberate SEC-v2 exception recorded in the delta spec. `filed_at` remains the legacy filing-date field and does not replace precise acceptance time. HTTP retrieval time never affects cutoff eligibility. Exact form matching excludes amendments.

The item ID remains accession-based so the top-level filing identity keeps its existing meaning. The top-level source points to the current official SEC complete submission and uses current acceptance as knowledge/publication time. Previous accession, report period, acceptance time, and official source URL live in the typed comparison structure.

Alternative considered: return only companies with a filing inside the window. Rejected because whole-slice replacement would drop unchanged watched companies.

### 5. Embed watched-company selection and validate SEC completeness

Add the resolved watched-company list to `feed_config.snapshot`, ordered by normalized CIK with deterministic ticker order. This is a canonical copy of the existing `config/config.yaml` authority, not another configuration source. Its hash and the Feed semantic projection therefore change when the selection changes.

SEC v2 validation always requires the canonical watched-company snapshot and checks every retained SEC item's semantics, matching configured CIK, and uniqueness. For a complete SEC outcome, it additionally requires exactly one SEC item per configured CIK and no extras, before snapshot selection and again on the final candidate. A genuinely blocked-exempt SEC outcome must contain no SEC items, has `not_evaluated` freshness, and may participate in the existing degraded publication path without fabricated company placeholders or prior carry-forward. A non-exempt incomplete candidate may retain only a valid unique subset for diagnostics, must have pipeline failure and `not_evaluated`, and cannot publish. Version-1 bundles may omit the new snapshot member and retain the legacy bounded read path.

An empty configured watched list remains supported: there are zero acquisition units, the complete SEC outcome is contract-permitted empty, the selected SEC slice is empty with `no_snapshot`, and no previous company may be carried. Each nonempty configured CIK must still yield its required current filing; an empty response for such a company is not successful empty acquisition.

CIK selection comes from configuration. Published `company_identity.name` and `company_identity.tickers` come from the SEC submissions response and are treated as official evidence; a non-empty official name is required and official tickers may be empty. Configuration aliases remain selection metadata and are not represented as SEC-supplied facts.

Alternative considered: validate only `accepted == len(watched_companies)`. Rejected because a count cannot detect duplicate, missing, or substituted CIKs.

### 6. Implement SEC 13F logic as a Provider-specific pure core

`sec_13f.py` performs no HTTP. Frozen dataclasses may represent filing candidates and normalized rows, but no generic comparator abstraction is introduced.

Complete-submission parsing first extracts the one required `INFORMATION TABLE` document from the bounded SEC SGML submission, then parses its XML using standard-library XML handling without network/entity lookup. Missing, duplicate, malformed, or wrong-document tables fail closed.

Canonical security key normalization is:

```text
CUSIP       = NFC, trim, uppercase, remove ASCII display spaces/hyphens,
              then require exactly 9 allowed CUSIP characters [0-9A-Z*@#]
put_call    = null, PUT, or CALL
amount_type = SH or PRN
key         = (cusip, put_call-null-sort-token, amount_type)
```

Rows with the same key are aggregated within each filing before comparison. `reported_amount` and `reported_value_usd_thousands` are bounded nonnegative canonical decimals and are summed using exact `Decimal` arithmetic after unit normalization. SEC's final rule, Federal Register document 2022-13936, section II.C.2.c and II.D/footnote 115, establishes that filings made from 2023-01-03 report dollar values in dollars rather than the earlier thousands convention. See `source-verification.md` for verified quotations and URLs. The rule follows filing date, never report period, retrieval date, or numeric magnitude.

For supported XML INFORMATION TABLE submissions, the official submissions `filingDate` must match the complete submission's `FILED AS OF DATE`, with CIK, accession and exact form also cross-checked. A filing date before 2023-01-03 selects `source_unit = usd_thousands`, `formula_id = identity`; from that date it selects `source_unit = usd`, `formula_id = usd_divided_by_1000`. Divide each raw reported dollar value by exactly 1000, without rounding or truncation. Parse/bound the raw token before Decimal construction; validate converted values, aggregates and deltas against the existing canonical numeric contract. Use a local precision sufficient for bounded exact inputs and reject inexact/overflowed arithmetic rather than round. Unknown/non-XML formats, missing or conflicting filing-date/unit authority, and unsupported explicit unit declarations fail closed. Do not heuristically correct an apparently misreported source value.

The SEC v2 manifest's existing `units` mapping declares the closed entries `13f_value_before_2023_01_03: usd_thousands`, `13f_value_from_2023_01_03: usd`, and `reported_value_usd_thousands: usd_thousands`. Resolution, the pure core, and embedded-contract validation must consume and verify these entries; missing, extra, or changed entries are unsupported for SEC v2 and fail before acquisition/mutation. These entries are absent/not required on the v1 compatibility path. The versioned rule is Provider-specific, not a new configurable unit framework. Manifest fixture provenance cites the official rule and labels synthetic arithmetic fixtures distinctly from recorded filing fixtures.

Distinct non-empty FIGIs under one key are irreconcilable and fail closed. Issuer name and title of class are display-only; after NFC and bounds validation, the lexicographically smallest non-empty canonical pair is selected so spelling and input order cannot alter identity or totals. FIGI is retained when uniquely present.

The comparison row shape is:

```text
security:
  cusip, figi, issuer_name, title_of_class, put_call, amount_type
current:
  reported_amount, reported_value_usd_thousands
previous:
  reported_amount, reported_value_usd_thousands
delta:
  reported_amount, reported_value_usd_thousands
change_type:
  new | increased | decreased | unchanged | no_longer_reported | null
```

`current`, `previous`, and `delta` are nullable objects. With an available previous filing, matched rows have both sides and a signed current-minus-previous delta; amount alone chooses increased/decreased/unchanged. Current-only and previous-only rows have a null absent side and null delta. With unavailable comparison, current remains populated and previous/delta/change_type are null for every row.

The filing payload additively retains legacy fields and adds:

```text
company_identity: cik, name, tickers
report_period
accepted_at
value_normalization:
  source_unit: usd | usd_thousands
  formula_id: usd_divided_by_1000 | identity
comparison:
  status: available | unavailable
  previous_accession_number
  previous_report_period
  previous_accepted_at
  previous_filed_at
  previous_source_url
  previous_value_normalization: same closed shape as value_normalization, or null
  reason
holdings: ordered comparison rows
```

For available comparison, previous fields are non-null and reason is null. For unavailable comparison, previous fields are null and reason is `no_previous_comparable_filing`. The current legacy `filed_at` and typed `comparison.previous_filed_at` retain official filing dates in the existing timestamp representation. Validation requires each normalization descriptor to match that filing date and the embedded SEC v2 unit contract. Thus a comparison spanning the unit transition uses the same canonical USD-thousands basis on both sides and exposes its conversion support without raw metadata or Host-Agent arithmetic.

### 7. Keep Feed major v4 and dispatch semantics by embedded Provider contract version

Replace the loader's global equality check with an explicit map:

```text
sec_edgar: {1, 2}
cftc:      {1, 2}
all others:{1}
```

The checked-in SEC and CFTC manifests move to version 2, so new production necessarily embeds v2. Feed JSON Schema adds closed optional semantic structures to the existing filing and positioning definitions; this allows old v4 payloads to remain structurally readable while still rejecting unknown properties. Cross-object semantic validation reads `provider_contracts[].snapshot.contract_version`, validates the supported Provider/version pair, and requires the appropriate semantic structure for every SEC/CFTC v2 item. It never branches on a manifest hash.

For SEC v2, validation additionally requires the watched-company snapshot and outcome-dependent exact CIK-set completeness described in Decision 5. For both Providers it checks nullability/status combinations, canonical numerics, units, deterministic ordering and unique keys, derivation equations, source consistency, and forbidden interpretation fields. The v1 path retains only the prior bounded v4 requirements.

Alternative considered: Feed major v5. Rejected because the extensions are additive and Provider contract versions can safely distinguish new production requirements from old v4 reads.

### 8. Acquire CFTC report dates and rows with a closed sequential query plan

Use the official Legacy Futures-Only dataset only. The adapter derives the latest report date whose conservative publication boundary is before the fixed cutoff, then performs a bounded ordered date-discovery query for the latest two eligible distinct dates. It performs separate sequentially paged queries for all rows at each selected date.

The query contract uses a fixed page size and deterministic SoQL ordering by `cftc_contract_market_code` followed by the Socrata stable row identifier. Offset/page-number progression is sequential. A short final page proves completion; a zero first page, repeated page, nonmatching date, nonascending order, duplicate stable row identity, or configured maximum page/row exhaustion fails closed. The CFTC v2 manifest declares page-number pagination and `empty_valid_for_window = false`; fixture provenance includes current and previous complete report responses. Query strings are constructed canonically and remain credential-free.

The conservative publication function remains Provider-specific and deterministic: Tuesday report date plus three days at 15:30 `America/New_York`, formatted as UTC. Date discovery constrains and rechecks this boundary so a report visible at retrieval but published at or after cutoff is excluded. Retrieval time is never substituted.

Only markets in the complete current report produce items. Previous-only markets are not current positioning and are omitted rather than assigned an unrequested disappearance interpretation.

Alternative considered: fetch an unqualified first 100 rows. Rejected because it cannot prove either selected dates or report completeness.

Alternative considered: publish previous-only markets. Rejected because ECO-124 defines current CFTC positioning and unavailable previous comparison, not a CFTC market-lifecycle semantic.

### 9. Implement CFTC comparison as a Provider-specific pure core

`cftc_cot.py` performs no HTTP. It validates and selects report dates, normalizes current and previous rows, requires a non-empty canonical CFTC contract market code, rejects duplicate/ambiguous current code rows, and orders output by market code independently of input order. Display market names are metadata and do not participate in matching.

Each current market produces a positioning payload retaining:

```text
type, instrument_id, as_of, position, raw_metadata
```

`instrument_id` retains the current display identity behavior, and `position` remains the current non-commercial-long `numeric_value`. The additive structures are:

```text
market_identity:
  cftc_contract_market_code
  contract_market_name
current_metrics / previous_metrics / delta_metrics:
  noncommercial_long
  noncommercial_short
  noncommercial_spreading
  open_interest
  net_noncommercial
comparison:
  status: available | unavailable
  previous_as_of
  reason
derivations:
  net_noncommercial:
    formula_id: noncommercial_long_minus_short
```

Every metric is a `{value, unit}` numeric object with `unit = contracts`. Current source components are nonnegative; net and deltas may be signed. `net_noncommercial = long - short`. For available comparison, every previous metric and delta is populated and `delta = current - previous`; net change must also equal long delta minus short delta. For a current code absent from the complete previous report, previous/delta objects are null, previous date is retained, status is unavailable, and reason is `market_absent_from_previous_report`.

`contract_market_name` carries the official display name, falling back to `market_and_exchange_names` only when the short name is absent, and matching never reads it. `market_and_exchange_names` is not a typed v2 field: it was never typed evidence (v1 retained it only inside `raw_metadata`, which the consumer contract forbids the Host Agent to parse), and the delta spec requires only typed market identity. The closed v2 identity therefore carries the unique contract market code plus the display name.

The top-level item ID retains the existing source stable-row identity when provided, with the existing report-date-plus-instrument fallback; cross-period matching uses market code separately. The source URL points to the market's own official dataset row, because a single shared dataset landing page would make Feed deduplication collapse every same-URL positioning item into one survivor. Source times retain report date and conservative publication boundary.

### 10. Preserve whole-slice replacement with SEC/CFTC-v2 exact-set carry admission

Make one bounded change to `feed/snapshot.py`: for current SEC or CFTC contract version 2, carry-forward requires both equality of current/prior item identity sets and exact canonical equality under each identity. Both v2 adapters produce complete current-state slices, unlike legacy advancing-window event lists. Current SEC completeness against the resolved watched set and CFTC complete-report acquisition are validated before selection. The caller derives this complete-state admission from already resolved Provider identity/version and passes it to the existing seam; do not select behavior by manifest hash, infer it from counts, or introduce another runtime configuration authority. A removed/added identity or changed item content selects the entire current Provider slice, never a member-level merge. A complete empty SEC watched set selects an empty slice with `no_snapshot` and null carry provenance even if prior companies exist; an empty CFTC report remains an acquisition failure under Decision 8. Failed/partial acquisition never reaches this carry admission.

Prior A–H and current A–G must publish A–G even when A–G item bytes are unchanged. Prior A–H and current changed-A plus B–H still publish A–H. A byte-identical equal-set slice may carry unchanged; an alias-only configuration change affects Feed identity but need not rewrite official SEC item bytes. All v1 and the other six Providers' event-list/empty-check semantics remain unchanged. For CFTC v2, a new report normally changes date-bearing identities/payloads, but a corrected same-date report may remove a market while leaving all remaining items byte-identical. The same exact-set gate must select the corrected whole current report rather than carry the removed market. This shares the single complete-state equality predicate; it does not add a generic snapshot framework.

This is an explicit narrowing of carry eligibility for the two complete-state Provider versions, not a snapshot schema migration, snapshot-history database, or per-company history merge.

Semantic structures remain inside `payload`, which is already part of `items` in the semantic projection. No digest exclusion or secondary projection is added. Tests mutate each material SEC/CFTC fact and assert digest/run ID changes, while permutations of rows, pages, adapters, and completion order produce identical output.

### 11. Keep semantic structures bounded and evidence-only

Schema and semantic validation apply explicit maximum lengths and item counts appropriate to the existing 10 MiB Provider response and 50 MiB bundle limits. INFORMATION TABLE and CFTC row/page bounds reject rather than truncate. Numeric values use the existing 64-byte, 24-significant-digit, exponent, magnitude, canonical plain-decimal, and negative-zero rules; Provider-specific validation adds nonnegative source-component constraints.

`raw_metadata` remains available for debug/provider metadata, but every fact needed for current/change expression is in closed typed fields. Validation rejects directional labels, scores, rankings, impact, predictions, recommendations, and signals. The Host Agent neither recalculates deltas nor resolves history.

## Risks / Trade-offs

- [Manual redirect handling can diverge from HTTP library behavior] -> Cover relative/absolute locations, cycles, target-host policy, method preservation for GET, close behavior, and redirect bounds with focused transport tests; only GET is exposed.
- [Moving reconciliation can cause double debit or double reconcile] -> Remove all rate mutation from `_run_adapter()` and assert transition counts for success, HTTP error, Retry-After, pre-send cancellation, and transport failure.
- [Eight SEC companies require up to 24 resource GETs for one pass, plus bounded redirect/retry sends] -> Keep units sequential under the existing SEC scope, admit every wait/send against the command deadline, and fail incomplete rather than bypass rate policy. Measured 2026-09-15 under the resolved policy: SEC 24 sends cost a 115s rate floor, CFTC 22s, and the other six Providers 1s each, against the 285s pre-commit budget. `test_sec_v2_send_shape_respects_the_rate_floor_and_fits_the_pre_commit_budget` pins that floor and the remaining headroom.
- [SEC submissions `recent` may not contain a previous comparable filing] -> Treat no earlier exact filing in the bounded submissions response as unavailable comparison; do not add historical-file traversal or hidden extra requests in ECO-124.
- [Complete submission SGML/XML varies] -> Use production-shaped fixtures for namespaces, optional elements, duplicate rows, and malformed/multiple INFORMATION TABLE documents; fail closed on ambiguity.
- [CUSIP display normalization could create collisions] -> Normalize only declared presentation separators, validate the exact allowed canonical form, and reject conflicting FIGI under an aggregated key.
- [CFTC API pagination can change during acquisition] -> Pin both report dates in each row query, use total ordering and stable row identity, reject repeated/invalid pages, and never mix rows outside the selected dates.
- [Conservative CFTC publication time is not an observed per-row timestamp] -> Preserve it as the verified Provider-specific cutoff rule, document the formula in typed provenance/manifest material, and never substitute retrieval time.
- [Additive semantic payloads increase bundle size] -> Retain response, row/holding, and serialized bundle bounds and fail without truncation or publication.
- [Embedding watched-company selection changes semantic identity when aliases change] -> Accept this deliberately because the resolved selection contract is semantic configuration; official SEC identity remains separately typed.

## Migration Plan

1. Add and verify the per-send managed transport while SEC/CFTC still behave as single-request v1 adapters.
2. Add backward-readable schema definitions and Provider-version semantic dispatch tests before changing checked-in manifests.
3. Implement and verify the SEC pure core, including verified filing-date unit conversion, against fixtures.
4. Integrate the SEC adapter, watched snapshot, outcome-dependent completeness, and SEC-v2 exact-set carry gate; activate its v2 manifest in the same working commit. CFTC remains v1 until its own integration.
5. Implement/verify the CFTC pure core and complete paginated adapter, including activation of the shared complete-state equality gate for CFTC v2; activate its v2 manifest and provenance in the same working commit. Task 2 uses test-local v2 contracts, never prematurely upgraded production manifests. Each intermediate commit advertises only the producer semantics it implements; completion of ECO-124 requires both Providers at v2.
6. Update only affected truthful documentation; accepted-spec changes occur through the later explicit sync/archive stage, not manual duplication during Apply.
7. Existing valid v4/provider-v1 bundles remain readable. The first complete v2 acquisition must not relabel legacy items as v2; current v2 semantics replace incompatible v1 slices. Compatible equal-set SEC/CFTC v2 slices may carry under Decision 10; no persisted data migration or Feed-major rewrite occurs.

Rollback requires reverting Producer code, manifests, schema, tests, and documentation together to the prior v1 contract. A v2-produced active bundle must not be consumed by a binary that lacks v2 support; normal manifest-led deployment ordering and validation remain the compatibility gate. No snapshot-history migration is performed.
