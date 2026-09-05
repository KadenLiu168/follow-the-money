## Why

GitHub Actions already owns normal production Feed collection and publishes one validated manifest-led bundle to repository `main`, but the current Skill contract also permits local Provider collection. This leaves normal Skill invocation with two producer paths, duplicates hosted runtime state, and permits a remote failure to turn a consumer into an implicit producer.

## What Changes

- **BREAKING**: Make normal Skill invocation consume only the canonical published Feed from `KadenLiu168/follow-the-money`, branch `main`; local Feed production remains available only for hosted deployment, development, diagnostics, tests, and explicit operator execution.
- Resolve `main` once to one exact Git commit and retrieve the manifest plus every inventoried artifact from that immutable commit.
- Keep `feed-manifest.json` as the sole bundle authority and reuse the existing manifest, bundle, logical Feed, identity, provenance, health, and fail-closed validation semantics.
- Add one minimal internal Skill consumer entry that emits the existing validated logical Feed representation without adding a public CLI or another Feed schema.
- Fail closed on discovery, transport, inventory, integrity, schema, identity, or non-consumable pipeline failure; never fall back to Provider collection, repository-local Feed products, another repository, another commit, or partial evidence.
- Preserve valid degraded Feed warnings and Provider availability metadata without contacting Providers or reinterpreting freshness.
- Keep retrieval credential-free and ephemeral: no token requirement, persistent cache, `feeds/` mutation, or `.feed-state/` mutation.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `feed-evidence-pipeline`: Define the commit-pinned published Feed consumption boundary, manifest-led remote discovery, shared fail-closed validation, normal Skill no-local-fallback rule, and distinct producer and consumer internal entries.

## Impact

- Expected implementation surface: `src/follow_the_money/feed/bundle.py`, a small remote consumer module under `src/follow_the_money/feed/`, and `scripts/skill/prepare-feed`.
- Focused tests will cover commit resolution and pinning, manifest-driven requests, healthy/degraded consumption, validation failures, typed network failure, and absence of local fallback or persistent product/runtime-state writes.
- `SKILL.md`, `README.md`, `README.zh-CN.md`, `docs/architecture.md`, and `docs/feed-contract.md` will describe the actual remote-only normal Skill caller graph while retaining the explicit local producer surface.
- Existing Feed schemas, Provider acquisition, GitHub Actions production and publication, Feed identity, deployment state, Audit/Event invocation, retained deterministic capabilities, dependencies, and public CLI status remain unchanged.
