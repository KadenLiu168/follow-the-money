## MODIFIED Requirements

### Requirement: Feed v4 supports bounded Provider semantic contract evolution

New production SHALL continue to emit Feed `schema_version = 4`. The checked-in SEC EDGAR manifest SHALL publish Provider `contract_version = 3`, the checked-in CFTC manifest SHALL publish Provider `contract_version = 2`, and the other six required Providers SHALL remain at contract version 1. Manifest resolution and embedded-contract validation SHALL use an explicit Provider-specific supported-version set rather than a global maximum, a manifest hash, or implicit acceptance of arbitrary versions.

A current consumer SHALL retain bounded read compatibility for structurally and semantically valid v4 items carrying SEC Provider contract versions 1 or 2 and CFTC Provider contract version 1. SEC contract version 2 items SHALL retain the complete required 13F semantic structure. SEC contract version 3 items SHALL carry the required closed filing subtype and SHALL satisfy either the complete 13F subtype contract or the complete Form 4 subtype contract. CFTC contract version 2 items SHALL contain the complete required COT semantic structure. Unknown fields, unsupported Provider/version combinations, malformed version declarations, and versioned items missing required semantics SHALL fail closed. New production SHALL NOT emit a legacy SEC v1/v2 or CFTC v1 contract after the corresponding working manifest activation. Each checked-in manifest bump SHALL be atomic with its working semantic adapter, configuration, validation, verified fixtures, and compatibility path.

#### Scenario: Existing v4 Provider-v1 bundle is read

- **WHEN** a valid previously published v4 bundle embeds SEC or CFTC Provider contract version 1 and uses the bounded legacy payload shape
- **THEN** the current consumer validates it without requiring newer semantic fields

#### Scenario: Existing SEC v2 bundle is read

- **WHEN** a valid previously published v4 bundle embeds SEC Provider contract version 2 with the complete existing 13F semantic structure
- **THEN** the current consumer validates it without requiring a filing subtype or Form 4 fields

#### Scenario: SEC v2 semantics are absent

- **WHEN** a v4 item belongs to an embedded SEC contract version 2 but omits any required 13F semantic structure
- **THEN** Feed validation rejects the bundle

#### Scenario: SEC v3 subtype semantics are absent

- **WHEN** a v4 item belongs to an embedded SEC contract version 3 but omits its filing subtype or the complete semantics required by that subtype
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

### Requirement: SEC v3 selects a complete watched-issuer Form 4 event set

The authoritative configuration SHALL contain a closed `watched_form4_issuers` selection distinct from the existing watched 13F-company selection, ordered by normalized CIK and embedded in the canonical Feed configuration snapshot. Shipped production SHALL select only Berkshire Hathaway issuer CIK `0001067983` for Form 4 acquisition. Unknown, duplicate, malformed, or missing selection fields SHALL fail static resolution before Provider work or persistent mutation.

For each watched issuer, SEC contract version 3 SHALL retrieve the official submissions `recent` listing, validate its aligned fields, unique accessions, and every precise acceptance time, and prove that the minimum represented precise acceptance time is at or before `window.start`. It SHALL NOT treat incidental source-row order as an acceptance-time coverage or ordering guarantee. It SHALL select every unique exact Form `4` or `4/A` whose precise SEC acceptance time is in `[window.start, evidence_cutoff_at)`, canonically order selected filings by `(accepted_at, accession_number)`, and retrieve every selected safe primary ownership XML. It SHALL NOT use filing date, period of report, transaction date, retrieval time, or current visibility to replace precise acceptance-time eligibility.

The embedded SEC v3 contract SHALL declare `max_filings_per_window = 20`. More than 20 eligible filings, a listing that cannot prove complete window coverage, misaligned or ambiguous listing data, duplicate accessions, an unsafe primary-document path, a missing selected document, malformed or unsupported ownership XML, or any omitted eligible filing or entry SHALL make SEC incomplete and prevent publication. The producer SHALL NOT truncate or choose a preferred subset. A proved-complete listing with zero eligible Form 4 filings SHALL be a valid empty Form 4 sub-slice. ECO-131 SHALL NOT traverse historical submissions files.

