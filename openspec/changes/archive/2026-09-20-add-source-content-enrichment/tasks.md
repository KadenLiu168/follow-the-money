## 1. Feed v5 Contract and Migration

- [x] 1.1 Add failing schema and bundle tests for Feed v5 `source_content`, v5-only production, v4-only bounded migration, v3 rejection, unchanged five-domain artifact major 2, and closed rejection outside news/macro/policy; verify the new cases fail against the v4 implementation with `.venv/bin/python -m pytest tests/test_feed_boundary.py tests/test_feed_bundle.py tests/test_feed_remote.py -q`
- [x] 1.2 Implement the Feed, manifest, bundle, deployment, snapshot, publication, and remote-consumer major transition to v5 with only v4 migration input and no artifact-layout major change; verify the focused schema/bundle/remote suites pass
- [x] 1.3 Add exact semantic validation for non-empty NFC text, `plain_text`, `official_html_text_v1`, boolean truncation, 64-hex raw-document digest, and the 12,000-code-point bound; verify malformed, misplaced, positioning, and filing source-content fixtures fail closed

## 2. Provider v2 Contracts and Deadline Admission

- [x] 2.1 Add manifest/config tests for Federal Reserve, PBOC, SSE, and SZSE contract v2 content fields, literal required enrichment, `text/html`, 2 MiB/12,000/50 bounds, exchange 10-page descending discovery contract, provider snapshots/hashes, provider-specific forbidden keys, and unknown/missing/unsupported mutations; verify the cases fail against current manifest resolution
- [x] 2.2 Extend the typed Provider/config models, strict manifest loader, four checked-in manifests, fixture provenance, and `source_content_request_network_headroom_seconds = 120`; verify `tests/test_manifest_registry.py`, `tests/test_provider_contract.py`, and `tests/test_config.py` pass
- [x] 2.3 Add shared-rate-scope send-shape tests covering `us_gov` and `china_gov`, token-refill/minimum-interval floors, other enabled base requests, missing/incompatible bounds, overflow, and an inadmissible configured deadline; implement narrow static source-content deadline validation and verify every failure occurs before Provider work or rate-state mutation
- [x] 2.4 Replace fixed 300/285 deadline assertions and documentation with authoritative configured deadline-minus-reserve semantics while retaining per-send admission and non-cancellable commit; verify focused deadline, deployment, lease-recovery, and commit-boundary tests pass

## 3. Deterministic Document Primitives

- [x] 3.1 Add provider-owned recorded official HTML fixtures for one Federal Reserve release, PBOC announcement, SSE notice, and SZSE notice, list them in each manifest's provenance, and verify manifest fixture validation and offline provenance tests pass
- [x] 3.2 Add failing extraction tests for exact text, entity decoding, NFC, intra-block whitespace, paragraph order, excluded script/style/non-content nodes, missing/duplicate containers, invalid UTF-8/non-HTML, attachment-only content, later-block truncation, oversized first block, and raw-body SHA-256
- [x] 3.3 Implement the minimum shared immutable candidate/acquisition/source-content values, raw digest, normalization, whole-block bounding, and four explicit provider-specific HTML extractors using existing/stdlib capabilities only; verify all extraction fixture tests produce exact deterministic values
- [x] 3.4 Extend the existing Provider fetch helper with an explicit detail-byte-limit override and final-canonical-URL equality enforcement without duplicating managed HTTP behavior; verify size, redirect, host allowlist, user-agent, timeout, and response-observation tests pass

## 4. Federal Reserve and PBOC Two-Stage Acquisition

- [x] 4.1 Add Federal Reserve acquisition-plan tests with 200 RSS entries, exact current-window selection, GUID-or-link identity preservation, zero unselected detail requests, 50-candidate pre-detail failure, final-URL enforcement, and network-free normalization
- [x] 4.2 Upgrade Federal Reserve fetch/normalize to required RSS-to-official-HTML source content and verify its adapter, semantic-context, stable-ID, request-count, and failure tests pass
- [x] 4.3 Add PBOC acquisition-plan tests for production-shaped HTML discovery, canonical-URL identity, exact duplicate collapse, conflicting duplicate rejection, current-window selection before detail requests, 50-candidate pre-detail failure, and network-free normalization
- [x] 4.4 Upgrade PBOC fetch/normalize to required HTML-index-to-official-HTML source content and verify its adapter, semantic-context, stable-ID, request-count, and failure tests pass

