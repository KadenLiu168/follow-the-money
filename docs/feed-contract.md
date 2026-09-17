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

### Item semantic context

`news`, `macro_release`, and `policy` items may contain one closed,
item-level `semantic_context` sibling. Its common envelope contains ordered
entities, a source-semantic event time, and bounded numeric facts; its closed
extension carries news document facts, macro indicator/period/observation and
explicit same-period revision facts, or policy issuer/action/date/scope. The
field is evidence-only and cannot express ranking, sentiment, signal,
prediction, recommendation, market impact, or trading direction. `filing` and
`positioning` items do not use it.

Consumer validation accepts a structurally valid v4 omission for legacy items.
Current Feed construction and `build_bundle` require valid context on every
newly acquired or replacement item in the three affected domains. A complete
contextless prior slice is the only production exception: it must retain its
non-null `carried_forward_from_run_id` and is carried without rewriting its
bytes, whether its existing freshness status is `valid_unchanged` or `stale`.

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
are not source-semantic timestamps and do not refresh carried evidence. SEC v4
filing evidence distinguishes the complete `form13f` current-state contract,
the complete current-window `form4`/`4/A` contract, and the bounded structured
`SCHEDULE 13D`/`13G` beneficial-ownership contract. Form 4 and beneficial-
ownership acceptance times are retained as source publication and knowledge
time; ownership comparison is source-supported and never a market or intent
interpretation.

## Validation and publication

Provider manifests are verified, HTTPS-only, credential-free, and closed over
the five payload types. The SEC v4 manifest bounds Form 4 selection to 20
eligible accessions per issuer/window and Schedule 13D/G selection to the
verified current/history/candidate limits; it declares ownership XML schemas
`X0609` and `X0202`. Selection is listing-bound and fails closed when coverage
or any required raw XML is incomplete. Normalization validates source URLs
before items enter the Feed. Items are deduplicated and serialized in the
deterministic `(source.knowledge_available_at, id)` order. Intelligence fields
and unsupported payloads fail closed.

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

The Skill then projects that validated Feed once into canonical v1
`DigestContext` JSON on stdout. The projection applies the closed domain field
inventory and preserves Feed identity, provenance, freshness, coverage,
warnings, and unavailable states. It is not persisted, published, checkpointed,
cached, or defined by a standalone JSON Schema; Feed artifacts remain the sole
evidence contract and Host-Agent summarization/formatting remains outside the
repository runtime.
