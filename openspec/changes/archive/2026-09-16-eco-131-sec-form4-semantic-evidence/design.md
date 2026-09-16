## Context

See `proposal.md` for motivation and `specs/feed-evidence-pipeline/spec.md` for observable requirements.

The current logical Feed is schema major v4 with five domains and eight required Providers. SEC EDGAR contract v2 is a complete 13F current-state slice: production builds one `SecEdgarAdapter` acquisition unit per watched 13F company, accumulates all units into one `sec_edgar` outcome, validates exact watched-CIK equality, and applies whole-Provider complete-state replacement. The filing JSON Schema is closed and its v2 semantic validator assumes every SEC item is a 13F-HR item.

ECO-125 intentionally added only internal numeric measured/derived facts and owned-context decimal operations. It did not create a generic identity, text, time, relationship, comparison, or serialized fact graph. Form 4 must therefore remain a third Provider-specific vertical slice while reusing only the proven numeric boundary.

The SEC submissions endpoint exposes issuer-associated Form 4 rows with precise acceptance times, accession numbers, and a `primaryDocument`. Current Berkshire rows may include an XSL presentation prefix such as `xslF345X06/primary_doc.xml`; fetching that path returns transformed HTML, while the same basename under the accession archive root is the official raw ownership XML. Current disseminated ownership XML reports schema version `X0609`. Both raw-source derivation and accepted schema versions must be closed and verified rather than guessed from content.

## Goals / Non-Goals

**Goals:**

- Add one bounded, credential-free Form 4 acquisition unit per configured issuer while retaining one logical SEC Provider outcome and the existing managed per-send guarantees.
- Prove complete current-window selection before treating no Form 4 as an empty sub-slice.
- Parse complete supported ownership XML into a closed structured payload without losing owner relationships, table entry kinds, footnote support, or source ordering.
- Preserve SEC v1/v2 read compatibility, existing 13F semantics, deterministic Feed identity, and whole-Provider publication guarantees.
- Reuse the ECO-125 numeric fact boundary without extending it into a generic semantic architecture.

**Non-Goals:**

- A generic filing parser, semantic graph, entity-reference system, formula registry, or cross-form framework.
- Form 3, Form 5, 13D/G, 8-K, 10-Q, 10-K, or Form 4 historical search.
- Amendment-to-accession resolution, effective-version selection, history merging, or historical Feed lookup.
- Reporting-owner address publication, insider-trading analysis, transaction valuation, holding deltas, signals, ranking, recommendations, or trading execution.
- Historical submissions-file traversal or support for an unbounded issuer universe.

## Decisions

### 1. Evolve SEC to Provider contract v3 while retaining Feed v4

Extend the explicit supported-version map to `sec_edgar: {1, 2, 3}` while leaving CFTC at `{1, 2}` and every other Provider at `{1}`. The checked-in SEC manifest moves to v3 only in the same implementation unit as working Form 4 acquisition, schema, validation, fixtures, configuration, and compatibility tests.

Under SEC v3 every SEC payload has a required discriminator:

```text
filing_subtype = form13f | form4
```

The existing 13F producer adds `form13f` without otherwise changing its semantic payload. The v3 validator dispatches by subtype. The v1 path remains legacy filing validation, and the v2 path remains the exact existing 13F contract without requiring the new discriminator.

Alternative considered: change SEC v2 in place. Rejected because valid published v2 bundles would acquire a new meaning and fail bounded compatibility.

Alternative considered: Feed v5 or a new evidence domain. Rejected because both shapes are filing evidence and Provider contract versioning already owns bounded semantic evolution.

### 2. Add a separate authoritative watched-issuer selection

Add a narrow frozen `WatchForm4Issuer` configuration value with normalized CIK and selection/audit name. `AppConfig` carries `watched_form4_issuers` separately from `watched_companies`; the strict loader requires both fields and rejects unknown keys, malformed CIKs, duplicates, or unsupported members. Shipped configuration contains only Berkshire Hathaway CIK `0001067983`.

