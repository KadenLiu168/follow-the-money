## Context

See `proposal.md` for motivation and `specs/feed-evidence-pipeline/spec.md` for observable requirements.

The logical Feed is schema major v4 with five domains and eight credential-free Providers. SEC EDGAR v3 currently combines a complete watched-company 13F state with current-window Form 4 events in one Provider outcome and one whole-slice replacement. SEC v3 uses a separate Form 4 watched-issuer selection, accession identity, official submissions listings, raw structured XML, Provider-specific parsing, and the shared managed-send boundary.

ECO-125 supplies only Producer-internal measured/derived numeric facts and owned-context decimal arithmetic. It deliberately leaves identity, matching, comparison state, source selection, and wire projection Provider-specific. ECO-131 likewise rejected a generic filing parser or entity resolver.

Read-only source verification against Berkshire CIK `0001067983` found exact submissions tokens `SCHEDULE 13D`, `SCHEDULE 13D/A`, `SCHEDULE 13G`, and `SCHEDULE 13G/A`; 223 matching recent rows; an observed rolling 72-hour maximum of seven events; SEC-native `edgarSubmission` XML; observed schema `X0202`; distinct 13D and 13G element structures; and locator prefixes including `xslSCHEDULE_13G_X01` and `X02`. The listing declares one historical submissions file spanning 1998-08-10 through 2017-01-08. These observations guide verification but do not become runtime authority until pinned in the manifest and fixtures.

The current request-budget regression simulates only the eight 13F units (24 sends) despite ECO-131 adding a Form 4 listing plus up to 20 XML sends. At the resolved five-second SEC minimum interval, the complete v3 successful-path shape can already require 45 sends and a 220-second spacing floor within the current 285-second pre-commit budget. Beneficial-ownership current and history requests cannot be safely added without correcting that model and increasing the deadline.

## Goals / Non-Goals

**Goals:**

- Add a third bounded SEC filing subtype without changing the Feed major or five-domain contract.
- Acquire every selected current-window filing for a closed watched reporting-filer universe and prove exact accession-set completeness.
- Preserve source-supported issuer, class, reporting-position, ownership, amendment, and provenance evidence from verified structured XML.
- Resolve previous comparable filings conservatively under explicit history and request bounds and compute exact reproducible deltas when operands are available.
- Preserve SEC v1-v3 read compatibility, current 13F/Form 4 behavior, one SEC outcome, deterministic identity, and whole-slice publication guarantees.
- Make the complete SEC v4 successful-path request shape admissible under unchanged SEC rate safety.

**Non-Goals:**

- A generic SEC parser, entity resolver, semantic graph, filing registry, persistent ownership index, or formula registry.
- Legacy 13D/G HTML or free-text parsing, arbitrary historical research, complete market-wide ownership state, or a public ownership-query API.
- Inferred group aggregates, fuzzy identity linkage, original-amendment accession inference, effective-version selection, or historical Feed lookup.
- Investment intent, activism, control, takeover, accumulation/distribution, importance, ranking, prediction, market impact, recommendation, or trading execution.
- New Providers, credentials, dependencies, Feed domains, public CLI operations, model runtime, or Agent orchestration.

## Decisions

### 1. Evolve SEC to Provider contract v4 while retaining Feed v4

Extend the explicit SEC supported-version set to `{1, 2, 3, 4}` and make production emit v4 only after configuration, manifest bounds, adapters, schema, semantic validation, fixtures, deadline, and compatibility tests are present. SEC v4 requires one of `form13f`, `form4`, or `beneficial_ownership`; existing v3 payloads retain their exact meaning under the compatibility reader.

Alternative considered: a new top-level `beneficial_ownership` payload type or Feed v5. Rejected because the evidence remains an SEC filing and Provider contract versioning already owns bounded semantic evolution.

### 2. Add an independent reporting-filer selection

Add a strict frozen `watched_beneficial_ownership_filers` configuration selection ordered by normalized CIK and embed it in `feed_config.snapshot`. Ship only Berkshire CIK `0001067983`. The configured name is audit metadata, not filing evidence.

