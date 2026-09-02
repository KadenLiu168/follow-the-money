## Context

See `proposal.md` for motivation and `specs/feed-evidence-pipeline/spec.md` for behavior. Today one canonical schema-v1 envelope is assembled, validated, hashed, and atomically replaced at `feeds/latest.json`; the checkpoint and hosted deployment both bind success to that file. The existing item union already defines the semantic boundary through eight closed `payload.type` discriminators.

A bundle cannot safely replace several fixed filenames one at a time: either the old manifest would temporarily reference new bytes or the new manifest would temporarily reference old bytes. The design therefore needs one atomic activation point while retaining deterministic bytes, fail-closed validation, repository-native publication, and no new storage service or history surface.

## Goals / Non-Goals

**Goals:**

- Reuse the eight existing payload discriminators as the complete domain taxonomy.
- Preserve the existing logical Feed identity projection, evidence items, provenance, ordering, health, cutoff, and checkpoint semantics.
- Make `feed-manifest.json` the only activation/discovery point and permit integrity validation without parsing every evidence payload.
- Keep failed publication from changing the active bundle.
- Provide a zero-network migration from the current valid `latest.json` state.

**Non-Goals:**

- Provider/domain remapping configuration, dynamic domains, bundle history, query APIs, new storage, or a public CLI.
- Any Host Agent, LLM/model, Event, Audit, market analytics, ranking, signal, or narrative integration.
- Changes to payload shapes or Provider acquisition contracts.

## Decisions

### 1. Payload discriminators are the domain taxonomy

Use this fixed order, matching the existing schema union:

1. `news`
2. `macro_release`
3. `policy`
4. `market_data`
5. `flow`
6. `positioning`
7. `filing`
8. `calendar`

Routing is `item["payload"]["type"]`; no lookup configuration or Provider-derived mapping is added. All eight artifacts are emitted, including empty ones. This makes completeness closed and testable and avoids inventing broader business categories.

Alternative considered: combine event-like or market-like payloads. Rejected because those categories do not exist in the accepted evidence model and would add a second taxonomy.

### 2. Keep a logical Feed object as the identity model, then split its serialization

Assembly continues to produce the existing logical Feed fields and globally ordered item list in memory. Existing semantic projection logic computes `content_digest` and `run_id` before physical routing. The producer then moves top-level metadata to the manifest and routes unchanged item objects into domain artifacts.

The manifest retains the logical `feed_schema` descriptor so reconstruction uses the exact existing identity projection. New physical `bundle_schemas` descriptors for the manifest and artifact schemas are integrity metadata excluded from semantic identity, as are inventory paths, sizes, and hashes. Thus a mechanical split of a current valid Feed can retain its `content_digest` and `run_id`; semantic evidence changes still change identity.

Alternative considered: define bundle identity as a hash of artifact hashes. Rejected because it creates a second semantic identity, makes migration unnecessarily breaking, and couples logical identity to file layout. Artifact SHA-256 values remain the physical integrity contract.

### 3. Use one manifest schema and one discriminator-based artifact schema

Add:

- `schemas/feed-manifest.schema.json`
- `schemas/feed-artifact.schema.json`

Retain `schemas/feed.schema.json` for the logical identity model and legacy read compatibility. The artifact schema is one closed envelope with `schema_version`, `run_id`, `domain`, and `items`; conditional schema rules require every item payload type to equal `domain`. Separate schema files per domain would duplicate the unchanged item definitions eight times.

The manifest is closed and carries the existing non-item envelope metadata plus:

- `bundle_schemas`: path/hash descriptors for both physical schemas;
- `artifacts`: fixed-order entries containing `domain`, safe relative `path`, `item_count`, `size_bytes`, and `sha256`.

Domain artifacts do not duplicate cutoff, timestamps, Provider contracts, pipeline state, configuration, or producer metadata.

Alternative considered: eight artifact schemas. Rejected as duplicated contract surface with no distinct payload model.

### 4. Generation-qualified artifact paths make the manifest an atomic pointer

Compute `generation_key = sha256(run_id UTF-8 bytes)[:32]`. The fixed artifact path pattern is:

`feed-<domain>-<generation_key>.json`

All paths are direct children of the explicit Feed product root. Validation rejects absolute paths, separators, traversal, unknown names, a key inconsistent with `run_id`, duplicates, and paths outside the root.

The filename qualifier prevents candidate bytes from overwriting artifacts referenced by the current manifest. These files are current publication mechanics, not a dated archive: only the active manifest inventory is a Feed product. Superseded and failed-candidate files are cleanup state.

Alternative considered: fixed `feed-<domain>.json` paths. Rejected because no portable standard-library operation atomically swaps all files. Generation directories plus a symlink were also rejected because symlink behavior adds portability and repository-policy complexity without improving the manifest commit point.

### 5. Validation has physical and logical phases

Validation performs, in order:

