# Provider source verification

This file records what has been verified against the official upstream sources
for the two Providers whose checked-in fixtures are production-shaped, and what
has not. It is the evidence the `sec_edgar` and `cftc` manifest
`fixture_provenance` declarations point at.

Verification observations here are dated and are not a runtime source registry,
a claim that fixture values were recorded from live responses, or an expected
immutable hash for future retrieval.

## SEC Form 13F value unit

### Official authority inspected

- Agency: Securities and Exchange Commission.
- Final rule: *Electronic Submission of Applications for Orders Under the
  Advisers Act and the Investment Company Act, Confidential Treatment Requests
  for Filings on Form 13F, and Form ADV-NR; Amendments to Form 13F*.
- Release Nos. 34-95148; IA-6056; IC-34635.
- Federal Register: 87 FR 38943–38981, published 2022-06-30, document
  2022-13936.
- Metadata: <https://www.federalregister.gov/api/v1/documents/2022-13936.json> —
  HTTP 200.
- Full text inspected:
  <https://www.federalregister.gov/documents/full_text/text/2022/06/30/2022-13936.txt>
  — HTTP 200. The response contains the Government Publishing Office rule text
  in an HTML/pre wrapper.
- Human-readable entry:
  <https://www.federalregister.gov/documents/2022/06/30/2022-13936/electronic-submission-of-applications-for-orders-under-the-advisers-act-and-the-investment-company>
- SHA-256 of the retrieved full-text response bytes:
  `5cf4b4056b7cb036027ab1a3a3fce3d21f83aca963b1047ddfacf27bacb1c1cd`,
  observed 2026-09-15.

### Relevant passages

Section II.C.2.c, “Technical Amendments to Form 13F”:

> requiring all dollar values listed on Form 13F to be rounded to the nearest
> dollar, rather than to the nearest one thousand dollars as is currently
> required.

The same paragraph removes the requirement to omit “000”. Footnote 107 explains
that the old form reports a security worth $5 million as $5,000.

Section II.D, “Effective and Compliance Dates”:

> With respect to the amendments to Form 13F, the Commission is delaying the
> effective date of those amendments until January 3, 2023.

The section says all managers begin reporting on the amended version
simultaneously. Footnote 115 specifies:

> A manager must use the amended Form 13F for any filing made after the
> amendments become effective, regardless of whether the manager is filing an
> initial quarterly report on Form 13F or an amendment to a previously filed
> Form 13F filing.

### Contract consequence

The canonical output field remains `reported_value_usd_thousands`; it is
normalized evidence, not an assertion that every raw XML value was originally
in thousands.

| Official filing date | Source reported-value unit | Conversion to canonical USD thousands |
| --- | --- | --- |
| Before 2023-01-03 | USD thousands | identity |
| On/after 2023-01-03 | USD | exact division by 1000 |

The rule follows filing date, not holdings report period. An older report period
filed after the transition uses the new dollar unit. Source rounding prescribed
to filers is not permission for this Producer to round: the Producer preserves
the actual reported token and performs only exact unit conversion, aggregation,
and subtraction. No magnitude-based correction is permitted even if a filer
appears to have reported the wrong scale.

## SEC Form 4 ownership XML and archive locator

### Official authority and bounded contract

- Submissions listing endpoint template:
  `https://data.sec.gov/submissions/CIK<10-digit-CIK>.json`.
- Raw filing archive root:
  `https://www.sec.gov/Archives/edgar/data/<CIK>/<accession-without-dashes>/`.
