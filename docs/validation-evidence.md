# Validation evidence

This document records the current Feed-only verification surface.

## Canonical checks

```bash
uv sync --frozen --all-groups
.venv/bin/pytest
.venv/bin/python scripts/quality_gate.py
openspec doctor
openspec validate simplify-to-feed-only-skill --strict
openspec validate --all --strict
```

Tests use deterministic Provider fixtures and injected clients. They do not
require credentials or live-network access. A real `--dry-run` can still reach
Providers and is not a substitute for fixture tests.

## Required regressions

- the five-domain schema and exact artifact inventory reject removed or mixed
  domains;
- v3/v1 input is accepted only by bounded migration and v4/v2 is the only
  production output;
- all eight Provider manifests resolve credential-free, and over-declared
  payloads fail before requests;
- CFTC weekly empty/unchanged behavior preserves source times and required
  coverage;
- fixed cutoff/window, provenance, freshness, blocked degradation, identity,
  canonical bytes, atomic publication, checkpoint, lease, and rate state fail
  closed;
- remote consumption reads only the canonical manifest-led five-artifact
  product;
- no private invocation, analysis runtime, market analytics, watchlist,
  scoring/ranking, or removed Feed domain is present in current code/config/docs.
