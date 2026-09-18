## 1. SEC CIK canonicalization helper

- [x] 1.1 Add a `sec_archive_cik(cik)` helper (ten-digit input → unpadded integer
  output, strict `re.fullmatch(r"\d{10}", cik)` guard, typed `SchemaError` on
  malformed input) in the shared providers URL-policy module (`providers/urls.py`);
  verify with a focused unit test that the padded→unpadded conversion holds and
  malformed input fails closed

## 2. Migrate Archive URL construction

- [x] 2.1 `SecEdgarAdapter._complete_url` — build the 13F complete submission `.txt`
  URL with `sec_archive_cik`; verify the constructed URL is unpadded canonical
- [x] 2.2 v1 13F document URL branch in `adapters.py` — use `sec_archive_cik` for
  the `Archives/edgar/data/...` form
- [x] 2.3 `derive_form4_xml_url` in `sec_form4.py` — use `sec_archive_cik` for the
  issuer CIK in the Archive path
- [x] 2.4 beneficial-ownership URL derivations in `sec_beneficial_ownership.py` —
  use `sec_archive_cik` for the filer CIK in the Archive path; verify all four
  construction sites now emit unpadded canonical URLs

## 3. Update Feed validator source-link contracts

- [x] 3.1 `validate.py:846` Form 4 source URL regex — require unpadded integer CIK
  in the Archive path
- [x] 3.2 `validate.py:1246` beneficial-ownership `document_url` regex — require
  unpadded integer CIK
- [x] 3.3 `validate.py:1538` beneficial-ownership reference URL regex — require
  unpadded integer CIK; verify producer and validator now agree and a padded
  Archive URL fails validation
- [x] 3.4 Update `references/provider-source-verification.md` Archive root templates
  to the unpadded integer CIK form (both occurrences); keep the submissions
  template padded so the verification reference stays truthful to the new contract

## 4. Digest / evidence-identity / canonical-bytes impact audit

- [x] 4.1 Confirm `stable_item_id` (provider_id + accession) and dedupe behavior
  are stable across the URL form change by reading `digest.py` and `dedupe.py`
- [x] 4.2 Confirm `DigestContext` canonical bytes and Feed `content_digest` change
  by design (content change), and that the change touches only URL-string fields
  (`source.url`, `payload.document_url`, `comparison.previous_source_url`, BO
  snapshot `document_url`); record the audit conclusion
- [x] 4.3 Confirm checkpoint carry-forward treats the cutover as an expected
  one-time canonical-inequality diff for SEC items (no invariant violation, no
  special handling)

## 5. Tests

- [x] 5.1 Update pinned padded-URL assertions to unpadded canonical form across the
  ten affected test files: `test_feed_bundle`, `test_feed_boundary`,
  `test_eco125_characterization`, `test_feed_determinism`, `test_digest_prepare`,
  `test_cftc_activation`, `test_sec_form4`, `test_sec_13f`,
  `test_sec_snapshot_slice`, `test_feed_cli`; verify with a focused `pytest` run
- [x] 5.2 Add a URL-shape regression covering 13F complete submission, Form 4 XML,
  and Schedule 13D/G current + historical URLs — assert padded submissions form and
  unpadded Archive form

## 6. Verification

- [x] 6.1 Run focused tests for touched modules; then the full suite: `pytest`,
  `ruff`, `mypy`; all green
- [x] 6.2 Run `.venv/bin/python scripts/quality_gate.py`; passes
- [x] 6.3 Run `openspec validate canonicalize-sec-archive-urls --strict` and
  `openspec validate --all --strict`; all pass
- [x] 6.4 Confirm scope: submissions URL form unchanged, no 404 retry, no blocked
  exemption, no complete-slice relaxation, item identity/dedupe/carry-forward
  invariants unchanged, no hash-algorithm or projection-shape change
