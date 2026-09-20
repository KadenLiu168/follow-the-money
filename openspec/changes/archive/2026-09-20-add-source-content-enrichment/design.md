## Context

See `proposal.md` for motivation. The current four target adapters fetch one RSS or HTML discovery resource and normalize title-level items. `BaseAdapter._fetch()` already routes every request through manifest-owned HTTPS, redirect, timeout, size, user-agent, rate, and deadline controls; SEC demonstrates that one `fetch()` may perform deterministic selection followed by multiple document requests. `_run_adapter()` already converts a failure after an observed successful resource into an atomic incomplete Provider outcome.

Feed v4 is a five-domain logical/bundle contract with artifact major 2, and the consumer currently retains v3 only as a bounded migration input. The complete item array is already part of semantic Feed identity. DigestContext v2 projects an explicit closed field inventory from only contract-proven current items and never performs network access.

Two accepted-contract conflicts shape this Change. First, the old deadline requirement still says 300 seconds while authoritative production configuration is 720 seconds because the verified SEC v4 request floor no longer fits 300 seconds. Second, the bounded-text requirement prohibits retained article bodies and must distinguish new verified first-party official document evidence from still-forbidden third-party copyrighted content.

## Goals / Non-Goals

**Goals:**

- Add one canonical first-class source-content evidence surface without changing the five-domain architecture or Provider protocol.
- Make discovery, current-window selection, required detail acquisition, extraction, Provider completeness, and shared-scope deadline safety deterministic and fail closed.
- Preserve stable item identity while making admitted raw-document changes visible in Feed identity.
- Give current Digest units enough bounded official text for evidence-preserving Host-Agent summaries without exposing extraction internals.
- Keep all runtime bounds and verification facts checked in, resolved, hashed, and embedded.

**Non-Goals:**

- Generic article extraction, crawling, attachment resolution, PDF parsing, OCR, JavaScript rendering, or LLM use.
- Enriching BLS, NBS, SEC, or CFTC in this Change; fixing BLS availability; changing SEC semantics or CFTC report identity.
- Creating a persisted enriched artifact, a second Feed, a second evidence authority, a Digest schema, or Host-Agent network access.
- Ranking, relevance selection, top-N output, financial interpretation, or a Digest renderer.

## Decisions

### 1. Evolve the logical Feed to v5 and migrate only v4

`source_content` is a new canonical payload surface under closed `additionalProperties: false` schemas, so new production uses logical Feed and bundle major 5. The domain inventory and artifact envelope do not change, so artifact major 2 remains current. The previous-major slot moves from v3 to v4; v3 support is removed rather than carrying two historical migrations.

Migration accepts a fully valid v4 bundle only through the existing explicit migration path, produces no normal v4 consumption result, and seeds a newly validated v5 candidate. Legacy v4 items may omit `source_content`; newly acquired target-Provider v2 items may not.

Alternative rejected: keep Feed v4 and make the field conditionally tolerated. That obscures a new canonical evidence contract and makes old and new item validity depend on producer history.

### 2. Put one closed source-content object inside applicable payloads

The schema adds an optional `source_content` property to `news`, `macro_release`, and `policy`. Its first version is exactly:

```json
{
  "text": "...",
  "format": "plain_text",
  "extraction_method": "official_html_text_v1",
  "truncated": false,
  "document_sha256": "..."
}
```

It remains optional at the general payload level for BLS, NBS, and migrated v4 evidence. Provider v2 validation makes it mandatory for every newly selected Federal Reserve, PBOC, SSE, and SZSE item. Existing `snippet` remains unchanged for BLS and compatibility; target exchange items may retain their schema-required empty snippet while `source_content` becomes their substantive text.

`document_sha256` hashes the exact admitted raw response body. This conservatively changes Feed identity for any raw page-byte change, including ignored chrome. The behavior is explicit and regression-tested. Execution observations and headers never enter the digest.

Alternatives rejected: `raw_metadata` is not reader evidence; `semantic_context` has a structured semantic role; a top-level enrichment artifact would become a second authority; separate `body`/`description` fields would fragment one contract.

The four manifests use one closed `content` section:

```yaml
content:
  acquisition: detail_document
  extraction_method: official_html_text_v1
  allowed_content_types: [text/html]
  max_document_bytes: 2097152
  max_text_chars: 12000
  max_detail_documents_per_window: 50
  required_for_selected_item: true
```

