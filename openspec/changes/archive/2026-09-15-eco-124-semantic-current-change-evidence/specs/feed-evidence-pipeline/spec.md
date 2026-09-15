## ADDED Requirements

### Requirement: Every real Provider HTTP send is independently managed
Every real outbound Provider HTTP send SHALL independently pass cancellation and pre-commit deadline admission, durable rate eligibility and debit, global concurrency admission, target-host concurrency admission, owning Provider host and identity policy, one upstream send, and exactly one controlled rate-state reconciliation. Automatic redirect following SHALL be disabled below this boundary; each permitted redirect hop and each sequential pagination request SHALL re-enter the same boundary. Provider-level attempts, retries, normalization, item validation, and outcomes SHALL remain outside this send-level boundary and SHALL NOT perform a second debit or reconciliation for an already managed send.

#### Scenario: One acquisition uses multiple requests
- **WHEN** one Provider acquisition performs two successful HTTP sends
- **THEN** each send receives its own durable debit, concurrency admission, upstream send, and reconciliation

#### Scenario: Redirect produces another upstream send
- **WHEN** a permitted response redirects the request to another permitted URL
- **THEN** the redirect hop is admitted as a separate managed send using the redirected target host rather than being followed invisibly by the underlying client

#### Scenario: Redirect is unsafe or unbounded
- **WHEN** a redirect target violates the owning Provider redirect policy, repeats a visited URL, exceeds the bounded redirect count, or cannot fit before the deadline
- **THEN** no request is sent to that target and the acquisition fails through the typed Provider boundary

#### Scenario: Deadline expires between sends
- **WHEN** a first send completes but the next required send or wait cannot be admitted before the pre-commit deadline
- **THEN** the next send does not occur, the Provider remains incomplete, and prior evidence cannot convert the run into success

#### Scenario: Transport fails after dispatch
- **WHEN** the underlying transport raises after a durable pre-send debit and dispatch may have occurred
- **THEN** the managed boundary reconciles rather than refunds the debit exactly once and exposes a typed retry classification to Provider-level orchestration

#### Scenario: Retry-After is returned
- **WHEN** an upstream response carries a valid `Retry-After` value
- **THEN** that send reconciles the owning durable rate scope with the declared delay exactly once and any later attempt must pass normal eligibility again

#### Scenario: Existing single-request Provider runs
- **WHEN** an existing adapter performs one request and otherwise produces the same normalized evidence
- **THEN** its Provider-level retry, validation, outcome, and evidence behavior remains unchanged while its one send is managed at the new boundary

### Requirement: Multi-request failures preserve typed lifecycle and blocked-exemption evidence
The managed transport and bounded fetch helper SHALL preserve typed fetch-error retryability, concrete HTTP status, Retry-After, and actual response-observation metadata. Durable rate-state failures SHALL remain hard execution failures rather than ordinary Provider failures or retries. Each Provider outcome's `retrieved_at` SHALL reflect its last concrete response observation across requests, retries and acquisition units, or null if none occurred; a later no-response failure SHALL NOT advance or erase that observation. Response observations SHALL NOT become source time.

A terminal HTTP 401/403 after a successful terminal resource response in an unresolved acquisition unit or after accepted evidence from another unit SHALL be partial and non-exempt, even when normalization has not produced items. The outcome SHALL serialize existing `state = partial`, `availability = blocked`, the concrete HTTP status/reason, and `freshness.status = not_evaluated`; pipeline status SHALL be failure and publication SHALL be forbidden. Successful resource progress SHALL survive unsuccessful retries of that unit until a complete retry resolves it. Counters SHALL NOT be fabricated to encode progress. A terminal incomplete company unit SHALL NOT be erased by later company success.

A first-resource 401/403 with no successful partial resource, accepted/rejected evidence, or other unresolved incompleteness SHALL retain the existing blocked exemption. Redirect responses alone SHALL be response observations, not successful resource results. Genuine blocked-exempt outcomes SHALL retain no prior evidence and MAY participate in the existing degraded publication path. No new public outcome field is required.

