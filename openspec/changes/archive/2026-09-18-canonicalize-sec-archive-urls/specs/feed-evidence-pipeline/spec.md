## ADDED Requirements

### Requirement: SEC source URLs use canonical CIK representation per locator

SEC EDGAR uses two distinct canonical CIK representations in its verified
locators. The submissions API URL SHALL use the ten-digit zero-padded CIK
(`https://data.sec.gov/submissions/CIK<ten-digit>.json`). Every Archive source
URL SHALL use the unpadded integer CIK in the path
(`https://www.sec.gov/Archives/edgar/data/<integer>/...`). A single
canonicalization helper SHALL derive the unpadded integer form from a normalized
ten-digit CIK, SHALL require a ten-digit input, and SHALL fail closed on malformed
input. The producer source-link contract and the Feed validator source-link
contract SHALL agree on the same canonical form for Archive URLs; neither side
SHALL independently accept the padded form in an Archive path. Submissions and
Archive URL construction SHALL NOT be duplicated across 13F, Form 4, and
Schedule 13D/G paths.

#### Scenario: Submissions URL uses padded CIK

- **WHEN** the SEC submissions API URL is constructed for a watched company
- **THEN** the URL is `https://data.sec.gov/submissions/CIK<ten-digit>.json` with
  the zero-padded CIK

#### Scenario: Archive URL uses unpadded integer CIK

- **WHEN** an SEC Archive source URL is constructed for a 13F complete submission,
  a Form 4 primary document, or a Schedule 13D/G current or historical document
- **THEN** the Archive path uses the unpadded integer CIK
  (`/Archives/edgar/data/<integer>/...`) and the URL is the SEC canonical locator,
  not a redirecting alias

#### Scenario: Producer and validator contracts agree

- **WHEN** a Form 4 or beneficial-ownership item is normalized and validated
- **THEN** both the producer-constructed source URL and the validator source-link
  regex require the unpadded integer CIK in the Archive path, and an item carrying a
  padded Archive URL fails validation

#### Scenario: Canonicalization helper rejects malformed CIK

- **WHEN** the canonicalization helper receives a CIK that is not a normalized
  ten-digit decimal string
- **THEN** it fails closed with a typed schema error and no Archive URL is emitted

#### Scenario: URL form change is reflected in digest identity

- **WHEN** an SEC Archive source URL changes from the padded form to the unpadded
  canonical form
- **THEN** the affected item's `DigestContext` projection and the Feed
  `content_digest` change by design, while `stable_item_id` (derived from
  `provider_id + accession`) and dedupe behavior remain stable
