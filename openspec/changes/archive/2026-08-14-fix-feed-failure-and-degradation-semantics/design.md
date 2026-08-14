## Context

The current evidence-only path already has the required serialized vocabulary: `ProviderOutcome.state` supports `healthy`, `empty`, `partial`, `failed`, and `skipped`; `pipeline.status` supports `healthy`, `degraded`, and `failure`; provider configuration carries `empty_valid_for_window`; and durable publication reports typed failures. The living `feed-evidence-pipeline` specification also already says that zero accepted items fail, partial evidence is retained, and only healthy/degraded candidates publish.

Production behavior does not yet enforce that contract end to end:

- `ProviderOutcome.healthy` counts every `empty` outcome without consulting the provider contract.
- `_run_adapter()` overwrites the provider state for each internal adapter/role and marks accepted-plus-rejected output healthy.
- `assess_pipeline()` can return `failure`, but `run_feed()` still builds, validates, and can publish that candidate; dry-run returns `0` unconditionally.
- coverage deficiency returns before provider-specific degradation warnings are accumulated.
- `assess_health()` propagates degraded warnings but does not reject a failure Feed.

The publication subsystem already owns dated-first/latest-second atomicity, no-replace dated artifacts, monotonic latest ownership, `fsync`, and durability uncertainty. This Change must add admission before that subsystem without altering those guarantees. The current provider adapters issue one request each; `yahoo_market` is the present multi-request provider because orchestration fans it out across 13 role adapters.

## Goals / Non-Goals

**Goals:**

- Establish one truthful provider-outcome aggregation rule across single-request and multi-role providers.
- Make coverage contribution depend on both outcome state and the existing provider empty contract.
- Make zero accepted evidence a non-publishable, exit-`1` outcome in normal and dry-run execution.
- Preserve usable evidence when incomplete provider work can be represented safely as `partial`.
- Preserve healthy/degraded publication and existing publication-failure behavior.
- Reject failure Feed at the consumer boundary even if one appears historically or outside the producer.
- Cover each trust decision with focused regression tests and existing Feed gates.

**Non-Goals:**

- No `ResearchContext`, `AgentAnalysis`, `BriefContext`, fixed Brief schema, Host Agent reasoning protocol, or Agent orchestration runtime.
- No internal LLM runtime, Resolver, Analyst, Editor, standalone public CLI, Bundle, replay, or Brief pipeline.
- No provider/config source-of-truth redesign, new provider contract field, schema version, or serialized shape change.
- No rewrite of publication durability, provider ordering, digest/timestamp determinism, verified market mappings, or provider pagination architecture.
- No expansion of item-validation policy beyond what is required to classify the existing accepted/rejected path truthfully.

## Decisions

### 1. Aggregate provider facts before deriving the final provider state

Provider counters and retained items remain additive across the provider's internal adapter/role work. Final state is derived from the aggregate facts instead of allowing the last sub-request to overwrite earlier results:

| Aggregate result | Provider state |
| --- | --- |
| accepted evidence, every sub-request complete, no rejection, and every empty sub-result permitted by contract | `healthy` |
| no accepted evidence, every sub-request complete, no rejection or execution error | `empty` |
| accepted evidence plus any rejection, failed/skipped later work, or non-permitted empty sub-result | `partial` |
| no accepted evidence plus validation rejection or execution failure | `failed` |
| provider was not executed | `skipped` |

A single-provider normal empty result remains `state=empty`; permission is a coverage decision, not a second serialized empty state. If valid evidence was retained before a later role/sub-request fails, the final provider is `partial` and the evidence remains. The current stop-after-failure behavior may remain bounded; this Change only requires the aggregate state to reflect retained evidence and incomplete work honestly.

Alternative considered: add `permitted_empty` as a new schema state. Rejected because the existing provider contract already supplies the missing context and a schema change is unnecessary.

### 2. Make `assess_pipeline()` the sole coverage and health truth table

Assessment resolves each outcome against `AppConfig.providers`; the context-free `ProviderOutcome.healthy` shortcut is removed or no longer used for coverage. Contribution is exactly:

| Provider outcome | Mandatory coverage contribution |
| --- | --- |
| `healthy` | yes |
| `empty` and `empty_valid_for_window=true` | yes |
| `empty` and `empty_valid_for_window=false` | no |
| `partial` | no |
| `failed` | no |
| `skipped` | no |

Pipeline precedence is global evidence first:

1. `total_accepted == 0` produces `failure`, regardless of permitted-empty coverage counts.
2. With accepted evidence, any deficient non-optional coverage group or any enabled provider that is partial, failed, skipped, or non-permitted empty produces `degraded`.
3. With accepted evidence, satisfied mandatory coverage, and no enabled-provider degradation, the result is `healthy`.

