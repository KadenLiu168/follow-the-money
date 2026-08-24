## Why

Candidate grouping still implements the packed Block envelope, aliases, and capacity limits that bounded requests to the removed semantic/LLM Resolver. With Phase 1 trust-boundary work complete and ECO-31 blocked on this cleanup, ECO-28 must deliberately change the currently accepted contract so the retained candidate layer is a transport-agnostic deterministic domain library.

## What Changes

- Preserve deterministic atomic-seed mention construction, canonical-fact equality, entity/time/predicate/title edge rules, connected Components, and stable identities and ordering.
- **BREAKING** Remove `CandidateBlock`, `pack_blocks()`, request-local component aliases, and Resolver-request record/seed/byte/total-block limits and capacity errors without introducing replacement batching.
- Determine whether `LedgerEntry.subject` is a canonical entity ID by exact membership in the closed configured entity registry, not by `ent_`, `raw_`, or `unresolved` naming conventions.
- Supply evidence titles to candidate edge construction as explicit metadata keyed by `evidence_id`; do not use `raw_subject`, add `raw_title` to `LedgerEntry`, invent missing titles, or change the existing title normalization/Jaccard algorithm and thresholds.
- Keep candidate preparation as a retained post-Feed library with no current production orchestration caller; do not define an Agent contract, add an LLM runtime, or wire a replacement pipeline.
- Synchronize only the current non-archive architecture documentation made stale by removing candidate Blocks; preserve archived Changes as historical evidence.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `deterministic-research-engine`: Replace candidate Block packing and transport capacities with registry-backed, evidence-title-aware deterministic Component grouping while preserving existing domain edge rules, identity, ordering, and honest caller status.
- `deterministic-core-retention`: Replace the direct claim that candidate Blocks are retained internal structures with transport-neutral candidate Components/grouping, without broadening the baseline alignment assigned to ECO-31.

## Impact

- Primary implementation: `src/follow_the_money/engine/candidates.py`; a minimum registry-membership surface may be added at the existing `EntityResolver` boundary only if needed by candidate grouping.
- Primary tests: `tests/test_engine.py`, including registry-backed identity, explicit evidence-title metadata, grouping thresholds, missing-title behavior, permutation determinism, and removal of transport-only assertions.
- Contracts and documentation: delta specs for `deterministic-research-engine` and `deterministic-core-retention`, plus only current non-archive documentation that directly describes candidate Blocks or Resolver transport (currently `docs/architecture.md`).
- No changes to Ledger/Event identity, Feed/provider/config/schema behavior, scoring/selection/audit semantics, production wiring, dependencies, external serialized contracts, archived Changes, or future Agent architecture.
- Repository tracing found no current non-test consumer of candidate graph or Block packaging; this is consistent with the accepted contract's statement that the retained post-Feed library has no production orchestration caller. If Apply-time tracing contradicts that fact, implementation must stop and record the conflict rather than expand scope.
