# Architecture

## Boundary

Follow the Money is a deterministic, typed, credential-free Evidence Feed for
Host Agents. Its only repository capability is the Feed:

```text
Provider manifests/config
        ↓
fixed-cutoff collection
        ↓
normalization + provenance + freshness
        ↓
coverage/degradation + deterministic identity
        ↓
canonical five-artifact publication
        ↓
canonical Feed consumption
        ↓
Host Agent evidence-preserving digest presentation
```

The repository does not perform Agent reasoning, financial interpretation,
ranking, prediction, recommendation, trading, or narrative generation. The
Host Agent owns grouping, headings, readability order, consolidation,
compression, semantic-support assessment, and final digest presentation over
the current validated Feed.

## Feed surface

New bundles use logical/manifest major 4 and artifact major 2. The fixed domain
set is:

```text
news | macro_release | policy | positioning | filing
```

Every domain artifact is required. The required credential-free Providers are
Federal Reserve, BLS, PBOC, NBS, SSE, SZSE, SEC EDGAR, and CFTC. CFTC supplies
required weekly positioning coverage. No Provider is selected dynamically and
no removed domain is reconstructed from another source.

## Trust boundaries

Provider manifests are the authority for verified identity, HTTPS URL policy,
source provenance, rate limits, empty-window semantics, implemented payloads,
and cadence. Activation and coverage are separately owned by
`config/providers.yaml`. Configuration and manifest resolution fails closed
before Provider work.

Collection captures a real start, one fixed cutoff before requests, and truthful
completion/generation observations. The half-open window and checkpoint enforce
advancing continuity. Provider freshness uses declared `weekly`, `scheduled`,
or `event_driven` contracts. Source times are never replaced by retrieval or
generation times.

The normal Skill entry is `scripts/skill/prepare-feed`; it retrieves only the
canonical published Feed and has no local fallback. The Feed rejects unsupported
payloads, intelligence fields, invalid provenance, invalid freshness, incomplete required coverage, and non-canonical identity.
Accepted HTTP 401/403 blocked Providers may produce bounded degraded status;
other incomplete required work is fatal. Publication installs immutable
artifacts and atomically activates the manifest. Remote consumption validates
the same manifest-led bundle and has no local fallback.

## Migration

A fully validated previous eight-domain bundle may be supplied only to the
bounded migration helper. It projects retained evidence, replaces the Feed and
Provider/configuration snapshots with the current five-domain contract,
recomputes `content_digest` and `run_id`, and publishes a new generation. Mixed
or corrupt generations fail closed.

## Code map

- `src/follow_the_money/feed/` — Feed planning, normalization support,
  validation, snapshots, bundle publication, deployment, and remote consumption;
- `src/follow_the_money/providers/` — Provider protocol, manifests, HTTP safety,
  locks, rates, and the eight adapters;
- `src/follow_the_money/config/` — closed typed configuration;
- `src/follow_the_money/canonical.py` and `boundary.py` — canonical encoding and
  producer build fingerprint used by Feed identity metadata;
- `schemas/` — logical Feed, manifest, and artifact contracts.