#### Scenario: Watched issuer has filings in the advancing window

- **WHEN** Berkshire's complete recent listing contains unique exact Form 4 or 4/A filings accepted inside the half-open window and no bound is exceeded
- **THEN** SEC retrieves and validates every selected primary ownership XML in deterministic order

#### Scenario: Filing falls on a window boundary

- **WHEN** a Form 4 acceptance time equals `window.start` or `evidence_cutoff_at`
- **THEN** the start-boundary filing is eligible and the cutoff-boundary filing is excluded

#### Scenario: Recent listing does not cover the window

- **WHEN** the minimum represented precise acceptance time is later than `window.start` or listing structure cannot prove complete coverage
- **THEN** SEC fails closed without treating an absent filing as an empty current check or consulting historical submissions files

#### Scenario: Recent source rows are not acceptance-time ordered

- **WHEN** an otherwise aligned official `recent` listing has historical rows out of acceptance-time order
- **THEN** SEC validates every row's precise acceptance time, derives coverage from the minimum time, and canonically orders the selected current-window accessions rather than rejecting the source's incidental row order

#### Scenario: Eligible filing bound is exceeded

- **WHEN** a complete listing contains more than 20 eligible Form 4/Form 4-A accessions
- **THEN** SEC is incomplete and publishes neither a truncated subset nor a replacement from prior evidence

#### Scenario: No ownership filing is eligible

- **WHEN** the recent listing proves complete coverage and contains no exact Form 4 or 4/A accepted inside the window
- **THEN** the Form 4 sub-slice is complete and empty without inventing an evidence item

### Requirement: SEC v3 publishes closed structured Form 4 evidence

Each selected accession SHALL produce exactly one `filing` item with `filing_subtype = form4`, exact form `4` or `4/A`, issuer CIK as the filing company, accession number, official filing date, precise acceptance time, period of report, official primary-document source URL, and a closed structured Form 4 payload. Source publication and `knowledge_available_at` SHALL use the precise SEC acceptance time. Issuer identity SHALL contain the filing-supplied CIK, name, and trading symbol and SHALL match one configured watched issuer CIK.

The payload SHALL contain one or more unique reporting owners ordered by normalized owner CIK. Each owner SHALL retain filing-supplied CIK and name plus the complete closed relationship fields `director`, `officer`, `ten_percent_owner`, `other`, nullable `officer_title`, and nullable `other_text`. Missing relationship booleans SHALL normalize to false, and at least one relationship boolean SHALL be true. The payload SHALL NOT publish reporting-owner address or introduce importance, ranking, or inferred entity roles.

The payload SHALL retain separate non-derivative and derivative entry arrays. Each array SHALL preserve the SEC table's mixed source order with consecutive source ordinals and support both `transaction` and standalone `holding` entry kinds. Transaction entries SHALL retain the applicable security title, transaction and deemed-execution dates, raw SEC transaction form type and transaction code, timeliness, equity-swap flag, acquisition/disposition code, reported transaction amount, price per share, derivative exercise/conversion fields, underlying security, post-transaction amount, and ownership nature. Standalone holdings SHALL retain their applicable security, derivative and underlying-security fields, post-transaction amount, and ownership nature. Fields inapplicable to an entry kind SHALL not be invented.

#### Scenario: Filing has multiple reporting owners and entries

- **WHEN** one valid filing contains multiple reporting owners and a mixture of transactions and standalone holdings across both SEC tables
- **THEN** one filing item preserves every owner, complete relationship, table, entry kind, and source ordinal without duplicating entries per owner or asserting an owner-to-entry relation absent from the filing structure

#### Scenario: Purchase, sale, or award code is published

- **WHEN** a transaction contains a supported SEC transaction code such as `P`, `S`, or `A`
- **THEN** the payload retains the SEC code and acquisition/disposition value without translating either into bullish, bearish, sentiment, signal, or recommendation semantics

#### Scenario: Standalone holding is present

