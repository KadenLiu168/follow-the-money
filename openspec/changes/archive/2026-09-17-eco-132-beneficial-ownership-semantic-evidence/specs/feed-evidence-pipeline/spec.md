## MODIFIED Requirements

### Requirement: Feed v4 supports bounded Provider semantic contract evolution

New production SHALL continue to emit Feed `schema_version = 4`. The checked-in SEC EDGAR manifest SHALL publish Provider `contract_version = 4`, the checked-in CFTC manifest SHALL publish Provider `contract_version = 2`, and the other six required Providers SHALL remain at contract version 1. Manifest resolution and embedded-contract validation SHALL use an explicit Provider-specific supported-version set rather than a global maximum, a manifest hash, or implicit acceptance of arbitrary versions.

A current consumer SHALL retain bounded read compatibility for structurally and semantically valid v4 items carrying SEC Provider contract versions 1, 2, or 3 and CFTC Provider contract version 1. SEC contract version 2 items SHALL retain the complete required 13F semantic structure. SEC contract version 3 items SHALL retain the complete required `form13f` or `form4` subtype structure. SEC contract version 4 items SHALL carry a required closed filing subtype and satisfy the complete `form13f`, `form4`, or `beneficial_ownership` subtype contract. CFTC contract version 2 items SHALL contain the complete required COT semantic structure. Unknown fields, unsupported Provider/version combinations, malformed version declarations, and versioned items missing required semantics SHALL fail closed. New production SHALL NOT emit a legacy SEC v1/v2/v3 or CFTC v1 contract after the corresponding working manifest activation. Each checked-in manifest bump SHALL be atomic with its working semantic adapters, configuration, validation, verified fixtures, request bounds, and compatibility path.

#### Scenario: Existing v4 Provider-v1 bundle is read

- **WHEN** a valid previously published v4 bundle embeds SEC or CFTC Provider contract version 1 and uses the bounded legacy payload shape
- **THEN** the current consumer validates it without requiring newer semantic fields

#### Scenario: Existing SEC v2 bundle is read

- **WHEN** a valid previously published v4 bundle embeds SEC Provider contract version 2 with the complete existing 13F semantic structure
- **THEN** the current consumer validates it without requiring a filing subtype or Form 4 fields

#### Scenario: Existing SEC v3 bundle is read

- **WHEN** a valid previously published v4 bundle embeds SEC Provider contract version 3 with a complete `form13f` or `form4` payload
- **THEN** the current consumer validates it without requiring beneficial-ownership fields or SEC-v4 configuration

#### Scenario: SEC v2 semantics are absent

- **WHEN** a v4 item belongs to an embedded SEC contract version 2 but omits any required 13F semantic structure
- **THEN** Feed validation rejects the bundle

#### Scenario: SEC v3 subtype semantics are absent

- **WHEN** a v4 item belongs to an embedded SEC contract version 3 but omits its filing subtype or the complete semantics required by that subtype
- **THEN** Feed validation rejects the bundle

#### Scenario: SEC v4 subtype semantics are absent

- **WHEN** a v4 item belongs to an embedded SEC contract version 4 but omits its filing subtype or the complete semantics required by that subtype
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

## ADDED Requirements

### Requirement: SEC v4 selects a bounded watched-filer beneficial-ownership event set

The authoritative configuration SHALL contain a closed `watched_beneficial_ownership_filers` selection distinct from the watched 13F-company and Form 4-issuer selections, ordered by normalized CIK and embedded in the canonical Feed configuration snapshot. Shipped production SHALL select only Berkshire Hathaway reporting filer CIK `0001067983`. Unknown, duplicate, malformed, missing, or unordered selection data SHALL fail before Provider work or persistent mutation, and configured names SHALL NOT replace filing-supplied identity evidence.

For each configured filer, SEC contract version 4 SHALL validate the official submissions listing and select every unique exact `SCHEDULE 13D`, `SCHEDULE 13D/A`, `SCHEDULE 13G`, or `SCHEDULE 13G/A` whose precise acceptance time falls in `[window.start, evidence_cutoff_at)`. Selection SHALL use precise acceptance time rather than filing date, event date, retrieval time, or source row order. Accessions repeated across configured filers SHALL be fetched once and produce one event item. The manifest SHALL declare closed, statically validated current-filing, history-file, historical-candidate-document, reporting-person, structured-format, schema-version, and locator-prefix bounds. Unproved window coverage, bound excess, unsafe source location, omitted selected accession, unsupported current format, or malformed selected current document SHALL make SEC incomplete and prevent publication rather than truncate the event set.

