# Follow the Money

A credential-free, deterministic five-domain Evidence Feed for Host Agents.
The repository provides an evidence-based information digest skill boundary:
it collects, normalizes, validates, and publishes evidence; the Skill prepares
one non-persisted Feed-bound `DigestContext` version `2`; the Host Agent consumes
its prepared current updates and produces an evidence-preserving information
digest.

## Capability boundary

The repository exposes one capability: the Evidence Feed. It owns Provider
contracts, provenance, fixed-cutoff collection, freshness, coverage,
degradation, deterministic identity, canonical serialization, atomic
publication, and canonical current-Feed consumption.

The normal path is:

```text
validated Feed -> DigestContext -> Host Agent -> evidence-preserving Digest
```

The Feed contains no financial interpretation, importance, ranking, regime,
market-impact, prediction, recommendation, or trading conclusion. The Host
Agent may group, order, consolidate, and compress the prepared current updates
for readability, but must preserve claim-level semantic support, and it does
not reclassify Feed evidence or account for every Feed item.

## Current Feed contract

New bundles use logical Feed schema major **5**, manifest major **5**, and
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
CFTC is a required minimum-one weekly positioning coverage member. SEC EDGAR
v4 filing items distinguish complete `form13f` current-state evidence, bounded
current-window `form4`/`4/A` ownership evidence, and bounded structured
`SCHEDULE 13D`/`13G` beneficial-ownership evidence. Form 4 items retain
issuer, reporting-owner, transaction/holding, post-state, and footnote data;
beneficial-ownership items retain source-supported issuer/class identity,
reporting positions, typed ownership facts, and conservative comparison states.
Neither subtype infers deltas, amendment lineage, intent, control, or market
impact. SEC v1-v3 reads remain bounded compatibility paths. CFTC v2 positioning
items expose market-code identity, typed current/previous metrics, deltas, and
an explicit net-position derivation; these fields are evidence only and do not
express market impact or direction.

Newly acquired or replaced `news`, `macro_release`, and `policy` items carry
the closed item-level `semantic_context` field. It contains only
source-supported subjects, event/document facts, bounded numeric observations,
macro periods or revisions, and policy dates or affected scope. It does not
rank evidence, state sentiment or market impact, make predictions, or provide
recommendations. `filing` and `positioning` items do not carry this field.
The published consumer still accepts a structurally valid legacy omission; a
contextless prior slice may be carried byte-for-byte only with its existing
carry-forward proof, while new or replacement affected items require valid
context.

`news`, `macro_release`, and `policy` items may also carry the closed
`source_content` field: bounded NFC plain text of one official document
(at most 12,000 code points), its `format`, its `truncated` state, and the
SHA-256 of the exact admitted raw response bytes. The Federal Reserve, PBOC,
SSE, and SZSE v2 Provider contracts require it for every selected
current-window item they acquire, so an unavailable, unsupported, unsafe,
oversized, or unextractable required document leaves the Provider incomplete
instead of producing a healthy title-only item. Bounded text never
reconstructs an absent structured semantic field, and DigestContext exposes
only `text`, `format`, and `truncated` — extraction method and document digest
stay Feed-only provenance.

A validated immediate-previous-major bundle may enter only the explicit
bounded migration path. Normal loading and remote consumption reject the
previous major and every older major, and never treat carried previous-major
evidence as a fresh acquisition.

## Repository layout

```text
config/                    closed Feed configuration and Provider activation
providers/                 verified Provider manifests and deterministic fixtures
schemas/                   Feed, manifest, and artifact JSON Schemas
src/follow_the_money/feed  producer, validation, publication, and consumption
src/follow_the_money/digest.py  deterministic non-persisted DigestContext v2 preparation
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
retrieves exactly the five manifest-declared artifacts and emits one canonical
`DigestContext` version `2` to stdout. The context is not persisted and does not
replace Feed authority or define an independent evidence schema. The consumer performs
no local, stale, partial, historical, or unvalidated fallback.

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