#### Scenario: SEC data acquisition is denied after submissions succeed
- **WHEN** submissions succeeds but a required current or previous complete-submission request returns HTTP 401 or 403 before any filing item is normalized
- **THEN** SEC is partial/blocked, accepted and rejected counters remain truthful, freshness is not_evaluated, and the pipeline fails without publication or prior-slice fallback

#### Scenario: CFTC acquisition is denied after discovery or a page succeeds
- **WHEN** a required CFTC page returns HTTP 401 or 403 after date discovery or an earlier page succeeds
- **THEN** CFTC remains partial, non-exempt and pipeline-failing even if accepted is zero

#### Scenario: Denial occurs before partial evidence exists
- **WHEN** the first resource returns HTTP 401 or 403, possibly after permitted redirects, and no successful resource or other incompleteness exists
- **THEN** the Provider retains the existing failed/blocked exemption with no items, and the Feed may publish degraded if every other required gate passes

#### Scenario: An unsuccessful retry must not erase partial progress
- **WHEN** one attempt obtained a resource before failing and a later attempt for the unresolved unit returns HTTP 403 before obtaining a resource
- **THEN** prior partial-resource progress prevents blocked exemption without inventing item counts

#### Scenario: A complete retry resolves its acquisition unit
- **WHEN** a retry completely obtains and validates the required evidence for a previously failed attempt of the same unit
- **THEN** transient attempt failure does not prevent that unit from succeeding, but an independently terminal failed unit cannot be cleared

#### Scenario: A later request has no response
- **WHEN** one response is observed and a later required request times out or is cancelled before a response
- **THEN** retrieved_at remains the actual earlier observation and the terminal failure keeps its typed non-blocked classification

#### Scenario: Durable reconciliation fails
- **WHEN** the managed send boundary encounters a durable rate reconciliation failure
- **THEN** bounded_fetch preserves the hard rate-state failure, no second reconciliation is attempted by orchestration, and publication fails through the existing execution boundary

### Requirement: Feed v4 supports bounded Provider semantic contract evolution
New production SHALL continue to emit Feed `schema_version = 4`. The checked-in SEC EDGAR and CFTC manifests SHALL publish Provider `contract_version = 2`; the other six required Providers SHALL remain at contract version 1. Manifest resolution and embedded-contract validation SHALL use an explicit Provider-specific supported-version set rather than a global maximum, a manifest hash, or implicit acceptance of arbitrary versions.

A current consumer SHALL retain bounded read compatibility for structurally and semantically valid v4 items carrying SEC or CFTC Provider contract version 1. SEC contract version 2 items SHALL contain the complete required 13F semantic structure, and CFTC contract version 2 items SHALL contain the complete required COT semantic structure. Unknown fields, unsupported Provider/version combinations, malformed version declarations, and version-2 items missing required semantics SHALL fail closed. After completion of this Change, new production SHALL NOT emit a version-1 SEC or CFTC contract. During implementation, each checked-in manifest bump SHALL be committed atomically with that Provider's working semantic adapter, required configuration/validation and verified fixtures; compatibility-only commits SHALL retain truthful v1 production manifests.

#### Scenario: Existing v4 Provider-v1 bundle is read
- **WHEN** a valid previously published v4 bundle embeds SEC or CFTC Provider contract version 1 and uses the bounded legacy payload shape
- **THEN** the current consumer validates it without requiring version-2 semantic fields

#### Scenario: SEC v2 semantics are absent
- **WHEN** a v4 item belongs to an embedded SEC contract version 2 but omits any required 13F semantic structure
- **THEN** Feed validation rejects the bundle

#### Scenario: CFTC v2 semantics are absent
- **WHEN** a v4 item belongs to an embedded CFTC contract version 2 but omits any required COT semantic structure
- **THEN** Feed validation rejects the bundle

