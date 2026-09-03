## Why

The verified CFTC Commitments of Traders Provider remains disabled in production, so authoritative weekly positioning evidence never reaches the Feed. The typed bundle and cadence-aware snapshot contracts now provide the existing boundaries needed to activate it without Provider-specific orchestration or freshness logic.

## What Changes

- Enable the existing verified CFTC Provider in the production Provider plan while retaining its credential-free contract.
- Publish normalized CFTC `positioning` evidence through the existing typed Feed bundle's positioning domain artifact.
- Apply the existing weekly cadence and snapshot carry-forward semantics: new reports replace the prior CFTC slice, unchanged valid reports retain original evidence timestamps, and current retrieval/generation timestamps remain operational observations.
- Keep CFTC failures observable as incomplete acquisition with `not_evaluated` freshness; prior evidence cannot convert a failed run into success or publication.
- Add deterministic production-path tests for a new report, a no-new-report carry-forward, and Provider failure, and update only directly affected documentation.
- Do not add analysis, signals, ranking, scoring, investment conclusions, new providers, Host Agent behavior, or a new activation/freshness framework.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `feed-evidence-pipeline`: Require the shipped production Feed plan to include the verified CFTC weekly positioning source and publish its evidence under the existing typed positioning, provenance, freshness, completeness, and failure contracts.

## Impact

The change affects CFTC activation policy, production Feed planning and integration tests, deterministic fixtures, and directly related Feed/provider documentation. Existing Feed and artifact schema shapes, the CFTC adapter and manifest contract, external dependencies, credentials, Host Agent boundaries, and retained analytics remain unchanged.

The request's phrase `feed-market.json positioning output` is interpreted as positioning evidence in the authoritative market Feed bundle. Under the accepted typed-bundle contract, the concrete output is the generation-qualified `positioning` domain artifact (`feed-positioning-<generation>.json`) inventoried by `feed-manifest.json`; routing positioning into the separate `market_data` artifact would violate the existing closed domain contract.