- Observed 2026-09-16 from Berkshire Hathaway Form 4 accession
  `0001728451-26-000003`: the raw ownership XML is an unnamespaced
  `ownershipDocument` with a `<schemaVersion>X0609</schemaVersion>` child,
  `0`/`1` relationship and equity-swap booleans, root-level Section 16/Rule
  10b5-1 flags, and an `ownerSignature`; those non-evidence fields are admitted
  but not projected. The submissions `recent` arrays do not include a per-row
  CIK; their required top-level `cik` identifies every row. The same live
  listing has blank `reportDate` values for unrelated forms such as `SCHEDULE
  13G`; alignment, accession uniqueness, and acceptance timestamps are
  verified across the complete listing, while filing/report dates and the
  primary document are validated for selected exact Form 4 rows. It also has a
  historical acceptance-time inversion: `0001193125-22-183048` at
  `2022-06-27T22:31:38.000Z` precedes `0000899243-22-024236` at
  `2022-06-27T22:43:23.000Z`. Selection therefore derives coverage from the
  minimum precise acceptance time and canonicalizes selected rows rather than
  treating incidental source row order as a guarantee.
- Observed 2026-09-16 from historical Berkshire Form 4/A accession
  `0000919574-25-001652`: its `xslF345X05/ownership.xml` locator resolves to
  raw XML with schema `X0508`. It is intentionally unsupported: the closed v3
  contract admits only `X0609` and only the corresponding verified
  `xslF345X06` presentation prefix. A future prefix/schema requires an
  explicit contract change rather than runtime expansion.
- SEC ownership-document payloads are admitted only for that declared `X0609`
  shape. The checked-in parser rejects other schema versions, DTD/entity
  content, unknown structures, unsafe primary-document locators, and
  transformed HTML in place of raw XML.
- Form `4` and `4/A` are selected from the aligned `recent` listing by precise
  `acceptanceDateTime`; the Feed uses the official acceptance instant for source
  publication and knowledge time.

The Form 4 XML and submissions files under
`providers/sec_edgar/fixtures/form4/` are explicitly synthetic,
production-shaped fixtures. They verify the closed parser and projection
contract; they are not claims that the fixture values were downloaded from a
live filing. No complete live Form 4 document is copied into the repository,
and the Producer does not broaden support to unverified filing variants.

## SEC Schedule 13D/G beneficial-ownership source shape

### Official authority and dated observations

- Agency: Securities and Exchange Commission, EDGAR submissions API. The
  official listing template is
  `https://data.sec.gov/submissions/CIK<10-digit-CIK>.json`; the Berkshire
  listing for CIK `0001067983` was inspected on 2026-09-16.
- The complete aligned `recent` arrays use `form`, `filingDate`, `reportDate`,
  `accessionNumber`, `acceptanceDateTime`, and `primaryDocument`. Eligibility
  is based only on the precise `acceptanceDateTime`; `reportDate` may be blank
  on unrelated rows and is not used for ownership selection.
- Exact observed form tokens are `SCHEDULE 13D`, `SCHEDULE 13D/A`,
  `SCHEDULE 13G`, and `SCHEDULE 13G/A`. The inspection found 223 matching
  recent rows and an observed rolling 72-hour maximum of seven matching rows.
  These observations are the production-shaped basis for the closed current
  event bound; the runtime never truncates an over-bound listing.
- The listing declares one historical submissions file covering
  1998-08-10 through 2017-01-08. Historical metadata is therefore bounded by
  the declared file count and its aligned fields; it is not an open-ended
  historical archive.
- The structured source is SEC-native `edgarSubmission` XML with observed
  schema version `X0202`. The 13D and 13G structures are distinct and are
  admitted by separate form-specific contracts. Observed raw-document locator
  forms include `xslSCHEDULE_13G_X01/<basename>.xml` and
  `xslSCHEDULE_13G_X02/<basename>.xml`; no other prefix is implicitly allowed.
- Raw filing documents are derived from the official archive root
  `https://www.sec.gov/Archives/edgar/data/<CIK>/<accession-without-dashes>/`.
  The checked-in Schedule 13D/G documents are explicitly production-shaped
  fixtures, not downloaded filing copies; their values and namespaces do not
  claim live provenance.

### Contract consequences

The verified source observations pin the following closed v4 limits:

