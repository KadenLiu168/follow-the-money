# SEC 13F value-unit verification

## Official authority inspected

Retrieved on 2026-09-15 during the stage-1 repair. This is planning evidence, not a runtime source registry or a claim that new filing fixtures have already been captured.

- Agency: Securities and Exchange Commission.
- Final rule: *Electronic Submission of Applications for Orders Under the Advisers Act and the Investment Company Act, Confidential Treatment Requests for Filings on Form 13F, and Form ADV-NR; Amendments to Form 13F*.
- Release Nos. 34-95148; IA-6056; IC-34635.
- Federal Register: 87 FR 38943–38981, published 2022-06-30, document 2022-13936.
- Metadata: https://www.federalregister.gov/api/v1/documents/2022-13936.json — HTTP 200.
- Full text inspected: https://www.federalregister.gov/documents/full_text/text/2022/06/30/2022-13936.txt — HTTP 200. The response contains the Government Publishing Office rule text in an HTML/pre wrapper.
- Human-readable entry: https://www.federalregister.gov/documents/2022/06/30/2022-13936/electronic-submission-of-applications-for-orders-under-the-advisers-act-and-the-investment-company
- SHA-256 of the retrieved full-text response bytes: `5cf4b4056b7cb036027ab1a3a3fce3d21f83aca963b1047ddfacf27bacb1c1cd`. This records this observation, not an expected immutable hash for future network retrieval.

## Relevant passages

Section II.C.2.c, “Technical Amendments to Form 13F”:

> requiring all dollar values listed on Form 13F to be rounded to the nearest dollar, rather than to the nearest one thousand dollars as is currently required.

The same paragraph removes the requirement to omit “000”. Footnote 107 explains that the old form reports a security worth $5 million as $5,000.

Section II.D, “Effective and Compliance Dates”:

> With respect to the amendments to Form 13F, the Commission is delaying the effective date of those amendments until January 3, 2023.

The section says all managers begin reporting on the amended version simultaneously. Footnote 115 specifies:

> A manager must use the amended Form 13F for any filing made after the amendments become effective, regardless of whether the manager is filing an initial quarterly report on Form 13F or an amendment to a previously filed Form 13F filing.

## Contract consequence

The canonical output field remains `reported_value_usd_thousands`; it is normalized evidence, not an assertion that every raw XML value was originally in thousands.

| Official filing date | Source reported-value unit | Conversion to canonical USD thousands |
| --- | --- | --- |
| Before 2023-01-03 | USD thousands | identity |
| On/after 2023-01-03 | USD | exact division by 1000 |

The rule follows filing date, not holdings report period. An older report period filed after the transition uses the new dollar unit. Source rounding prescribed to filers is not permission for this Producer to round: the Producer preserves the actual reported token and performs only exact unit conversion, aggregation and subtraction.

Design Decision 6 specifies the closed manifest entries, typed current/previous normalization descriptors, matched filing-date provenance, canonical numeric bounds and unsupported-format failures. Tests cover the transition date, late filing, cross-transition comparison and conflicting authority. No magnitude-based correction is permitted even if a filer appears to have reported the wrong scale.

## Verification limits and implementation gate

Direct requests to `https://www.sec.gov/files/form13f.pdf`, `https://www.sec.gov/files/rules/final/2022/34-95148.pdf`, and `https://www.sec.gov/divisions/investment/13ffaq` returned HTTP 403. The official Federal Register copy supplies the verified regulatory unit/effective-date basis; those SEC endpoints are not claimed to have been read successfully.

## CFTC Legacy Futures-Only row shape

Retrieved on 2026-09-15 during the stage-3 post-implementation review. This is the verification Task 5.5 required and that was previously missing.

- Dataset endpoint: `https://publicreporting.cftc.gov/resource/6dca-aqww.json` — HTTP 200, no credentials.
- `report_date_as_yyyy_mm_dd` is a Socrata floating timestamp, serialized as `"2026-09-08T00:00:00.000"`. The latest report date observed was `2026-09-08`.
- The non-commercial spreading column is named **`noncomm_postions_spread_all`** — misspelled upstream ("postions"). `noncomm_positions_spread_all` **does not exist** in the dataset. The earlier implementation read only the corrected spelling and therefore failed closed on every real row; the checked-in fixtures had reproduced the corrected spelling rather than the official one. Both are now aligned with this observation.
- `$where=report_date_as_yyyy_mm_dd='2026-09-08'` matches rows; Socrata coerces the bare date literal, so the pinned-query predicate is valid as written.
- The per-row resource URL `https://publicreporting.cftc.gov/resource/6dca-aqww/<row-id>.json` returns HTTP 200 (observed for row id `930511001601F`). Row `id` values are opaque identifiers such as `26090886565AF`, and `cftc_contract_market_code` values may be alphanumeric (`86565A` as well as `088691`).
- `id`, `contract_market_name`, and `market_and_exchange_names` are all present on current rows.

Fixture values in `providers/cftc/fixtures/cot-current.json`, `cot-previous.json`, and `cot.json` remain synthetic. Only the column names, value shapes, and row ordering are production-shaped and verified here.

## Verification limits and implementation gate

Direct requests to `https://www.sec.gov/files/form13f.pdf`, `https://www.sec.gov/files/rules/final/2022/34-95148.pdf`, and `https://www.sec.gov/divisions/investment/13ffaq` returned HTTP 403. The official Federal Register copy supplies the verified regulatory unit/effective-date basis; those SEC endpoints are not claimed to have been read successfully.

No complete SEC filing/INFORMATION TABLE fixture was downloaded or validated in this repair. Task 4.3 must verify supported source shape, CIK/accession/form/filing-date agreement, and truthful recorded/synthetic fixture provenance before Task 4.7 activates the SEC v2 manifest. The regulatory unit question is resolved; runtime parser/fixture verification remains a normal explicit implementation gate. Unsupported non-XML historical tables remain fail-closed under the original bounded XML design. Do not broaden source support, weaken provenance, or mark unverified fixtures as verified to complete that gate.
