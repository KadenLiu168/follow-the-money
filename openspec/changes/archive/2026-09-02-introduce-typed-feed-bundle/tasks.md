## 1. Bundle Schemas and Deterministic Model

- [x] 1.1 Add closed `feed-manifest.schema.json` and discriminator-based `feed-artifact.schema.json`, reuse the existing item definitions without changing payload shapes, and verify valid/unknown/mismatched domain fixtures with focused schema tests.
- [x] 1.2 Add the fixed eight-domain order, generation-key/path derivation, deterministic split, and logical reconstruction helpers; verify permutations route each item once, emit empty artifacts, preserve global ordering/provenance, and round-trip the existing `content_digest`/`run_id`.

## 2. Bundle Validation and Consumption

- [x] 2.1 Implement canonical manifest/artifact validation for exact inventory, safe paths, byte size, SHA-256, schema versions, domain/type agreement, shared `run_id`, item count, and reconstructed Feed semantics; verify missing, extra, corrupt, reordered, traversal, mixed-generation, and identity-invalid bundles fail closed.
- [x] 2.2 Update the internal Feed loader to prefer a present manifest, reject invalid bundles without fallback, and read legacy `latest.json` only when the manifest is absent; verify healthy/degraded/failure, freshness, calendar horizon, provenance, and selective-domain behavior remain correct.

## 3. Generation and Atomic Publication

- [x] 3.1 Change Feed assembly and dry-run results to produce one manifest plus eight canonical artifact candidates while retaining existing collection, coverage, cutoff, lifecycle, and evidence-only behavior; verify deterministic bytes and no product/checkpoint writes during dry-run.
- [x] 3.2 Replace single-file publication with generation-qualified artifact installation followed by atomic manifest activation, monotonic ownership, idempotence, deadline admission, `fsync`, and safe orphan/superseded cleanup; verify failures at each pre-manifest stage preserve the prior active bundle and post-rename durability uncertainty does not advance continuity.
- [x] 3.3 Update successful status and checkpoint handling to bind `manifest_relative_path`, cutoff, and `run_id` to accepted manifest ownership; verify source failure, stale ownership, dry-run, publication failure, and checkpoint failure retain their existing typed exits and continuity guarantees.

## 4. Repository Deployment and Migration

- [x] 4.1 Add zero-network current-state migration from a valid checkpoint-matched `latest.json` to an identity-equivalent bundle and reject partial/mixed/invalid state; verify migration exits before Provider work and leaves legacy state unchanged on failure.
- [x] 4.2 Update deployment admission/finalization to validate and stage only runtime state, checkpoint, manifest, its exact active artifacts, superseded deletions, and migration deletion of `latest.json`; verify controlled failure stages no Feed product or checkpoint change and Git publication remains non-force fast-forward.
- [x] 4.3 Update workflow and generated-state CI path validation for the closed bundle set without broad `feeds/**` exclusions; verify valid generated-only commits skip recursive full CI while unreferenced artifacts or mixed source changes remain eligible.

## 5. Contract Regression and Documentation

- [x] 5.1 Update Feed boundary, determinism, pipeline, deployment, CLI, engine, no-LLM, and Phase 5 integration tests/fixtures for manifest discovery, artifact integrity, mixed/incomplete generations, provenance preservation, empty domains, idempotence, and publication failure behavior; run the focused Feed test set successfully.
- [x] 5.2 Update `docs/feed-contract.md`, architecture/runbooks, `SKILL.md`, README files, schema references, and generated product examples to describe only the implemented manifest-led contract and manifest-absent legacy read path; verify repository searches reveal no stale claim that new production writes only `feeds/latest.json`.

## 6. Acceptance Gates

- [x] 6.1 Run `openspec doctor`, `openspec validate introduce-typed-feed-bundle --strict`, and `openspec validate --all --strict`; resolve every contract validation failure.
- [x] 6.2 Run `.venv/bin/python scripts/quality_gate.py` and verify the canonical repository quality gate passes without a real-network Feed dry run.
