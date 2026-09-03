## Why

Explicit upstream access denials are external availability conditions, but the Feed currently collapses them into unexpected Provider failure and therefore rejects otherwise valid evidence. Recent HTTP 403 responses from official sources such as BLS and SSE require truthful availability diagnostics and a publishable warning path without weakening handling of unknown failures.

## What Changes

- Add a closed Provider availability classification: `success`, `blocked`, `failed`, and `disabled`; reserve `degraded` for future partial-data semantics without implementing it here.
- Classify only confirmed HTTP 401 and HTTP 403 responses as `blocked`; timeouts, parser errors, and all unconfirmed failures remain `failed`.
- Keep Provider availability separate from Feed pipeline status.
- Exempt a `blocked` planned Provider from independently causing Provider-completeness or mandatory-group coverage failure. Reduce each affected mandatory group's effective minimum only by its blocked planned members; do not change configured group membership or minimums. Other incomplete outcomes and non-blocked coverage deficiencies remain failures.
- Produce `pipeline.status = degraded` when blocked availability is the only source-acquisition issue and all non-source hard boundaries pass; preserve `healthy` and `failure` behavior otherwise.
- Expose deterministic diagnostics containing Provider identity, availability, bounded reason, and affected coverage groups. Disabled Providers remain outside the run plan and do not create synthetic outcomes.
- Update the serialized Feed contracts and compatibility handling required by the new Provider availability data.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `feed-evidence-pipeline`: Add explicit Provider availability, access-denial classification, blocked coverage exemption, degraded publication, and truthful diagnostics while preserving fail-closed behavior for unknown failures.

## Impact

- Provider HTTP error propagation and orchestration classification under `src/follow_the_money/providers/` and `src/follow_the_money/feed/`.
- Feed planning, completeness/coverage assessment, semantic validation, snapshot/carry-forward behavior, publication, deployment diagnostics, and consumer health handling.
- Closed Feed and manifest schemas, including the repository's supported-major compatibility policy if the serialized contract changes incompatibly.
- Regression tests for classification, coverage exemption, status selection, validation, publication, and diagnostics.
- No Provider-specific exceptions, coverage configuration changes, retries, alternate acquisition paths, credentials, or Agent/LLM runtime changes.
