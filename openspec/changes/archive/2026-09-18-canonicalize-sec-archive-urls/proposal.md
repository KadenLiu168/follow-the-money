# Change: canonicalize-sec-archive-urls

## Why

SEC EDGAR has two distinct canonical CIK representations in its verified
locators: the submissions API uses a ten-digit zero-padded CIK
(`https://data.sec.gov/submissions/CIK0001067983.json`), while the Archives use the
unpadded integer CIK (`https://www.sec.gov/Archives/edgar/data/1067983/...`). The
current SEC producers build every Archive URL with the padded CIK
(`.../data/0001067983/...`). `www.sec.gov` 301-redirects padded Archive paths to the
unpadded canonical form, and `bounded_fetch` follows redirects, so padded Archive
URLs do not fail acquisition — but the Feed publishes a source-link locator that is
not the SEC canonical form: the recorded URL differs from the canonical resource
locator it resolves to. For an evidence-only Feed whose source links are the
evidence anchors, the published locator SHALL be the canonical locator, not a
redirecting alias. This is a canonical source-link contract change, not an
availability fix (Change 1 `fix-sec-edgar-watched-ciks` restores production).

## What Changes

- Introduce a single SEC CIK canonicalization helper (e.g. `sec_archive_cik`) that
  converts a normalized ten-digit CIK to the unpadded integer form, with a strict
  ten-digit input contract that fails closed on malformed input. Submissions URLs
  continue to use the padded CIK; Archive URLs use the unpadded form.
- Migrate the four Archive-URL construction sites to the helper:
  `SecEdgarAdapter._complete_url` and the v1 13F document URL
  (`src/follow_the_money/providers/adapters.py`), `derive_form4_xml_url`
  (`src/follow_the_money/providers/sec_form4.py`), and the beneficial-ownership
  URL derivations (`src/follow_the_money/providers/sec_beneficial_ownership.py`).
- Update the three Feed validator source-link regexes in
  `src/follow_the_money/feed/validate.py` so that Archive source URLs are required
  to carry the unpadded integer CIK, keeping producer and validator consistent
  (currently both sides are self-consistent on the padded form; changing only the
  producer would make Form 4 and beneficial-ownership validation fail closed — the
  13F source URL carries no separate validator Archive-URL regex).
- Audit and update the digest / evidence-identity / bundle canonical-bytes impact:
  `stable_item_id` is derived from `provider_id + accession` (no URL), so item IDs
  and dedupe behavior are stable; but `DigestItem.source.url`, 13F
  `comparison.previous_source_url`, beneficial-ownership `payload.document_url`,
  and the beneficial-ownership current/previous snapshot `document_url` values all
  enter the `DigestContext` projection (13F payloads carry no `document_url`
  field; it is a beneficial-ownership payload field), so `DigestContext` canonical
  bytes and the Feed `content_digest` change by design (a content change, not a
  hash-algorithm change).
  The audit confirms no checkpoint cross-run invariant relies on URL-string equality
  beyond the expected one-time diff at cutover.
- Update the pinned-URL tests across the affected test files to assert the unpadded
  canonical Archive form; add a URL-shape regression covering 13F, Form 4, and
  Schedule 13D/G historical/current URLs.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `feed-evidence-pipeline`: add a requirement that SEC Archive source URLs SHALL use
  the unpadded integer CIK canonical form while submissions API URLs SHALL use the
  ten-digit padded form, and that producer and validator source-link contracts
  remain consistent.

## Impact

- `src/follow_the_money/providers/adapters.py`, `sec_form4.py`,
  `sec_beneficial_ownership.py`: Archive URL construction via the helper.
- `src/follow_the_money/feed/validate.py`: three source-link regexes.
- `src/follow_the_money/digest.py`: no projection change (URLs are already
  projected); audit confirms the canonical-bytes change is content-driven and
  expected.
- `tests/`: update pinned padded-URL assertions in `test_feed_bundle`,
  `test_feed_boundary`, `test_eco125_characterization`, `test_feed_determinism`,
  `test_digest_prepare`, `test_cftc_activation`, `test_sec_form4`, `test_sec_13f`,
  `test_sec_snapshot_slice`, `test_feed_cli`; add URL-shape regression.
- `references/provider-source-verification.md`: state the unpadded integer CIK in
  the two Archive root templates; the submissions template stays padded.
- Published Feed bytes change (Archive source URLs become canonical). SEC
  complete-slice fail-closed semantics, coverage policy, item identity, and the
  eight-Provider evidence-only boundary are unchanged.
