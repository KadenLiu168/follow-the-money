## 1. Establish Failing Trust-Boundary Tests

- [x] 1.1 Add `tests/test_feed_pipeline.py` truth-table cases proving permitted empty contributes coverage, non-permitted empty does not, partial/failed/skipped do not, zero accepted evidence always fails, and provider plus deficient-group warnings are both retained.
- [x] 1.2 Add provider aggregation cases proving accepted-plus-rejected items and success followed by a failed/empty non-permitted role retain accepted evidence and finish `partial`, while all-rejected work without accepted evidence is not reported healthy or empty.
- [x] 1.3 Add `tests/test_feed_cli.py` orchestration cases for one failed provider plus one successful provider, deficient mandatory coverage, all permitted-empty failure, dry-run failure exit `1`, and an explicit spy proving `publish_feed()` is not called for pipeline failure.
- [x] 1.4 Add publication-error regression coverage proving an admitted healthy/degraded candidate still exits `1` on publication failure and does not falsely replace a previous valid `latest.json` or report degraded success.
- [x] 1.5 Add `tests/test_engine.py` defense-in-depth coverage proving a schema/identity-valid Feed with `pipeline.status=failure` raises `FeedLoadError`, while healthy and degraded behavior remains unchanged.

## 2. Implement Provider and Coverage Semantics

- [x] 2.1 Replace the context-free provider health shortcut in `src/follow_the_money/feed/plan.py` with contract-aware coverage contribution using the existing `AppConfig.providers[*].empty_valid_for_window` values.
- [x] 2.2 Update `assess_pipeline()` to apply the single precedence rule—zero accepted is failure; otherwise any enabled-provider or mandatory-group deficiency is degraded; otherwise healthy—and accumulate provider-specific and group-specific warnings without early-return loss.
- [x] 2.3 Update `src/follow_the_money/feed/cli.py` provider execution aggregation so counters/items remain additive and final state is derived truthfully across rejected items and multiple adapter/role results, including partial retention after later incomplete work.

## 3. Enforce Producer and Consumer Admission

- [x] 3.1 Add the post-validation `run_feed()` admission guard so failure returns typed status/exit `1` without exposing success artifact paths or calling `publish_feed()`, while healthy/degraded dry-run and publication remain exit `0`.
- [x] 3.2 Preserve existing typed `FeedExecutionError` handling for schema, identity, filesystem, publication, and durability failures; do not modify the dated-first/latest-second publication algorithm.
- [x] 3.3 Update `src/follow_the_money/engine/feed_health.py` so `assess_health()` explicitly rejects `pipeline.status=failure` and continues to propagate degraded warnings.

## 4. Verify the Change

- [x] 4.1 Run the focused Feed pipeline, CLI, engine-health, boundary, and publication tests and resolve only ECO-24-caused failures.
- [x] 4.2 Run the existing Feed integration/gate tests that exercise fixture-backed generation, publication recovery, workflow exit propagation, and no-LLM architecture boundaries.
- [x] 4.3 Run `UV_CACHE_DIR=/tmp/follow-the-money-uv-cache uv run python scripts/quality_gate.py` and record the fresh result.
- [x] 4.4 Run `openspec validate fix-feed-failure-and-degradation-semantics --strict`, `openspec validate --all --strict`, and `openspec doctor`; confirm production code/config/schema changes remain limited to the approved trust boundary and no deferred ECO-25/26/27 or Agent-contract work was introduced.
