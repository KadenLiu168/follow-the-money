# Follow the Money

A credential-free, deterministic five-domain Evidence Feed for Host Agents.
The repository provides an evidence-based information digest skill boundary:
it collects, normalizes, validates, and publishes evidence; the Host Agent
consumes the current Feed and produces an evidence-preserving information
digest.

## Capability boundary

The repository exposes one capability: the Evidence Feed. It owns Provider
contracts, provenance, fixed-cutoff collection, freshness, coverage,
degradation, deterministic identity, canonical serialization, atomic
publication, and canonical current-Feed consumption.

The normal path is:

```text
published Feed -> validation -> Host Agent summarization/formatting -> information digest
```

The Feed contains no financial interpretation, importance, ranking, regime,
market-impact, prediction, recommendation, or trading conclusion. The Host
Agent may group, order, consolidate, and compress evidence for readability,
but must preserve semantic support and disclose omissions.

## Current Feed contract

New bundles use logical Feed schema major **4**, manifest major **4**, and
artifact major **2**. The fixed artifact order is the retained evidence surface:

```text
news
macro_release
policy
positioning
filing
```

Every artifact is required, including when empty. The required credential-free
Providers are Federal Reserve, BLS, PBOC, NBS, SSE, SZSE, SEC EDGAR, and CFTC.
CFTC is a required minimum-one weekly positioning coverage member.

A validated previous eight-domain bundle may enter only the explicit bounded
migration path. Normal loading and remote consumption reject the previous
major and never use removed-domain artifacts as current evidence.

## Repository layout

```text
config/                    closed Feed configuration and Provider activation
providers/                 verified Provider manifests and deterministic fixtures
schemas/                   Feed, manifest, and artifact JSON Schemas
src/follow_the_money/feed  producer, validation, publication, and consumption
scripts/feed/              internal deterministic producer entry
scripts/skill/             canonical published-Feed consumer entry
feeds/                     current manifest-led Feed product
.feed-state/               lock, rate registry, lease, and checkpoint state
tests/                     credential-free tests
docs/                     current Feed contracts and runbooks
.github/workflows/         CI and scheduled Feed production
```

## Quick start

```bash
uv sync --frozen --all-groups
uv run pytest
scripts/skill/prepare-feed
scripts/feed/follow-the-money-feed --dry-run
```

The producer requires no API key or paid data credential. The normal Skill
consumer retrieves `feeds/feed-manifest.json` from canonical `main`, then
retrieves exactly the five manifest-declared artifacts. It performs no local,
stale, partial, historical, or unvalidated fallback.

## Exit codes

- `0` — healthy or accepted degraded Feed
- `1` — Feed generation, publication, schema, or integrity failure
- `2` — usage, configuration, or startup-capability failure

## Scheduled production

GitHub Actions runs the Feed producer on the configured schedule or via
`workflow_dispatch`. Collection state uses `.feed-state/`; the active product
uses `feeds/`. Fixed cutoff/window planning, Provider freshness and provenance,
required coverage, bounded blocked-Provider degradation, atomic manifest
activation, checkpoint continuity, and durable rate safety remain enforced.

See [`docs/feed-contract.md`](docs/feed-contract.md),
[`docs/configuration.md`](docs/configuration.md), and
[`docs/architecture.md`](docs/architecture.md) for the current contracts.