#### Scenario: Versioned semantic item is complete
- **WHEN** a v4 SEC or CFTC item matches its embedded supported contract version and all required typed semantic and provenance fields
- **THEN** Feed validation accepts the item without requiring a Feed major-version change

#### Scenario: Unknown semantic field is supplied
- **WHEN** a versioned semantic payload contains a field outside its closed schema
- **THEN** Feed validation rejects the item rather than treating the field as untyped metadata

#### Scenario: Unsupported Provider version is embedded
- **WHEN** a bundle or checked-in manifest declares a Provider contract version outside the explicit supported set for that Provider
- **THEN** resolution or consumption fails closed without using the contract hash to select behavior

### Requirement: SEC v2 publishes a complete cutoff-bounded watched-company 13F state
A complete SEC contract-version-2 acquisition SHALL publish exactly one filing item for every configured watched company and no other SEC item. The authoritative configured watched-company selection SHALL be embedded in the Feed configuration snapshot in deterministic CIK order. Every retained SEC item SHALL have valid v2 semantics, a configured CIK and unique company identity. For complete SEC outcomes, validation SHALL require exact configured CIK-set equality before snapshot selection and on the final candidate. Genuine blocked-exempt SEC outcomes SHALL contain zero SEC items with not_evaluated freshness and MAY participate in accepted degraded publication without placeholders. Non-exempt incomplete candidates MAY retain a valid unique subset only as pipeline-failure diagnostics and SHALL NOT publish. An empty configured watched set SHALL yield a complete permitted-empty SEC outcome, no SEC items, no_snapshot freshness and no prior carry-forward.

For each watched CIK, the current filing SHALL be the latest exact `13F-HR` whose precise SEC acceptance timestamp is earlier than `evidence_cutoff_at`. It MAY be earlier than `window.start` because this Provider contract represents current state at the cutoff rather than only filings first observed in the advancing interval. `13F-HR/A` amendments and every other form SHALL be excluded. The previous comparable filing SHALL be the nearest earlier exact `13F-HR` with a different report period. Failure, ambiguity, an unavailable current exact filing, or a missing required readable INFORMATION TABLE for any watched company SHALL make the SEC outcome partial or failed; it SHALL NOT silently omit that company. Absence of a previous comparable filing SHALL NOT make an otherwise valid current item incomplete.

#### Scenario: Only one company files during the current window
- **WHEN** eight watched companies have valid latest filings before the cutoff, only company A has a new filing in the current advancing window, and all eight acquisitions complete
- **THEN** the current SEC slice contains exactly A through H and may replace the prior whole SEC slice without losing B through H

#### Scenario: Current filing predates the window
- **WHEN** a watched company's latest exact `13F-HR` was accepted before `window.start` but before `evidence_cutoff_at`
- **THEN** that filing is retained as the company's cutoff-bounded current state with its original source times

#### Scenario: Filing is accepted at or after cutoff
- **WHEN** an exact `13F-HR` has an earlier report or filing date but its precise acceptance timestamp is at or after `evidence_cutoff_at`
- **THEN** it is ineligible and the latest earlier eligible exact filing is selected

#### Scenario: Amendment is newer than the exact filing
- **WHEN** a `13F-HR/A` is newer than the latest exact `13F-HR`
- **THEN** the amendment is neither selected nor merged in this contract

#### Scenario: One watched company is incomplete
- **WHEN** seven company acquisitions succeed and one current filing is missing, ambiguous, unreadable, or fails acquisition
- **THEN** SEC is partial or failed, required coverage is incomplete, and the seven accepted items cannot make the Feed publishable

#### Scenario: Previous filing is unavailable
- **WHEN** a valid current exact `13F-HR` exists but no earlier exact filing with a different report period exists
- **THEN** the item is publishable with comparison status `unavailable` and reason `no_previous_comparable_filing`