Do not reuse `watched_companies`: that selection owns 13F completeness, while 13D/G has different acquisition, source-format, and request-budget guarantees. Do not use watched issuers: filer submissions are the bounded discovery authority available to this vertical slice and are not assumed to be a complete issuer-centric index of all third-party filings.

### 3. Select current events from official submissions by precise acceptance time

For each watched filer, validate every consumed aligned listing field, accession uniqueness, precise acceptance time, exact supported form, primary-document locator, and full advancing-window coverage. Select exact supported forms in `[window.start, cutoff)`, canonicalize by `(accepted_at, accession)`, and deduplicate identical accessions across filer units before document acquisition and output.

The manifest owns a closed maximum current-event count. Exceeding it fails before current-document requests; selection never truncates. Filing date, source row order, retrieval time, and blank report date do not replace acceptance-time eligibility.

Alternative considered: reuse the Form 4 selector or create a generic submissions selector. Rejected because form tokens, coverage evidence, document locators, historical traversal, and completeness outputs differ; small shared timestamp/URL primitives may be reused without creating a framework.

### 4. Admit only verified SEC-native structured XML

Create one Provider-specific beneficial-ownership pure core beside `sec_13f.py` and `sec_form4.py`. It performs no HTTP and contains distinct closed 13D and 13G document admission/parsing paths under manifest-declared namespaces, schema versions, and safe presentation-prefix-to-raw-archive locator rules.

Current unsupported format/schema is an acquisition failure. A nearest previous legacy/unsupported document is retained as a filing reference with `previous_format_unsupported` and no numeric comparison; it is never skipped for an older parseable filing. DTD/entity declarations, unexpected structures, duplicate scalar fields, unsupported mixed content, or source cross-check conflicts fail closed. Header credentials, CCC, addresses, phones, and signatures are admitted only as necessary structural input and never projected.

Alternative considered: parse rendered HTML or add a generic XML-to-facts layer. Rejected because it would broaden unverified source shapes and detach values from the form contract.

### 5. Keep one accession item with source-ordered ownership positions

One selected accession produces one item. Its payload retains exact form and schedule family, issuer, ownership class, amendment metadata, and source-ordered reporting positions. Each position owns its measured ownership facts; entries are not duplicated into one item per reporting person.

An explicit source CIK is the preferred reporting-position identity. When absent, exact NFC/whitespace-normalized source name is the conservative identity basis. The submissions filer CIK remains filing discovery identity and is not assigned to a cover-page person without a source relation. No alias or fuzzy matching is introduced.

Source-reported group membership may produce a canonical group member set only when the structured document explicitly supports it. Position values are never summed to manufacture a group aggregate. If membership or identity cannot be compared, the affected comparison is unavailable rather than `new` or `initial`.

Alternative considered: flatten one filing to one `reporting_entity` and one amount. Rejected because joint filings can report multiple positions with different values.

### 6. Resolve ownership-class identity conservatively

Use normalized source CUSIP when available. Otherwise use exact normalized source class title and record the fallback basis. If neither exists, retain current evidence but set comparison unavailable with `ownership_class_identity_unavailable`.

CUSIP differences are not bridged through title, ticker, corporate-action logic, or aliases. Equal CUSIP may compare despite display-title changes; title fallback compares exact normalized titles only. This prefers false-negative unavailability over a false ownership delta.

### 7. Represent required facts as typed nullable wrappers

`beneficially_owned_shares` and `ownership_percentage` wrappers are required for every position. Each wrapper contains closed status, canonical value or null, unit, reason, and document-local source-field references. Optional voting/dispositive power wrappers appear only when the source field exists.

Use `shares`, `percent`, and `percentage_points` units. Values reported as numeric are canonicalized through `MeasuredNumericFact`; shares and powers are nonnegative and percentages lie in `[0, 100]`. Missing source values remain null with a closed reason. The Producer never derives shares from percentage, percentage from shares/outstanding count, or any missing value from prose.

