# Validation evidence

This document records the current Feed-only verification surface.

## Canonical checks

```bash
uv sync --frozen --all-groups
.venv/bin/pytest
.venv/bin/python scripts/quality_gate.py
openspec doctor
openspec validate add-source-content-enrichment --strict
openspec validate --all --strict
```

Tests use deterministic Provider fixtures and injected clients. They do not
require credentials or live-network access. A real `--dry-run` can still reach
Providers and is not a substitute for fixture tests.

## Required regressions

- the five-domain schema and exact artifact inventory reject removed or mixed
  domains;
- Feed schema major 5 is the only production output and the physical
  five-domain artifact major is unchanged; bounded migration handles only the
  immediate previous Feed major and every older major is rejected, while SEC
  v1/v2 bundles remain readable and SEC v4 is the only shipped SEC producer
  contract, with bounded SEC v1-v3 compatibility reads;
- the Federal Reserve, PBOC, SSE, and SZSE v2 contracts acquire every selected
  current-window official detail document, extract bounded NFC plain text from
  a verified container, and fail the whole Provider slice on any missing,
  unsupported, unsafe, oversized, unextractable, or attachment-only document;
- Feed v5 source content is a closed item member: it is admissible only in
  `news`, `macro_release`, and `policy` payloads, rejects malformed, misplaced,
  non-NFC, over-bound, or smuggled placement, and requires valid content for
  every item a target Provider acquired in current production while carried
  previous-major evidence may omit it;
- bounded official source content drives DigestContext v2 as reader-relevant
  `text`, `format`, and `truncated` only, with byte-identical repeated
  preparation and no URL or document access, while extraction method and
  document digest stay Feed-only;
- all eight Provider manifests resolve credential-free, and over-declared
  payloads fail before requests;
- CFTC weekly empty/unchanged behavior preserves source times and required
  coverage;
- SEC Form 4 selection proves recent-listing coverage, exact half-open-window
  membership, the 20-filing bound, raw XML provenance, structured owners/table
  entries/footnotes, and independent Form 4/A identity without analysis;
- SEC Schedule 13D/G selection and parsing prove bounded current/history
  coverage, safe raw XML provenance, issuer/class identity, source-ordered
  positions, typed facts, conservative comparison states, and no inferred
  intent/control/market-impact semantics;
- SEC v4 mixed 13F/Form 4/13D-G slices enforce exact watched-company, watched-
  issuer, and watched-filer accession sets, whole-Provider replacement,
  deterministic bytes, and fail-closed partial acquisition;
- fixed cutoff/window, provenance, freshness, blocked degradation, identity,
  canonical bytes, atomic publication, checkpoint, lease, and rate state fail
  closed;
- remote consumption reads only the canonical manifest-led five-artifact
  product;
- no private invocation, analysis runtime, market analytics, watchlist,
  scoring/ranking, or removed Feed domain is present in current code/config/docs.

## Known follow-ups

- The BLS and NBS adapters still discover candidates through the generic
  link-and-date HTML index reader. Their contracts remain single-resource and
  outside this Change; a verified container-driven contract for them, and any
  availability fix, belongs to a separate reviewed change.
- Exchange discovery reads the verified SZSE embedded `curHref`/`curTitle`
  literals because that list is written by inline script. If SZSE replaces the
  list with a server-rendered list, the recorded fixture and manifest
  verification date must be refreshed.
- The recorded fixture for the immediate previous Feed major is produced in
  tests by the previous release's writer; no production path emits it.
