## Context

See `proposal.md` for motivation. The accepted `feed-evidence-pipeline` spec already requires exact SEC `13F-HR` selection, exact watched-CIK-set completeness, whole-Provider-slice replacement, and bounded complete CFTC pagination.

Current implementation inspection shows:

- `sec_13f.select_filings()` already uses `form != "13F-HR"` exclusion and raises when no eligible exact filing exists.
- production creates one `SecEdgarAdapter` per watched company, aggregates them under one `sec_edgar` outcome, and `feed/cli.py` changes a nominally healthy outcome to partial when the actual SEC CIK set differs from configuration.
- `snapshot.select_provider_slices()` already treats SEC/CFTC v2 as complete-state slices and replaces the whole current slice when identity sets or canonical content differ.
- `CftcAdapter` v2 already discovers report dates and fetches current/previous reports with `PAGE_SIZE = 100`, deterministic `(market code, stable id)` order, sequential offsets, short-page termination, duplicate/order checks, and bounded failure. The unqualified `$limit=100` and `data[:100]` paths remain only in the bounded Provider-v1 compatibility path; production manifests are v2.

The missing work is therefore direct regression evidence around the requested boundaries. Production changes are conditional on a new test exposing a contract violation.

## Goals / Non-Goals

**Goals:**

- Pin exact-form SEC selection and permutation invariance with small pure-core tests.
- Exercise SEC acquisition completeness and snapshot publication together, so A changing cannot erase B-H and a missing company cannot become publishable.
- Exercise CFTC v2 beyond one page, prove normalized semantic output is independent of valid pagination partitioning/input order, and prove an unresolved required page fails closed.
- Keep tests deterministic, fixture-driven, credential-free, and network-free.

**Non-Goals:**

- Changing accepted OpenSpec requirements, Feed schema, Provider manifests, snapshot persistence, or Feed identity rules.
- Supporting amendments, merging SEC company history, or retaining cross-run CFTC history.
- Refactoring common pagination/comparison logic or introducing ECO-125 abstractions.
- Testing or changing the Provider-v1 compatibility fetch as though it were the v2 production path.

## Decisions

### 1. Treat this as contract-preserving hardening with no delta spec

The requested behavior is already normative in `feed-evidence-pipeline`; a new requirement would duplicate accepted authority. The Change therefore uses `skip_specs: true`, and implementation success means new regressions pass without changing externally observable behavior.

Alternative considered: restate the three constraints in a delta spec. Rejected because it would imply a contract change where none exists.

### 2. Add direct SEC selection cases to the existing pure-core test file

Extend `tests/test_sec_13f.py` with the exact three cases: exact filing followed by a newer amendment, amendment-only input, and both input permutations. Assert candidate identity (not merely form text) and `SchemaError` for amendment-only input.

This directly tests `select_filings()` and avoids indirect adapter fixtures obscuring the boundary. If these tests already pass, production selection code remains untouched.

Alternative considered: test only through `SecEdgarAdapter.fetch()`. Rejected because the additional HTTP fixture setup weakens failure localization.

### 3. Test SEC completeness at both acquisition/outcome and snapshot seams without changing snapshot semantics

Create `tests/test_sec_snapshot_slice.py` around the existing production seams. Use eight deterministic SEC-v2 company items and a prior A-H slice. The successful case supplies current changed-A plus unchanged B-H and asserts the selected/published slice is exactly A-H, with whole-current replacement rather than per-company merge.

A second case simulates one absent watched CIK and verifies the existing completeness boundary marks SEC partial/failed before publication; snapshot selection must not carry prior evidence for that non-complete outcome. Prefer an existing Feed execution/integration helper where it can assert pipeline failure and no publication. If fixture setup requires testing the post-acquisition completeness check more directly, keep the helper test-local rather than extracting a new production abstraction solely for tests.

No change to `snapshot.py` is planned. If a defect exists, fix the completeness decision where configured CIK equality is established or where acquisition units become one Provider outcome.

Alternative considered: add company-level merge to snapshot selection. Rejected because it would violate whole-Provider-slice replacement and turn snapshot retention into a history database.

### 4. Separate CFTC pure normalization invariants from acquisition completeness

Add a 150-market current report (and complete prior report where comparison is asserted) to `tests/test_cftc_cot.py`, then verify all 150 unique market codes enter normalization/comparison and canonical output is identical under row permutations.

Pagination itself belongs to `CftcAdapter.fetch()`, so acquisition-focused cases may be added to the existing adapter tests while `tests/test_cftc_cot.py` retains the requested semantic-universe assertions. Use synthetic pages with stable IDs and globally ordered keys:

- more than 100 rows requires offsets 0 and 100 for each selected report and retains all rows;
- equivalent valid page partition/input grouping yields the same normalized canonical bytes/digest;
- failure while fetching a required next page raises typed failure and produces no partial semantic comparison.

The accepted design is sequential and requires total upstream ordering. “page1/page2 order variation” is therefore interpreted as semantically identical valid pagination partitioning or row/input delivery variation, not swapping ordered offset ranges. A literal swapped range is invalid ordering and must fail closed rather than produce a digest.

Alternative considered: remove pagination ordering checks and sort after acquisition. Rejected because sorting partial or ambiguous pages would conceal acquisition incompleteness.

### 5. Make production edits only at the violated responsibility layer

If regressions fail:

- exact-form defects are fixed in `sec_13f.select_filings()`;
- watched-company completeness defects are fixed in SEC acquisition aggregation or its existing pre-snapshot CIK-set validation;
- CFTC truncation/completion defects are fixed in `CftcAdapter` v2 pagination.

Do not modify semantic presentation, Digest behavior, schemas, manifests, or unrelated Provider paths. Existing provenance, cutoff, freshness, typed outcome, canonical ordering, and rate-managed per-send behavior remain mandatory.

## Risks / Trade-offs

- [A snapshot-only test could pass while acquisition silently omits a company] → Include an acquisition/outcome integration assertion against the configured CIK set, not only `select_provider_slices()`.
- [A 150-row test could exercise only the pure core and miss HTTP pagination] → Pair the pure semantic test with adapter offset/page-completion coverage.
- [Synthetic page permutations could accidentally model an invalid Socrata response] → Keep successful variants globally ordered; assert swapped/repeated/missing ranges fail closed.
- [Existing behavior may already satisfy all cases] → Accept a tests-only implementation and avoid no-op production edits.
- [Large fixtures make reviews noisy] → Generate deterministic rows in test helpers rather than adding bulky recorded fixture files.
