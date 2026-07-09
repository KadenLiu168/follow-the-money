# edgar-archive-url Specification

## Purpose
TBD - created by archiving change refactor-store-and-edgar-utils. Update Purpose after archive.
## Requirements
### Requirement: canonical archive base URL
The system SHALL provide `edgarArchiveUrl(cik, accession)` in `lib/edgar/archive-url.js` that returns `https://www.sec.gov/Archives/edgar/data/${cikNoPad}/${accNoDash}`, where `cikNoPad = String(parseInt(cik, 10))` and `accNoDash = accession.replace(/-/g, '')`.

#### Scenario: zero-padded CIK is normalized
- **WHEN** `edgarArchiveUrl('0001067983', '0001067983-26-000123')` is called
- **THEN** it MUST return `https://www.sec.gov/Archives/edgar/data/1067983/000106798326000123`

#### Scenario: already-unpadded CIK is unchanged
- **WHEN** `edgarArchiveUrl('1067983', '0001067983-26-000123')` is called
- **THEN** it MUST return `https://www.sec.gov/Archives/edgar/data/1067983/000106798326000123`

### Requirement: document URL derivation
The system SHALL provide `edgarDocUrl(cik, accession, fileName)` in `lib/edgar/archive-url.js` that returns `${edgarArchiveUrl(cik, accession)}/${fileName}`.

#### Scenario: doc url appends file name
- **WHEN** `edgarDocUrl('0001067983', '0001067983-26-000123', 'form13fInfoTable.xml')` is called
- **THEN** it MUST return `https://www.sec.gov/Archives/edgar/data/1067983/000106798326000123/form13fInfoTable.xml`

### Requirement: callers use the URL helper
`lib/edgar/fetch-thirteen-f-xml.js` and `lib/aggregate/pipeline-b.js` MUST construct EDGAR archive/base/doc URLs via `edgarArchiveUrl` / `edgarDocUrl` and MUST NOT inline `cikNoPad` / `accNoDash` / `baseUrl` construction.

#### Scenario: no inline URL construction in callers
- **WHEN** `fetch-thirteen-f-xml.js` and `pipeline-b.js` are inspected
- **THEN** they MUST import the helpers from `lib/edgar/archive-url.js` and MUST NOT contain a local `baseUrl = .../edgar/data/${cikNoPad}/${accNoDash}` template literal