### 8. Use document-local Provider-specific source support

SEC-native XML does not provide a stable iXBRL fact-ID contract. Each measured field therefore carries a closed parser-defined locator such as `cover_page_reporting_person[0].class_percent` or `reporting_person[0].percent_of_class`. The ordinal comes from source order. The containing current/previous snapshot supplies accession, acceptance time, and official URL.

The locator vocabulary is form/schema-specific and validated; callers cannot provide arbitrary XPath. Derived deltas expose only the Provider-specific `current_minus_previous` descriptor. ECO-125 object references remain internal and are not serialized as a generic fact graph.

### 9. Resolve prior filings before matching positions

Comparable filing resolution has two stages:

1. find the nearest earlier distinct accession with the same official discovery filer CIK, issuer CIK, and ownership-class key;
2. inside that filing, match positions by explicit CIK or exact normalized source name.

Schedule family and amendment status do not enter the filing key, so 13D/13G transitions may compare source-reported numeric facts while retaining both exact forms. A prior filing with an unmatched person makes that position unavailable; it does not create a `new holder` claim.

`initial_filing` is allowed only after complete supported official history has been exhausted without a filing-level match. The non-amendment form alone never proves initial status.

Alternative considered: include schedule family in the key. Rejected because it would hide a directly comparable source-reported transition. Alternative considered: key discovery by reporting-person name. Rejected because submissions metadata does not supply all internal person identities.

### 10. Use one shared bounded reverse scan per acquisition run

Submissions metadata lacks subject issuer and class, so a candidate document must be parsed before comparability is known. Build one deterministic newest-first candidate stream from recent plus declared historical submissions metadata for the watched filer. Fetch each distinct candidate document at most once per run, index its parsed filer/issuer/class/positions immutably in memory, and reuse it across all unresolved current keys.

Stop when every key resolves, complete supported history is exhausted, or the manifest-owned total historical-candidate-document bound is reached. Bound exhaustion yields `history_candidate_bound_exhausted`; it does not fail the current item or prove initial status. A transport, URL, source-integrity, or supported-parser failure for an admitted required candidate remains Provider-incomplete rather than comparison-unavailable.

No cross-run semantic cache, database, historical Feed read, or checkpoint ownership index is introduced. The existing managed transport may cache/retry according to its current contract, but that is not semantic authority.

### 11. Calculate only exact source-supported deltas

Construct current and previous measured facts independently, then use ECO-125 subtraction for shares and percentage points. A delta exists only when both corresponding operands are reported and unit-compatible. Internal derivation metadata references the immutable input objects in current-then-previous order; payload validation recomputes the Provider-specific `current_minus_previous` result.

Initial, identity-unavailable, class-unavailable, history-bound, unsupported-previous, and missing-operand states retain null deltas. The Host Agent receives the arithmetic result but is not permitted to calculate or interpret one.

### 12. Keep amendments independent from comparison lineage

Project exact form, schedule family, `is_amendment`, and a source-supported amendment number when present. Do not infer `amends_accession`, original accession, effective/latest version, or merged state. `previous_comparable` means only prior ownership evidence under the comparison key and does not become amendment lineage.

Alternative considered: infer the original from the first earlier non-amendment filing. Rejected because ordering and similarity do not establish an accession relationship and cross-family history makes the claim more ambiguous.

### 13. Extend the one complete SEC slice

Append beneficial-ownership acquisition units after deterministic existing SEC units under the same `sec_edgar` Provider, managed client, rate scope, and outcome. Pre-snapshot validation requires exact configured 13F CIKs, exact selector-proven Form 4 accessions, and exact deduplicated beneficial-ownership accessions.

Whole-Provider replacement remains authoritative. History-only documents stay nested under current event evidence. An independently current-window previous accession may also be its own top-level event. Prior-window events are not unioned into the next slice. Any non-exempt incomplete SEC unit prevents publication without prior-slice fallback.

