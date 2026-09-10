## Context

See `proposal.md` for motivation. The current normal Skill already consumes a validated published Feed and delegates evidence-preserving summarization to the Host Agent, but the repository also exposes a private Audit/Event process boundary and retains an unwired deterministic research engine. The Feed itself publishes eight domain artifacts although `flow` has no Provider producer, `calendar` is declared by manifests but not emitted by current adapters, and `market_data` exists only for the product surface now being removed.

The target must preserve the repository's trust boundaries while removing obsolete breadth. In particular, deleting analytics must not weaken Provider contract resolution, evidence provenance, fixed-cutoff collection, freshness, coverage, accepted degradation, deterministic identity, bundle validation, durable publication, or canonical remote consumption.

## Goals / Non-Goals

**Goals:**

- Leave one repository capability: the deterministic Evidence Feed consumed by the information-digest Skill.
- Publish exactly five evidence domains: `news`, `macro_release`, `policy`, `positioning`, and `filing`.
- Keep eight required credential-free Providers: Federal Reserve, BLS, PBOC, NBS, SSE, SZSE, SEC EDGAR, and CFTC.
- Remove all code and contracts whose only purpose is Audit, Event/research preparation, market interpretation, confidence, watchlist, scoring, ranking, or removed Feed domains.
- Simplify shared configuration at the owning boundary rather than retaining fields for deleted consumers.
- Preserve fail-closed behavior and truthful Provider/domain claims.

**Non-Goals:**

- Adding or replacing Providers, implementing calendar extraction, or introducing another evidence type.
- Changing Host-Agent summarization into repository runtime behavior.
- Weakening evidence accounting, provenance, or validation to reduce line count.
- Preserving compatibility for the private Agent invocation protocol or the removed Feed schema/domain major.
- Rewriting archived OpenSpec Changes or adding product context to `openspec/config.yaml`.

## Decisions

### 1. Make the semantic capability catalog Feed-only

The accepted six-family catalog is replaced by one Evidence Feed capability. The private Agent invocation schema/runtime is deleted rather than retained as a dormant compatibility surface. The deterministic research-engine contract and implementations are deleted rather than moved to a `legacy` package.

Alternative considered: retain Audit as a safety helper. Rejected because the selected product boundary is Feed-only, the normal Skill does not invoke Audit, and Host-Agent digest constraints already prohibit trading judgment without requiring a repository validator.

### 2. Contract the serialized Feed to five domains with an explicit major migration

New production and canonical consumption use exactly these domain artifacts in stable order:

```text
news
macro_release
policy
positioning
filing
```

`market_data`, `flow`, and `calendar` payload branches and artifacts are removed. This is a breaking serialized contract and therefore requires new logical Feed, manifest, and artifact schema majors rather than silently changing the domain set under the current major. The migration retains only evidence that validates under the new five-domain contract; removed-domain artifacts are excluded from the activated inventory and generated-state allowlist.

Alternative considered: keep empty compatibility artifacts. Rejected because `flow` has no producer, `calendar` has no implemented producer, and empty permanent artifacts preserve exactly the ambiguity this change removes.

### 3. Keep only Providers that produce the retained evidence surface

Yahoo Market and its fixtures, role mappings, activation, coverage, and runtime adapter fan-out are removed with `market_data`. Federal Reserve, BLS, PBOC, NBS, SSE, SZSE, SEC EDGAR, and CFTC remain required and credential-free. CFTC receives an explicit minimum-one required coverage obligation; a complete check with no new weekly report remains valid under its cadence contract, while incomplete CFTC acquisition cannot be silently treated as optional completeness.

Provider manifests are narrowed to payload behavior their current adapters can actually emit. Unsupported `calendar` and `market_data` declarations are removed; coverage labels such as `future_calendar`, `verified_market_data`, and `notice_and_market` are removed or narrowed. This is correction of the Provider trust boundary, not implementation of missing adapters.

### 4. Separate shared Feed configuration from deleted analysis configuration

