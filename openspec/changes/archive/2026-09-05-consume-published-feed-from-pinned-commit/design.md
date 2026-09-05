## Context

See `proposal.md` for motivation. The repository already has a manifest-led bundle validator and logical Feed loader, while normal Skill instructions still allow the local producer. The validator currently receives a complete filesystem directory: remote retrieval must inspect a manifest before all artifact files exist, so the design needs one shared pre-validation seam without creating a second semantic validator.

The canonical public source is closed to repository `KadenLiu168/follow-the-money`, branch `main`, product root `feeds/`. The existing logical Feed and three bundle schemas remain authoritative. The implementation already depends on `httpx`; no GitHub SDK, GitHub CLI, Node runtime, token, or new dependency is needed.

## Goals / Non-Goals

**Goals:**

- Make one normal Skill invocation consume one immutable Git commit snapshot.
- Reuse one manifest/inventory authority before retrieval and the existing complete bundle loader after retrieval.
- Give the Host Agent canonical logical Feed JSON on stdout and precise failure diagnostics without persistent Feed state.
- Preserve the local producer unchanged as an explicitly operated capability.

**Non-Goals:**

- No generic remote Feed SDK, configurable repository/branch/URL registry, persistent cache, archive, or historical query API.
- No Provider, schema, Feed identity, GitHub Actions publication, or producer retry/rate behavior changes.
- No consumer-age threshold, Provider recheck, fallback source, Agent orchestration, LLM runtime, or wiring of retained capabilities.

## Decisions

### 1. Resolve one closed Git reference, then use only commit-qualified raw URLs

The consumer will resolve `refs/heads/main` through GitHub's public Git reference API and require a successful response whose object is a commit with a syntactically valid exact SHA. Resolution occurs once after any bounded discovery attempt succeeds. Every later URL is constructed from constants plus that SHA; artifact retries, if implemented, remain on the same URL.

Redirects to a renamed repository or another host are not source discovery. Unexpected status, host transition, response shape, object type, or SHA fails closed. Anonymous GitHub rate limiting remains an ordinary typed discovery failure rather than a reason to add credentials or fallback.

Alternatives rejected:

- Mutable `raw/.../main/...` reads retain the cross-commit race.
- `git clone`, `git ls-remote`, or GitHub CLI add runtime/tooling assumptions not needed for public HTTP consumption.
- GitHub repository archives download unrelated content and bypass manifest-led discovery.

### 2. Extract one shared manifest-and-inventory pre-validation operation

`feed.bundle` will expose the smallest operation needed to accept canonical manifest bytes and return the validated manifest plus its exact ordered safe artifact paths. It will own the existing canonical JSON, manifest schema/major, cutoff consistency, fixed domain order, generation-qualified path, and path-safety rules. `validate_bundle()` will use the same operation before opening local files, so rules are moved rather than copied.

The remote consumer will use only the returned paths. After all exact bytes are present in a temporary product root, it will call `load_feed()` rather than reconstructing or validating Feed semantics itself. Because the manifest exists in that temporary root, legacy `latest.json` compatibility cannot activate; `load_feed()` also retains the existing `pipeline.status = failure` rejection that `validate_bundle()` alone does not provide.

Alternatives rejected:

- Parsing inventory and duplicating path checks in the remote module creates two trust authorities.
- Inferring filenames from domains and `run_id` violates the manifest-only authority even if the names happen to match.
- Adding an artifact-loader callback throughout bundle validation changes more proven code than the temporary-directory adapter.

### 3. Keep transport small, bounded, and injectable only at the HTTP client seam

The implementation will use the existing `httpx` dependency with explicit finite timeouts. Tests will pass `httpx.MockTransport` through a client seam; there will be no remote-source interface, registry, or plugin abstraction.

The manifest read will have a finite transport-size bound before parsing. Each artifact will be streamed into the temporary directory and stopped if it exceeds its manifest-declared byte size; a short response also fails. The existing bundle validator remains responsible for exact size, SHA-256, canonical bytes, schema, binding, ordering, provenance, content digest, and Feed identity. No partially downloaded object is exposed.

Initial implementation need not add automatic retry: zero retries is bounded and a later explicit invocation can retry. If a small retry is justified during Apply, only the same discovery operation may be retried before a SHA is selected, and only the same commit-qualified object URL may be retried afterward; retry count and eligible transport failures must remain fixed and tested.

### 4. Emit only the existing logical Feed representation

The Python consumer operation returns the existing logical Feed mapping. The internal entry writes its canonical JSON bytes to stdout on success and writes precise typed discovery, HTTP, inventory, or bundle errors to stderr with nonzero exit status. The resolved publication SHA may be included in non-semantic diagnostics but must not be injected into Feed data, schema, `content_digest`, or `run_id`.

The launcher will mirror the existing physical-repository-root and repository virtualenv behavior so symlinked Skill installations work outside the checkout. It accepts no repository, branch, URL, token, cache, or producer options.

### 5. Do not activate invocation-time stale-Feed policy

Remote preparation calls the bundle loader but not `engine.feed_health.assess_health()` or `check_calendar_horizon()`. Those functions contain invocation-time thresholds and currently have no production caller. Activating them would create a consumer-age product policy contrary to this Change and would make a daily Feed unusable for much of each day.

Embedded Provider freshness, availability, timestamps, pipeline warnings, structural calendar semantics, and identity continue through existing Feed validation. A future consumer-age policy requires a separate product decision.

### 6. Enforce producer/consumer separation through the available repository boundary

The repository cannot control arbitrary third-party Agent behavior. It will make the supported path unambiguous: normal Skill instructions call only the remote consumer entry, the remote module imports no producer/deployment/Provider path, and static regressions prove failure never calls or mutates them. The existing producer launcher and modules remain available and are documented only for hosted/development/diagnostic/operator use.

## Risks / Trade-offs

- [Anonymous GitHub API quota or outage prevents retrieval] -> Surface the exact typed failure and stop; never introduce a hidden credential or local producer fallback.
- [A valid future manifest exceeds the transport bound] -> Fail explicitly; adjust the documented safety bound in a later deliberate compatibility change rather than accepting unbounded input.
- [Remote transport rules drift from local bundle rules] -> Keep manifest/inventory validation in `feed.bundle` and test both local and remote callers through it.
- [A Host Agent bypasses the documented entry] -> Keep the normative Skill contract and caller graph explicit; do not claim enforcement outside this repository's provided path.
- [A newer remote schema major reaches an older installed Skill] -> Preserve existing supported-major rejection; producer/consumer build equality is not required, but unsupported contracts fail closed.

## Migration Plan

1. Add the shared manifest pre-validation seam and focused regressions without changing accepted local bundle behavior.
2. Add the remote consumer and internal launcher with deterministic mocked HTTP tests.
3. Update Skill and architecture/contract documentation so normal invocation names only the remote entry and local generation is explicitly operator/development/hosted.
4. Run focused tests, the canonical repository quality gate, OpenSpec strict validation, doctor, and whitespace checks. Do not use a real Provider dry-run.

Rollback removes the remote entry and restores the prior Skill documentation; the unchanged local producer and published bundle remain available throughout. Archive, delivery, and hosted acceptance remain separately authorized.