1. Parse and schema-validate canonical manifest bytes.
2. Require the exact domain inventory in fixed order and validate every safe expected path.
3. Read each artifact once; compare byte count and SHA-256 before JSON parsing.
4. Require canonical bytes, artifact schema validity, matching `run_id`/domain, deterministic per-artifact item order, and payload/domain agreement.
5. Merge items using the existing global `(knowledge_available_at, id)` total order and reconstruct the logical Feed.
6. Run existing Feed semantic, numeric, evidence-only, provenance, time, health, digest, and `run_id` validation.
7. For consumption, reject pipeline failure and then apply existing freshness/calendar checks.

A selective consumer may stop parsing non-target artifacts after steps 2–3 verify complete inventory bytes; it parses the selected artifact and manifest metadata. The standard full loader performs all phases. No public query API is added.

### 6. Publication installs artifacts first and manifest last

For a healthy or accepted degraded candidate:

1. Produce and validate all canonical artifact bytes and candidate manifest bytes in memory.
2. Validate the current manifest, when present, and apply existing monotonic ownership rules.
3. Stage every candidate artifact under an unpredictable same-parent name using create-only writes and file `fsync`.
4. Install each generation-qualified final artifact with no-replace semantics; an already-existing identical canonical artifact is reusable, while differing bytes fail closed.
5. `fsync` the product directory and validate the complete candidate from final artifact paths.
6. Stage and `fsync` the manifest, re-check current ownership, enforce pre-commit deadline admission, atomically replace `feed-manifest.json`, and `fsync` the parent directory without cancellation.
7. Remove superseded/candidate-orphan artifact files when safe. Cleanup failure is reported but cannot invalidate or roll back an already activated complete bundle; such files remain undiscoverable and finalization excludes them.

Before step 6, any failure leaves the prior active manifest valid. After manifest rename, durability uncertainty follows the existing fail-without-rollback rule and blocks checkpoint advancement. Idempotence requires matching semantic identity and identical artifact integrity; equal ownership with incompatible physical descriptors or artifacts fails closed.

Alternative considered: dual-write `latest.json` and the bundle. Rejected because there is no single atomic activation point across both contracts and consumers could observe different generations.

### 7. Compatibility is read fallback, not producer dual-write

Consumer selection is strict:

- manifest exists → validate/use bundle only;
- manifest absent → validate/use legacy `latest.json`;
- manifest present but invalid → fail, never fallback.

New producer paths publish only bundles. This preserves startup from existing checked-in state while preventing a stale legacy file from masking bundle corruption.

Repository deployment adds a migration-only mode for valid current state: validate `latest.json` and its matching checkpoint, split it deterministically, activate the bundle, then commit bundle additions and `latest.json` deletion together without Provider work. Rollback before that generated-state commit leaves legacy state intact. Rollback after deployment requires reverting the generated-state commit and software change together; no reverse runtime converter is added.

### 8. Status, checkpoint, deployment, and CI bind to the manifest inventory

Successful status changes `latest_relative_path` to `manifest_relative_path: "feed-manifest.json"`; retaining the old field would falsely describe a product no longer written. `run_id` and cutoff stay unchanged. The checkpoint schema stays unchanged and advances only after durable manifest ownership.

Hosted finalization validates status/checkpoint/manifest identity and every inventory path, then stages the closed set: durable runtime state, checkpoint, lease, manifest, active artifact files, deletion of the immediately superseded artifact set, and migration deletion of `latest.json`. Controlled failure stages no Feed product or checkpoint change.

Generated-state CI exclusion cannot be a broad `feeds/**` pattern. The workflow validator derives and validates the active and immediately superseded closed paths; unexpected or unreferenced Feed paths keep full CI eligible.

## Risks / Trade-offs

- [A manifest commit can leave unreferenced files after a crash or cleanup failure] → They are never discoverable products; deployment finalization excludes them and a later safe cleanup removes only files not referenced by the validated active manifest.
- [Eight artifacts add filesystem and Git churn] → The domain set is fixed and small; no per-Provider or optional artifact expansion is allowed.
- [Legacy-only external consumers stop receiving updates] → Document the breaking producer switch and manifest contract; retain only manifest-absent legacy reads because dual-write would weaken atomicity.
- [The current logical Feed schema remains part of identity despite split storage] → Keep it as the canonical logical projection/legacy schema rather than duplicate identity code; remove it only in a future explicitly breaking identity Change.
- [Publication can activate a bundle and then fail directory `fsync`] → Preserve the existing durability-unknown behavior: no rollback claim and no checkpoint advancement.

## Migration Plan

1. Ship schemas, deterministic split/reconstruction validation, consumer manifest-first fallback, and tests while current checked-in `latest.json` remains readable.
2. Extend publication, status, checkpoint matching, deployment state classification/finalization, workflow validation, and generated-state path handling.
3. On the first hosted invocation with valid legacy product state, run migration-only: create and validate the equivalent bundle, activate its manifest, commit the exact bundle plus `latest.json` deletion, and exit without network collection.
4. On the next invocation, follow the normal bundle generation path.
5. Roll back pre-migration by reverting code only; roll back post-migration by reverting code and the migration generated-state commit together so legacy consumer and product state stay aligned.