SSE and SZSE additionally declare `max_discovery_pages_per_window: 10` and `discovery_order: published_at_descending` in that section. Those two keys are forbidden for the non-paginated Federal Reserve and PBOC contracts.

### 3. Preserve the Provider protocol with typed in-memory acquisition values

`fetch(window, client)` parses discovery only far enough to construct immutable `DocumentCandidate` values, prove window membership, enforce deterministic identity/order/bounds, and fetch selected documents. It returns an immutable acquisition value containing the discovery evidence, ordered candidates, final admitted document bytes, and resolved URLs needed by normalization. `normalize(raw, window)` validates that value, extracts text, computes hashes, and constructs Feed items without I/O.

`DocumentCandidate.identity` preserves existing Provider identity inputs: RSS GUID with link fallback for Federal Reserve and canonical source URL for PBOC/SSE/SZSE. A document hash never enters item identity.

The shared document module owns only the small cross-Provider primitives: candidate/acquisition/source-content value types, raw SHA-256, NFC and whitespace normalization, and complete-block bounded assembly. Four explicit extractor functions own verified container rules. There is no extractor registry or plugin framework.

Alternative rejected: extracting in `fetch()` mixes I/O and normalization and makes fixture-level deterministic extraction harder to test. Adding `discover()` or `enrich()` expands a deliberately small protocol without a second consumer.

### 4. Make discovery complete before detail acquisition

Federal Reserve RSS and the PBOC index remain single discovery resources. SSE and SZSE use their declared sequential page-number contract. Their v2 manifests add a maximum of 10 discovery pages and assert descending publication-time order. Fetching proceeds page by page, validates monotonic order across page boundaries, and stops when that order proves all later entries predate the window. Reaching page 10 without proving the boundary fails closed.

Candidates are canonicalized before comparison. Exact duplicates with the same identity, title, URL, and publication time collapse; an identity collision with different metadata fails. The selected candidate list is deterministically ordered before its count is compared with the per-Provider limit of 50. Exceeding 50 fails before detail requests; it never chooses a first or latest 50.

Alternative rejected: retaining `entries[:200]` or fetching only the first exchange page can silently miss current evidence and cannot support atomic Provider completeness.

### 5. Reuse the managed HTTP boundary with a stricter document limit

`BaseAdapter._fetch()` gains an optional explicit maximum-byte override while preserving the manifest-owned user agent, attempt timeout, fetch-host policy, redirect-host policy, and the managed client. Discovery keeps the existing Provider response limit; detail documents use the v2 `max_document_bytes = 2 MiB` limit and require a declared `text/html` media type before decoding. Every redirect hop remains a separate managed send.

The acquisition value records the final admitted URL. Detail acquisition requires the final canonical URL to equal the requested canonical candidate URL; a redirect that changes document identity fails closed. This avoids hashing bytes retrieved from one locator while publishing another locator as provenance.

Alternative rejected: a second document HTTP helper would duplicate rate, deadline, allowlist, redirect, and failure behavior.

### 6. Use explicit Provider containers and complete-block truncation

Each extractor is a small stateful standard-library HTML parser configured for the verified Provider container and excluded descendants. It admits only declared block elements within that container, decodes character references, removes script/style/non-content descendants, normalizes each block to NFC, folds intra-block whitespace, drops empty blocks, and preserves source order. Joined paragraphs use exactly `\n\n`.

The 12,000-code-point budget includes separators. Complete blocks are appended until the next block would exceed the budget; remaining blocks set `truncated = true`. If the first non-empty block alone exceeds the bound, extraction fails because returning empty text or slicing the block would violate the contract. Missing/duplicate expected containers, invalid UTF-8, non-HTML content, empty content, and attachment-only pages fail closed. No `document.body` fallback exists.

Provider-owned recorded HTML fixtures live beside each manifest and are listed in fixture provenance. Synthetic malformed and combined Digest fixtures may remain under `tests/fixtures`.

Alternative rejected: readability/trafilatura/newspaper introduce heuristic behavior and new dependencies for four verified stable sites.

### 7. Treat enrichment as one atomic Provider slice

The adapter returns no acquisition result until every selected document is successfully admitted. Therefore a fetch failure cannot yield title-only normalized items. An extraction failure occurs before the adapter returns normalized items. Existing orchestration then marks a post-discovery/detail failure `partial` because acquisition progress was observed, or `failed` if no successful resource was observed; freshness remains `not_evaluated`, required coverage fails, and snapshot substitution remains forbidden.

