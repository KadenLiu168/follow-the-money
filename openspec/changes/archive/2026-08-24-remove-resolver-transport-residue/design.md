## Context

See `proposal.md` for motivation. The accepted `deterministic-research-engine` contract and `engine/candidates.py` currently agree on mention graphs followed by packed candidate Blocks with request aliases and 20-record, 24-seed, 32-KiB, and 40-block limits. Those shapes were transport for the removed semantic/LLM Resolver, while the retained graph has no production orchestration caller.

Two correctness defects sit inside the retained graph boundary. Canonical-entity recognition currently ignores the supplied closed registry and instead interprets subject prefixes. Title similarity attempts to read a nonexistent `LedgerEntry.raw_title`, while tests place titles in `raw_subject`. The Feed already carries title metadata, and the existing title module delegates to the closed Feed normalization/Jaccard algorithm.

Current non-archive reference tracing finds Block-only helpers confined to candidate packaging and its focused tests. It also finds current Block claims in the two modified living requirements and `docs/architecture.md`; README files and `SKILL.md` contain no direct current candidate-Block claim. Archived Changes remain historical evidence.

## Goals / Non-Goals

**Goals:**

- End candidate preparation at deterministic connected Components.
- Preserve the exact domain edge rules and v1 time/title thresholds while correcting their identity and title inputs.
- Keep `LedgerEntry.subject` authoritative and make canonical status an exact closed-registry fact.
- Keep evidence titles separate from fact identity through a minimal read-only internal association.
- Remove only helpers, errors, tests, and documentation whose responsibility is the former Resolver transport.

**Non-Goals:**

- Redesigning Ledger, canonical fact, Event, family, scoring, selection, Feed, provider, configuration, or schema contracts.
- Changing alias or fuzzy behavior of entity resolution, adding semantic clustering, or re-resolving stored Ledger subjects.
- Defining Agent data shapes, batching, budgets, orchestration, production callers, or any LLM/model/credential runtime.
- Broad baseline normalization, which remains ECO-31 work.

## Decisions

### 1. The candidate boundary ends at Components

Delete the Block model, packing function, request aliases, Resolver capacity constants and failure paths, and helpers used only to project, size, or package Components. Keep mention nodes, edge construction, connected Components, and their current hash-derived identity and canonical ordering. Do not replace Blocks with batches, envelopes, pages, or another capacity layer.

This subtraction is preferred over renaming because the removed responsibilities have no independent deterministic-domain consumer. Retaining a generic batch would preserve the same unowned transport policy; imposing new limits would invent a future caller contract.

### 2. Canonical-entity status is exact registry membership

Candidate matching will ask the existing closed entity boundary whether the exact stored `LedgerEntry.subject` is a configured canonical ID. The implementation may expose the smallest read-only membership operation needed for this check, but the contract does not freeze a new public method name. It must not call broad `resolve()` on the stored subject because that includes alias and substring behavior and could reinterpret an already-stored identity.

This is preferred over prefix heuristics because IDs are defined by the registry, not their spelling. It also avoids changing the separately retained alias/fuzzy resolution semantics. Unregistered subjects—including canonical-looking `ent_*` strings—participate only in the existing entity-less rule; configured IDs remain canonical even if their text begins with `raw_` or `unresolved`.

### 3. Evidence titles are an explicit read-only candidate input

Edge construction will receive a minimal association from `evidence_id` to the actual evidence title alongside facts and the registry. The exact incidental Python signature remains an Apply-time implementation choice, but ownership is fixed: the caller supplies evidence metadata, and the candidate layer performs no acquisition, lookup, caching, or schema projection. Missing keys and empty titles both mean title unavailable.

Title comparisons continue through `engine/title.py` and therefore reuse `feed.dedupe.normalize_title` and `title_jaccard`. `LedgerEntry` gains no `raw_title`; `raw_subject` remains raw subject provenance and is never consulted for title similarity. There is no synthetic or heuristic fallback.

This is preferred over extending Ledger because title is evidence metadata rather than canonical fact identity, and over passing whole Feed items because candidate grouping needs only a narrow internal value.

### 4. Preserve the three existing edge rules exactly

Edge construction retains the following precedence and values:

1. Equal complete canonical fact keys create an edge independent of title or registry recognition.
2. The same exact registry-recognized entity within 48 hours creates an edge when predicates match or evidence-title Jaccard is at least 0.45.
3. When neither subject is registry-recognized, matching `origin_payload` and predicate within 12 hours creates an edge when evidence-title Jaccard is at least 0.85.

The third rule is described by its actual typed fields rather than the historical “market/category” shorthand. Different recognized entities do not join through title similarity. Missing titles disable only title-derived paths; they do not weaken exact canonical-fact or same-predicate behavior.

### 5. Tests move from transport fixtures to domain invariants

Apply begins by making focused tests RED for registry membership, title provenance and thresholds, missing titles, `raw_subject` non-influence, entity-less boundaries, and full permutation determinism. Candidate fixtures that need canonical entities will construct a closed test registry explicitly. Transport packing/capacity/alias tests will be deleted or replaced by a regression proving large valid Component sets are not rejected by removed transport limits; no arbitrary replacement bound will be asserted.

A narrowly scoped architecture check may inspect current non-archive candidate code for the removed symbols and equivalent batching. It must not reject the legitimate deterministic `EntityResolver`, archived history, or negative architectural statements.

## Risks / Trade-offs

- [Risk] A hidden current consumer depends on Block packaging despite the present reference trace. → Re-run non-archive call/reference tracing before deletion; if a non-transport responsibility exists, stop and record the conflict instead of widening ECO-28.
- [Risk] Adding registry membership accidentally changes alias/fuzzy resolution. → Use exact configured-ID membership only and retain existing `resolve()` behavior and focused entity-resolution regressions.
- [Risk] Title fixtures pass through `raw_subject` accidentally. → Use an explicit evidence-title fixture mapping and add a negative test where changing `raw_subject` cannot alter the edge set.
- [Risk] Removing transport limits is mistaken for removing all safety bounds. → Limit deletion to the four Resolver-envelope capacities and their exclusive helpers/errors; preserve time windows, title thresholds, typed domain validation, and unrelated repository limits.
- [Risk] Documentation cleanup expands into ECO-31. → Change only direct current candidate-Block/transport claims confirmed by search and report unrelated stale baseline language separately.

## Migration Plan

1. Reconfirm references and establish focused RED tests for the corrected domain behavior before changing implementation.
2. Add the minimum exact registry-membership support and explicit evidence-title input, then make focused identity/title/component tests GREEN.
3. Remove Block packaging and any now-orphaned transport-only helpers/imports/errors; remove the corresponding transport tests without replacement capacities.
4. Synchronize only the two living requirements and directly stale non-archive architecture claims identified by the Change.
5. Run focused deterministic regressions, the canonical repository quality gate, `openspec doctor`, and target/all strict validation.

Rollback is a normal code/spec revert before archive. No persisted data or external serialized contract migration is required because current tracing finds no production caller and the removed Block types are internal Python transport residue.
