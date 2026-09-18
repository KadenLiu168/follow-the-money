## ADDED Requirements

### Requirement: SEC 13F INFORMATION TABLE recognition is XML namespace neutral

The SEC 13F complete-submission parser SHALL identify the INFORMATION TABLE
document by XML semantics: a candidate XML document SHALL be recognized as the
INFORMATION TABLE when its root element's local name is `informationTable`.
The XML namespace binding form SHALL NOT alter semantic recognition. A valid
INFORMATION TABLE using no namespace, a default namespace, or any namespace
prefix (for example `ns1`, `sec`, or any other prefix bound to the SEC
information-table namespace) SHALL be recognized identically, and its
prefixed child elements (`infoTable`, `cusip`, `sshPrnamt`, and the other
13F holding fields) SHALL be read with the same namespace-neutral local-name
semantics already used downstream.

Recognition SHALL apply to both input paths: a complete SEC submission whose
INFORMATION TABLE is embedded in an `<XML>` block alongside other XML documents
(such as the primary `edgarSubmission` document), and a standalone Information
Table XML document with no SEC `<XML>` wrapper. Other XML documents present in
a complete submission SHALL NOT be selected and SHALL NOT create ambiguity.

The existing fail-closed contracts SHALL be preserved unchanged: a submission
containing a number of recognized INFORMATION TABLE documents other than
exactly one SHALL fail closed, a malformed INFORMATION TABLE XML document SHALL
fail closed as malformed rather than as missing, and these outcomes SHALL
continue to make the SEC provider outcome partial or failed under the existing
watched-company coverage requirement. Namespace neutrality SHALL NOT weaken or
bypass any coverage, degradation, or blocked-exemption semantics.

#### Scenario: Prefixed information table root is recognized

- **WHEN** a complete SEC submission embeds an INFORMATION TABLE whose root is
  `<ns1:informationTable xmlns:ns1="http://www.sec.gov/edgar/document/thirteenf/informationtable">`
  with prefixed `infoTable` holdings
- **THEN** the parser recognizes exactly that document as the INFORMATION TABLE,
  reads its holdings, and the acquisition does not fail on information-table
  recognition

#### Scenario: Arbitrary prefix is recognized without prefix-specific logic

- **WHEN** the INFORMATION TABLE root uses an arbitrary prefix such as
  `<sec:informationTable xmlns:sec="...">` instead of `ns1`
- **THEN** recognition and holdings extraction succeed identically, because the
  QName prefix carries no business semantics

#### Scenario: Complete submission containing other XML documents selects only the information table

- **WHEN** a complete submission contains a primary `13F-HR` XML document with
  an `edgarSubmission` root in addition to the prefixed INFORMATION TABLE
  document
- **THEN** only the INFORMATION TABLE document is selected, and the presence of
  the additional XML document does not create ambiguity or failure

#### Scenario: Standalone prefixed information table is recognized

- **WHEN** the input is a bare Information Table XML document with a prefixed
  root and no SEC `<XML>` wrapper or submission header
- **THEN** the prefixed document is recognized and parsed identically to the
  default-namespace standalone form

#### Scenario: Two information tables still fail closed

- **WHEN** a submission contains two XML documents each with an
  `informationTable` root, in any namespace binding form
- **THEN** the parser fails closed with the existing exactly-one requirement
  error and the SEC outcome is partial or failed

#### Scenario: Malformed information table keeps its error classification

- **WHEN** a candidate XML document intended as the INFORMATION TABLE is not
  well-formed XML
- **THEN** the parser fails closed with the existing malformed error
  classification rather than reporting a missing information table

#### Scenario: Default namespace recognition is unchanged

- **WHEN** the INFORMATION TABLE root uses a default namespace
  (`<informationTable xmlns="...">`) or no namespace, as in all existing
  fixtures
- **THEN** recognition and holdings extraction continue to succeed with no
  behavior change
