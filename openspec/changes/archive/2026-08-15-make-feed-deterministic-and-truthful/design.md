## Context

See `proposal.md` for motivation. The live path collects providers concurrently, stores outcomes in a mapping, deduplicates after collection, builds a schema-v1 envelope, recomputes identity from every top-level field except `content_digest` and `run_id`, and publishes module-local JSON bytes. `_build_feed()` currently derives `collection_started_at` from `cutoff - 30s`, copies completion time into `generated_at`, and serializes `outcomes.values()` directly. Publication treats same-path byte differences as incompatible even when the future `run_id` identifies the same semantic evidence.

The existing publication contract is valuable and remains fixed: dated artifacts are create-only, latest ownership is monotonic by `(evidence_cutoff_at, content_digest)`, staging and replacement are atomic, and file/directory `fsync` boundaries remain authoritative. Existing schema-v1 artifacts also need to remain readable after identity semantics change.

## Goals / Non-Goals

**Goals:**

- Make scheduling and input permutations irrelevant to the normalized semantic Feed.
- Make each persisted audit timestamp correspond to an observed lifecycle event.
- Give `content_digest` one explicit, reviewable semantic projection.
- Preserve canonical publication, immutable history, crash recovery, and old schema-v1 readability.

**Non-Goals:**

- Reworking provider adapters, retry/rate/deadline contracts, collection concurrency, or coverage policy.
- Adding a second artifact for each repeated execution or an execution-log subsystem.
- Changing the Feed schema major, Agent inputs, deterministic research libraries, or publication durability primitives.
- Claiming that `content_digest` cryptographically covers execution audit metadata; it becomes a semantic identity digest.

## Decisions

### 1. Normalize unordered inputs before any order-sensitive operation

Create provider outcomes for the collection plan by stable `provider_id` key before concurrent work begins. Workers update only their keyed outcome; envelope construction serializes the mapping in ascending `provider_id` order. This produces one deterministic representation for healthy, empty, partial, failed, and skipped terminal states without serializing completion order.

Use one item total-order helper with key `(source.knowledge_available_at, id)`. Apply it before URL grouping, before same-source near-dedup comparison, when selecting the first survivor, when constructing `source_lineage`, and for final `items`. Observation ordering remains governed by its existing timestamp-specific contract. Provider contracts and any other set-like projection members are likewise sorted by their declared stable identity.

Alternative considered: sort only the final arrays. Rejected because it cannot repair an earlier order-dependent survivor or lineage choice.

### 2. Capture lifecycle instants in orchestration and pass them explicitly

The orchestration clock remains injectable. Capture `collection_started_at` at the actual collection phase entry, then capture the single cutoff before any provider request. Record `retrieved_at` immediately when a response returns and before normalization. Capture `collection_completed_at` after provider futures have resolved or been safely fenced and outcome aggregation is complete. Assemble all semantic and audit fields, then capture `generated_at` at the final envelope-generation boundary before identity fields are attached.

The builder receives these captured values; it does not calculate offsets, call `max(cutoff, completed)`, or reuse completion as generation time. Validation retains null `retrieved_at` for providers with no observed response and enforces the lifecycle partial order for every non-null retrieval timestamp.

Alternative considered: preserve deterministic fixture timestamps by deriving them from cutoff. Rejected because deterministic tests can inject a deterministic clock without fabricating production audit events.

### 3. Hash an allowlisted semantic projection

Introduce one projection owner used by both producer and validator. It constructs a new mapping rather than deleting fields from the full envelope. Its top-level members are:

- `schema_version`, `window`, and `evidence_cutoff_at`;
- `provider_outcomes`, ordered by `provider_id`, with `retrieved_at` removed and all other current outcome fields retained;
- `producer`, `feed_config`, `feed_schema`, and `provider_contracts`;
- normalized `items`;
- the pipeline semantic result: `status` and structured `coverage_gap` (free-form execution reporting is not promoted into identity).

`collection_started_at`, `collection_completed_at`, `generated_at`, every provider `retrieved_at`, top-level `git`, `content_digest`, `run_id`, and any future undeclared execution metadata are outside this projection. `canonical_digest(projection)` yields `content_digest`; the existing cutoff-plus-digest format yields `run_id`.

