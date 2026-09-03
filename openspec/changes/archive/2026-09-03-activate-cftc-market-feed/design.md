## Context

See `proposal.md` for motivation and `specs/feed-evidence-pipeline/spec.md` for behavior. The repository already has a verified CFTC adapter and manifest that emit typed `positioning` evidence, but production activation policy disables it. The Feed already resolves enabled Provider contracts, plans registered adapters, routes payloads into typed artifacts, and applies cadence-aware snapshot selection after complete acquisition.

The accepted bundle contract has no `feed-market.json`: CFTC positioning belongs in the generation-qualified `feed-positioning-<generation>.json` artifact inventoried by `feed-manifest.json`. The separate `market_data` artifact cannot contain `positioning` payloads.

## Goals / Non-Goals

**Goals:**

- Activate CFTC through the existing authoritative Provider configuration.
- Exercise the existing adapter-to-plan-to-positioning-artifact path in production-level deterministic tests.
- Prove weekly new-slice, unchanged carry-forward, and failure isolation behavior without changing shared semantics.

**Non-Goals:**

- A CFTC-specific planner, snapshot store, freshness evaluator, output schema, or coverage engine.
- Changes to the CFTC data interpretation, payload shape, validity window, Feed domain routing, or publication boundary.
- Any analysis, signal, ranking, scoring, Agent runtime, or investment behavior.

## Decisions

### 1. Activate CFTC only in the existing Provider policy

Change the single enablement authority so normal resolution includes the already registered CFTC adapter. Keep Provider facts—including weekly cadence, `data_as_of`, validity, hosts, rate scope, and empty-window behavior—in the existing CFTC manifest.

Alternative considered: add an activation hook or CFTC-specific Feed wiring. Rejected because registry construction and production planning already derive from resolved enablement, so another path would duplicate authority.

### 2. Keep existing typed domain routing

Let the shared bundle router place CFTC items by `payload.type = positioning`. Do not add a market wrapper or route positioning into `market_data`.

Alternative considered: create the requested literal `feed-market.json`. Rejected because it does not exist in the accepted typed-bundle contract and would require an out-of-scope Feed redesign.

### 3. Verify integration at the production orchestration boundary

Use deterministic fixtures and controlled clocks to run the resolved production path with CFTC included. Cover a newly available report, a subsequent complete empty check against a valid active bundle, and an acquisition failure with that prior bundle present. Assertions should inspect the manifest-selected positioning artifact, Provider outcome, freshness, provenance, timestamps, and publication result.

Alternative considered: test only the adapter and freshness helpers. Rejected because those capabilities already have focused tests and would not prove production activation or end-to-end routing.

### 4. Preserve existing optional coverage membership

Activation makes CFTC planned work subject to the existing rule that every planned Provider must complete. It does not create or alter a mandatory coverage row; CFTC positioning remains additive evidence and cannot satisfy unrelated coverage requirements.

Alternative considered: introduce mandatory CFTC coverage. Rejected because the requested capability is production activation, not a coverage-policy redesign, and existing source-completeness semantics already keep failures observable.

## Risks / Trade-offs

- [Enabling another production Provider adds network work and can fail the whole source-complete run] → Keep existing bounded CFTC request/rate contracts and explicitly test failure visibility rather than hiding it with carry-forward.
- [A fixture-only test could miss configuration drift] → Resolve the checked-in production configuration in at least one test and assert CFTC is planned and represented in the output contract.
- [Documentation could imply positioning lives in `market_data`] → Name the manifest-inventoried positioning artifact and preserve the closed payload/domain distinction.

## Migration Plan

1. Enable CFTC in the authoritative Provider activation policy and update directly affected tests/documentation.
2. Run focused deterministic production-path tests for new, unchanged, and failed acquisition.
3. Run OpenSpec validation and the repository quality gate before deployment.
4. Deploy through the existing scheduled Feed workflow; the first successful run either publishes a current CFTC slice or records `no_snapshot` under existing semantics.
5. Roll back by reverting the activation and related contract/documentation changes. Existing published bundles remain governed by their embedded Provider contracts and normal bundle validation.
