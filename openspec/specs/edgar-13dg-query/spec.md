# edgar-13dg-query Specification

## Purpose
TBD - created by archiving change fix-edgar-13dg-query. Update Purpose after archive.
## Requirements
### Requirement: Use EDGAR `startdt`/`enddt` date params
When `fetchThirteenDGSearch` builds the EDGAR `search-index` URL, it MUST use `startdt`/`enddt` (with `YYYY-MM-DD` format), NOT `startDate`/`endDate`. EDGAR silently ignores `startDate`/`endDate`, which collapses the date window and returns the full filing history.

#### Scenario: Wrong params are ignored (spike-confirmed)
- **WHEN** the URL uses `startDate`/`endDate` with `dateRange=custom`
- **THEN** EDGAR ignores them and returns the unfiltered history (response identical to sending no date params)

#### Scenario: Correct params constrain the window
- **WHEN** the URL uses `startdt`/`enddt` with `dateRange=custom`
- **THEN** only filings whose `file_date` falls in the window are returned

### Requirement: Query 13D/G via `q=` full-text for recent coverage
`fetchThirteenDGSearch` MUST query with `q="<formType>"` (the full-text query), NOT `forms=SC 13D`. The `forms=` facet combined with `dateRange=custom` returns 0 hits for 2025+ filings, which would silently drop all recent 13D/G ingestion.

#### Scenario: `forms=` fails for recent filings
- **WHEN** the URL uses `forms=SC 13D` + `dateRange=custom` for a 2025+ window
- **THEN** it returns 0 hits (reproducible across 2025 and 2026)

#### Scenario: `q=` returns recent filings
- **WHEN** the URL uses `q="SC 13D"` + `startdt`/`enddt` for a 2026 window
- **THEN** it returns the expected recent filings

### Requirement: Filter results by `root_forms`
`fetchThirteenDGSearch` SHALL drop any returned hit whose `_source.root_forms` is neither the requested `formType` nor its `SCHEDULE` alias. This removes `q=` noise (e.g. `SC TO-T`) before results reach the ingest pipeline.

#### Scenario: Noise is dropped
- **WHEN** a hit has `root_forms: ["SC TO-T"]` and `formType` is `SC 13D`
- **THEN** that hit is excluded from the result

#### Scenario: Legitimate form and its SCHEDULE alias are kept
- **WHEN** a hit has `root_forms: ["SC 13D"]` or `root_forms: ["SCHEDULE 13D"]` and `formType` is `SC 13D`
- **THEN** that hit is included in the result

