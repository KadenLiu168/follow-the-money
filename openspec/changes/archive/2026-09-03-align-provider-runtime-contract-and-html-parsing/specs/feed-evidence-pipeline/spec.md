## ADDED Requirements

### Requirement: Resolved Provider identity governs shared outbound requests
Every outbound request made through the shared Provider request boundary SHALL include the exact user-agent value from the owning resolved Provider contract. Provider-specific additional request headers SHALL be merged with that identity metadata, but no additional header declaration, including a differently cased user-agent field, SHALL replace or create a second authority for the resolved Provider user-agent. Existing host validation, redirect validation, request and response limits, timeout, retry classification, rate discipline, and credential-free behavior SHALL remain unchanged.

#### Scenario: Provider uses shared request boundary
- **WHEN** an enabled Provider sends a request through the shared request boundary
- **THEN** the outbound request contains the exact user-agent value from that Provider's resolved contract

#### Scenario: Provider supplies additional headers
- **WHEN** a Provider supplies request headers other than user-agent to the shared request boundary
- **THEN** those headers are preserved alongside the resolved Provider user-agent

#### Scenario: Additional headers attempt to replace identity
- **WHEN** Provider-specific headers contain a user-agent field in any letter case
- **THEN** the outbound request uses only the resolved Provider user-agent as identity authority

#### Scenario: SEC EDGAR request is issued
- **WHEN** the SEC EDGAR Provider sends its submissions request through the shared request boundary
- **THEN** its existing endpoint and descriptive resolved user-agent behavior remain valid

### Requirement: Shared HTML index date extraction isolates malformed candidates
Shared HTML index extraction SHALL retain the existing supported separated and compact Provider date formats and their deterministic candidate-source precedence. Within that precedence it SHALL select the first calendar-valid candidate, ignore invalid or unrelated date-like candidates, and continue evaluating later candidates for the same link when available. A link SHALL be promoted to a candidate evidence entry only when it has non-empty link text, a non-empty target, and a supported calendar-valid date. Ignored links SHALL NOT bypass existing URL validation, provenance, acquisition-window, or evidence-normalization rules.

#### Scenario: Production-shaped Provider link contains a valid date
- **WHEN** an HTML index link contains a supported calendar-valid date in an existing Provider URL or link-text format
- **THEN** extraction returns the same normalized UTC date and resolved candidate URL under the existing deterministic precedence

#### Scenario: Navigation link contains an invalid date-like token
- **WHEN** an unrelated navigation link contains a syntactically date-like token with an invalid month or day
- **THEN** extraction ignores that token without emitting an entry or allowing an uncategorized calendar-construction exception to escape

#### Scenario: Invalid candidate precedes a valid candidate
- **WHEN** a link contains multiple supported date-like candidates and an earlier candidate is calendar-invalid while a later candidate is calendar-valid
- **THEN** extraction deterministically selects the first calendar-valid candidate under the existing candidate-source precedence

#### Scenario: Link has no valid supported date
- **WHEN** a malformed or unrelated link contains no calendar-valid candidate in a supported date format
- **THEN** the link is ignored rather than promoted as evidence

#### Scenario: Genuine Provider acquisition fails
- **WHEN** Provider acquisition fails because of upstream blocking, throttling, timeout, network failure, undecodable content, or another existing typed failure condition
- **THEN** the Provider remains incomplete under existing retry and Feed failure semantics and prior evidence does not convert the run into success
