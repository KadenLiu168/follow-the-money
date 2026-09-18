# Design: canonicalize-sec-archive-urls

## Context

SEC EDGAR has two canonical CIK representations:

```
  Submissions API :  https://data.sec.gov/submissions/CIK0001067983.json   (padded)
  Archive         :  https://www.sec.gov/Archives/edgar/data/1067983/...   (unpadded)
```

The current producers build every Archive URL with the padded CIK. `www.sec.gov`
301-redirects padded Archive paths to the unpadded canonical form, and
`bounded_fetch` (`src/follow_the_money/providers/http.py:81`) follows redirects,
then validates the final URL against the `redirect_hosts` allowlist (SEC manifest
permits `www.sec.gov` and `data.sec.gov`). So padded Archive URLs do not fail
acquisition — but the Feed publishes a non-canonical source-link locator.

This change makes the published locator the SEC canonical form. It is a
canonical source-link contract change, not an availability fix (Change 1
`fix-sec-edgar-watched-ciks` restores production).

## Decision: one canonicalization helper, producer and validator updated together

A single helper derives the unpadded integer form from a normalized ten-digit CIK:

```python
def sec_archive_cik(cik: str) -> str:
    if not re.fullmatch(r"\d{10}", cik):
        raise SchemaError("SEC CIK must be normalized ten-digit CIK")
    return str(int(cik))
```

The helper lives in the shared providers URL-policy module (`providers/urls.py`)
so `adapters.py`, `sec_form4.py`, and `sec_beneficial_ownership.py` import one
definition; `feed/validate.py` derives its Archive-path regex CIK through the same
helper (feed→providers imports already exist elsewhere in the package).

Rule:

```
  normalized_cik = "0001067983"   (ten-digit, padded; submissions URL, item identity)
  archive_cik    = "1067983"       (unpadded integer; Archive URL path only)
```

Submissions URL:

```
  f"https://data.sec.gov/submissions/CIK{normalized_cik}.json"
```

Archive URL (all four construction sites):

```
  f"https://www.sec.gov/Archives/edgar/data/{archive_cik}/{accession}/{doc}"
```

### Why producer and validator must move together

Producer and validator are currently self-consistent on the padded form. Changing
only the producer would make the validator reject every Form 4 and
beneficial-ownership item (fail closed) — the 13F source URL carries no separate
validator Archive-URL regex, so 13F cannot develop a producer/validator
disagreement:

```
  validate.py:846   Form 4 source URL    requires re.escape(company) == padded \d{10}
  validate.py:1246  BO document_url      requires \d{10} in Archive path
  validate.py:1538  BO reference URL    requires padded filer CIK
```

All three regexes move to the unpadded integer form in the same change. This is the
load-bearing coupling the original fix plan omitted.

### Construction sites migrated

- `SecEdgarAdapter._complete_url` — 13F complete submission `.txt`
  (`src/follow_the_money/providers/adapters.py`)
- v1 13F document URL (`adapters.py`, the `Archives/edgar/data/{cik}/...` branch)
- `derive_form4_xml_url` (`src/follow_the_money/providers/sec_form4.py`)
- beneficial-ownership URL derivations
  (`src/follow_the_money/providers/sec_beneficial_ownership.py`)

## Impact audit: digest / evidence identity / bundle canonical bytes

This is the audit requested for Change 2 scope. Findings from reading
`src/follow_the_money/digest.py`, `feed/dedupe.py`, `feed/bundle.py`,
`providers/http.py`:

### Stable across the URL change

- **Item identity.** `stable_item_id(provider_id, record_identity)` hashes
  `provider_id + accession` (e.g. `sec-{stable_item_id(self.provider_id,
  accession)}`). No URL participates, so every SEC item keeps its `id` across the
  padded→unpadded cutover.
- **Dedupe.** `feed/dedupe.py` groups by exact canonical `source.url` before the
  same-source title-trigram pass, so the grouping keys do change form on
  cutover. The equivalence classes do not: padded→unpadded is a uniform,
  injective relabeling applied to every SEC Archive URL, so items that shared a
  URL still share one and distinct URLs stay distinct. Survivor selection and the
  lineage merge stay on the `(knowledge_available_at, id)` total order, so dedupe
  outcomes are unchanged.
