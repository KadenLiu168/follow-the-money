## Why

`follow-the-money` is now a current information-digest Skill whose repository responsibility is a deterministic published evidence Feed. Keeping independent Audit/Event invocation and unwired research, market, confidence, watchlist, scoring, and ranking capabilities preserves obsolete product surfaces, while three Feed domains also have no required place in the simplified product.

## What Changes

- **BREAKING** Reduce the repository and Skill capability surface to Evidence Feed only; remove the private Agent invocation protocol and its Audit and Event Structuring operations.
- **BREAKING** Remove retained Ledger/Event candidate preparation, Market Analytics and State, Confidence and Watchlist, and Scoring and Ranking contracts, implementations, configuration, tests, schemas, and documentation.
- **BREAKING** Reduce the Feed payload domain set from eight to five: retain `news`, `macro_release`, `policy`, `positioning`, and `filing`; remove `market_data`, `flow`, and `calendar` plus their artifacts and domain-specific validation.
- **BREAKING** Remove Yahoo Market and make CFTC a required Provider. Retain Federal Reserve, BLS, PBOC, NBS, SSE, SZSE, SEC EDGAR, and CFTC as the required credential-free Provider set, with Provider manifests narrowed to behavior actually implemented by their adapters.
- Remove analysis-only configuration, the unused local Brief health path, replay-only residue, obsolete dependencies, and tests that assert removed behavior.
- Preserve deterministic Feed collection, normalization, deduplication, provenance, freshness, coverage and degraded-state semantics, identity/digest integrity, fail-closed validation, durable publication, and canonical remote consumption.
- Keep Host-Agent summarization and formatting evidence-preserving and outside repository runtime; add no LLM, model, credential, orchestration, public CLI, investment, or trading capability.
- Align current OpenSpec, project `AGENTS.md`, `SKILL.md`, schemas, configuration, Provider contracts, scripts, tests, READMEs, references, and documentation. Leave `openspec/config.yaml` and archived Changes unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `feed-evidence-pipeline`: Contract the Feed to five evidence domains and eight required Providers while preserving its trust, validation, health, identity, publication, and consumption guarantees.
- `information-digest-invocation`: Make the current validated Feed the Skill's only repository capability and remove references to independent or retained non-Feed capabilities.
- `skill-capability-surface`: Replace the six-family catalog with an Evidence-Feed-only capability surface.
- `skill-agent-responsibility-boundary`: Narrow Skill ownership to Feed semantics and remove Audit, Event, and retained research-capability ownership.
- `agent-grounding-validation-contract`: Remove Audit and non-Feed deterministic-result dependencies while retaining Feed-grounded, evidence-preserving digest constraints.
- `agent-runtime-invocation-contract`: Remove the private one-shot Agent invocation capability in full.
- `deterministic-core-retention`: Redefine the retained deterministic core as Feed-only and remove obsolete configuration and caller-status requirements.
- `deterministic-research-engine`: Remove the retained research-engine capability in full.

## Impact

- Runtime removal under `src/follow_the_money/`: Agent invocation, Audit, Ledger/Event/candidate preparation, Feed-health residue, Market, Confidence, Watchlist, Scoring, and Ranking modules.
- Feed/runtime changes: five domain artifacts, no Yahoo adapter/contract, CFTC required coverage, narrower Provider declarations, and simplified Feed/config validation.
- Schema/config/dependency changes: remove the Agent invocation schema, three Feed payload branches, analysis-only configuration, Yahoo role/session configuration, and dependencies used only by removed analytics.
- Test/documentation changes: remove obsolete capability suites, add five-domain/required-CFTC/evidence-only regressions, and align project instructions and current-facing documentation.
- No Provider or source type is added; no embedded model, credential, Agent orchestration, public CLI, or trading behavior is introduced.
