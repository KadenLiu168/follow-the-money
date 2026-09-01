## Why

The GitHub-hosted Feed path can finish with actionable structured failure facts inside `FeedRunResult` and its existing Provider outcomes while Actions exposes little beyond a generic non-zero exit. The accepted failure contract already requires transient observability; this Change aligns hosted deployment and workflow presentation with that contract before later runtime-state work begins.

## What Changes

- Project an existing failed `FeedRunResult` into transient `feed-status.json` with its `message`, `warnings`, and existing serialized `provider_outcomes`; typed input or execution failures expose only facts actually available at that boundary.
- Add an always-run, failure-only hosted diagnostics step after exact finalization and before original Feed failure restoration.
- Add a small private deployment renderer that selects, sanitizes, bounds, and deterministically renders known status fields to Actions logs and `$GITHUB_STEP_SUMMARY` without reassessing Feed health.
- Make missing, corrupt, or unrenderable diagnostics non-gating while preserving the existing `.feed-exit-code` authority and finalization behavior.
- Keep `feed-status.json` transient and outside repository publication; add no second failure model, Feed schema field, public diagnostics API, telemetry framework, or artifact upload.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `feed-evidence-pipeline`: Clarify the existing minimal-entry and GitHub-hosted deployment requirements so structured failure facts survive transient status projection and are safely presented after finalization without changing Feed decisions, persistence, or exit semantics.

## Impact

- Primary implementation: `src/follow_the_money/feed/deployment.py` and `.github/workflows/generate-feed.yml`.
- Focused regressions: `tests/test_feed_deployment.py`, `tests/test_workflows.py`, and the repository workflow validator/tests; existing Feed CLI and pipeline tests remain authoritative unless a narrow projection regression belongs there.
- No Provider/config/schema/dependency change, no durable generated-state path, and no change to completeness, coverage, publication, retry, rate, lease, recovery, identity, provenance, or Host-Agent behavior.