- **Total order.** The Feed item total order is `(knowledge_available_at, id)`;
  unaffected.
- **Checkpoint carry-forward.** Carry-forward requires equality of current/prior
  item identity sets plus canonical equality of each item. Because the URL form
  changes for every SEC item, the first run after cutover produces an expected
  one-time canonical-inequality diff for SEC items (current ≠ prior bytes). This is
  a content change, not a carry-forward invariant violation: the checkpoint logic
  treats it as a normal content change and re-selects the current slice. No special
  handling is required.

### Changes by design

- **`DigestContext` canonical bytes.** `DigestItem.source.url`, 13F
  `comparison.previous_source_url`, beneficial-ownership `payload.document_url`,
  and the beneficial-ownership current/previous snapshot `document_url` values all
  enter the digest projection (`COMMON_PATHS`, `FILING_COMMON_PATHS`,
  `FILING_13F_PATHS`, `BENEFICIAL_PATHS`). (13F payloads carry no `document_url`
  field; it is a beneficial-ownership payload field.) Their
  string values change from padded to unpadded Archive form, so the
  `DigestContext.canonical_bytes()` output changes for every SEC-bearing run.
- **Feed `content_digest`.** The manifest `content_digest` is computed over feed
  content including source URLs, so it changes for SEC-bearing runs. This is the
  intended behavior of a content change.
- **Published bundle bytes.** Archive source URLs in the published Feed change from
  padded to unpadded. Consumers that recorded padded URLs will see the new canonical
  form; both forms resolve to the same resource (padded 301→unpadded).

### No change

- Submissions API URL form (stays padded).
- `stable_item_id`, dedupe, item total order, coverage policy, complete-slice
  fail-closed semantics, rate/lease/checkpoint semantics.
- Hash algorithm, canonical JSON serialization, manifest structure.

### Audit verification (implementation time)

Re-confirmed against the implementation rather than the plan:

- `providers/http.py:stable_item_id` hashes `provider_id|record_identity` only —
  no URL is an input, so every SEC item keeps its `id`.
- `feed/dedupe.py:deduplicate_items` keys on canonical `source.url` (see the
  corrected bullet above) with stable equivalence classes and total-order
  survivors.
- `digest.py` path tuples project `source.url` (`COMMON_PATHS`),
  `payload.document_url` (`FILING_COMMON_PATHS`),
  `payload.comparison.previous_source_url` (`FILING_13F_PATHS`) and the
  beneficial-ownership snapshot/reference `document_url` values
  (`BENEFICIAL_PATHS`); `canonical_bytes()` serializes that projection, so the
  bytes change for SEC-bearing runs.
- `validate.py:recompute_feed_identity` derives `content_digest` from
  `canonical_digest(semantic_feed_projection(feed))`, so the changed URLs move
  both `content_digest` and the `run_id` derived from it. Content-driven, not an
  algorithm or projection-shape change.
- `feed/snapshot.py:select_provider_slices` compares identity sets plus
  `canonical_bytes` per item, so cutover yields one expected re-selection with
  fresh provenance and no invariant violation.
- `feed/checkpoint.py` and `feed/freshness.py` contain no URL participation.

## Test impact

Ten test files pin padded Archive URLs and must be updated to the unpadded
canonical form (`test_sec_snapshot_slice` hand-builds 13F fixture URLs that no
validator regex rejects, but the corpus moves to the canonical form):

```
  test_feed_bundle.py
  test_feed_boundary.py
  test_eco125_characterization.py
  test_feed_determinism.py
  test_digest_prepare.py
  test_cftc_activation.py
  test_sec_form4.py
  test_sec_13f.py
  test_sec_snapshot_slice.py
  test_feed_cli.py
```

A new URL-shape regression covers 13F complete submission, Form 4 XML, and
Schedule 13D/G current + historical URLs, asserting padded submissions form and
unpadded Archive form.

## Non-goals

- Not changing the submissions API URL form.
- Not adding 404 retry, not making SEC 404 a blocked exemption, not relaxing
  complete-slice semantics, not making `us_company_filings` optional.
- Not changing item identity, dedupe, or carry-forward invariants.
- Not a digest hash-algorithm or projection-shape change; the bytes change is
  content-driven.
