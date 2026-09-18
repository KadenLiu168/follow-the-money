## Context

`_extract_document()` in `src/follow_the_money/providers/sec_13f.py` currently
extracts `<XML>...</XML>` blocks with a regex, then decides which block is the
INFORMATION TABLE with a second regex requiring the literal text
`<informationTable` at a tag start. This fails on legal SEC filings that bind
the information-table namespace through a prefix. The production trigger
(Oaktree 0000949509-26-000005, verified against the real complete submission)
contains two `<XML>` blocks: a primary `edgarSubmission` (default namespace) and
an INFORMATION TABLE rooted at
`<ns1:informationTable xmlns:ns1="http://www.sec.gov/edgar/document/thirteenf/informationtable">`
with 145 `<ns1:infoTable>` holdings; the regex matches neither, so the parser
reports zero tables and fails with the exactly-one error. See proposal.md for
the full failure chain.

Two structural facts shape the fix:

1. Downstream parsing is already namespace-safe: `_local()` matches descendant
   tags by `tag.rsplit("}", 1)[-1]`, so prefixed children work today. Only
   document recognition is broken.
2. The same prefix-blind regex appears twice — the per-block check and the
   standalone fallback (`if not documents and re.search(...): documents = [text]`).
   Both paths must be fixed or the fix is incomplete.

## Goals / Non-Goals

**Goals:**

- Recognize the INFORMATION TABLE document by XML semantics (root local name),
  uniform across the complete-submission and standalone input paths.
- Preserve the exact existing error classifications and fail-closed contracts:
  exactly-one, malformed, header cross-checks, coverage, blocked exemption.
- Keep the change surgical: one function in one module plus tests.

**Non-Goals:**

- No changes to coverage groups, provider config, manifests, workflow, or any
  failure/exemption strategy (see proposal.md Non-goals).
- No new dependencies; `xml.etree.ElementTree` is already imported.
- No fixture files under `providers/sec_edgar/fixtures/` (new fixtures would
  require `manifest.yaml` `fixture_provenance` registration; tests build XML
  inline today and will continue to).
- No support for INFORMATION TABLE roots nested inside another XML document
  root (see Decision 4).

## Decisions

### Decision 1: Classify candidate documents by parsed root local name

For each extracted `<XML>` block, strip the block, parse it with
`ET.fromstring`, and classify it as the INFORMATION TABLE when the root
element's local name (`root.tag.rsplit("}", 1)[-1]`) is `informationTable`.
Exactly one classified table must exist; otherwise the existing exactly-one
error is raised.

- Why over alternatives: prefix-tolerant regexes (`(?:ns1:)?`) enumerate
  prefixes and stay string-level — the root cause is using string matching for
  a QName, so the fix must move to XML semantics. The `<TYPE>INFORMATION
  TABLE</TYPE>` SGML marker was considered as a primary signal; it is
  SEC-native but depends on SGML header layout and cannot serve the standalone
  input path, so it would still need an XML-semantic fallback. Local-name
  classification alone covers both paths.
- `<XML>...</XML>` block extraction itself stays regex-based: those tags are
  SEC SGML container structure, not XML QNames, and the existing extraction
  already works on real submissions (verified on the Oaktree file).

### Decision 2: Strip each candidate before parsing

Real complete-submission blocks begin with a newline (and often a blank line)
followed by an `<?xml ...?>` declaration. `ET.fromstring` rejects whitespace
before the declaration (`XML or text declaration not at start of entity` —
reproduced against the Oaktree file). Every candidate must therefore be
`.strip()`-ed before parsing, mirroring the existing `document.strip()` in the
current code. Without this, the fix would reclassify the Oaktree filing from
"exactly one" to "malformed" and still fail closed.

### Decision 3: Confine regex to malformed-error classification, not recognition

When a candidate block fails to parse, the parser cannot know its intended
document type from XML semantics (it is malformed by definition). Options
considered:

- (a) Fail with the existing malformed error only when the unparseable text
  contains the substring `informationTable` (case-insensitive); otherwise skip
  the block as a non-table document.
- (b) Fail with the malformed error on any unparseable block regardless of
  type.
- (c) Silently skip unparseable blocks.

Chosen: (a). It preserves the existing error classification (the current test
asserts `match="malformed"` for a truncated `<XML><informationTable><infoTable>`
block) and diagnostics quality, while regex is demoted from recognition
authority to a best-effort error-message classifier. Both branches fail closed,
so the regex's imprecision there carries no safety consequence. (c) was
rejected because a malformed INFORMATION TABLE would degrade to the
exactly-one (missing) error, weakening diagnostics and the existing contract
test. (b) was rejected as an unnecessary tightening: it turns malformed
non-table XML documents, which the current code ignores, into fatal errors.

### Decision 4: Root-only recognition (deliberate tightening)

Recognition requires the `informationTable` root element. An `informationTable`
nested as a descendant of another root (e.g. inside `edgarSubmission`) is not
recognized. The current regex approach would select such a document (it matches
anywhere in the block) and rely on `_local()`'s full-tree walk to find rows.
Modern 13F-HR e-filings always publish the INFORMATION TABLE as its own
`<DOCUMENT>` with `<TYPE>INFORMATION TABLE</TYPE>` (confirmed on the production
file and consistent with the spec's wording "INFORMATION TABLE XML document"),
so root-only recognition matches the SEC document taxonomy. This is an
intentional, documented tightening; it is recorded here so a future nested-only
filing is diagnosed as a new contract question, not mistaken for a regression
of this change.

### Decision 5: Exact-case local-name comparison

The local name is compared exactly (`informationTable`), matching XML's
case-sensitive name semantics. The current regex uses `re.IGNORECASE` and would
accept `<INFORMATIONTABLE>`; no real SEC filing uses that form, and exact-case
comparison is the XML-correct behavior. Recorded as an intentional,
zero-practical-risk tightening.

### Decision 6: Standalone fallback unified into the same classification

When no `<XML>` blocks exist, the whole (stripped) text becomes a single
candidate document and goes through the same parse-and-classify path. This
replaces the prefix-blind fallback regex and keeps one recognition authority
instead of two. Current semantics are preserved: the fallback triggers only
when there are no `<XML>` blocks at all.

## Risks / Trade-offs

- [Candidate block parses but with an encoding declaration inconsistent with
  the already-UTF-8-decoded string] → Pre-existing exposure: the current code
  already `ET.fromstring`-es the selected document as a decoded str. Real SEC
  XML documents declare UTF-8. No new handling; a failure remains fail-closed.
- [A submission contains a second well-formed `informationTable`-rooted
  document] → Exactly-one error, unchanged fail-closed contract.
- [Nested-only information tables stop being recognized (Decision 4)] →
  Documented tightening; believed unreachable for modern 13F-HR e-filings. If
  observed in production, it is a new change, not a regression to hide.
- [Whitespace-before-declaration ParseError silently reintroduced by future
  refactoring] → Covered by the production-shaped regression test, which uses
  a declaration with leading whitespace exactly as extracted from real
  submissions.

## Migration Plan

Single-commit code change with tests; no data, config, or workflow migration.
Rollback is reverting the commit — the failure mode before and after is a
fail-closed SchemaError, never a wrong publication. After merge and archive,
manually trigger `generate-feed` and confirm `sec_edgar` no longer reports the
exactly-one error and `us_company_filings` coverage recovers; a subsequent,
different SEC production failure is a separate change (see proposal.md
Non-goals).