The allowlist makes schema evolution fail visibly: a new semantic field must be deliberately added to the projection and tests. A delete-fields approach was rejected because new runtime metadata would silently enter identity unless every caller remembered to exclude it.

### 4. Read legacy identity, write semantic identity

Changing the projection without a schema-major bump would otherwise make the current `latest.json` fail validation and block the next run. Validation therefore attempts the new semantic projection first and, only on identity mismatch for a supported existing schema-v1 artifact, verifies the former whole-envelope projection. Producers never emit the legacy form after this change.

This is a narrow read-compatibility path, not identity ambiguity: the embedded digest and cutoff-derived `run_id` must match one complete projection exactly. Tests use literal legacy and semantic vectors so the fallback cannot become a permissive partial check. After the first new publication, `latest.json` naturally advances to the semantic form while immutable historical artifacts remain consumable.

Alternative considered: add an identity-version field within schema v1. Rejected because the closed schema and same-major cross-build contract would make that additive field incompatible with existing consumers. A major bump is explicitly out of scope.

### 5. Canonical bytes are the only Feed publication bytes

The orchestration serializes the fully validated envelope once with shared `canonical_bytes()`. The same bytes are supplied as dated and latest candidates. Publisher-side parsing continues to require canonical JSON and tests assert that any Feed admitted to publication round-trips byte-for-byte through `canonical_bytes()`.

This rule applies to Feed artifacts, not unrelated status output, rate-registry JSON, provider response fixtures, or other non-Feed JSON paths.

### 6. Existing immutable bytes win repeated semantic execution

For a new semantic `run_id`, publication follows the existing create-only dated then atomic latest path. If the dated path already exists, publication validates its canonical Feed, checks that filename/embedded `run_id`, cutoff, and semantic `content_digest` match the candidate, and retains the existing bytes even when excluded audit metadata differs.

Any latest repair or replacement for that idempotent run uses bytes read from the retained dated artifact. This preserves the invariant that latest and dated views of one run are identical and avoids overwriting truthful audit history from the first completed publication. The later execution still returns its own truthful in-memory audit envelope, but it does not create a second persisted execution record.

Invalid existing bytes or a semantic mismatch at the same path still fail closed. Latest ownership comparisons and all staging, admission-deadline, atomic-replace, recovery, and `fsync` behavior remain unchanged.

Alternative considered: overwrite the dated artifact with the later audit envelope or mint an execution-specific suffix. Both violate the existing immutable single-`run_id` publication architecture.

## Risks / Trade-offs

- [Audit timestamps are no longer covered by `content_digest`] → Keep strict timestamp/schema validation, canonical immutable artifact bytes, and publication integrity checks; document `content_digest` as semantic identity rather than a whole-file checksum.
- [Legacy fallback could accept an unintended invalid artifact] → Require exact success under either the full new projection or the full former projection, with matching cutoff-derived `run_id`; cover both with known vectors and mutation tests.
- [An unordered nested member could escape normalization] → Centralize total-order helpers and add permutation tests that compare normalized projections, digests, run IDs, lineage, and canonical bytes where audit timestamps are held constant.
- [Repeated execution audit metadata is not persisted] → Treat the first immutable artifact as the audit record for that semantic run; do not add an execution-log architecture in this Change.
- [Free-form warning text is outside identity] → Keep structured provider outcomes plus pipeline `status` and `coverage_gap` in the projection; warnings remain truthful diagnostics and cannot silently change the semantic status.

## Migration Plan

1. Add RED regression vectors for legacy identity, semantic/runtime separation, provider schedules, item permutations, lifecycle clocks, canonical bytes, and repeated semantic publication.
2. Introduce normalization and semantic-projection behavior while preserving legacy read validation.
3. Switch new Feed serialization and publication to canonical semantic identity.
4. Run focused Feed/provider/publication tests, full tests, repository quality gates, and strict OpenSpec validation.

Rollback is code-only: reverting the writer restores legacy identity generation. Semantic artifacts already published under distinct run IDs remain immutable schema-v1 Feed artifacts; a rollback reader must not be deployed if it cannot validate those artifacts, so rollback validation must retain the semantic-reader path or occur before any semantic artifact is published.
