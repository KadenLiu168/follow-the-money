# Validation evidence

This document records the current Feed-only verification surface.

## Canonical checks

```bash
uv sync --frozen --all-groups
.venv/bin/pytest
.venv/bin/python scripts/quality_gate.py
openspec doctor
openspec validate eco-131-sec-form4-semantic-evidence --strict
openspec validate --all --strict
```

Tests use deterministic Provider fixtures and injected clients. They do not
require credentials or live-network access. A real `--dry-run` can still reach
Providers and is not a substitute for fixture tests.

## Required regressions

- the five-domain schema and exact artifact inventory reject removed or mixed
  domains;
- Feed schema major 4 remains the only production output; bounded migration
  handles the previous Feed major, while SEC v1/v2 bundles remain readable and
  SEC v3 is the only shipped SEC producer contract;
- all eight Provider manifests resolve credential-free, and over-declared
  payloads fail before requests;
- CFTC weekly empty/unchanged behavior preserves source times and required
  coverage;
- SEC Form 4 selection proves recent-listing coverage, exact half-open-window
  membership, the 20-filing bound, raw XML provenance, structured owners/table
  entries/footnotes, and independent Form 4/A identity without analysis;
- SEC v3 mixed 13F/Form 4 slices enforce exact watched-company and selected
  accession sets, whole-Provider replacement, deterministic bytes, and
  fail-closed partial acquisition;
- fixed cutoff/window, provenance, freshness, blocked degradation, identity,
  canonical bytes, atomic publication, checkpoint, lease, and rate state fail
  closed;
- remote consumption reads only the canonical manifest-led five-artifact
  product;
- no private invocation, analysis runtime, market analytics, watchlist,
  scoring/ranking, or removed Feed domain is present in current code/config/docs.