#### Scenario: Current-window ownership filings are selected

- **WHEN** a configured filer's complete official listing contains supported exact Schedule 13D/G accessions accepted inside the half-open Feed window and all declared bounds hold
- **THEN** every unique selected accession is fetched and normalized in deterministic `(accepted_at, accession_number)` order

#### Scenario: Filing lies on a window boundary

- **WHEN** one supported filing is accepted exactly at `window.start` and another exactly at `evidence_cutoff_at`
- **THEN** the start-boundary filing is included and the cutoff-boundary filing is excluded

#### Scenario: Current event bound is exceeded

- **WHEN** the complete listing contains more eligible current-window Schedule 13D/G accessions than the manifest permits
- **THEN** SEC is incomplete and publishes neither a truncated subset nor prior SEC evidence

#### Scenario: Same accession is listed for multiple configured filers

- **WHEN** an identical accession is discovered through more than one configured filer
- **THEN** it is acquired once and produces one accession-identified Feed item without inferring a reporting group from duplicate discovery

#### Scenario: No ownership filing is eligible

- **WHEN** every configured listing proves complete window coverage and contains no eligible Schedule 13D/G accession
- **THEN** the beneficial-ownership sub-slice is complete and empty without fabricating an event

### Requirement: SEC v4 publishes closed structured beneficial-ownership evidence

Each selected accession SHALL produce exactly one `filing` item with `filing_subtype = beneficial_ownership`, accession-based item identity, exact SEC form, schedule family, filing and precise acceptance times, official raw structured-document URL, issuer identity, ownership-class identity, source-ordered reporting positions, and closed amendment metadata. Source publication and `knowledge_available_at` SHALL equal the precise SEC acceptance time. The Producer SHALL parse only manifest-declared verified SEC-native structured 13D and 13G shapes through form-specific contracts and SHALL NOT invoke a legacy prose, HTML, generic SEC, or heuristic parser.

Ownership-class identity SHALL prefer a normalized source CUSIP and otherwise use an exact normalized source class title. When neither is available, current evidence MAY remain publishable but comparison SHALL be unavailable with reason `ownership_class_identity_unavailable`. Each reporting position SHALL retain a zero-based source ordinal, source name, optional explicit source CIK, source-reported person type and group membership, required beneficially-owned-shares and ownership-percentage wrappers, and only those voting or dispositive power facts explicitly present in the source. A reporting-position identity SHALL use an explicit source CIK when available and otherwise exact normalized source name; configured aliases, fuzzy matching, and inferred CIK assignment are prohibited. A group identity or aggregate SHALL be published only when explicitly supported by the filing, and member values SHALL NOT be summed to invent group ownership.

The required shares and percentage wrappers SHALL contain a closed status, canonical value or null, unit, typed reason, and form-specific document-local source-field references. `reported` SHALL require a non-null source value; `unavailable` SHALL require null and a permitted reason. Shares and power values SHALL be nonnegative, and reported percentages SHALL be between zero and one hundred inclusive. Missing values SHALL NOT default to zero or be algebraically inferred from other filing facts. Source-field references SHALL resolve within their own current or previous filing snapshot to closed form/schema fields and source ordinals; arbitrary XPath, dangling references, credentials, filer CCC values, addresses, telephone numbers, and signatures SHALL NOT enter the Feed.

#### Scenario: Filing contains several reporting persons

- **WHEN** one supported filing contains multiple source reporting positions with distinct ownership values
- **THEN** one accession item preserves every position in source order with its own identity basis, measured facts, optional powers, and source-field support without collapsing the filing to one holder

#### Scenario: Reporting person has no source CIK

- **WHEN** a structured filing supplies a reporting-person name but no person CIK
- **THEN** the position retains `source_name` identity basis and no configured or inferred CIK is added

#### Scenario: CUSIP is absent

- **WHEN** the source supplies an ownership class title but no usable CUSIP
- **THEN** class identity uses exact deterministic normalized title matching and records `class_title` as its identity basis

#### Scenario: Required numeric value is not reported

- **WHEN** a supported structured source explicitly lacks a numeric shares or percentage value in an allowed shape
- **THEN** the required wrapper is retained with null value, `unavailable` status, and a closed source-supported reason rather than zero

#### Scenario: Group aggregate is not explicit

- **WHEN** several reporting persons jointly file but the structured source does not supply an explicit group aggregate
- **THEN** the item preserves the persons and group-membership evidence without summing their ownership facts or inventing a group aggregate

#### Scenario: Prohibited private or interpretive field is supplied

