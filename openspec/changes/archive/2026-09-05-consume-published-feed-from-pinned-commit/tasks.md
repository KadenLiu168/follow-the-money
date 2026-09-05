## 1. Shared Manifest Validation Boundary

- [x] 1.1 Add focused failing tests for canonical manifest pre-validation, exact ordered safe inventory extraction, and unchanged local bundle loading; verify the new tests fail for the missing shared seam while existing bundle tests still pass.
- [x] 1.2 Extract the minimum shared manifest-and-inventory validation operation in `feed.bundle`, route `validate_bundle()` through it without changing local or legacy behavior, and verify the focused bundle tests pass.

## 2. Commit-Pinned Remote Consumer

- [x] 2.1 Add deterministic `httpx.MockTransport` tests proving valid Git reference resolution, one-SHA pinning across manifest and artifact requests, manifest-only discovery, healthy logical Feed output, closed source constants, and rejection of invalid discovery responses; verify the tests fail before the remote consumer exists.
- [x] 2.2 Implement the minimal remote consumer with explicit finite HTTP bounds, temporary isolated storage, manifest-declared artifact retrieval, and final `load_feed()` reuse; verify the commit-resolution, pinning, discovery, and healthy-bundle tests pass.
- [x] 2.3 Add parameterized remote integration regressions for degraded warning/availability preservation, missing or short/oversized artifacts, SHA-256 and schema mismatch, mixed generation, Feed identity mismatch, `pipeline.status = failure`, timeout, HTTP/rate-limit failure, and cleanup; verify every failure exposes no logical Feed.
- [x] 2.4 Add the no-local-fallback regression proving remote failure never imports or invokes Provider collection, the local producer, or deployment and never mutates repository `feeds/`, `.feed-state/`, or a stale local Feed; verify the focused boundary test passes.

## 3. Internal Skill Entry and Truthful Documentation

- [x] 3.1 Add `scripts/skill/prepare-feed` with the existing physical-repository-root and virtualenv launcher convention, canonical logical Feed stdout, precise stderr, fixed source, and no producer/configuration options; verify launcher success, failure exit behavior, and symlinked invocation outside the checkout with focused tests.
- [x] 3.2 Update `SKILL.md`, `README.md`, `README.zh-CN.md`, `docs/architecture.md`, and `docs/feed-contract.md` so normal Skill invocation uses only the commit-pinned remote consumer while local generation remains explicitly hosted/development/test/diagnostic/operator-only; verify static caller/documentation regressions reject a normal local-producer or fallback claim.
- [x] 3.3 Verify the Change introduced no Feed schema, dependency, GitHub Actions, Provider, Audit/Event, retained-capability wiring, persistent cache, arbitrary source option, or consumer-age policy changes by inspecting the final scoped diff and running the relevant architecture/no-LLM boundary tests.

## 4. Acceptance Verification

- [x] 4.1 Run the focused bundle, remote consumer, launcher, Feed boundary, and documentation/caller-graph tests and record their passing results without invoking a real Provider dry-run.
- [x] 4.2 Run `.venv/bin/python scripts/quality_gate.py` and verify the canonical repository gate passes on the stable final diff.
- [x] 4.3 Run `openspec doctor`, `openspec validate consume-published-feed-from-pinned-commit --strict`, `openspec validate --all --strict`, and `git diff --check`; verify all checks pass and report any unresolved conflict or risk without archiving, committing, pushing, or updating Linear.