#### Scenario: SEC is genuinely blocked-exempt
- **WHEN** SEC is denied on its first resource without partial-resource evidence and all other publication gates pass
- **THEN** validation permits the degraded candidate with no SEC items and not_evaluated freshness rather than requiring fabricated items for each configured CIK

#### Scenario: A failed diagnostic candidate retains a company subset
- **WHEN** some configured company items are valid but SEC is non-exempt incomplete
- **THEN** validation may retain the valid unique configured subset only with pipeline failure and not_evaluated freshness, never as a publishable complete SEC slice

#### Scenario: Published company identity is inspected
- **WHEN** a SEC v2 item is validated
- **THEN** it exposes the official submissions CIK, name, and tickers while the configuration snapshot remains the authority for watched-company selection

### Requirement: SEC v2 normalizes and compares 13F holdings deterministically
Each SEC v2 item SHALL expose current and, when available, previous filing accession number, report period, precise acceptance time, and official source URL together with a closed typed holdings comparison. Security matching SHALL use only a canonical key composed of normalized CUSIP, normalized nullable put/call, and normalized `SH` or `PRN` amount type. Issuer name and title of class SHALL be display metadata and SHALL NOT determine matching. Optional FIGI SHALL remain optional; conflicting non-empty stable identity metadata under one canonical key SHALL fail closed.

Rows sharing a canonical key within one INFORMATION TABLE SHALL be deterministically aggregated before cross-period comparison by summing reported amount and reported value normalized to USD thousands. Under the verified SEC Form 13F unit transition effective 2023-01-03, supported XML filings made before that date SHALL interpret reported value as USD thousands and filings made on or after that date SHALL interpret reported value as USD and divide exactly by 1000. Selection SHALL use the official filing date, cross-checked between submissions and the complete submission, never report period or value magnitude. No arithmetic step SHALL round or truncate. The closed SEC v2 manifest unit mapping SHALL declare both source regimes and the canonical target; unsupported/missing/extra entries SHALL fail resolution and embedded-contract validation. Current and previous filing evidence SHALL expose their filing dates and closed value-normalization descriptors identifying source unit and conversion formula. Unknown/unsupported formats or contradictory unit/date provenance SHALL fail closed rather than invoke a unit heuristic. Display metadata SHALL be selected by a documented canonical rule independent of input order. Output rows SHALL be unique and ordered solely by canonical security key. Raw numeric tokens and arithmetic SHALL obey the existing bounded canonical-decimal contract; current and previous reported amounts and values SHALL be nonnegative, while matched deltas MAY be signed.

When a previous comparable filing exists, change classification SHALL use reported amount only: a key present on both sides is `increased`, `decreased`, or `unchanged`; a current-only key is `new`; and a previous-only key is `no_longer_reported`. Reported market value SHALL NOT determine that classification. For matched keys, delta fields SHALL be the reproducible current-minus-previous values. For `new` and `no_longer_reported`, the absent side and delta SHALL be null rather than an invented zero. `no_longer_reported` SHALL mean only that the key is absent from the current report.

When no previous comparable filing exists, every current holding SHALL preserve its current values while `previous`, `delta`, and `change_type` are null. Such holdings SHALL NOT be classified as `new`.

#### Scenario: Current value is reported in dollars
- **WHEN** a supported filing made on or after 2023-01-03 reports raw value 1234567 dollars
- **THEN** its reported_value_usd_thousands is the exact canonical string "1234.567" and value_normalization identifies usd and usd_divided_by_1000

#### Scenario: Comparison spans the unit transition
- **WHEN** a pre-transition filing reports raw value 1234 and the comparable post-transition filing reports 1234567
- **THEN** their normalized previous/current values are "1234" and "1234.567" USD thousands with exact delta "0.567", and each filing retains its own date and unit descriptor

