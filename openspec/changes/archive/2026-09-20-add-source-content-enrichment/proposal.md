## Why

Reader-first Digest preparation now exposes only deterministic current updates, but Federal Reserve, PBOC, SSE, and SZSE items usually carry only a title and thin metadata. The Host Agent therefore lacks sufficient official evidence for a concise source-supported summary even though the Feed remains the sole evidence authority.

## What Changes

- **BREAKING** Advance newly produced logical Feed bundles from schema version 4 to version 5, retain only version 4 as the bounded previous-major migration input, and keep the unchanged five-domain artifact layout.
- Add a closed `payload.source_content` evidence object for `news`, `macro_release`, and `policy`, containing bounded normalized plain text, extraction provenance, truncation state, and the SHA-256 of the admitted raw official document bytes.
- Upgrade Federal Reserve, PBOC, SSE, and SZSE to Provider contract version 2 and require bounded two-stage discovery/detail acquisition for every selected current-window item; any missing, unsupported, unsafe, oversized, or unextractable required detail document makes the Provider slice incomplete rather than silently producing a healthy title-only item.
- Preserve the existing `fetch(window, client)` / `normalize(raw, window)` Provider protocol: all network I/O remains in `fetch()`, while deterministic extraction and Feed normalization remain network-free.
- Add checked-in per-Provider content bounds and a shared-rate-scope successful-path deadline-admissibility check. Candidate limits are safety bounds that fail closed rather than top-N selection.
- Align the accepted command-deadline contract with the authoritative configured deadline and exact commit reserve, replacing the stale fixed 300-second statement while preserving send-level deadline admission and non-cancellable commit semantics.
- Permit bounded first-party official document text while continuing to reject retained third-party copyrighted article bodies, PDF/OCR acquisition, generic crawling, and unsupported attachment-only content.
- Extend DigestContext v2's closed evidence projection with `source_content.text`, `format`, and `truncated` for current news, macro-release, and policy units. Extraction method and document hash remain Feed-only provenance; current-membership, status, limitation, CFTC, and Form 13F behavior remain unchanged.
- Add provider-owned offline document fixtures and regressions for extraction, exact acquisition plans, failure semantics, stable item identity, Feed identity, v4-to-v5 migration, and Reader-first composition with stale CFTC and old Form 13F evidence.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `feed-evidence-pipeline`: Define Feed v5 source-content evidence, Provider-native bounded detail acquisition and extraction, strict completeness and request-budget semantics, identity/migration behavior, and the corrected configured deadline contract.
- `digest-preparation-contract`: Admit only the reader-relevant source-content fields into current DigestContext v2 units without adding network access or changing membership and reference-state rules.
- `digest-presentation-contract`: Permit evidence-preserving summaries of bounded official source content while keeping extraction provenance private and preserving all existing analytical and editorial prohibitions.

## Impact

- Feed contracts and validation: `schemas/feed.schema.json`, `schemas/feed-manifest.schema.json`, bundle/validation/migration constants, identity tests, Feed contract documentation, and current fixtures.
- Provider contracts and runtime: the Federal Reserve, PBOC, SSE, and SZSE manifests/adapters; manifest resolution; managed detail requests; shared document extraction primitives; shared-rate-scope deadline validation; and provider-owned fixtures.
- Digest boundary: `src/follow_the_money/digest.py`, the news/macro/policy domain references, preparation tests, and production-shaped Reader-first regressions.
- No new dependency, model/LLM runtime, credential path, persisted enrichment artifact, second evidence authority, Digest renderer, PDF/OCR support, BLS availability fix, SEC redesign, or CFTC identity change.
