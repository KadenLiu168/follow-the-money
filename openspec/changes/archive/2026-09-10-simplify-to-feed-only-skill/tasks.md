## 1. Establish the Breaking Feed Contract

- [x] 1.1 Confirm the corresponding Linear execution issue, blockers, and approved Feed-only scope before implementation; verify the issue explicitly covers non-Feed capability and three-domain removal.
- [x] 1.2 Add new logical Feed, manifest, and artifact schema majors for the ordered five-domain set (`news`, `macro_release`, `policy`, `positioning`, `filing`); verify schema tests reject `market_data`, `flow`, `calendar`, missing domains, extra domains, and reordered inventories.
- [x] 1.3 Implement bounded migration from a fully validated previous eight-domain bundle to a new five-domain candidate without preserving removed-domain evidence; verify migration recomputes identity and rejects corrupt or mixed-generation input.

## 2. Narrow Providers and Configuration

- [x] 2.1 Remove Yahoo Market activation, adapter, manifest, fixtures, market coverage, and market-data fan-out; verify static configuration and import tests find no Yahoo or `market_data` production path.
- [x] 2.2 Narrow Federal Reserve, BLS, NBS, SSE, and SZSE payload declarations and coverage labels to outputs their adapters actually implement; verify a manifest that over-declares a payload type fails before Provider requests.
- [x] 2.3 Make CFTC enabled and minimum-one required coverage while preserving weekly complete-check, valid-empty/valid-unchanged, provenance, and incomplete-acquisition semantics; verify focused CFTC planning, freshness, coverage, and degradation tests pass.
- [x] 2.4 Remove analysis-only configuration for scoring, Market State, watchlist policy, safety lexicon, entities, roles, sessions, and Brief-era run/lag fields while retaining Feed limits, roots, rates, source provenance, coverage, and SEC watched-company filtering; verify removed keys fail closed and surviving shipped configuration loads without credentials.
- [x] 2.5 Remove `exchange-calendars` and any other dependency used only by deleted capabilities after static import tracing confirms no Feed caller remains; verify `uv sync --frozen --all-groups` succeeds with the regenerated lockfile.

## 3. Convert Feed Production and Consumption

- [x] 3.1 Update bundle construction, validation, publication, remote retrieval, semantic reconstruction, deterministic ordering, and generated-state allowlists to exactly five artifacts; verify focused bundle, publication, remote, determinism, and deployment tests pass.
- [x] 3.2 Remove `market_data`, `flow`, and `calendar` payload normalization/validation branches, market lookback limits, future-calendar coverage/horizon state, and removed cadence values without weakening retained payload validation; verify Feed schema and semantic negative tests cover all removed fields and domains.
- [x] 3.3 Preserve fixed cutoff/window, Provider provenance, cadence-aware freshness, required coverage, bounded blocked-provider degradation, identity/digest, canonical bytes, atomic manifest activation, checkpoint/lease/rate safety, and typed exits; verify the existing focused trust-boundary regressions pass after fixture conversion.
- [x] 3.4 Update canonical five-domain fixtures and checked-in generated-product expectations through deterministic test/migration tooling rather than hand-editing identities; verify `scripts/validate_generated_state.py` succeeds in the intended repository state without an unnecessary real-network dry run.

## 4. Remove Non-Feed Runtime Surfaces

- [x] 4.1 Delete the private Agent invocation runtime and schema together with Audit and Event invocation tests; verify no executable, schema reference, operation name, or production caller for `audit.text`, `audit.claims`, or `event.structure` remains.
- [x] 4.2 Delete Ledger, Event, entity resolution, candidate grouping, and candidate-only title wrappers; verify Feed deduplication remains available directly under the Feed package and no removed import remains.
- [x] 4.3 Delete Market formulas/snapshot/surprise, Market State, Confidence, Watchlist, Scoring, and Ranking implementations and their tests; verify repository static audits find no retained non-Feed capability module or configuration.
- [x] 4.4 Delete the Brief-oriented local Feed-health path and replay-only fingerprint helpers while preserving the producer build fingerprint used by Feed identity; verify focused producer fingerprint and canonical Feed tests pass.
- [x] 4.5 Remove obsolete test modules and replace any cross-surface acceptance test with Feed-only architecture regressions; verify tests assert absence of non-Feed runtime/schema/config and continued evidence-only Feed behavior.

## 5. Align Contracts, Instructions, and Documentation

- [x] 5.1 Update the project `AGENTS.md` to the Feed-only architecture, removing private Audit/Event, retained-capability, Phase 5, and no-caller retention instructions while preserving deterministic, credential-free, fail-closed Feed invariants; verify no current instruction contradicts the Change specs.
- [x] 5.2 Sync the accepted living specs to the Feed-only delta, removing obsolete capability specs or requirements as designed while leaving archived Changes and `openspec/config.yaml` unchanged; verify current specs contain no positive non-Feed capability claim.
- [x] 5.3 Update `SKILL.md`, READMEs, references, architecture/configuration/feed docs, runbooks, and validation evidence; delete scoring/capability-status documentation that has no surviving subject and verify documentation tests describe five domains, eight required Providers, and no private invocation.
- [x] 5.4 Ensure wording distinguishes retained raw positioning/filing evidence from prohibited interpretation and does not claim calendar, flow, market data, ranking, regime, anomaly, recommendation, or trading output; verify repository text audits pass outside archived history.

## 6. Final Verification

- [x] 6.1 Run all directly affected focused pytest suites during implementation and verify each passes with deterministic fixtures and no credential or live-network dependency.
- [x] 6.2 Run `.venv/bin/python scripts/quality_gate.py` and verify the canonical repository quality gate passes.
- [x] 6.3 Run `openspec doctor`, `openspec validate simplify-to-feed-only-skill --strict`, and `openspec validate --all --strict`; verify all checks pass.
- [x] 6.4 Perform a final caller/import/config/schema/documentation review and verify the only repository capability is the five-domain Evidence Feed, all eight Providers including CFTC are required, no removed domain or capability remains current, and unresolved risks are documented.