Embed the ordered selection in `feed_config.snapshot`, so configuration identity and independent SEC v3 validation can prove issuer membership. Published issuer identity still comes from ownership XML; the configured name is not substituted into evidence.

Alternative considered: reuse `watched_companies`. Rejected because most current entries are 13F managers rather than the intended Form 4 issuer universe and the two selections have different completeness semantics.

### 3. Keep one SEC Provider with deterministic acquisition units

Production adapter construction retains the existing 13F units in CIK order, then appends one `SecForm4Adapter` unit per watched Form 4 issuer in CIK order. Every unit uses `provider_id = sec_edgar`, the same resolved contract, managed client and durable rate scope, and contributes to the existing single outcome. Units remain sequential under the current Provider loop.

A Form 4 unit performs:

1. one submissions request;
2. pure listing validation and selection;
3. zero to twenty raw ownership-XML requests in `(accepted_at, accession_number)` order;
4. pure normalization of every selected filing.

A failure in any unit leaves earlier accepted SEC items available only as failed-candidate diagnostics and makes the Provider incomplete. Existing progress-aware blocked semantics remain authoritative: denial after successful 13F or listing/XML progress is partial and non-exempt.

Alternative considered: a ninth Provider or one outcome per issuer. Rejected because the production Provider set, coverage and rate authority are closed at eight and SEC provenance remains one source.

### 4. Use recent-only selection with explicit coverage proof

Add a pure Form 4 listing selector that validates all fields it consumes as aligned arrays, requires unique accessions, and parses every precise acceptance timestamp. The live `recent` source contains historical acceptance-time inversions, so source row order is not treated as a coverage or ordering guarantee. The selector proves coverage only when the minimum represented acceptance time is at or before `window.start`, then canonically orders selected exact `4` and `4/A` rows by `(accepted_at, accession_number)`; all other forms are ignored only after listing completeness is established.

The SEC v3 manifest owns a closed Form 4 section containing:

```text
max_filings_per_window: 20
ownership_xml_schema_versions: [X0609]
```

Manifest resolution requires these exact supported entries for v3 and rejects them for legacy versions or other Providers. Selection fails before XML requests when the eligible count exceeds 20. It never truncates. Runtime deadline admission remains authoritative for every actual send.

Alternative considered: traverse `filings.files`. Rejected for this first one-issuer, maximum-72-hour slice because the current 1,000-row Berkshire recent listing covers years; explicit coverage proof safely fails if that assumption ceases to hold.

### 5. Derive and validate the official raw XML URL narrowly

Treat the submissions `primaryDocument` as a source locator, not as bytes known to be XML. Accept only a basename or the verified single XSL presentation-directory prefix followed by a safe basename; reject credentials, absolute paths, dot segments, unexpected nesting, empty names, and non-XML names. Construct the raw source URL beneath:

```text
https://www.sec.gov/Archives/edgar/data/<issuer-cik>/<accession-without-dashes>/<basename>
```

The raw URL must pass the resolved SEC fetch and source-link rules. The returned body must be admitted as supported XML, have root `ownershipDocument`, declare an allowed manifest-owned schema version, and cross-check exact form, issuer CIK, accession-context metadata, and selected submissions row dates where both sources supply them. The item source URL is this official raw XML URL, not transformed HTML or the submissions endpoint.

Alternative considered: parse the XSL-rendered HTML. Rejected because it loses the machine contract and field-level footnote structure.

Alternative considered: extract ownership XML from the complete submission text. Rejected because the verified raw primary document is smaller and requires one resource rather than an additional container parser.

### 6. Implement a Provider-specific pure Form 4 core

Add `providers/sec_form4.py` beside `sec_13f.py`. It performs no HTTP and owns small frozen raw/normalized records, listing selection, safe source metadata checks, XML parsing, Form 4 semantics, entry identity, and payload projection support. Do not add `semantic/filing`, a generic fact base class, an entity resolver, or a shared filing comparator.

Use standard-library XML parsing after bounded transport decoding. Reject DTD/entity declarations and unsupported element/content shapes rather than allowing external lookup or preserving unknown XML. Namespace handling may accept the verified ownership-document namespace shape but must not select nodes by unrestricted descendant-name search when that could hide duplicates or unexpected structure.

