## Context

See `proposal.md` for motivation. The normal Skill path currently performs one GitHub REST API request to resolve `main`, then downloads a manifest-led Feed bundle from commit-qualified raw URLs. The manifest already closes artifact discovery and records each artifact's path, size, digest, schema/generation identity, while logical reconstruction validates Feed identity and consumability.

The requested transport removes immutable commit pinning. Because `main` may advance between requests, transport can no longer guarantee that every response came from one Git tree; the existing bundle validators must remain the authority that rejects unavailable or mixed responses before any logical Feed is emitted.

## Goals / Non-Goals

**Goals:**

- Make every normal Skill network request target the fixed canonical `raw.githubusercontent.com/KadenLiu168/follow-the-money/main/feeds/` root.
- Keep manifest-first artifact discovery and the complete existing validation path intact.
- Keep remote failure terminal and temporary storage isolated.
- Make tests prove both the absence of GitHub REST API traffic and preservation of fail-closed bundle validation.

**Non-Goals:**

- Adding retries, caching, fallback branches, local products, Provider collection, authentication, or a second consistency mechanism.
- Changing Feed publication, filenames, schemas, semantic identity, freshness, or Host Agent responsibilities.

## Decisions

### 1. Build raw URLs directly from the closed repository, branch, and product-root constants

The consumer will construct both manifest and artifact URLs from the existing canonical repository, `main` branch, and `feeds` root. Commit-discovery constants, response parsing, SHA validation, and the discovery request will be removed.

Alternative: retain GitHub API discovery with fallback to `main`. Rejected because it preserves the dependency and creates two transport paths with ambiguous failure behavior.

### 2. Use existing bundle validation as the sole consistency boundary

The consumer will still retrieve and validate the manifest before requesting its exact ordered inventory, enforce each declared byte limit during transfer, write only to temporary storage, and invoke the existing complete bundle loader. No branch-stability probe or post-download commit check will be added.

Alternative: request branch metadata before and after download. Rejected because it reintroduces GitHub API dependency and does not improve semantic integrity beyond the existing fail-closed manifest/artifact validation. Alternative retries are also rejected because the contract requires remote failure to remain terminal rather than silently switch bundle generations.

### 3. Replace discovery-specific tests with transport-boundary assertions

Focused tests will assert that the manifest is the first request, every request uses only the canonical `main/feeds/` raw prefix, and no request targets `api.github.com`. Discovery response/error tests will be removed; raw manifest/artifact HTTP, redirect, timeout, size-limit, schema, digest, mixed-generation, identity, temporary-storage, and no-fallback coverage will remain or be minimally adjusted.

Documentation contract tests will require canonical-main terminology and reject stale commit-pinned/Git reference API claims.

## Risks / Trade-offs

- **`main` advances between manifest and artifact requests** → Existing generation-qualified inventory, byte-size, digest, schema, `run_id`, and semantic identity checks reject inconsistent results; the invocation fails without partial output or fallback.
- **A superseded generation artifact is removed before retrieval completes** → The artifact request fails terminally, matching the existing remote-failure contract.
- **Mutable branch retrieval loses the transport-level immutable snapshot guarantee** → This is an explicit accepted trade-off; Feed semantic integrity remains established by bundle validation rather than Git history identity.
- **Stale documentation or tests continue to claim commit pinning** → Update all existing runtime-contract documentation surfaces and their focused regression assertions in the same implementation change.

## Migration Plan

1. Update the living contract delta and focused tests to describe canonical-main retrieval.
2. Simplify the remote consumer to direct raw URLs and run focused Feed remote/documentation tests.
3. Update runtime documentation, then run the canonical repository quality gate and strict OpenSpec validation.
4. Roll back by reverting the implementation, tests, documentation, and accepted spec delta together; no data or Feed producer migration is required.
