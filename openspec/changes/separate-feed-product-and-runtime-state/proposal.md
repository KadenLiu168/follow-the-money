## Why

`feeds/latest.json` is both a consumer Feed product and the runtime authority for the next acquisition window, while RateRegistry, lease, lock, and persistence state share the same `feeds/` root. ECO-74 removes that coupling now that ECO-73 is complete, so later Feed publication-layout changes cannot break execution continuity.

## What Changes

- Keep `output_root: feeds` as the explicit consumer Feed product root and add required `runtime_state_root: .feed-state` as a separately resolved application configuration value.
- Move the collection lock, existing RateRegistry registry/scopes, persistence marker, and deployment lease to `.feed-state/`; keep dated and latest Feed publication under `feeds/`.
- Add one closed, versioned `feed-checkpoint.json` with explicit `previous_success: null` or the last successfully published Feed's `evidence_cutoff_at` and `run_id`; do not add a Feed schema or second Feed model.
- Plan normal Feed windows exclusively from the validated checkpoint while preserving bootstrap, half-open window, advancing-cutoff, maximum-gap, coverage-gap, and fixed-cutoff semantics.
- Establish a null checkpoint during genuine zero-network bootstrap, fail closed on missing or corrupt checkpoint in established state, and advance it atomically only after accepted non-dry-run dated/latest publication.
- Separate runtime-safety, successful-continuity, and successful-product staging so hosted success validates Feed/checkpoint parity and publishes all matching state, while controlled failure cannot stage a changed checkpoint or Feed product.
- Add a one-time zero-network migration that validates and relocates complete legacy runtime state without resetting RateRegistry or lease/recovery semantics, seeds the checkpoint only from a valid legacy `feeds/latest.json` or explicit null, stages exact additions/deletions, and fails closed on mixed, partial, corrupt, unsupported, or inconsistent layouts.
- Align GitHub Actions, generated-state CI exclusions, `.gitignore`, tests, and documentation with the dual-root contract while preserving current dated-before-latest publication and ECO-73 diagnostics.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `feed-evidence-pipeline`: Separate consumer Feed products from repository-backed runtime state; make a minimal checkpoint the sole steady-state previous-success authority; add deterministic legacy migration, success-only checkpoint advancement, and exact dual-root hosted finalization without changing Feed schema, payload semantics, Provider completeness, RateRegistry policy, or dated/latest publication.

## Impact

- Configuration and orchestration: `config/config.yaml`, `src/follow_the_money/config/model.py`, `src/follow_the_money/config/load.py`, Feed planning/entry/deployment boundaries, and existing lock/RateRegistry root ownership where required.
- Repository deployment: `.github/workflows/generate-feed.yml`, `.github/workflows/test.yml`, `.gitignore`, the workflow validator, and exact generated-state staging/migration logic.
- Contract and regressions: the existing `feed-evidence-pipeline` capability, focused config/Feed/deployment/workflow tests, and truthful Feed architecture/configuration/runbook documentation.
- No dependency, Provider transport/policy, Feed schema, consumer Feed field, Agent/LLM runtime, public CLI, ECO-75 latest-only publication, or ECO-76 behavior is introduced.