Provider-level retries intentionally restart the whole atomic acquisition under existing semantics. Per-send deadline admission bounds the retry path; the new static calculation proves the successful path, not that all configured retries can complete.

Alternative rejected: best-effort enrichment creates indistinguishable intentional-empty versus failed-content items and makes Host-Agent evidence quality nondeterministic.

### 8. Validate source-content send shape by shared rate scope

The four v2 manifests own detail and discovery bounds. `config/config.yaml` adds one explicit `source_content_request_network_headroom_seconds = 120` field. Static resolution computes each affected scope's successful-path sends, including the unchanged base request of every enabled Provider in that scope, bounded exchange discovery pages, and bounded detail documents. It derives the token-refill and minimum-interval floor from the resolved shared policy and requires:

```text
managed_send_floor
+ source_content_request_network_headroom_seconds
+ commit_reserve_seconds
<= pre_commit_deadline_seconds
```

For the checked-in maximum shape this evaluates the `us_gov` scope containing Federal Reserve and BLS and the `china_gov` scope containing PBOC, NBS, SSE, and SZSE. It complements the existing SEC-specific v4 calculation and does not create a generic scheduling framework.

The accepted deadline requirement is changed from stale numeric seconds to the authoritative configured deadline and reserve. Runtime still uses monotonic admission at `deadline - reserve`, and admitted commit remains non-cancellable.

Alternative rejected: per-Provider checks ignore contention within `china_gov`; silently lowering candidate counts would violate completeness.

### 9. Expose only reader-relevant content through DigestContext

The news, macro-release, and policy eligible-path inventories gain `payload.source_content.text`, `format`, and `truncated`. Projection copies those fields as one nested object when present. It does not expose `extraction_method` or `document_sha256`; those remain Feed validation/provenance fields. Digest preparation performs no URL access or document parsing.

Membership authorities, update identities, Feed-item traces, order, domain status, limitations, CFTC status-only handling, and old Form 13F exclusion are unchanged. Domain references permit attributed summaries of source text but prohibit treating truncated text as complete or reconstructing absent structured semantics.

Alternative rejected: exposing the hash/method adds no reader value; asking the Host Agent to dereference URLs breaks the Feed-only authority boundary.

## Risks / Trade-offs

- [Official markup changes while URLs remain valid] -> provider-specific container tests fail closed; refresh the verified manifest and recorded fixture in a later reviewed contract change rather than using whole-body fallback.
- [One attachment-only selected notice makes required coverage fail] -> preserve truthful atomic completeness and defer PDF/attachment acquisition to a separate Change.
- [Raw page chrome changes but extracted text does not] -> conservatively change document and Feed identity as the explicit raw-byte contract requires.
- [A burst exceeds 50 current documents or exchange discovery exceeds 10 pages] -> fail closed and recalibrate checked-in bounds with verified source evidence; never top-N truncate.
- [Feed v3 remains deployed somewhere] -> v5 supports only immediate previous v4 migration; operators must first migrate or regenerate through a v4-capable release.
- [Larger payloads approach the 50 MiB product limit] -> retain the existing serialized Feed size gate; four providers at the closed text bound remain subject to it with no special bypass.
- [Atomic retry repeats already successful detail requests] -> retain simple existing Provider-attempt semantics and rely on managed rate/deadline bounds rather than adding an execution cache.

## Migration Plan

1. Add v5 schemas and validators while retaining explicit v4 migration input; update logical/bundle constants without changing artifact major 2.
2. Add and statically validate the four Provider v2 content contracts, provider-owned fixtures, typed runtime fields, shared-scope send shape, and configured headroom before enabling v2 adapters.
3. Add document primitives and provider-specific fixture extractors, then upgrade Federal Reserve and PBOC to cover RSS-to-HTML and HTML-to-HTML acquisition patterns.
4. Add bounded sequential exchange discovery and upgrade SSE and SZSE.
5. Activate v5 production validation, stable-identity/source-content identity regressions, and v4-to-v5 migration.
6. Extend DigestContext and domain presentation contracts, then run the production-shaped Reader-first regression and canonical gates.

Rollback before publication is a code/contract revert. After a v5 bundle is published, rollback requires a v5-capable reader or regeneration by the prior release from its still-valid v4 migration input; production must never emit a v4 bundle from the new producer.