Assessment accumulates both provider-specific and group-specific warnings before returning so a coverage warning cannot hide the provider cause. Optional coverage rows do not independently fail their minimum, but an enabled provider's explicit incomplete outcome remains truthful degradation.

Alternative considered: derive coverage in each adapter. Rejected because adapters do not own cross-provider group minimums and would duplicate policy.

### 3. Admit only healthy/degraded candidates after full candidate validation

`run_feed()` continues fetch, normalize, item acceptance/rejection accounting, deduplication, pipeline assessment, Feed construction, schema validation, and identity validation. After validation and before either dry-run success or `publish_feed()`, it applies one admission decision:

- `healthy` or `degraded`: expose the candidate; dry-run returns `0`, while normal execution calls the unchanged publisher and returns `0` only after successful publication.
- `failure`: do not call `publish_feed()`, do not create a dated artifact, do not replace `latest.json`, and return a typed failure result with exit `1`. The failed candidate is not exposed as a consumable Feed or given success artifact paths.

Keeping candidate validation before admission makes dry-run and normal execution use the same full trust decision. It also leaves existing planning, runtime, schema, identity, filesystem, publication, and durability exceptions mapped through `FeedExecutionError` to exit `1`. Publication errors are never converted to degraded results.

Alternative considered: teach `publish_feed()` to inspect pipeline health. Rejected because the publisher accepts already validated bytes and owns filesystem commit semantics, not Feed business admission; the regression test shall prove it is not called for failure.

### 4. Reject failure again at consumption

After schema and identity validation, `assess_health()` accepts `healthy`, accepts `degraded` while propagating pipeline warnings, and raises `FeedLoadError` for `failure`. This check is independent of freshness degradation and occurs before a failure Feed can be reported as usable. Retaining `failure` in `feed.schema.json` is intentional: structural validity does not imply semantic consumability.

Alternative considered: remove `failure` from the schema. Rejected because it would eliminate the requested defense-in-depth distinction and make historical/hand-written failure artifacts only generic schema errors.

### 5. Verify behavior at the owning boundaries

Focused tests cover the pure truth table in `test_feed_pipeline.py`, orchestration/admission and CLI exits in `test_feed_cli.py`, and consumer rejection in `test_engine.py`. Multi-role partial aggregation is exercised through fixture adapters under one provider ID; tests do not require network access or introduce a future pagination abstraction. Existing publication failure-injection tests remain the authority for dated/latest durability, with only the minimal additional assertion needed to prove failure candidates never enter publication.

## Risks / Trade-offs

- [Risk] A provider with accepted evidence can be misclassified if sub-request state is overwritten during concurrent or sequential aggregation. → Mitigation: derive the final state from additive counters and explicit incomplete-work flags, and test success-then-failure plus accepted-and-rejected sequences.
- [Risk] Treating a non-permitted empty as `failed` would conflate execution with contract sufficiency. → Mitigation: keep serialized state `empty`, deny coverage in assessment, name the provider in warnings, and degrade when other evidence exists.
- [Risk] Returning failure without a Feed could reduce diagnostic detail. → Mitigation: preserve status and accumulated provider/group warnings in the typed run result/status output while withholding success artifact identity and publication.
- [Risk] Broader provider/config cleanup could leak into ECO-24. → Mitigation: read existing `ProviderEntry.empty_valid_for_window` and coverage rows directly; defer ownership normalization to ECO-26.
- [Risk] ECO-25 determinism work could be pulled forward through warning/order changes. → Mitigation: use existing stable identifiers and only the minimum ordering needed for deterministic assertions; do not change Feed identity or timestamp generation here.

## Migration Plan

1. Add failing focused tests for outcome aggregation, coverage contribution, zero-evidence admission, dry-run exit, publication-call exclusion, publication error mapping, and consumer rejection.
2. Implement provider aggregation and the centralized assessment truth table without changing serialized fields.
3. Add the CLI admission guard and consumer rejection, then run focused Feed tests and existing publication/integration gates.
4. Run repository quality gates and strict OpenSpec validation. No artifact or configuration migration is required because the schema and provider contract shape remain unchanged.

Rollback is a code/spec revert; no data migration or destructive cleanup is needed. A failure run never replaces the previous valid `latest.json`, and durable artifacts already committed before a genuine publication failure retain the existing publication contract.

## Open Questions

None. Pagination-specific streaming or resumability remains outside this Change; any future multi-page adapter must report retained evidence and incomplete later work through the same aggregate `partial` contract.
