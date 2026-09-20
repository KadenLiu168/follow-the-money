## ADDED Requirements

### Requirement: Feed v5 carries bounded official source content

New production SHALL emit logical Feed `schema_version = 5`. A `news`, `macro_release`, or `policy` payload MAY contain one closed `source_content` object with exactly non-empty `text`, `format`, `extraction_method`, `truncated`, and `document_sha256` fields. `format` SHALL be `plain_text`; `extraction_method` SHALL be `official_html_text_v1`; `truncated` SHALL be boolean; and `document_sha256` SHALL be the lowercase SHA-256 of the admitted raw detail-response body bytes without HTTP headers, retrieval time, execution metadata, or another runtime observation. The text SHALL be NFC-normalized deterministic plain text of at most 12,000 Unicode code points. Positioning, filing, `raw_metadata`, and `semantic_context` SHALL NOT carry source content.

Every serialized source-content field SHALL remain part of the item and therefore part of the canonical Feed semantic projection. Source content SHALL NOT create a new artifact, cache, checkpoint, or evidence authority.

#### Scenario: Official HTML content is admitted

- **WHEN** a supported Provider produces valid bounded official detail-document text
- **THEN** Feed v5 retains it in the matching payload's closed `source_content` object with its deterministic extraction provenance and raw-document digest

#### Scenario: Source content is placed outside its contract

- **WHEN** source content appears in `raw_metadata`, `semantic_context`, a positioning or filing payload, or another undeclared location
- **THEN** Feed validation rejects the candidate rather than treating it as reader evidence

#### Scenario: Source content exceeds its closed shape

- **WHEN** source content is empty, over 12,000 Unicode code points, non-NFC, uses an unknown format or extraction method, or carries a malformed document digest
- **THEN** Feed validation rejects the item before publication or consumption

### Requirement: Four Provider v2 contracts acquire every selected official detail document

Federal Reserve, PBOC, SSE, and SZSE Provider contract version 2 SHALL make source-content acquisition mandatory for every deterministically selected current-window candidate. Each contract SHALL declare and snapshot `acquisition = detail_document`, `extraction_method = official_html_text_v1`, `allowed_content_types = [text/html]`, `max_document_bytes = 2097152`, `max_text_chars = 12000`, `max_detail_documents_per_window = 50`, and `required_for_selected_item = true`. SSE and SZSE SHALL additionally declare `max_discovery_pages_per_window = 10` and `discovery_order = published_at_descending`. These facts SHALL be strictly parsed into the resolved runtime contract, included in its hash and embedded snapshot, and drive behavior without Python-only defaults.

Discovery SHALL validate and canonicalize candidate identities and URLs, select membership in the half-open acquisition window before detail requests, collapse only exact duplicate candidates, and fail on conflicting duplicate identity metadata. Federal Reserve SHALL preserve its existing RSS GUID-or-link stable identity rule; PBOC, SSE, and SZSE SHALL preserve their existing canonical-URL stable identity rules. SSE and SZSE SHALL traverse sequential official index pages until the verified descending order proves the window boundary; missing, conflicting, non-descending, unsafe, or over-bound discovery SHALL fail closed rather than silently treating a partial first page as complete.

After selection, the Provider SHALL fetch every selected detail document and no unselected detail document. A selected count above the declared detail bound SHALL fail before any selected detail request; it SHALL NOT select a top-N subset. All Provider network I/O, including discovery pages, detail documents, and permitted redirect hops, SHALL remain inside `fetch(window, client)` and the existing managed-send boundary. `normalize(raw, window)` SHALL perform no network access.

#### Scenario: Three of two hundred discovered entries are current

- **WHEN** deterministic discovery returns 200 valid candidates and exactly three fall in the acquisition window
- **THEN** the Provider performs the bounded discovery requests plus exactly three detail-document acquisitions and requests no detail document for the other 197 candidates