Alternative considered: place issuer/owner/transaction objects in the ECO-125 semantic package. Rejected because that package's accepted contract is numeric-only and Provider meaning remains SEC-specific.

### 7. Preserve the SEC table model instead of flattening facts

The public Form 4 portion of the filing payload is a closed nested structure:

```text
issuer
reporting_owners[]
non_derivative_entries[]
derivative_entries[]
footnotes[]
remarks
amendment
```

Each table array retains the mixed XML order of transaction and standalone holding entries. Every entry carries `entry_kind`, zero-based `source_ordinal`, `entry_id`, and only the fields applicable to that kind/table. Transaction post-state and ownership nature remain nested in the same entry, avoiding dangling references. Multiple reporting owners describe the filing; entries are not duplicated per owner and no absent owner-to-entry edge is invented.

Relationship booleans normalize absent XML elements to false, require at least one true, and retain `officer_title` and `other_text` separately. Reporting-owner addresses and signatures are not projected. Issuer and owner names are required from disseminated XML for this production contract; missing identities fail rather than trigger another lookup.

Alternative considered: flat `facts[]` with IDs and references. Rejected because it adds a semantic graph solely to reconstruct relationships already present in one bounded filing.

### 8. Reuse numeric facts only for measured source values

For every numeric XML value, create a `MeasuredNumericFact` from raw with Provider-local source-field support and the closed unit selected by the XML branch. Project its canonical value/unit into the Form 4 payload; do not serialize internal fact metadata. No shared derivation is required because ECO-131 calculates no transaction value or holding delta.

Represent SEC choices explicitly:

```text
transaction amount: shares | total_value
post-transaction amount: shares | value
underlying amount: shares | value
```

Use `shares`, `usd`, and `usd_per_share` units as specified. Optional value wrappers always carry `value`, `unit`, and ordered `footnote_ids`; null is accepted only for the SEC optional-with-footnote shapes with actual support. Direct/indirect ownership remains a closed code projected to descriptive wire values, and indirect ownership requires nature text.

Alternative considered: publish raw numbers or Python floats. Rejected because both bypass the existing canonical numeric contract.

### 9. Make footnotes first-class bounded evidence support

Parse the filing-level footnote table into unique `F1`-`F99` records. Extract plain text deterministically from schema-supported mixed text, normalize NFC and whitespace, reject unsupported child markup, and require at most 4,000 code points per footnote. Sort records and every field reference list by numeric ID. Resolve all references after parsing; dangling or malformed references fail. Preserve unreferenced valid footnotes because they remain filing evidence. Retain `remarks` independently under the official 2,000-character bound.

Do not move footnote text into `raw_metadata`, summarize it, or combine field references at entry level. A null numeric supported by a footnote remains null; footnote prose is never parsed into a numeric replacement.

Alternative considered: retain IDs only. Rejected because a current Feed consumer could not inspect the support for a null or qualified value.

### 10. Keep accession identity and position-based entry identity separate

The top-level item ID continues the existing pattern:

```text
stable_item_id("sec_edgar", accession_number)
```

Derive entry IDs from a canonical tuple of accession, table kind, and source ordinal. Do not include owner CIK, names, transaction values, security titles or entry kind. The entry kind is validated content: a corrected same-position value changes canonical bytes without silently creating another entry identity.

Canonical assembly orders owners by CIK, tables non-derivative then derivative, entries by source ordinal, and footnotes/references numerically. It does not sort transactions by code, date, security or amount. Item order remains the existing global `(knowledge_available_at, id)` order.

### 11. Treat amendments as independent source events

For Form `4`, emit `is_amendment = false` and null `date_of_original_submission`. For exact `4/A`, require the XML field and emit `is_amendment = true`. Do not emit `amends_accession`: the official ownership XML supplies an original-submission date but not an accession, and date/issuer/owner matching can be ambiguous.