Delete scoring, Market State, watchlist calendar policy, safety lexicon, entities, application-level Brief lag/run fields, market roles, and sessions. Keep Feed limits, Provider activation/coverage, Provider manifests, source-family provenance needed by Provider validation, SEC watched-company filtering, rate registry, output/runtime roots, and other values with verified Feed callers.

After roles/sessions and market snapshot code are removed, remove `exchange-calendars` if static import tracing and tests confirm no Feed caller remains. Defaults duplicated in Python remain prohibited for surviving normative fields.

### 5. Delete obsolete paths as coherent vertical slices

Remove the Agent invocation schema/runtime and its tests together. Remove Event Structuring with Ledger/Event/candidate/entity code. Remove Market/State/Confidence/Watchlist/Scoring/Ranking code with their configuration, dependency, tests, and docs. Remove the old local Brief-oriented Feed-health module and replay-only fingerprint helpers that have no surviving Feed caller.

Shared helpers are retained only when a surviving Feed import or accepted Feed invariant requires them. Feed deduplication title logic remains under the Feed package even though candidate title wrappers are removed.

### 6. Preserve the complete Feed trust chain

The simplification does not replace the manifest-led bundle with an unvalidated or partially published file. Provenance, cadence-aware freshness, required-Provider coverage, bounded blocked-provider degradation, semantic identity, canonical serialization, create-only staging, atomic manifest activation, continuity state, and remote fail-closed consumption remain. Domain removal simplifies these mechanisms' closed sets; it does not remove their guarantees.

### 7. Align instructions and living contracts without creating another truth source

Project `AGENTS.md` is updated because it currently requires private Audit/Event and retained analytics. Living OpenSpec is updated or removed to describe Feed-only behavior. `SKILL.md`, references, READMEs, and docs are aligned with actual behavior. `openspec/config.yaml` remains unchanged because it contains only workflow schema selection; adding product context there would duplicate the living specs and project instructions.

## Risks / Trade-offs

- **Breaking existing Agent invocation callers** -> Treat removal as intentional with no compatibility shim; document the removed surface and new Feed-only boundary.
- **Existing published eight-domain bundle cannot satisfy the new closed domain set** -> Introduce explicit schema-major migration and atomically publish a validated five-domain bundle before canonical consumers require the new major.
- **Deleting market configuration could accidentally remove Provider trust fields** -> Trace every surviving Feed caller and retain only Provider identity, source, fetch, cadence, coverage, and SEC filtering fields actually required by the five-domain pipeline.
- **CFTC weekly emptiness could be mistaken for Provider failure** -> Preserve its complete-check, valid-unchanged, source-time, and cadence semantics while making its coverage membership mandatory.
- **Manifest declarations currently exceed adapter output** -> Narrow declarations and add static tests that every declared payload type is producible and belongs to the five-domain set.
- **Smaller domain set may reduce digest breadth** -> This is the accepted product trade-off; Host Agent must not reconstruct removed market, flow, or calendar products from unsupported data.
- **Large deletion could weaken negative safety guarantees** -> Retain Feed intelligence-field rejection and Skill evidence-only/no-financial-judgment regressions even though Deterministic Audit is removed.

## Migration Plan

1. Add the new five-domain schema majors and update bundle construction/validation to recognize the explicit migration boundary.
2. Narrow Provider contracts and configuration; remove Yahoo and make CFTC required before deleting shared market configuration.
3. Update producer, generated-state allowlists, publication, remote consumption, and fixtures to the five-domain inventory.
4. Delete non-Feed runtime/schema/config/dependency slices and obsolete tests; add focused Feed-only and absence regressions.
5. Update project instructions, Skill/docs/references, and living OpenSpec; do not modify archived Changes or `openspec/config.yaml`.
6. Generate and atomically activate a valid five-domain current bundle through the approved deployment path. Do not hand-edit generated Feed identity or runtime state.
7. Run focused tests, the canonical quality gate, OpenSpec doctor, strict Change validation, and strict all-artifact validation.

Rollback requires reverting code/contracts and atomically restoring a complete schema-compatible active bundle as one coherent repository state; mixed five-domain/eight-domain code and generated artifacts are not a valid rollback state.