Alternative considered: a ninth Provider, subtype-specific persisted slices, or cross-window event union. Rejected because each would create another coverage/snapshot authority or unbounded history.

### 14. Pin request bounds and deadline before activation

First correct the regression baseline to include all v3 13F and Form 4 maximum successful-path sends. Then add beneficial-ownership listing, current document, declared history-file, and shared candidate-document maxima. Calculate the managed-send spacing floor from the unchanged resolved SEC minimum interval, add explicit bounded network headroom and commit reserve, and set `pre_commit_deadline_seconds` above that result. Static/config regression fails whenever selections, manifest bounds, rate policy, or deadline invalidate the inequality.

Concrete bounds and the resulting deadline are pinned atomically from verified Berkshire listings, accepted source variants, production-shaped fixtures, and the closed request formula before the v4 manifest activates. They are contract constants, not user-tunable runtime heuristics. The implementation may reuse an identical submissions response inside one run only when provenance and exact request accounting remain explicit; correctness and budget admission do not depend on that optimization.

Alternative considered: lower the SEC minimum interval, omit history, or depend on typical rather than maximum event counts. Rejected because each weakens rate safety or required evidence guarantees.

## Risks / Trade-offs

- [A busy filing window exceeds the current-event bound] -> Fail before document fetch and raise the contract only through a verified later change; never truncate.
- [Many unrelated historical 13D/G filings consume the candidate bound] -> Share one reverse scan across current keys and publish typed unavailable comparisons at the bound without claiming initial status.
- [Name-based identities change spelling] -> Require exact normalized matching and return `reporting_identity_not_comparable`; do not add aliases or fuzzy matching.
- [A nearest previous filing is legacy HTML] -> Preserve its accession/time/URL and return `previous_format_unsupported`; do not parse prose or skip backward.
- [13D and 13G structured schemas diverge or evolve] -> Keep separate manifest-pinned parsers and fixtures; unknown versions fail closed until explicitly added.
- [The longer global deadline affects operational scheduling] -> Derive the minimum acceptable value from the complete request shape, document the value, and retain pre-commit admission and non-cancellable commit semantics.
- [The existing v3 budget regression gives false confidence] -> Add a red characterization proving the omission, then pin v3 and v4 maximum send shapes before activation.
- [Nested previous evidence enlarges Feed items] -> Bound positions, source references, current events, historical candidates, response bytes, and total Feed bytes; fail rather than truncate semantic content.
- [Group evidence is ambiguous] -> Publish only explicit membership/aggregate fields and keep person positions separate; no inferred sum or control meaning.
- [A source document exposes sensitive filing metadata] -> Closed projection excludes CCC, credentials, addresses, phones and signatures, with negative schema/semantic tests.

## Migration Plan

1. Characterize the current SEC v3 compatibility bytes, mixed-slice behavior, and true maximum request shape; add failing coverage proving the existing budget test omits Form 4.
2. Add backward-readable SEC v4 schema/version dispatch, strict watched-filer configuration, manifest contract fields, and test-local closed bounds while production remains v3.
3. Verify and record supported 13D/13G source forms, namespaces, schema versions, locator prefixes, historical-file shape, safe raw URLs, and fixture provenance; pin the closed production constants.
4. Add the pure structured 13D/13G parser, identity/source-support model, comparison resolver, bounded shared reverse scan, and deterministic arithmetic tests.
5. Integrate beneficial-ownership units into the existing SEC outcome and exact mixed-slice validation, then set the verified deadline and activate SEC v4 atomically.
6. Run focused compatibility, acquisition, rate/deadline, schema, semantic, snapshot, determinism, provenance, documentation, and canonical identity checks followed by the repository quality gate and strict OpenSpec validation.

Rollback reverts the SEC manifest, configuration, deadline, schema, producer, validation, fixtures, and documentation together to v3. A v4-produced active bundle must not be consumed by a binary without v4 support; existing manifest-led deployment and bundle validation remain the compatibility gate. No checkpoint or persisted ownership-index migration is required.
