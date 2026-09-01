## Context

See `proposal.md` for motivation and `specs/feed-evidence-pipeline/spec.md` for the behavior delta. The current deployment collector already receives a failed `FeedRunResult`, writes transient `feed-status.json`, records the typed result in `.feed-exit-code`, and finalizes only exact durable allowlisted paths. The information loss is local to failure-status projection and hosted presentation: `_write_feed_status()` omits the failed result message and Feed `provider_outcomes`, while the workflow has no diagnostics step between finalization and failure restoration.

The existing Feed candidate already serializes outcomes through `ProviderOutcome.to_dict()` in deterministic order. The renderer must therefore remain a one-way presentation adapter rather than another health, completeness, or Provider-failure model.

## Goals / Non-Goals

**Goals:**

- Preserve already available failure facts through the transient deployment boundary.
- Render a deterministic, bounded, human-readable failure report after safety-critical finalization.
- Keep diagnostics best-effort and preserve the existing typed Feed exit category as workflow authority.

**Non-Goals:**

- Reassessing Provider completeness, coverage, Feed health, publication eligibility, or exit categories.
- Changing `ProviderOutcome`, `FeedRunResult`, exceptions, Feed schema, generated-state allowlists, RateRegistry, lease/recovery, finalization, or Provider runtime.
- Adding a public CLI, persisted failure model, generic redaction/logging framework, dependency, or Actions artifact upload.

## Decisions

### 1. Extend the existing deployment status projection directly

For a completed failed result, `_write_feed_status()` will include the existing `message`, `warnings`, and `result.feed["provider_outcomes"]`. It will copy that existing serialized list rather than call completeness logic, parse warnings, or create a diagnostic type. Healthy and degraded success-path fields remain unchanged.

The existing typed exception handlers will use the same narrow failure status shape with `status`, the exception message, and an empty warnings list. They will omit `provider_outcomes` because no completed outcome collection exists at that boundary. `.feed-exit-code` remains `2` for `FeedInputError` and `1` for `FeedExecutionError` or a failed Feed result.

Alternative rejected: reconstruct Provider fields from warnings or exception text. That couples diagnostics to prose and creates a second, potentially conflicting truth source.

### 2. Keep rendering inside the private deployment module

Add one small private deployment subcommand that reads the status path, validates only the narrow presentation shape, selects known fields, and emits the report. It does not mutate status or any runtime state. Keeping JSON handling in Python makes the boundary unit-testable and avoids complex workflow `bash`/`jq` logic; no console-script or public API is added.

The renderer accepts only `status`, `message`, `warnings`, and known Provider outcome fields. Unknown fields are ignored. Provider outcomes retain input order, which is already deterministic at the Feed boundary. Missing optional values render as absent rather than inferred.

Alternative rejected: `cat feed-status.json` or parse it in YAML shell. Raw output can leak unrelated fields and lets multiline or Markdown-sensitive content damage the presentation structure.

### 3. Use one minimal sanitization policy for both outputs

The renderer will accept expected scalar types only, replace line breaks and control characters with visible safe spacing or escapes, escape Markdown table/list delimiters, and truncate each human-facing message, warning, and error plus the overall report at fixed documented bounds. Numeric counters remain validated scalar values and are not derived from text. The same selected facts drive the Actions log and Step Summary so the two views cannot disagree through separate parsing.

This is presentation sanitization, not secret redaction: the renderer reads no environment values and never scans arbitrary fields. Existing error facts remain the only content source.

Alternative rejected: a generic redaction framework. ECO-73 has one closed transient input and requires neither configurable policies nor inspection of arbitrary payloads.

### 4. Make workflow ordering and non-gating behavior explicit

The workflow order will remain:

```text
Collect Feed
→ Finalize exact deployment state
→ Failure diagnostics
→ Preserve original Feed failure
```

The diagnostics step uses `always()` together with the Feed step's failure outcome, appends to `$GITHUB_STEP_SUMMARY`, and is explicitly non-gating for unexpected renderer or summary-write failure. Expected missing/corrupt status is handled by the renderer as a bounded unavailable report with success return. An unexpected diagnostics-step failure is also tolerated by the workflow, while the following restoration step continues to read `.feed-exit-code` and re-emits the original category.

Alternative rejected: rendering before finalization or folding rendering into finalization. Either ordering could couple optional observability to safety-critical durable state handling.

### 5. Preserve the current transient and durable boundaries

No allowlist or ignore-policy change is required. Tests will continue to prove `feed-status.json` is absent from `allowlisted_paths()` and that failure finalization publishes only the existing rate/lease paths. Diagnostics writes only to the runner log and GitHub-provided summary path.

Alternative rejected: upload or commit a diagnostic artifact. Actions logs and Step Summary satisfy the issue without creating retention, truth-source, or publication semantics.

## Risks / Trade-offs

- [A malformed status file prevents detailed output] → Emit one bounded diagnostics-unavailable notice and preserve the underlying Feed/finalization result.
- [Unexpected text disrupts logs or Markdown] → Select known scalar fields, normalize controls/newlines, escape Markdown delimiters, and enforce per-field and total bounds.
- [A diagnostics implementation error masks the real failure] → Keep the step after finalization, explicitly non-gating, and retain the existing final `.feed-exit-code` restoration step.
- [Duplicated workflow assertions become brittle] → Validate ordering and behavioral markers without freezing incidental YAML formatting or a specific shell expression.

## Migration Plan

1. Add focused no-network regressions for failure projection, typed failures, renderer sanitization/bounds/unavailable behavior, workflow order/non-gating semantics, and allowlist exclusion.
2. Extend the existing deployment projection and private parser with the smallest implementation satisfying those tests.
3. Insert the diagnostics step between finalization and original failure restoration; keep all other hosted and successful paths unchanged.
4. Run focused Feed deployment/workflow tests, the canonical repository quality gate, supported OpenSpec checks, and `git diff --check`.

No data migration or deployment-state reset is required. Rollback is a normal source/spec revert; existing Feed, RateRegistry, lease, and generated repository state remain compatible.