| Contract field | Pinned value | Basis |
| --- | ---: | --- |
| `max_filings_per_window` | 7 | observed Berkshire rolling 72-hour maximum, 2026-09-16 |
| `max_history_files` | 1 | declared Berkshire submissions history file |
| `max_historical_candidate_documents` | 64 | production-shaped bounded reverse-scan safety limit |
| `max_reporting_positions_per_filing` | 32 | production-shaped structured projection limit |
| structured schema versions | `X0202` | observed SEC-native `edgarSubmission` shape, 2026-09-16 |
| raw locator prefixes | `xslSCHEDULE_13G_X01`, `xslSCHEDULE_13G_X02` | observed archive locators, 2026-09-16 |

The 64-document and 32-position limits are explicitly labeled
production-shaped fixture contract limits rather than claims about an
unbounded EDGAR universe. Missing, extra, malformed, or changed manifest
values fail manifest resolution before Provider work. Current, historical,
and nested candidate acquisition remains fail-closed at every bound.

Every production contract claim above has either a dated official SEC URL or
an explicitly labeled production-shaped fixture basis. No runtime selection
uses a fixture as a source registry, and no unsupported namespace, schema
version, locator prefix, or legacy document format is accepted implicitly.

## CFTC Legacy Futures-Only row shape

Observed 2026-09-15 against the live dataset.

- Dataset endpoint: `https://publicreporting.cftc.gov/resource/6dca-aqww.json`
  — HTTP 200, no credentials.
- `report_date_as_yyyy_mm_dd` is a Socrata floating timestamp, serialized as
  `"2026-09-08T00:00:00.000"`. The latest report date observed was `2026-09-08`.
- The non-commercial spreading column is named **`noncomm_postions_spread_all`**
  — misspelled upstream (“postions”). `noncomm_positions_spread_all` **does not
  exist** in the dataset. `providers/cftc_cot.py` reads the official spelling
  first and keeps the corrected spelling only as a bounded alias.
- `$where=report_date_as_yyyy_mm_dd='2026-09-08'` matches rows; Socrata coerces
  the bare date literal, so the pinned-query predicate is valid as written.
- The per-row resource URL
  `https://publicreporting.cftc.gov/resource/6dca-aqww/<row-id>.json` returns
  HTTP 200 (observed for row id `930511001601F`). Each positioning item points
  at its own row URL rather than a shared dataset landing page, because Feed
  deduplication collapses same-URL records into one survivor.
- Row `id` values are opaque identifiers such as `26090886565AF`, and
  `cftc_contract_market_code` values may be alphanumeric (`86565A` as well as
  `088691`).
- `id`, `contract_market_name`, and `market_and_exchange_names` are all present
  on current rows.

## Verification limits

Direct requests to `https://www.sec.gov/files/form13f.pdf`,
`https://www.sec.gov/files/rules/final/2022/34-95148.pdf`, and
`https://www.sec.gov/divisions/investment/13ffaq` returned HTTP 403. The
official Federal Register copy supplies the verified regulatory
unit/effective-date basis; those SEC endpoints are not claimed to have been read
successfully.

No complete SEC filing or INFORMATION TABLE fixture was downloaded from EDGAR or
validated against a real submission. The SEC fixtures under
`providers/sec_edgar/fixtures/` are production-shaped and explicitly synthetic;
their namespace URIs are not claimed to be official. The regulatory unit
question is resolved and the SEC normalization contract in
`references/feed-contract.md` is authoritative, but the complete-submission
parser remains fail-closed on unsupported or ambiguous source shapes rather than
verified against every real document variant.

Fixture values in `providers/cftc/fixtures/cot-current.json`,
`cot-previous.json`, and `cot.json` are likewise synthetic. Only the column
names, value shapes, and row ordering are production-shaped and verified.

Do not broaden source support, weaken provenance, or present an unverified
fixture as verified.
