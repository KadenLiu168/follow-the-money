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
- Metadata: https://www.federalregister.gov/api/v1/documents/2022-13936.json —
  HTTP 200.
- Full text inspected:
  https://www.federalregister.gov/documents/full_text/text/2022/06/30/2022-13936.txt
  — HTTP 200. The response contains the Government Publishing Office rule text
  in an HTML/pre wrapper.
- Human-readable entry:
  https://www.federalregister.gov/documents/2022/06/30/2022-13936/electronic-submission-of-applications-for-orders-under-the-advisers-act-and-the-investment-company
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
