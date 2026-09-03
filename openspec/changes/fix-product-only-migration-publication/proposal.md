## Why

A hosted product-only migration correctly generated the first manifest-led Feed bundle, but pre-network publication failed because its Git staging allowlist also contained nonexistent legacy runtime paths under `feeds/`. The migration could therefore neither commit the valid bundle nor reach the next normal Feed lifecycle invocation.

## What Changes

- Distinguish paths eligible for product-only migration publication from legacy runtime-state deletion paths.
- Stage the generated bundle, tracked `feeds/latest.json` deletion, and required `.feed-state/` files without passing nonexistent, untracked legacy runtime paths to Git; fail before removal if `latest.json` itself is untracked.
- Preserve exact allowlisting, non-force fast-forward publication, zero Provider requests during migration, and fail-closed handling of missing required state or unexpected staged paths.
- Add repository-backed regression coverage that reproduces the hosted product-only migration and exercises the real Git staging boundary.
- Re-run hosted migration and the following normal lifecycle invocation to verify migration completion before returning to the blocked Provider runtime verification.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `feed-evidence-pipeline`: Clarify exact generated-state staging for product-only migration when runtime state is already established in `.feed-state/` and only `feeds/latest.json` remains to migrate.

## Impact

- Affected implementation: migration allowlist and pre-network publication in `src/follow_the_money/feed/deployment.py`.
- Affected tests: repository-backed deployment migration tests, primarily `tests/test_feed_deployment_separation.py`.
- Contract impact: narrows migration staging to paths that belong to the detected migration form; no schema, Provider, rate policy, checkpoint format, workflow topology, or public CLI change.
- Operational impact: the current product-only migration can publish its generated-state commit and exit without Provider work; the next invocation can proceed through normal arming and collection subject to existing recovery and external Provider conditions.