- **WHEN** an item contains filer credentials, CCC, contact details, signatures, arbitrary raw metadata, inferred identity, or investment interpretation
- **THEN** Feed validation rejects the item

### Requirement: Beneficial-ownership comparison is bounded, conservative, and reproducible

For each selected current filing, SEC v4 SHALL first resolve the nearest earlier filing comparable by official discovery filer CIK, issuer CIK, and ownership-class identity, without including schedule family or amendment status in that key. It SHALL then match reporting positions by explicit source CIK or, when absent, exact normalized source name. Schedule 13D and 13G forms MAY therefore compare across family transitions, but the Feed SHALL retain both exact forms and SHALL NOT interpret the transition. A previous filing SHALL precede current by precise acceptance time and have a distinct accession.

Resolution SHALL use a deterministic newest-first scan of official recent and declared historical submissions metadata. Historical candidate documents SHALL be fetched and parsed at most once per run and shared across all unresolved current keys. The scan SHALL stop when all keys resolve, official supported history is exhausted, or the closed total historical-candidate-document bound is reached. An unsupported nearest previous document SHALL be retained by accession, time, and source URL with reason `previous_format_unsupported`; it SHALL NOT be skipped in favor of an older parseable filing. A reached history or candidate bound SHALL produce typed unavailability rather than an initial-filing claim. Transport, source-validation, or parser failure for a document required within the supported acquisition contract SHALL keep SEC incomplete rather than masquerade as absent history.

A filing SHALL be classified `initial_filing` only after all official supported earlier metadata candidates have been exhausted with no prior filing matching its filer, issuer, and ownership class. When a prior filing exists but an internal reporting position cannot be matched, that position SHALL be unavailable with reason `reporting_identity_not_comparable`, not initial or new. Current and previous snapshots SHALL each retain their own accession, precise acceptance time, official URL, measured facts, and document-local source support.

For compatible reported facts, share delta SHALL equal exact current shares minus previous shares in `shares`, and percentage delta SHALL equal exact current percentage minus previous percentage in `percentage_points`. Arithmetic SHALL use the deterministic measured/derived numeric boundary and SHALL not round, truncate, use an LLM, or defer calculation to the Host Agent. Derived output SHALL carry the Provider-specific descriptor `current_minus_previous`; generic internal fact-object derivation metadata SHALL not be serialized. If either operand is unavailable, the corresponding delta SHALL be null and unavailable.

#### Scenario: Comparable filing changes schedule family

- **WHEN** the nearest earlier filing has the same filer, issuer and class but current and previous forms belong to different 13D/13G families
- **THEN** their explicitly reported compatible ownership facts are compared while both exact forms are retained without intent or market interpretation

#### Scenario: Supported previous facts are available

- **WHEN** current and nearest previous positions match and both report shares and percentages
- **THEN** share and percentage-point deltas equal exact current-minus-previous values and are reproducible from the two accession-supported snapshots

#### Scenario: Previous identity cannot be matched

- **WHEN** a previous comparable filing exists but a current name-based position cannot be matched exactly to a previous source identity
- **THEN** that position has comparison unavailable with reason `reporting_identity_not_comparable` and no initial or new-holder claim

#### Scenario: Nearest previous filing has an unsupported format

- **WHEN** the nearest metadata-comparable previous accession uses a legacy or otherwise unsupported document format
- **THEN** its filing reference is retained, comparison is unavailable with reason `previous_format_unsupported`, and no older filing is substituted

#### Scenario: Historical candidate bound is exhausted

- **WHEN** the shared reverse scan reaches its closed candidate-document bound before proving a previous filing or complete absence
- **THEN** unresolved comparisons use reason `history_candidate_bound_exhausted` without previous zero, delta, or initial-filing classification

#### Scenario: Complete history has no previous comparable filing

- **WHEN** all official supported earlier history is exhausted without any filing matching the current filer, issuer and ownership class
- **THEN** comparison is `initial_filing`, previous is null, and every delta is null rather than calculated from zero

#### Scenario: One operand is unavailable

- **WHEN** current or previous shares or percentage is unavailable
- **THEN** the corresponding delta remains null and unavailable without deriving the missing operand

### Requirement: Beneficial-ownership amendments remain independent evidence events

Exact `SCHEDULE 13D/A` and `SCHEDULE 13G/A` items SHALL retain `is_amendment = true`, their schedule family, and any source-supported amendment number. Non-amendment forms SHALL retain `is_amendment = false`. Every accession SHALL remain an independent event with its own provenance and canonical identity. The Producer SHALL NOT infer or publish an original accession, `amends_accession`, effective/latest version, merged filing, or amendment relationship from issuer, reporting persons, dates, ordering, similarity, or previous-comparable resolution unless the supported structured source explicitly supplies that accession linkage.