#### Scenario: Late filing uses an older report period
- **WHEN** a filing made on 2023-01-03 reports holdings for a period before that date
- **THEN** the dollar source regime applies based on filing date rather than the older report period

#### Scenario: Value-unit authority is missing or conflicting
- **WHEN** official filing dates conflict, the XML format is unsupported, or the declared SEC v2 unit contract is missing or inconsistent
- **THEN** parsing or contract validation fails closed without magnitude-based conversion or invented provenance

#### Scenario: Duplicate rows are reordered
- **WHEN** the same duplicate security rows are supplied in different orders
- **THEN** their aggregate, display selection, comparison rows, and canonical output bytes are identical

#### Scenario: Issuer spelling changes
- **WHEN** current and previous rows have the same canonical security key but different issuer-name spelling
- **THEN** they are matched by the security key and issuer spelling does not create `new` or `no_longer_reported`

#### Scenario: Put and call differ
- **WHEN** two rows share a CUSIP and amount type but one is a put and the other is a call
- **THEN** they remain distinct security keys

#### Scenario: SH and PRN differ
- **WHEN** two rows share a CUSIP and put/call value but use different amount types
- **THEN** they remain distinct security keys

#### Scenario: Amount rises while market value falls
- **WHEN** a matched holding's reported amount rises and reported market value falls
- **THEN** its change type is `increased` and both numeric deltas remain independently reproducible

#### Scenario: Current-only security is compared
- **WHEN** a previous comparable filing exists and a canonical key appears only in the current filing
- **THEN** change type is `new`, previous and delta are null, and no transaction path is asserted

#### Scenario: Previous-only security is compared
- **WHEN** a previous comparable filing exists and a canonical key appears only in the previous filing
- **THEN** change type is `no_longer_reported`, current and delta are null, and no full-sale assertion is made

#### Scenario: Stable identity metadata conflicts
- **WHEN** rows under one canonical security key contain irreconcilable non-empty stable identity metadata
- **THEN** parsing fails closed instead of choosing an identity by row order

### Requirement: CFTC v2 publishes deterministic current and previous Legacy Futures-Only evidence
CFTC contract version 2 SHALL deterministically discover the latest and immediately previous distinct Legacy Futures-Only report dates whose declared conservative publication boundary is earlier than `evidence_cutoff_at`, and SHALL retrieve every row for both selected dates through bounded sequential pagination. Queries SHALL use a fixed bounded page size, total deterministic ordering including contract market code and a final stable tie-breaker, a closed maximum row/page bound, and a termination condition that proves each selected date is complete. Invalid ordering, duplicate or ambiguous current market identity, bound exhaustion, an incomplete page sequence, or a numeric parse failure SHALL fail closed.

Cross-period matching SHALL use normalized CFTC contract market code, not a display market name. The current slice SHALL publish one positioning item for every current-report market and SHALL NOT synthesize items for markets found only in the previous report. A display-name change SHALL NOT break comparison. A current market absent from the complete previous report SHALL publish explicit unavailable comparison rather than invented previous or delta values.

Each item SHALL retain legacy `instrument_id`, `as_of`, and `position`, with `position` remaining the compatibility alias for current non-commercial long contracts. It SHALL additionally expose typed market identity; current and, when available, previous non-commercial long, non-commercial short, non-commercial spreading, open interest, and net non-commercial metrics; typed deltas; comparison status and previous report date; and a derivation descriptor identifying net non-commercial as `noncommercial_long_minus_short`. All persisted numeric values SHALL be canonical decimal strings in contracts. `net_noncommercial` SHALL equal long minus short, each metric delta SHALL equal current minus previous, and net change SHALL be reproducible from both the typed net values and the component deltas.

#### Scenario: Input row order changes
- **WHEN** identical complete current and previous report rows arrive in different orders or page completion schedules
- **THEN** selected dates, matched markets, semantic output, and canonical bytes are identical