#### Scenario: Exchange discovery crosses the window boundary

- **WHEN** sequential SSE or SZSE pages preserve the verified descending publication order and one page proves that all remaining candidates predate the window
- **THEN** discovery stops at that proof without fetching later historical pages

#### Scenario: Selected candidate count exceeds the safety bound

- **WHEN** more than 50 unique valid candidates are selected for one Provider window
- **THEN** that Provider fails closed before the first selected detail request and does not emit a truncated subset

#### Scenario: Detail content type is unsupported

- **WHEN** a selected detail response declares a media type other than the contract's allowed `text/html`
- **THEN** the Provider fails closed before extraction and does not reinterpret the response by sniffing or extension

#### Scenario: Stable source is enriched

- **WHEN** a selected source retains the same existing identity while its required detail document is acquired
- **THEN** enrichment leaves the Feed item ID unchanged and attaches source content to that item

### Requirement: Official HTML extraction is deterministic, bounded, and fail closed

Each Provider SHALL extract only from its verified official article or release container. Extraction SHALL remove script, style, and declared non-content descendants; decode HTML character references; traverse declared content blocks in source order; normalize Unicode to NFC; fold intra-block whitespace; remove empty blocks; and join retained blocks with deterministic paragraph separation. It SHALL NOT fall back to whole-document body text, generic article inference, a readability library, an LLM, PDF parsing, OCR, or attachment dereferencing.

Bounded extraction SHALL append only whole normalized blocks while counting both block text and separators toward the 12,000-code-point limit. It SHALL set `truncated = true` exactly when one or more otherwise admissible later blocks are omitted. A missing or empty expected container, invalid declared charset, non-HTML response, unsupported attachment-only source, a single first admissible block larger than the bound, or another extraction violation SHALL fail the Provider slice.

#### Scenario: Identical official bytes are normalized twice

- **WHEN** the same admitted raw detail bytes are extracted under the same Provider v2 contract
- **THEN** the exact source-content object is byte-identical across runs

#### Scenario: A later block exceeds the remaining budget

- **WHEN** one or more complete blocks fit and the next complete block would exceed 12,000 code points
- **THEN** extraction retains the fitting blocks, omits that block and all later blocks, and sets `truncated = true`

#### Scenario: The first content block is oversized

- **WHEN** the first otherwise admissible normalized content block exceeds 12,000 code points
- **THEN** extraction fails closed rather than returning empty text or cutting the block

#### Scenario: Expected article container is absent

- **WHEN** an official detail response lacks the Provider contract's verified content container
- **THEN** the Provider fails closed without falling back to navigation, menu, recommendation, or footer text

### Requirement: Required source content is an atomic Provider completeness obligation

For each of the four Provider v2 contracts, successful discovery plus successful acquisition and extraction of every selected detail document SHALL form one atomic Provider slice. A 401, 403, 404, timeout, unsafe redirect, response over the detail-document byte bound, decoding error, unsupported format, missing container, extraction error, or any other selected-detail failure SHALL leave the Provider `failed` or `partial` under the existing observed-progress rules, set freshness to `not_evaluated`, and remain ineligible for prior-slice substitution. Accepted evidence from an earlier acquisition unit or a title-only representation of the failed candidate SHALL NOT make the Provider complete or the run publishable.

#### Scenario: One of three detail documents fails

- **WHEN** discovery selects three candidates, two detail documents succeed, and the third required detail acquisition or extraction fails
- **THEN** the Provider is incomplete, publishes no healthy three-item or two-item source-content slice, and cannot silently emit the failed candidate as title-only evidence

#### Scenario: First detail request is blocked

- **WHEN** discovery succeeds and the first selected detail request returns HTTP 403
- **THEN** acquisition progress prevents the existing first-resource blocked exemption and the Provider remains partial and non-publishable

### Requirement: Source-content request bounds are deadline admissible by shared rate scope

