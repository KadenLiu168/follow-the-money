## Why

The living Feed contract already distinguishes usable `healthy`/`degraded` evidence from `failure`, but the production path can still build and publish a zero-evidence failure candidate, treats every empty provider as coverage-healthy, does not truthfully aggregate partial provider work, and lets a schema-valid failure Feed cross the consumer boundary. Before any future Agent contract is designed, the evidence-only Feed needs one fail-closed trust decision that consistently controls coverage, publication, CLI exits, dry-run, and consumption.

## What Changes

- Make provider coverage contribution depend on the recorded outcome and the existing `empty_valid_for_window` provider contract: `healthy` and permitted `empty` contribute; non-permitted `empty`, `partial`, `failed`, and `skipped` do not.
- Aggregate item rejection and multi-request/role outcomes truthfully so safely retained evidence plus incomplete work produces `partial`, never `healthy`; retain valid evidence and report provider-specific degradation.
- Define one pipeline decision: accepted evidence plus complete mandatory coverage and no provider degradation is `healthy`; accepted evidence plus any recoverable provider or mandatory-coverage deficiency is `degraded`; zero accepted evidence is `failure`.
- Add a producer admission guard so a fully assessed and validated `failure` candidate is not exposed as a successful Feed or passed to publication, exits `1` in both dry-run and publication modes, and cannot replace the last valid `latest.json`.
- Preserve existing healthy/degraded publication, typed execution-error mapping, and dated-first/latest-second durability behavior; publication failure remains exit `1`, not degraded success.
- Reject `pipeline.status == failure` at the Feed consumer health boundary while continuing to accept degraded Feed with propagated warnings.
- Add focused provider, coverage, orchestration, publication-failure, dry-run, and consumer regression tests for the trust boundary.
- Keep `feed.schema.json` capable of representing `failure` so historical, hand-written, fixture, or regressed artifacts can be validated structurally and then rejected semantically.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `feed-evidence-pipeline`: Clarify provider outcome aggregation, contract-aware coverage contribution, zero-evidence failure admission, dry-run/CLI outcomes, and defensive consumer rejection.

## Impact

- Production boundaries: `src/follow_the_money/feed/plan.py`, `src/follow_the_money/feed/cli.py`, and `src/follow_the_money/engine/feed_health.py`.
- Focused verification: `tests/test_feed_pipeline.py`, `tests/test_feed_cli.py`, `tests/test_engine.py`, and existing Feed integration/publication gates where their current ownership requires coverage.
- Existing provider/config models and `empty_valid_for_window` values are consumed as-is; configuration ownership is not redesigned.
- No new dependency, serialized Feed shape, public CLI, LLM runtime, Agent analysis contract, Brief pipeline, Resolver/Analyst/Editor runtime, Bundle, or replay architecture is introduced.
