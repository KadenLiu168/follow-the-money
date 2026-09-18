## Why

Production `generate-feed` run #67 failed closed because the SEC 13F parser
(`src/follow_the_money/providers/sec_13f.py::_extract_document`) recognizes the
INFORMATION TABLE document with a regex that requires the literal local name
`<informationTable` at the start of a tag. Real SEC complete submissions may
legally bind the information-table namespace through a prefix
(`<ns1:informationTable xmlns:ns1="http://www.sec.gov/edgar/document/thirteenf/informationtable">`),
which the regex does not match. The verified production trigger is Oaktree
Capital Management (CIK 0000949509, accession 0000949509-26-000005), whose
complete submission contains exactly one valid prefixed INFORMATION TABLE XML
with 145 holdings; the parser recognizes zero, raises
`SEC submission must contain exactly one INFORMATION TABLE XML document`,
makes `sec_edgar` partial, and drives `us_company_filings` (minimum 1) deficient,
so the Feed correctly fail-closes on a parser defect. The fail-closed coverage
contract is working as designed; the recognition logic is the defect.

## What Changes

- Replace regex-based INFORMATION TABLE recognition in `_extract_document()` with
  XML-semantic recognition: parse each `<XML>...</XML>` candidate document block
  and classify it by its root element's local name (`informationTable`), making
  recognition independent of the XML namespace binding form (no namespace,
  default namespace, or any prefix such as `ns1`, `sec`, `x`).
- The same XML-semantic classification covers the standalone-input fallback path
  (a bare Information Table XML document with no SEC `<XML>` wrapper), fixing the
  same prefix blindness there.
- Preserve every existing fail-closed contract unchanged: exactly-one
  INFORMATION TABLE, malformed INFORMATION TABLE error classification, header
  cross-checks, coverage requirements, and blocked-exemption semantics.
- Add regression tests covering prefixed and arbitrary-prefix roots, prefixed
  child elements, complete submissions that also contain a primary
  `edgarSubmission` XML document, standalone prefixed input, and unchanged
  fail-closed cases, plus a synthetic production-shaped regression modeled on the
  observed Oaktree namespace shape.

Non-goals (explicitly out of scope): BLS 403 handling, workflow changes,
coverage or exemption changes, reverting the watched-CIK or canonical Archive
URL changes, Form 4 / Schedule 13D/G work, and any relaxation of fail-closed
behavior.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `feed-evidence-pipeline`: Adds a focused requirement making SEC 13F
  INFORMATION TABLE document recognition XML-namespace-neutral (prefix SHALL NOT
  alter semantic recognition) while reaffirming that the existing exactly-one,
  malformed, and coverage fail-closed semantics are unchanged. The living spec
  already requires a "readable INFORMATION TABLE"; this delta records the
  namespace-neutrality contract explicitly instead of leaving it implicit.

## Impact

- Code: `src/follow_the_money/providers/sec_13f.py` (`_extract_document()` and
  its standalone fallback path only; downstream `_local()`/`_text()` are already
  namespace-safe and are expected to require no change, verified by new tests).
- Tests: `tests/test_sec_13f.py` (new regression cases; existing assertions
  unchanged).
- No configuration, manifest, provider, schema, or workflow changes.
- No new dependencies; uses the existing `xml.etree.ElementTree` usage already
  imported in the module.
- Production effect after merge: the Oaktree-shaped filing parses, `sec_edgar`
  completes, and `us_company_filings` coverage recovers without any change to
  failure strategy.