Static production resolution SHALL compute the maximum successful-path managed sends introduced by the four Provider v2 contracts, including bounded discovery pages, all bounded selected detail documents, and the existing base request of every enabled Provider sharing the same rate scope. For each affected scope it SHALL compute the managed-send floor from the resolved capacity, refill period, and minimum interval, then require that floor plus an explicit configured source-content network headroom and the exact commit reserve to fit within the authoritative configured pre-commit deadline. Missing bounds, incompatible policies within one scope, arithmetic overflow, or an inadmissible deadline SHALL fail before Provider requests or persistent rate-state mutation.

This validation SHALL NOT weaken per-send deadline admission, durable debit, retry, cancellation, redirect, or rate reconciliation. The bounds establish admission safety and SHALL NOT authorize top-N evidence loss.

#### Scenario: China Provider bounds exceed the shared scope budget

- **WHEN** the combined PBOC, NBS, SSE, and SZSE successful-path send shape cannot fit its resolved `china_gov` rate policy, network headroom, and commit reserve before the configured deadline
- **THEN** startup fails before any Provider request rather than relying on runtime timeout or silently reducing selected documents

#### Scenario: Provider contracts and deadline are admissible

- **WHEN** every affected shared-scope send shape plus its declared headroom and reserve fits the configured deadline
- **THEN** static resolution admits the production plan while every actual send still re-enters the existing managed-send boundary

### Requirement: Enrichment preserves item identity while changing semantic Feed identity

Source-content acquisition SHALL NOT add the document digest or extracted text to a stable item identity input. Equal item identity with changed admitted detail bytes SHALL retain the same item ID, change `document_sha256`, and change `content_digest` and cutoff-derived `run_id`. Identical discovery inputs, detail bytes, resolved contracts, cutoff, and other semantic inputs SHALL produce byte-identical logical Feed and bundle content. Because the raw document digest is semantic evidence, any admitted raw-response byte change, including a non-extracted page byte, SHALL conservatively change Feed identity even when extracted text is equal.

#### Scenario: Official document body changes at the same identity

- **WHEN** a canonical source identity is unchanged but its admitted raw detail bytes change
- **THEN** the item ID remains unchanged while the document digest, Feed content digest, and run ID change

#### Scenario: Only non-extracted page bytes change

- **WHEN** two admitted raw documents extract to identical text but their other raw bytes differ
- **THEN** their document digests and Feed semantic identities differ by contract

#### Scenario: All semantic inputs are identical

- **WHEN** discovery, admitted detail bytes, contracts, cutoff, and every other semantic input are identical
- **THEN** source content and the canonical Feed are byte-identical

## MODIFIED Requirements

### Requirement: Bounded command deadline and non-cancellable commit

The minimal Feed entry SHALL enforce the authoritative configured command-start monotonic deadline with the exact configured pre-commit reserve. Static resolution SHALL reject any closed successful-path request shape whose rate-policy floor plus its declared network headroom and commit reserve cannot fit that deadline. Lock waits, rate waits, pagination, retries, request attempts, reversible processing, and staging `fsync` SHALL fit before `pre_commit_deadline_seconds - commit_reserve_seconds`. Once a fully staged candidate is admitted to filesystem commit before that boundary, rename and parent-directory `fsync` SHALL run to their normal result without cancellation or rollback; completion after the configured nominal deadline MAY only add `commit_elapsed_overrun` to external status or stderr and SHALL NOT change the already hashed Feed bytes.

#### Scenario: No attempt fits before the reserve

- **WHEN** the next wait or request attempt cannot complete within the remaining pre-commit budget
- **THEN** collection stops with the typed deadline outcome before that attempt begins

#### Scenario: Staging crosses the reserve boundary

- **WHEN** candidate staging or its required pre-commit `fsync` reaches or crosses the configured deadline minus the exact commit reserve
- **THEN** publication removes reversible staging files and fails typed `pre_commit_deadline_exceeded` before replacing the active Feed product