No source outside the current advancing window is fetched for amendment resolution. If original and amended filings both fall inside the window, both remain independent items. Snapshot selection does not designate one effective.

Alternative considered: infer a unique original accession. Rejected because it turns matching policy into filing evidence and expands the slice into a history resolver.

### 12. Validate and replace the complete mixed SEC v3 slice

Before snapshot selection, partition current SEC v3 items by `filing_subtype`. Reuse the existing v2 13F validator after requiring `form13f`, and require exact configured watched-company CIK equality. Validate each `form4` item and require its issuer in the watched issuer set, accession uniqueness, and equality with the complete selector result accumulated by the acquisition units.

Treat SEC v3 as a complete-state admission for the whole produced slice: all 13F current state plus exactly the current-window Form 4 events. The existing exact identity-set/content equality rule then has the desired behavior. An identical no-event run may carry the prior v3 SEC slice; a newly added event replaces it; and an event from a prior window is removed when the complete current identity set no longer contains it. There is no cross-run union or per-subtype persisted snapshot.

Alternative considered: independently carry the 13F sub-slice and merge Form 4 events. Rejected because it creates a second snapshot authority and risks unbounded history.

### 13. Keep fixtures authoritative and scoped

Place recorded or production-shaped Provider fixtures under `providers/sec_edgar/fixtures/form4/` so the SEC manifest can name their provenance. Cover purchase, sale, award, amendment, multiple mixed transactions, derivative transaction, standalone holdings, multiple owners, footnotes/null values, and listing coverage. Synthetic malformed/boundary fixtures may live with focused tests when they are clearly labeled and need not claim recorded provenance.

Pin representative canonical item bytes before broader integration. Tests must also mutate each material semantic field, permute only inputs whose order is non-semantic, vary ambient decimal context, and exercise old SEC v1/v2 bundle reads.

## Risks / Trade-offs

- [SEC changes the submissions XSL prefix or ownership schema version] -> Keep both declarations in the verified v3 manifest and fail static/source validation until fixtures and parser support are deliberately updated.
- [The recent listing no longer covers the maximum window] -> Fail closed and add historical traversal only through a later contract change; never infer empty coverage.
- [A busy issuer exceeds 20 filings] -> Fail without truncation; the one-issuer production selection and manifest bound preserve deadline headroom.
- [The additional SEC requests approach the command deadline] -> Keep units sequential under the shared SEC rate scope, perform count/coverage checks before XML requests, and let every send pass existing deadline admission.
- [XML optionality and footnote-only fields are mistaken for absent evidence] -> Use explicit value wrappers and field-level references, production-shaped fixtures, and closed nullability validation.
- [Position-based entry identity changes when SEC reorders a filing] -> An accession is treated as an immutable source document; a same-accession source correction retains positional identity but changes canonical content and Feed identity.
- [Mixed current-state and event semantics complicate carry-forward] -> Validate the complete current SEC v3 slice before the existing exact-set whole-slice gate; do not introduce independent histories.
- [Footnote text increases bundle size] -> Enforce per-footnote, per-filing entry, response and existing total serialized Feed bounds; fail rather than truncate.

## Migration Plan

1. Add backward-readable v3 schema definitions, supported-version dispatch, strict configuration/manifest fields, and compatibility tests while production remains SEC v2.
2. Add Form 4 pure-core characterization and parser tests, including official-source verification and canonical-byte fixtures.
3. Integrate the watched-issuer acquisition units through the existing managed client and one SEC outcome; verify request bounds, progress semantics, and complete-window failure behavior.
4. Add SEC v3 subtype completeness and whole-slice snapshot validation, then activate the SEC v3 manifest atomically with Berkshire configuration and all working producer paths.
5. Update affected Feed/provider/semantic documentation and run focused regressions, the canonical quality gate, OpenSpec doctor, and strict change/all-spec validation.

Rollback reverts the SEC manifest, configuration, schema, producer, validation, tests and documentation together to v2. A v3-produced active bundle must not be consumed by a binary lacking v3 support; existing manifest-led deployment and validation ordering remains the compatibility gate. No checkpoint or persisted snapshot migration is required.