## 5. SSE and SZSE Complete Discovery and Enrichment

- [x] 5.1 Add shared exchange-discovery tests for sequential `index_N` traversal, monotonic order across pages, deterministic boundary stop, exact duplicate collapse, conflicting/non-descending candidate failure, and failure when 10 pages cannot prove the window boundary
- [x] 5.2 Implement the narrow SSE/SZSE bounded page-number discovery path, remove silent `entries[:200]` selection for these contracts, and verify only proved current candidates proceed to detail acquisition
- [x] 5.3 Add SSE acquisition/extraction tests for exact selected requests, official notice content, stable canonical-URL identity, bounds, unsafe/changed redirects, unsupported attachments, and network-free normalization; upgrade SSE v2 and verify the focused suite passes
- [x] 5.4 Add equivalent SZSE acquisition/extraction tests, upgrade SZSE v2, and verify its focused suite passes without changing SSE behavior

## 6. Atomic Failure and Completeness Semantics

- [x] 6.1 Add parameterized Provider-boundary tests for detail 401/403/404, timeout, oversized response, unsafe redirect, invalid charset/content type, missing container, extraction failure, and selected-count overflow; verify no case emits a healthy title-only item or partial publishable slice
- [x] 6.2 Verify discovery success followed by first-detail HTTP 403 is `partial` and non-exempt, later-detail failure sets freshness `not_evaluated`, required coverage fails, prior-slice substitution is forbidden, and retries remain bounded by existing managed-send semantics

## 7. Feed Identity and Determinism

- [x] 7.1 Add identity regressions proving identical discovery/detail bytes produce byte-identical source content and Feed, changed body bytes preserve item ID while changing document/content/run digests, and chrome-only raw-byte changes alter Feed identity even when extracted text is equal
- [x] 7.2 Extend current-production semantic validation so every newly acquired target-Provider v2 item requires valid source content while migrated v4, BLS, and NBS items may omit it; verify forged contract snapshots and title-only v2 items fail closed
- [x] 7.3 Run focused feed determinism, boundary, freshness, snapshot, bundle, publication, deployment, and remote-consumer suites and fix only regressions attributable to the v5 transition

## 8. Reader-First Projection and Presentation

- [x] 8.1 Add DigestContext tests proving current news/macro/policy units expose only nested source-content `text`, `format`, and `truncated`; extraction method/hash remain absent; repeated preparation is byte-identical; and preparation performs no URL or document access
- [x] 8.2 Extend the closed eligible-path inventories and projections, then update news, macro-release, and policy domain references plus Feed/Digest documentation to describe bounded official text, truncation, attribution, and the prohibition on reconstructing absent semantic fields; verify presentation-contract and documentation tests pass
- [x] 8.3 Add a production-shaped combined regression with enriched current SSE news and Fed/PBOC policy, hundreds of stale CFTC rows, and old Form 13F state; verify only current updates carry source content and CFTC/13F membership, status, limitations, and substantive exclusion remain unchanged

## 9. Final Contract and Quality Verification

- [x] 9.1 Audit the complete diff against the four v2 Provider scope, five-domain/eight-Provider/evidence-only boundary, Feed-only authority, no-model/no-credential/no-second-artifact non-goals, and unchanged SEC/CFTC/BLS semantics; verify `git diff --check` passes and document any follow-up issue without expanding this Change
- [x] 9.2 Run all directly affected pytest suites, then `.venv/bin/python scripts/quality_gate.py`; verify every executed gate passes without network-dependent tests or a real Provider dry run
- [x] 9.3 Run `openspec doctor`, `openspec validate add-source-content-enrichment --strict`, and `openspec validate --all --strict`; verify the Change, accepted specs, implementation, tests, configuration, schemas, and truthful documentation are coherent before requesting independent review
