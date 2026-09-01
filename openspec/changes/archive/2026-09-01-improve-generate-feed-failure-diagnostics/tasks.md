## 1. Lock the Diagnostics Contract with Focused Tests

- [x] 1.1 Add no-network deployment tests proving a completed failed `FeedRunResult` projects its existing message, warnings, and deterministically ordered serialized `provider_outcomes`, including `provider_id`, `state`, `error`, `attempted`, `fetched`, `accepted`, and `rejected`, without parsing warning text.
- [x] 1.2 Add typed `FeedInputError` and `FeedExecutionError` deployment tests proving exit categories remain `2` and `1`, existing messages and deterministic empty warnings are visible, and no Provider outcome is fabricated.
- [x] 1.3 Add renderer tests for known-field selection, all required Provider fields, input order, multiline/control/Markdown-safe presentation, per-field and total bounds, and ignored unknown fields.
- [x] 1.4 Add missing/corrupt status and unavailable summary-output tests proving diagnostics emits only a bounded unavailable notice and returns non-gating behavior.
- [x] 1.5 Extend workflow and repository validator tests to assert behavioral order `collect → finalization → always-run failure diagnostics → original failure restoration`, failure-only diagnostics, explicit non-gating behavior, retained `.feed-exit-code` authority, and no staging of transient status.

## 2. Preserve and Render Existing Failure Facts

- [x] 2.1 Extend the existing deployment status writer so failed completed results copy `message`, `warnings`, and the Feed's existing serialized `provider_outcomes`, while leaving healthy/degraded success projection unchanged.
- [x] 2.2 Normalize typed input/execution failure status through the same narrow transient shape with no inferred Provider information and no change to existing exit categories.
- [x] 2.3 Add the smallest private deployment rendering entry that validates the expected status structure, selects known fields, preserves Provider ordering, sanitizes and bounds human-facing text, prints the report, and appends the same concise content to a supplied Step Summary path.
- [x] 2.4 Handle missing/corrupt status and summary-write failure as bounded diagnostics-unavailable outcomes without mutating Feed status, runtime state, finalization state, or exit files.

## 3. Wire Non-Gating Hosted Diagnostics

- [x] 3.1 Insert a focused `.github/workflows/generate-feed.yml` diagnostics step after exact finalization and before original Feed failure restoration, conditioned with `always()` and the Feed step failure outcome.
- [x] 3.2 Pass `feed-status.json` and `$GITHUB_STEP_SUMMARY` only to the private renderer and make unexpected diagnostics failure non-gating; preserve the final restoration step's existing `.feed-exit-code` behavior.
- [x] 3.3 Keep `feed-status.json` outside `allowlisted_paths()` and prove controlled failure finalization still publishes only the existing exact durable rate/lease paths.

## 4. Verify Unchanged Feed and Deployment Semantics

- [x] 4.1 Run focused deterministic tests for Feed pipeline, CLI, deployment, and workflows plus the repository workflow validator; retain existing healthy, degraded accepted, source-completeness failure, publication, finalization, and exit-code regressions without real Provider network calls.
- [x] 4.2 Prepare with `uv sync --frozen --all-groups` if needed, then run `.venv/bin/python scripts/quality_gate.py` and `git diff --check`.
- [x] 4.3 Run `openspec doctor`, `openspec validate improve-generate-feed-failure-diagnostics --strict`, and `openspec validate --all --strict`; confirm no Provider/config/schema/dependency, Feed health, RateRegistry, lease/recovery, generated-state allowlist, or future ECO-74+ architecture change entered the diff.
