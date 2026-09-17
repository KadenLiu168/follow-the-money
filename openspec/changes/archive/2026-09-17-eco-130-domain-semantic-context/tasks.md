## 1. Characterize the Semantic-Context Contract

- [x] 1.1 Add focused failing tests for the closed common context shape, bounded text/arrays, domain-extension match, deterministic ordering/deduplication, forbidden analytical keys, and filing/positioning exclusion; verify the new cases fail for the expected missing ECO-130 behavior with `.venv/bin/python -m pytest tests/test_semantic_context.py tests/test_feed_boundary.py -q`.
- [x] 1.2 Add fixture-driven failing tests for BLS/NBS/SSE/SZSE news, NBS macro, and Federal Reserve/PBOC policy mappings, including safe fallbacks, null reporting period and other null/empty optional facts, unknown macro series, previous-period-versus-revision behavior, and repeated execution under altered decimal context; verify failures identify the unimplemented mappings rather than unrelated setup errors.

## 2. Implement the Closed Semantic Primitive and Domain Mappers

- [x] 2.1 Implement the minimal immutable `SemanticContext` construction/serialization boundary in `src/follow_the_money/semantic/context.py`, reusing ECO-125 canonical numeric guards without expanding their import surface or wire responsibility; verify common-model and ambient-decimal tests pass.
- [x] 2.2 Implement pure bounded news mapping in `src/follow_the_money/semantic/news.py` for BLS, NBS, SSE, and SZSE, with exact refinements and factual Provider-specific fallbacks; verify focused news mapper tests prove subject/event/document output, deterministic references, unsupported-provider failure, and no inferred entities.
- [x] 2.3 Implement pure bounded macro mapping in `src/follow_the_money/semantic/macro.py` for the closed NBS series vocabulary, explicit null preservation for a missing observation period, ordered actual/consensus/previous facts, explicit unavailability, and source-explicit same-period revisions; verify macro tests prove canonical values, null period behavior, and that a previous-period value never becomes a revision.
- [x] 2.4 Implement pure bounded policy mapping in `src/follow_the_money/semantic/policy.py` for Federal Reserve and PBOC exact actions plus generic official-announcement fallbacks; verify policy tests prove issuer/type/action output and preserve null effective date/empty scope when source evidence is absent.

## 3. Add and Enforce the Wire Contract

- [x] 3.1 Extend `schemas/feed.schema.json` with one optional closed `semantic_context` definition and domain-discriminated extension, relying on the existing artifact schema item reference rather than duplicating the shape; verify valid contexts pass and unknown fields, vocabularies, mismatched domains, malformed numerics, and context on unaffected domains fail schema/Feed tests.
- [x] 3.2 Add semantic cross-field validation in `src/follow_the_money/feed/validate.py` for payload-domain/time/title/nullable-period/numeric/effective-date consistency, Provider issuer/series consistency, total ordering, uniqueness, and recursive evidence-only boundaries; verify consumer-mode tests accept legacy omissions and a matching null macro period but reject every malformed present context.
- [x] 3.3 Add explicit current-production admission to Feed validation and use it from Feed construction and `build_bundle`, allowing omission only for a complete contextless prior slice proven by non-null `carried_forward_from_run_id`, regardless of whether its independently evaluated carry status is `valid_unchanged` or `stale`; verify focused tests reject new/replacement omissions, preserve byte-identical legacy carry through both statuses, and do not enable partial/failed fallback.

## 4. Integrate Current Provider Paths

- [x] 4.1 Attach semantic context after existing normalized payload/source construction for Federal Reserve policy, PBOC policy, BLS news, NBS news/macro, and SSE/SZSE news without changing fetches, payload discriminators, item IDs, manifests, or contract versions; verify `tests/test_adapters.py` and new mapper assertions cover every current path.
- [x] 4.2 Verify semantic-construction failures flow through existing item rejection, Provider completeness, and publication semantics without a new orchestration layer or hidden fallback by running the focused adapter and Feed pipeline/CLI tests.

## 5. Preserve Canonical Identity, Bundle, and Snapshot Behavior

- [x] 5.1 Add deterministic regressions proving identical fixtures/cutoff produce identical context, item/artifact canonical bytes, `content_digest`, and `run_id`, while changing one context fact changes Feed identity but not the source-derived item ID; verify `tests/test_feed_determinism.py` and the new ECO-130 tests pass.
- [x] 5.2 Add bundle round-trip, artifact, remote-consumer, and snapshot migration regressions proving present context survives unchanged, pre-ECO-130 v4 bundles remain readable, legacy slices retain exact bytes when carried as `valid_unchanged` and after aging to `stale`, and the next complete replacement requires context; verify the focused bundle, boundary, snapshot/freshness, and remote tests pass.
- [x] 5.3 Run the existing SEC/CFTC semantic regression suites to prove ECO-125 numeric behavior and filing/positioning typed payloads remain unchanged and do not acquire `semantic_context`.

## 6. Align Documentation and Complete Verification

- [x] 6.1 Update the current Feed contract and architecture/Host-Agent documentation in `docs/`, `references/`, `README.md`, `README.zh-CN.md`, and `SKILL.md` only where needed to describe `semantic_context`, its legacy omission boundary, and the unchanged evidence-only presentation responsibility; verify documentation tests and repository searches contain no claim of ranking, impact analysis, or Digest generation.
- [x] 6.2 Run `.venv/bin/python scripts/quality_gate.py` and resolve only ECO-130 regressions until the canonical gate passes.
- [x] 6.3 Run `openspec doctor`, `openspec validate eco-130-domain-semantic-context --strict`, and `openspec validate --all --strict`; verify every command succeeds and the completed implementation, tests, schemas, specs, and truthful documentation remain aligned.
