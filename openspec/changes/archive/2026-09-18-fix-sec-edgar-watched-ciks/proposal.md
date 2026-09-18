# Change: fix-sec-edgar-watched-ciks

## Why

`generate-feed #66` failed with `sec_edgar` HTTP 404 from `data.sec.gov` and
`deficient coverage groups: us_company_filings`. The direct cause is that 6 of 8
`watched_companies` CIKs in `config/config.yaml` are wrong: 2 point to nonexistent
CIKs (HTTP 404) and 4 point to unrelated SEC entities. SEC v4 acquires per watched
company in sorted-CIK order, so the first wrong CIK (Oaktree `0000926522`) 404s and
fails the complete SEC slice; under the accepted complete-slice fail-closed
semantics this makes `us_company_filings` deficient and the Feed unpublishable. SEC
is the sole `us_company_filings` Provider; BLS is already handled as a blocked-exempt
degradation and is not in scope. The Feed is currently not publishable.

## What Changes

- Correct 6 `watched_companies` CIKs in `config/config.yaml` to verified SEC
  identities (Berkshire `0001067983` and Pershing Square `0001336528` are already
  correct and unchanged). The 6 corrections, verified against the official SEC
  submissions API (`https://data.sec.gov/submissions/CIK<cik>.json`):

  | Entity | Wrong CIK | Verified CIK | SEC API name |
  |---|---|---|---|
  | Oaktree Capital Management | `0000926522` (404) | `0000949509` | OAKTREE CAPITAL MANAGEMENT LP |
  | Baupost Group | `0001535213` (Littel Christopher J.) | `0001061768` | BAUPOST GROUP LLC/MA |
  | Coatue Management | `0001098249` (ANNUITYNET INSURANCE AGENCY) | `0001135730` | COATUE MANAGEMENT LLC |
  | Tiger Global Management | `0001160822` (404) | `0001167483` | TIGER GLOBAL MANAGEMENT LLC |
  | Scion Asset Management | `0001539579` (Bien Janet Lynn) | `0001649339` | Scion Asset Management, LLC |
  | ARK Investment Management | `0001499575` (Scorpion-Remmel Trust 2010) | `0001697748` | ARK Investment Management LLC |

  The existing list order is preserved; runtime acquisition already sorts by CIK, so
  no config-level ordering change is needed.
- Tighten `_parse_watched_companies` in `src/follow_the_money/config/load.py` to
  reject non-ten-digit and duplicate CIKs (fail closed), matching the existing
  `watched_form4_issuers` and `watched_beneficial_ownership_filers` validation. No
  ordering enforcement is added: the SEC v2 acquisition requirement already mandates
  deterministic CIK order in the embedded snapshot and runtime `sorted()` delivers it.
- Record SEC identity verification evidence in `references/provider-source-verification.md`,
  citing the official submissions API as the verification source for each watched
  company CIK.
- Add regression tests: a shipped watched-CIK exact-set regression that fails if any
  shipped CIK drifts, and config-validation regressions for non-ten-digit and
  duplicate CIKs.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `feed-evidence-pipeline`: tighten the SEC 13F watched-company configuration
  requirement so that malformed or duplicate CIKs fail closed at static resolution,
  matching the existing Form 4 and beneficial-ownership filer validation.

## Impact

- `config/config.yaml`: 6 CIK value corrections.
- `src/follow_the_money/config/load.py`: `_parse_watched_companies` format/duplicate
  checks.
- `references/provider-source-verification.md`: SEC identity evidence.
- `tests/`: shipped CIK exact-set + config-validation regressions.
- No SEC producer URL logic, no `validate.py` source-link regex, no digest or
  canonical-bytes change. SEC complete-slice fail-closed semantics, coverage policy,
  and the eight-Provider evidence-only boundary are unchanged.