- **WHEN** either SEC table contains a valid standalone holding entry
- **THEN** the entry is retained with its security, amount and ownership evidence rather than silently omitted or represented as a transaction

#### Scenario: Unsupported entry is encountered

- **WHEN** a selected ownership document contains an entry or required field that cannot be represented by the closed supported contract
- **THEN** SEC fails closed for that acquisition instead of dropping the entry or preserving it only in raw metadata

### Requirement: Form 4 numeric values and footnotes remain typed and reproducible

Every supported Form 4 source numeric SHALL be a bounded nonnegative canonical decimal string produced independently of ambient decimal context. The closed payload SHALL distinguish SEC choice branches rather than coercing them: transaction shares versus total USD value, post-transaction shares versus USD value, and underlying-security shares versus USD value. Reported price per share and conversion/exercise price SHALL use `usd_per_share`; count values SHALL use `shares`; reported total/value branches SHALL use `usd`. The producer SHALL NOT derive transaction value, holding delta, price direction, or another arithmetic or financial interpretation.

Every value-bearing Form 4 field SHALL retain its own deterministically ordered SEC footnote references and SHALL permit a null value only where the SEC structure permits footnote-supported omission. The payload SHALL retain a unique filing-level footnote table ordered numerically from `F1` through `F99`, with deterministic plain-text extraction, NFC normalization, and at most 4,000 Unicode code points per footnote. Duplicate or malformed IDs, dangling references, unsupported mixed content, oversized text, or a required null value without permitted footnote support SHALL fail closed rather than truncate or detach support. Filing remarks SHALL remain separate, normalized evidence bounded to the SEC maximum of 2,000 characters.

Ownership nature SHALL retain direct or indirect ownership and nullable nature text. Indirect ownership without non-empty nature text SHALL fail closed. Numeric fact construction MAY retain internal measured-fact provenance, but generic fact/derivation metadata SHALL NOT be serialized into the Feed.

#### Scenario: Numeric processing runs under different ambient decimal state

- **WHEN** the same valid ownership XML is processed under different process-global Decimal precision, rounding, flags, or traps
- **THEN** every numeric field and the complete canonical filing item bytes are identical

#### Scenario: Derivative transaction reports total value

- **WHEN** a derivative transaction uses `transactionTotalValue` rather than `transactionShares`
- **THEN** the payload retains the selected `total_value` branch in canonical USD without inventing a share count

#### Scenario: Value is supplied only through a footnote

- **WHEN** the SEC structure permits a numeric value to be absent and the field carries valid footnote references
- **THEN** the payload retains a null value, its explicit unit and the field-level references to available filing footnote text

#### Scenario: Footnote reference cannot be resolved

- **WHEN** a field references an absent, duplicate, malformed, unsupported, or oversized footnote
- **THEN** the selected filing fails validation and cannot enter a published Feed

#### Scenario: Indirect ownership lacks its nature

- **WHEN** an entry reports indirect ownership without non-empty nature-of-ownership evidence
- **THEN** the filing fails closed rather than representing incomplete ownership semantics

### Requirement: Form 4 amendment evidence does not infer filing lineage

A Form `4/A` item SHALL retain `is_amendment = true` and the SEC-required `date_of_original_submission`; a Form `4` item SHALL retain `is_amendment = false` and a null original-submission date. Every original and amended accession SHALL remain an independent event with its own source provenance and canonical identity. The Producer SHALL NOT infer or publish `amends_accession`, merge an amendment with another filing, overwrite historical evidence, designate an effective/latest version, or retrieve evidence outside the advancing window to construct a lineage.

#### Scenario: Form 4/A is selected

- **WHEN** a valid Form 4/A is accepted inside the advancing window
- **THEN** it is published under its own accession with its SEC-supplied original-submission date and no inferred accession linkage

#### Scenario: Original and amendment occur in one window

- **WHEN** both a Form 4 and one or more Form 4/A accessions are independently eligible
- **THEN** each accession produces a separate item and none is removed, replaced, or labeled effective by amendment resolution

#### Scenario: Consumer requests an amended accession

