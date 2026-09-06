## Why

Normal Skill Feed consumption currently depends on GitHub REST API branch-reference discovery before it can retrieve an otherwise self-validating published bundle. Removing that unnecessary API call avoids anonymous API rate limits and reduces transport failure modes now that manifest-first bundle integrity and semantic identity validation are mature.

## What Changes

- Retrieve `feeds/feed-manifest.json` and its declared artifacts directly from the canonical `main` branch under `raw.githubusercontent.com`.
- Remove GitHub REST API branch discovery and commit-SHA resolution from normal Skill runtime retrieval.
- Preserve manifest-first loading, closed inventory, canonical path, byte-size, digest, schema, provenance, pipeline-consumability, and Feed identity validation unchanged.
- Preserve remote-only, credential-free, fail-closed behavior: retrieval or validation failure remains terminal with no Provider collection, persistent cache, stale substitution, partial output, or local fallback.
- Update focused remote-consumer tests and runtime-contract documentation to describe canonical-main retrieval rather than commit-pinned retrieval.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `feed-evidence-pipeline`: Replace commit-pinned GitHub API discovery and retrieval requirements with direct canonical-main raw Feed retrieval while retaining the existing manifest-led trust boundary and failure semantics.

## Impact

- Runtime transport: `src/follow_the_money/feed/remote.py` and the `scripts/skill/prepare-feed` path.
- Tests: remote URL/call-order and documentation contract regressions; existing invalid manifest, artifact, schema, identity, remote-only, and persistent-state tests remain authoritative.
- Documentation: `SKILL.md`, `README.md`, `README.zh-CN.md`, `docs/architecture.md`, and `docs/feed-contract.md`.
- No Feed producer, schema, artifact contract, Host Agent boundary, Provider behavior, credential, or dependency change.
