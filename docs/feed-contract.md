# Feed contract

The repository publishes one deterministic, credential-free Evidence Feed. New
production bundles use logical Feed schema major 4, manifest major 4, and
artifact major 2.

## Closed domains

Artifacts are always present and ordered as:

1. `news`
2. `macro_release`
3. `policy`
4. `positioning`
5. `filing`

`market_data`, `flow`, `calendar`, and unknown domains are not current Feed
capabilities. A previous eight-domain major is accepted only by the bounded
migration helper, which validates it first, projects retained evidence, and
recomputes identity before publication.

## Bundle shape

`feed-manifest.json` is the only entry point. It contains the logical Feed
envelope without `items`, plus exactly one generation-qualified artifact entry
for each domain. Each artifact contains only its schema version, bundle
`run_id`, domain discriminator, and evidence items. Empty artifacts are still
required. Artifact paths, byte sizes, hashes, item counts, and inventory order
are validated before any artifact is consumed.

The logical Feed retains:

- one fixed half-open window `[window.start, evidence_cutoff_at)`;
- observed collection lifecycle timestamps;
- exactly eight required Provider outcomes and contract snapshots;
- source provenance, payload-specific source time, freshness, and availability;
- required coverage and bounded blocked-Provider degradation;
- canonical Feed configuration/schema descriptors;
- semantic `content_digest` and cutoff-derived `run_id`;
- evidence-only pipeline status and structured coverage gaps.

Execution observations such as Provider `retrieved_at` and Feed `generated_at`
are not source-semantic timestamps and do not refresh carried evidence.

## Validation and publication

Provider manifests are verified, HTTPS-only, credential-free, and closed over
the five payload types. Normalization validates source URLs before items enter
the Feed. Items are deduplicated and serialized in the deterministic
`(source.knowledge_available_at, id)` order. Intelligence fields and unsupported
payloads fail closed.

Publication writes immutable generation-qualified artifacts, validates the
installed candidate, and atomically activates the manifest. Existing equal
bundles are idempotent; an older active bundle is retained. Invalid or partial
bundles are never consumed.

## Skill consumption

`scripts/skill/prepare-feed` retrieves the canonical manifest first and then its
five declared artifacts. It uses temporary storage, makes no Provider request,
and has no local or stale fallback. Healthy and accepted degraded bundles are
returned with their provenance, warnings, freshness, coverage, and source
availability limits intact.