The payload and Host-Agent boundary SHALL remain evidence-only. They SHALL NOT add bullish, bearish, activist, takeover, control-change, accumulation, distribution, importance, confidence, signal, prediction, market-impact, recommendation, or trading semantics. Source-reported form transitions, ownership facts, amendment metadata, and exact changes MAY be expressed without interpretation.

#### Scenario: Amendment supplies only an amendment number

- **WHEN** a supported amendment identifies its amendment number but does not supply an original accession
- **THEN** the number and amendment status are retained while original-filing and `amends_accession` fields are absent

#### Scenario: Previous comparable is an earlier amendment

- **WHEN** the nearest earlier comparable filing is itself an amendment
- **THEN** it may support deterministic ownership comparison but is not relabeled as the original or effective filing

#### Scenario: Investment meaning is added

- **WHEN** a beneficial-ownership item adds intent, control, takeover, sentiment, signal, ranking, prediction, recommendation, or market-impact semantics not explicitly present as retained source evidence
- **THEN** Feed validation rejects the item

### Requirement: SEC v4 mixed slices remain complete, bounded, and deadline-admissible

A complete SEC contract-version-4 acquisition SHALL contain exactly one valid `form13f` item for every configured watched 13F company, exactly the selector-proven current-window `form4` accession set for configured watched issuers, and exactly the selector-proven deduplicated current-window `beneficial_ownership` accession set for configured watched beneficial-ownership filers. Validation SHALL dispatch every subtype explicitly, require exact configured membership and selector-produced accession sets, require unique accession-based identities across the SEC slice, and reject legacy or unknown filing shapes under v4.

The mixed SEC v4 slice SHALL remain one Provider outcome and one whole-Provider replacement. Historical filings fetched only for beneficial-ownership comparison SHALL remain nested references/snapshots and SHALL NOT become additional top-level events. A previous filing that is independently selected in the current window MAY be both its own top-level event and nested comparison evidence for a later event. Events absent from the next complete advancing-window slice SHALL not be unioned or carried from prior output. Failed or partial work in any SEC subtype SHALL remain `not_evaluated`, pipeline-failing, and ineligible for prior-slice substitution; genuine first-resource blocked exemption SHALL retain the existing no-prior-evidence degraded behavior.

Before production v4 activation, the configured pre-commit deadline SHALL be at least the verified complete SEC v4 successful-path managed-send floor plus explicit bounded network headroom and commit reserve. The calculation SHALL include all configured 13F sends, the existing maximum Form 4 listing/document sends, beneficial-ownership listing/current/history/candidate-document sends, the unchanged SEC minimum interval, and any reused request exactly once. Static resolution or regression verification SHALL fail when configuration, selections, manifest bounds, rate policy, or deadline no longer satisfy that inequality. ECO-132 SHALL NOT lower SEC rate safety or silently reduce evidence to fit the deadline.

#### Scenario: Complete SEC v4 event sets are produced

- **WHEN** all configured 13F, Form 4, and beneficial-ownership acquisition units complete under their closed contracts
- **THEN** the one SEC outcome contains the exact required mixed subtype sets and is eligible for whole-slice selection

#### Scenario: Historical enrichment filing is inspected

- **WHEN** a previous 13D/G document is fetched solely to support a current ownership event
- **THEN** it appears only in the current event's previous evidence and not as an extra top-level item unless independently selected in the current window

#### Scenario: Prior-window ownership event is absent now

- **WHEN** a beneficial-ownership accession appeared only in the prior advancing window and is absent from the complete current selector result
- **THEN** whole-slice replacement does not carry or union that prior top-level event

#### Scenario: Beneficial-ownership acquisition is incomplete

- **WHEN** 13F and Form 4 work succeeds but a required current beneficial-ownership listing, document, or supported historical request fails
- **THEN** SEC is incomplete, freshness is not evaluated, publication is forbidden, and prior SEC evidence does not convert the run into success

#### Scenario: Existing request-budget regression omits a subtype

- **WHEN** the successful-path send calculation excludes Form 4, beneficial-ownership, history, or another configured SEC v4 acquisition unit
- **THEN** production v4 activation fails verification rather than relying on an understated deadline floor

#### Scenario: Complete slices are byte-identical

- **WHEN** exact 13F, Form 4, and beneficial-ownership identity sets and every canonical item are equal to the validated prior SEC v4 slice
- **THEN** existing whole-slice valid-unchanged carry-forward remains eligible without changing source-semantic times
