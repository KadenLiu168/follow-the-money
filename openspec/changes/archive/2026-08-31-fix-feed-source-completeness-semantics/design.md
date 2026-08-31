## Context

See `proposal.md` for motivation and `specs/feed-evidence-pipeline/spec.md` for the revised behavior. The existing runtime already creates the Provider run plan before collection, pre-seeds one `ProviderOutcome` per planned Provider, resolves `empty_valid_for_window` in the Provider contract, computes coverage in `assess_pipeline()`, rejects `pipeline.status == failure` before `publish_feed()`, and lets ECO-62 finalization preserve a non-zero Feed result while persisting only allowlisted safety state.

The defect is concentrated in assessment: it derives Provider membership again from enabled configuration, treats incomplete source outcomes as degradation when evidence exists, and treats `total_accepted == 0` as failure. Existing Feed and transient status shapes already contain the Provider outcome fields needed for diagnosis.

## Goals / Non-Goals

**Goals:**

- Make the actual resolved run plan and its resolved contracts the only inputs for Provider completeness.
- Use one completeness predicate for both Provider failure and mandatory coverage counting.
- Admit a source-complete `items: []` candidate through the normal validation, identity, publication, and next-window path.
- Preserve actionable failure details and the original non-zero result through the existing CLI and deployment boundaries.

**Non-Goals:**

- No new health model, Provider registry, serialized field, Feed schema change, checkpoint, or persistent failure artifact.
- No change to Provider enablement, CFTC, Yahoo mapping verification, transports, coverage policy values, optional-group policy, or hard-failure boundaries.
- No redesign of publication, RateRegistry, lease/recovery, deployment finalization, workflow scheduling, Git behavior, Host-Agent use, or retained analytics.

## Decisions

### 1. Assess the explicit run plan, not enabled configuration or evidence

The collection orchestration will pass the already computed planned Provider identities into the existing assessment boundary together with the resolved configuration and keyed outcomes. Assessment will validate that planned identities are unique, each planned identity has exactly one matching known terminal outcome, and no missing or ambiguous outcome is silently synthesized as success. It will not scan hard-coded Provider names, accepted items, or coverage evidence.

Alternative considered: continue reconstructing membership from `config.providers`. Rejected because test-injected and future production plans can legitimately differ from the enabled registry, and it creates a second planning authority.

### 2. Reuse one Provider-outcome predicate

The existing outcome/contract rule will be the single predicate used by both source completeness and coverage: `healthy`, or `empty` with resolved `empty_valid_for_window = true`. All other states are incomplete. This may remain an existing `ProviderOutcome` method or a small local predicate; it is not a new domain model.

Alternative considered: add `complete` or `source_health` to the Feed. Rejected because completeness is derived assessment behavior and the existing serialized outcome states already preserve all facts.

### 3. Make source failure precede accepted non-source status handling

Assessment will first fail on invalid/incomplete planned outcomes, then fail on deficient mandatory coverage computed from complete planned members. Only after those checks may existing non-source status rules apply. `total_accepted` and `items` will no longer participate in the success predicate. Existing `degraded` vocabulary, serialization, consumer handling, and any independently accepted non-source trigger remain intact; this Change adds none.

Alternative considered: retain source `degraded` and block it only in publication. Rejected because that leaves pipeline status untruthful and lets other consumers mistake incomplete collection for usable success.

### 4. Reuse normal empty-Feed publication and identity

A source-complete empty candidate follows the same build, schema/semantic validation, identity/digest calculation, dated publication, and `latest.json` replacement as any other successful Feed. The current cutoff remains part of the normal Feed, so the next run naturally starts from the newly published latest cutoff.

Alternative considered: add an empty-run checkpoint or special publisher path. Rejected because `items: []`, Provider outcomes, identity metadata, and cutoff are already valid in the existing Feed contract.

### 5. Surface failures through existing outcome and transient status paths

The fixed zero-evidence failure message will be replaced with source-completeness diagnostics derived from existing Provider outcomes. The existing Feed candidate/status/log path will expose `provider_id`, `state`, `error` when present, and warnings. No new tracked file or generated-state allowlist entry will be added.

ECO-62 collection/finalization should require no production change: its existing exit-file/result handling and terminal failure lease already preserve Feed exit `1`. A deployment code change is allowed only if a focused regression proves that the current path loses the original result or required transient details.

Alternative considered: persist a failure report for later inspection. Rejected because workflow logs and transient status are sufficient and repository persistence semantics are explicitly out of scope.

## Risks / Trade-offs

- [The planned-ID/outcome contract is currently implicit in keyed mutable state] → Validate plan uniqueness, outcome key equality, terminal state, and Provider identity at the assessment boundary, with focused missing/duplicate/ambiguous tests.
- [A permitted empty result can now advance `latest.json`] → Verify normal schema/identity publication and prove the next plan starts at the new cutoff; do not add a parallel checkpoint.
- [Changing source degradation to failure can reduce publication frequency] → This is the intended fail-closed contract; retain successful Providers' outcomes and errors in transient diagnostics.
- [Generic `degraded` support could be accidentally removed because no source case uses it] → Keep the enum, serializer, CLI success mapping, and consumer regression coverage unchanged.
- [Deployment finalization could mask Feed failure] → Retain ECO-62's exact finalization behavior and add a focused source-failure propagation regression without changing RateRegistry or lease semantics.

## Migration Plan

1. Add focused assessment and CLI regressions for the new truth table, empty publication/window progression, diagnostics, and no-publication safety.
2. Replace the assessment predicate and failure message with the minimum changes at the existing boundaries.
3. Update only documentation that explicitly states zero-evidence failure or source-incomplete degradation.
4. Run focused Feed/deployment tests, the canonical repository quality gate, `openspec doctor`, target strict validation, and all strict validation.

Rollback is a normal code/spec revert. No persisted schema or data migration is introduced; previously published valid Feeds remain readable.