#### Scenario: A post-cutoff report is visible at retrieval
- **WHEN** the upstream dataset contains a report whose conservative publication boundary is at or after the fixed cutoff
- **THEN** that report is excluded even if it is visible when the HTTP request occurs

#### Scenario: Display name changes across weeks
- **WHEN** one market has the same contract market code but different display names in the selected reports
- **THEN** the rows are compared as one market

#### Scenario: Current metrics are compared
- **WHEN** a market exists in both complete reports
- **THEN** long, short, spreading, open-interest, net, and all deltas are typed canonical contract values reproducible from the two source rows

#### Scenario: Previous market is unavailable
- **WHEN** a current market code does not occur in the complete previous report
- **THEN** comparison is explicitly unavailable and previous and delta metrics are null

#### Scenario: Market exists only in previous report
- **WHEN** a market code occurs only in the previous report
- **THEN** no current positioning item is synthesized for that code

#### Scenario: Directional interpretation is supplied
- **WHEN** a CFTC item adds bullish, bearish, crowded, risk-on, risk-off, signal, score, importance, prediction, or recommendation semantics
- **THEN** Feed validation rejects the item

### Requirement: Semantic current-change evidence preserves Feed identity and snapshot contracts
All SEC 13F and CFTC COT typed semantic fields, including current values, previous values, report periods or dates, comparison status and reason, change classification, derivation descriptors, and deterministic deltas, SHALL participate in the existing canonical item bytes and logical Feed semantic projection. Changing any such fact SHALL change `content_digest` and cutoff-derived `run_id`; input row order, company acquisition completion order, pagination partitioning, and Provider completion order SHALL NOT change them.

Snapshot selection SHALL retain whole-Provider-slice replacement. For current SEC or CFTC contract version 2, carry-forward SHALL additionally require equality of current/prior item identity sets as well as canonical equality of each item; subset matching alone SHALL NOT permit carry-forward. Both versions represent complete current-state slices, including same-date source corrections. Removing a configured CIK SHALL select the complete current SEC slice without the removed member. An empty configured set SHALL select an empty slice with no_snapshot freshness and null carry provenance. All Provider-v1 and the other six Providers' legacy event-list and empty-check behavior SHALL remain unchanged. Dispatch SHALL use the resolved Provider contract version, not a hash or a second configuration authority.

A complete equal-set identical SEC or CFTC v2 slice MAY carry prior bytes as valid_unchanged; any added/removed identity or changed canonical content SHALL cause whole-current-slice replacement. Partial or failed acquisition SHALL remain not_evaluated without prior-slice fallback. Genuine blocked exemption MAY still publish degraded without that Provider's evidence, while all non-exempt incomplete work SHALL remain pipeline-failing. No per-company SEC merge, cross-run CFTC history merge, or unbounded evidence history SHALL be introduced.

A Host Agent inspecting only one current validated SEC v2 or CFTC v2 item SHALL be able to identify current state, previous comparable evidence when available, deterministic change or explicit unavailability, and official provenance or reproducible derivation support without Provider network access, historical Feed access, `raw_metadata` parsing, or its own cross-period arithmetic.

#### Scenario: A semantic fact changes
- **WHEN** a 13F amount, 13F change type, 13F report period, CFTC source metric, CFTC comparison date, or deterministic delta changes at the same cutoff
- **THEN** the canonical semantic projection, `content_digest`, and `run_id` change

#### Scenario: Only acquisition order changes
- **WHEN** SEC rows, CFTC rows, company adapters, pages, or Provider outcomes complete in another order with identical evidence
- **THEN** the final canonical semantic output, `content_digest`, and `run_id` remain identical

#### Scenario: Complete semantic slice changes
- **WHEN** one watched company's SEC item or one CFTC market item changes and the complete Provider acquisition succeeds
- **THEN** the whole current Provider slice replaces the prior slice without merging historical members