- **WHEN** no explicit amended accession exists in the supported SEC ownership evidence
- **THEN** the payload omits that relationship rather than deriving it from issuer, owner, period, date, ordering, or similarity

### Requirement: Form 4 identities and ordering are deterministic

A Form 4 filing item identity SHALL derive solely from the SEC Provider identity and accession number. Every non-derivative or derivative table entry SHALL expose a stable entry identity derived solely from accession number, table kind, and its zero-based source ordinal within that table's mixed transaction/holding sequence. Reporting-owner names, transaction values, security titles, issuer aliases, and acquisition completion order SHALL NOT participate in identity.

Reporting owners SHALL be unique and ordered by normalized CIK. Non-derivative entries SHALL precede derivative entries in semantic projection, and each table's entries SHALL remain in ascending consecutive source ordinal. Filing footnotes and every field-level reference list SHALL use numeric footnote-ID order. Repeated processing of identical listing and XML bytes SHALL produce byte-identical canonical items; changing a typed identity, relationship, entry, amount, date, ownership, amendment, remark, or footnote fact SHALL change canonical item content and therefore Feed semantic identity.

#### Scenario: Same filing is processed repeatedly

- **WHEN** the same selected submissions row and ownership XML are processed more than once
- **THEN** filing identity, entry identities, ordering, canonical item bytes, content digest, and cutoff-derived run identity are identical

#### Scenario: Filing has multiple table entry kinds

- **WHEN** transaction and standalone-holding elements are interleaved in an SEC table
- **THEN** their source ordinals and entry identities follow that mixed SEC table order without regrouping by kind, code, date, price, or amount

#### Scenario: One semantic field changes

- **WHEN** any retained Form 4 semantic or provenance fact changes at the same cutoff
- **THEN** canonical item content, Feed content digest, and run identity change while the accession-based filing identity and position-based entry identities remain stable

### Requirement: SEC v3 snapshot selection combines 13F state with current-window Form 4 events

A complete SEC contract-version-3 acquisition SHALL contain exactly one valid `form13f` filing item for every configured watched 13F company and no extra 13F company, together with exactly the complete set of valid `form4` filing items selected for configured watched issuers in the current advancing window. Validation SHALL dispatch subtype semantics explicitly, require exact configured 13F and Form 4 issuer membership, require unique accession-based identities across the SEC slice, and reject a legacy or unknown filing shape under v3.

The resulting mixed SEC slice SHALL remain a whole-Provider replacement. Equal identity sets with byte-identical canonical content MAY carry prior bytes under existing complete-state admission. Any added, removed, or changed 13F or Form 4 identity SHALL select the complete current SEC slice. In particular, Form 4 events from an earlier window SHALL not be unioned into a later slice when they are absent from the current complete event set. Failed or partial 13F or Form 4 acquisition SHALL remain `not_evaluated`, pipeline-failing and ineligible for prior-slice substitution. Genuine first-resource blocked exemption SHALL retain the existing no-prior-evidence degraded behavior.

#### Scenario: Current window adds a Form 4 event

- **WHEN** all 13F items are unchanged and a complete current Form 4 acquisition adds one eligible accession
- **THEN** the whole current SEC v3 slice containing all required 13F items and that event replaces the prior SEC slice

#### Scenario: Earlier Form 4 event leaves the current window

- **WHEN** the current complete SEC slice contains unchanged 13F state and no Form 4 event that appeared only in the preceding advancing window
- **THEN** the current slice replaces the prior slice without carrying or merging that earlier event

#### Scenario: Form 4 sub-acquisition fails

- **WHEN** every watched 13F company succeeds but one required Form 4 listing or selected filing is incomplete
- **THEN** SEC is incomplete, freshness is not evaluated, the Feed cannot publish, and prior SEC evidence does not convert the run into success

#### Scenario: Complete SEC v3 slice is byte-identical

- **WHEN** the exact 13F and Form 4 item identity sets and every canonical item are equal to the validated prior SEC v3 slice
- **THEN** existing whole-slice valid-unchanged carry-forward remains eligible without rewriting source-semantic times
