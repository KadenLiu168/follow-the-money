## 1. Apply Preflight and Reference Trace

- [x] 1.1 Re-read ECO-28 scope/blockers, the two living requirements, active Changes, `engine/candidates.py`, `engine/entities.py`, `ledger.py`, focused tests, and current non-archive docs; record any conflict and stop rather than expanding into ECO-29/30/31 or future Agent work.
- [x] 1.2 Run non-archive symbol/call tracing for `CandidateBlock`, `pack_blocks()`, capacity constants/errors, aliases, `Component.projection_records()`, canonical-byte sizing, candidate graph entry points, and docs claims; confirm every planned deletion is transport-only and preserve any independently owned domain responsibility.
- [x] 1.3 Prepare the frozen environment with `uv sync --frozen --all-groups` and confirm the worktree so unrelated user changes can be preserved.

## 2. RED Candidate Contract Tests

- [x] 2.1 Refactor candidate fixtures to keep `raw_subject` as subject provenance, provide explicit `evidence_id -> title` metadata, and explicitly construct closed test registries for cases that require canonical entities.
- [x] 2.2 Add RED identity tests proving exact registry membership recognizes IDs without `ent_`, rejects unregistered `ent_*`, and is not overridden by `raw_`/`unresolved` prefixes, while preserving existing `EntityResolver.resolve()` alias/fuzzy behavior.
- [x] 2.3 Add RED same-entity title tests at/above and below 0.45, missing/empty-title tests, and a negative test proving `raw_subject` cannot influence title similarity.
- [x] 2.4 Add RED entity-less tests for the matching `origin_payload`/predicate, 12-hour, and 0.85 title conditions and their negative boundaries; retain canonical-fact and same-predicate title-independent coverage.
- [x] 2.5 Strengthen permutation tests to compare mention IDs, edge sets, Component membership, Component IDs, and Component order across equivalent fact and title-association reorderings.
- [x] 2.6 Remove transport-only Block packing/alias/capacity assertions and add a focused RED regression showing valid Components are returned without the former record/seed/byte/total-block failures or a renamed batching abstraction.
- [x] 2.7 Run the focused candidate/entity/title test selection and capture the expected failures before editing implementation.

## 3. Minimal Candidate Implementation

- [x] 3.1 Add the minimum read-only exact canonical-ID membership support at the closed entity-registry boundary, without changing alias/substring resolution or re-resolving stored Ledger subjects.
- [x] 3.2 Make candidate entity matching use only registry membership of authoritative `LedgerEntry.subject`; remove all prefix and `raw_subject` identity heuristics.
- [x] 3.3 Make candidate edge construction consume explicit evidence titles keyed by `evidence_id`, reuse the existing title normalization/Jaccard path, and treat missing/empty titles as unavailable with no fallback or synthetic value.
- [x] 3.4 Preserve the complete-canonical-fact, 48-hour same-entity predicate/0.45-title, and 12-hour entity-less same-origin/predicate/0.85-title rules exactly, using terminology matching the implemented typed fields.
- [x] 3.5 Remove `CandidateBlock`, `pack_blocks()`, request aliases, all four Resolver transport capacities and exclusive failure paths, and any now-orphaned projection/sizing helpers and imports; do not introduce replacement batching or unrelated limits.
- [x] 3.6 Run `tests/test_engine.py` until all focused candidate/entity/title and determinism regressions pass.

## 4. Contract and Documentation Alignment

- [x] 4.1 Apply the `deterministic-research-engine` delta to its living requirement, retaining Components and exact edge semantics while removing Blocks, aliases, transport capacities, and false title/identity assumptions.
- [x] 4.2 Apply only the direct candidate-Block wording delta to `deterministic-core-retention`; leave unrelated baseline acceptance, Feed, scoring, safety, and future architecture requirements unchanged.
- [x] 4.3 Update only current non-archive documentation directly made stale by ECO-28 (currently the candidate-Block claims in `docs/architecture.md`); recheck README files and `SKILL.md`, modifying them only if tracing finds an inaccurate current claim.
- [x] 4.4 Verify archived Changes, external schemas, Ledger/Event identity, Feed/provider/config behavior, scoring/selection/audit semantics, and production wiring are unchanged.

## 5. Verification and Scope Audit

- [x] 5.1 Run focused candidate/entity/title tests in `tests/test_engine.py` and confirm they pass.
- [x] 5.2 Run related deterministic regressions in `tests/test_dedupe.py` and `tests/test_events.py` and confirm they pass.
- [x] 5.3 Run the canonical repository gate `.venv/bin/python scripts/quality_gate.py` and confirm it passes; do not substitute a weaker custom check set.
- [x] 5.4 Run `openspec doctor`, `openspec validate remove-resolver-transport-residue --strict`, and `openspec validate --all --strict`, and confirm all structural/strict checks pass.
- [x] 5.5 Review the final diff and reference trace against ECO-28 acceptance criteria: only transport residue and directly scoped correctness/docs/contracts changed, deterministic Components remain, no equivalent batching/external schema/Agent/LLM/fake wiring was added, archived history is untouched, and any unresolved conflict or later-issue work is reported.