#### Scenario: Commit crosses the nominal deadline

- **WHEN** a candidate is fully staged and admitted before the configured reserve boundary but durable replacement completes after the configured nominal deadline
- **THEN** commit finishes without cancellation or rollback and reports the overrun only outside the immutable Feed payload

### Requirement: Feed bundle is the serialized external contract

Every published bundle SHALL validate against the five-domain manifest, artifact, and logical Feed schema majors and their semantic invariants. New production SHALL emit logical Feed and bundle major 5 while retaining the unchanged five-domain physical artifact layout. Logical and bundle major 4 MAY remain read-compatible only as the immediately preceding bounded migration input; major 3 and every older major SHALL be rejected. New production SHALL NOT emit major 4, and normal current-Feed consumption SHALL use major 5. The bundle SHALL retain fixed acquisition window, truthful lifecycle timestamps, Provider outcomes with freshness and availability, canonical redacted Feed configuration snapshot, eight required Provider contract snapshots, producer descriptor, canonical logical `content_digest`, cutoff-derived `run_id`, pipeline semantics, and exactly one supported payload per item. Consumers SHALL validate from embedded producer contracts without requiring equality with the consumer build.

#### Scenario: Producer and consumer builds differ

- **WHEN** another build produced a valid supported major-5 five-domain bundle
- **THEN** the consumer validates it from embedded descriptors without requiring current build hashes to match

#### Scenario: Payload type and artifact domain disagree

- **WHEN** an item is stored outside the artifact matching its retained payload discriminator
- **THEN** validation rejects the bundle

#### Scenario: Previous-major active bundle is read

- **WHEN** a complete major-4 bundle enters the explicit bounded migration path
- **THEN** it may seed only a newly validated major-5 five-domain candidate and is not exposed as the normal current product after migration

#### Scenario: Version 3 bundle is supplied

- **WHEN** a consumer or migration caller receives a logical Feed or bundle with major 3 or older
- **THEN** validation rejects it rather than retaining two previous-major compatibility paths

#### Scenario: New production attempts the preceding major

- **WHEN** a producer candidate declares major 4
- **THEN** new-production validation rejects it before publication

### Requirement: Bounded canonical evidence and conservative deduplication

Normalized text SHALL use strict manifest-declared decoding, Unicode scalar values, NFC normalization, and bounded UTF-8 fields. A verified first-party official Provider MAY retain its schema-permitted bounded official document text as `source_content`; news-like items SHALL NOT retain full third-party copyrighted article bodies or text outside the closed source-content contract. Raw numeric tokens SHALL satisfy the existing lexical, digit, exponent, magnitude, sign, and unit-domain bounds before `Decimal` construction, and persisted financial values SHALL be canonical plain decimal strings without exponent or negative zero. Stable IDs and canonical URLs SHALL remove exact and same-source near duplicates while retaining independently originated cross-source reports and their source-lineage provenance.

#### Scenario: Verified official document content is returned

- **WHEN** a Provider contract explicitly permits bounded first-party official source content and the detail document satisfies that contract
- **THEN** the Feed may retain only the closed normalized source-content evidence in addition to its existing typed fields

#### Scenario: Full article content is returned

- **WHEN** a Provider response contains a third-party copyrighted article body or text outside the closed official source-content contract
- **THEN** the Feed does not retain that body and rejects any payload that attempts to serialize it outside existing bounded evidence fields

#### Scenario: Numeric input is adversarial

- **WHEN** a raw numeric token exceeds the configured byte, significant-digit, exponent, magnitude, sign, or unit-domain bounds
- **THEN** it is rejected before `Decimal` arithmetic, hashing, or Feed publication

#### Scenario: Independent sources report one event

- **WHEN** two independent sources publish similar evidence at distinct canonical URLs
- **THEN** both items remain available for later corroboration rather than being collapsed as one origin