#### Scenario: Watched company is removed without changing remaining filings
- **WHEN** prior SEC v2 contains A-H and complete current acquisition contains byte-identical A-G after removing H from configuration
- **THEN** the selected current slice is exactly A-G, H is not carried, and the Feed identity reflects the changed selection

#### Scenario: Watched selection becomes empty
- **WHEN** configuration contains no watched companies while the prior SEC slice contains companies
- **THEN** complete permitted-empty SEC selects no items with no_snapshot and null carry provenance rather than restoring prior companies

#### Scenario: Only configuration aliases change
- **WHEN** configured aliases change but CIKs and all official SEC item bytes remain equal
- **THEN** Feed configuration identity changes while the equal-set SEC slice remains eligible for unchanged carry-forward

#### Scenario: A corrected same-date CFTC report removes a market
- **WHEN** prior CFTC v2 has markets X and Y, complete current acquisition for the same report dates contains only byte-identical X, and pagination proves the corrected report complete
- **THEN** the whole current slice contains only X and prior Y is not carried, while an empty current report still fails acquisition

#### Scenario: Legacy event-list subset remains compatible
- **WHEN** a Provider-v1 or one of the other six Providers returns the same contract-valid subset or empty check as before this Change
- **THEN** its existing validation-gated carry-forward behavior is preserved rather than receiving SEC/CFTC-v2 complete-set semantics

#### Scenario: Semantic acquisition is incomplete
- **WHEN** any required company, page, selected report, parse, or current-slice validation fails without genuine blocked exemption after prior evidence exists
- **THEN** the Provider remains partial or failed with freshness `not_evaluated`, the pipeline remains incomplete, and prior evidence cannot make the run publishable

#### Scenario: Consumer expresses current and change evidence
- **WHEN** a Host Agent receives one validated v2 semantic item
- **THEN** the item itself contains the typed current, previous or unavailable, change, provenance, and derivation facts needed for evidence-preserving expression

## MODIFIED Requirements

### Requirement: Provenance tiers and payload-specific time semantics
Every Feed item SHALL retain Provider identity, source name, tier, kind, canonical URL, supplied publication/update time, `source.knowledge_available_at`, and the retained payload's source-semantic effective/reference time and selection basis. Provider `retrieved_at` and Feed `generated_at` SHALL remain execution observations and SHALL NOT be copied into evidence or treated as source time. Newly acquired `news`, `macro_release`, `policy`, and Provider-contract-version-1 `filing` evidence SHALL be selected by knowledge time in the half-open window; SEC contract-version-2 exact `13F-HR` current-state evidence SHALL instead select the latest precise acceptance timestamp strictly before the cutoff for each configured watched CIK and MAY predate `window.start`; current `positioning` and validation-gated carried slices MAY contain earlier source times only under declared cadence contracts. Retrieval time SHALL NOT establish cutoff eligibility or freshness.

#### Scenario: Evidence becomes known after cutoff
- **WHEN** retained evidence has an earlier effective time but source availability at or after the cutoff
- **THEN** it is excluded from the run rather than admitted from effective time alone

#### Scenario: SEC v2 current state predates the window
- **WHEN** the latest eligible exact `13F-HR` for a configured watched CIK was accepted before `window.start` and no later exact filing was accepted before the cutoff
- **THEN** the filing MAY be retained as cutoff-bounded current state with its original acceptance, filing, report-period, and source provenance

#### Scenario: Calendar evidence was announced earlier
- **WHEN** previously announced calendar evidence is encountered during migration or collection
- **THEN** it is excluded from the five-domain candidate rather than retained through a future-horizon exception

#### Scenario: Tier 3 evidence is normalized
- **WHEN** a supported commentary source emits an otherwise valid retained-domain item
- **THEN** it remains explicitly Tier 3 and is not promoted

#### Scenario: Unchanged evidence is checked again
- **WHEN** a complete Provider check allows a prior slice to be carried
- **THEN** current retrieval time records the check while carried evidence retains original source-semantic times
