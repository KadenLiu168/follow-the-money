## Context

See `proposal.md` for motivation. ECO-50 implements one private `python -m` process that classifies request shapes before validating the shared root schema, statically dispatches two Audit operations, maps values explicitly, and emits one success or typed error response. The retained `ledger.py` and `events.py` already own stable fact IDs, canonical Event IDs, key-fact order, `fully_known_at`, family/coexistence identities, display templates, and effective-time projections.

ECO-51 needs a serialized trust-boundary mapping, not a new Event algorithm. One current implementation defect is nevertheless directly observable through the proposed result: when key facts use different precisions, `economic_effective_time.value` is selected from the first canonical key fact while `precision` is selected from an unordered set and changes across `PYTHONHASHSEED`. Apply must repair only that accepted determinism violation at its source after a RED cross-process test.

## Goals / Non-Goals

**Goals:**

- Extend the existing version-1 schema and literal dispatcher with one self-contained `event.structure` branch.
- Keep the external DTO smaller than `LedgerEntry` and the internal Event dictionary while preserving all Event semantics exposed by the operation.
- Make duplicated provenance/identity relationships either derived or explicitly validated before domain construction.
- Prove backward compatibility, deterministic serialization, caller isolation, and bounded authority.

**Non-Goals:**

- No Ledger operation/state, Feed wrapper, entity resolution, candidate grouping, raw-evidence extraction, registry/framework, automatic capability chain, or new Event/domain algorithm.
- No external `event.schema.json`, internal dataclass serialization, public CLI, remote/session transport, LLM/model/credential runtime, narrative, or proof/authority claim.

## Decisions

### 1. Add one root-schema request/result pair under contract version 1

Add `request_event_structure` and `success_event_structure` to `schemas/agent-invocation.schema.json` and its existing root `oneOf`. Preserve the common envelope and error variants byte-for-byte in meaning; existing Audit variants remain valid. The runtime's supported-name classification and literal dispatch gain exactly one branch.

Alternative considered: version 2. Rejected because adding a closed namespaced operation invalidates no version-1 Audit message. Alternative considered: a second Event schema/protocol. Rejected because the existing root schema already owns operation-specific variants and no separate consumer/reuse case exists.

### 2. Use key-fact DTOs, not caller-supplied fact IDs or Ledger records

The Event input contains `event_type`, `evidence_ids`, `entity_ids`, `key_facts`, and `subject_zh`. A key fact contains only `entry_type`, `origin_payload`, `evidence_id`, `subject`, `predicate`, `effective_time`, `effective_precision`, `value`, `unit`, and `knowledge_available_at`. `entry_type` is limited to `FACT|CLAIM`; origins are limited to the accepted atomic Event origins. Dates/times and precision combinations are validated at the serialized boundary before mapping.

No `fact_id` or separate `key_fact_ids` input exists: the adapter derives each ID through `build_ledger_entry`, and every supplied fact is Event-defining. This removes an otherwise contradictory reference list. Full Ledger bookkeeping is excluded because canonical Event construction does not require it.

Alternative considered: accept complete `LedgerEntry` records plus a fact-ID list. Rejected because it duplicates generated identity, externalizes unrelated internal state, and creates contradictory provenance sources.

### 3. Represent family and coexistence inputs as peers of the new Event

Optional `story_family_peer_event_ids` names existing canonical Event peers; the adapter derives the new Event ID and includes it exactly once in the member set before invoking existing family identity semantics. Optional `coexisting_event_ids` similarly derives each unordered pair from the new Event and one peer. Both arrays accept semantic permutations/duplicates because the existing canonical set/pair behavior removes ordering significance.

This avoids asking the caller to predict and resubmit the generated Event ID or to submit an independently authoritative family ID/pair projection.

Alternative considered: accept `story_family_id` and complete coexistence pairs. Rejected because those outputs are deterministically derivable and accepting them would require conflict reconciliation.

### 4. Keep display inputs at the existing template boundary

`subject_zh` is required because every existing template consumes it. `company` and `form` are accepted only for `event_type: filing`, with `form` required there; `company` retains the existing fallback to `subject_zh`. Macro, policy, news, flow, positioning, and default labels use existing fact fields and templates, so no summary/title/description input is added.

Alternative considered: accept a display label or summary. Rejected because it would bypass deterministic templates and create narrative/authority ambiguity.

### 5. Validate consistency before building invocation-local state

After schema validation and before constructing any fact, the Event adapter checks that every key-fact evidence ID occurs in the top-level evidence set, all optional peer IDs are well-formed canonical Event IDs, filing-only fields match the Event type, effective values match their declared precision, and no two key facts generate the same stable fact ID. A contradiction becomes `invalid_request`; the adapter never drops, overwrites, substitutes, or repairs input.

Then it builds one `Ledger`, adds each derived entry, computes the current Event ID with the existing canonical utility so peer sets can include it, and calls existing `build_event` with the derived fact IDs and optional family/coexistence inputs. State is local to the call and discarded with the process.

Alternative considered: rely on exceptions from `Ledger`/`build_event`. Rejected because predictable trust-boundary inconsistencies belong to `invalid_request`, while `execution_failure` remains reserved for unexpected post-validation failures.

### 6. Map only the bounded Event projection

Copy the canonical Event fields required by the delta spec, omit internal `schema_version`, and add `key_fact_references` by joining each generated fact ID to its preserved evidence ID in fact-ID order. Map each object field explicitly, then validate the complete success envelope against the shared root schema before stdout emission.

The mapper does not return entity/display inputs, because the caller already owns them, or full fact values/Ledger fields, because the Host Agent only needs stable identity-to-provenance association.

Alternative considered: recursively serialize the Event dictionary and Ledger entries. Rejected because internal layout changes would become accidental compatibility changes and could leak future fields.

### 7. Keep implementation local and repair the proven determinism defect at source

Use either a few local Event helpers in `agent_invocation.py` or one small `agent_event_structuring.py` mapper if direct mapping would obscure stdin/error handling. No shared dispatcher abstraction, registry, service class, DTO class hierarchy, or dependency injection layer is justified.

Before the adapter is implemented, add a cross-process test that varies `PYTHONHASHSEED` for mixed key-fact precisions. Repair `build_event` so `economic_effective_time.value` and `precision` both come from the same first canonical key fact. This is the smallest root-cause correction to an already accepted deterministic invariant; no other Event semantics or adjacent code are changed.

### 8. Prove isolation and truthful status mechanically

Contract tests exercise closed request/result variants and retain all Audit fixtures. Process tests cover success, validation precedence, anticipated Event rejections, forced unexpected failure, exact result mapping, and one-operation call counts. Architecture tests permit only the private invocation adapter to call Event construction and continue rejecting Feed, Audit, Market, Watchlist, Confidence, Scoring, Ranking, and legacy orchestration edges.

Only after these tests pass do current-facing specs/docs mark Evidence/Event Structuring `live-production`; the status remains descriptive text, not runtime configuration.

## Risks / Trade-offs

- [A key-fact DTO can drift from the internal constructor] → Keep the DTO deliberately smaller, map fields explicitly, and compare generated identities/results with direct domain construction fixtures.
- [Schema format checking alone may miss precision/value consistency] → Add explicit pre-construction semantic checks and classify them as `invalid_request`.
- [Peer inputs could omit the current Event] → Define them as peers and derive inclusion/pairs from the generated Event ID.
- [Mixed precision currently exposes hash-seed nondeterminism] → Add the RED cross-process check and change only the mismatched precision selection at the existing Event source.
- [A helper could become a framework] → Permit at most one mapping module with no registry, base class, configuration, transport, or future-operation seam.
- [Live status could overstate the family] → State that only `event.structure` has a caller; entity resolution, candidates, persistent Ledger behavior, and other families remain unwired.

## Migration Plan

1. Add RED schema, process, deterministic-permutation, cross-process, ownership, and caller-graph tests while retaining existing Audit fixtures.
2. Correct the proven mixed-precision projection defect minimally, extend the existing schema, and add one literal Event mapping/dispatch path until focused tests pass.
3. Reconcile the four living specs and current-facing architecture/Skill docs only after the real caller is verified; run focused tests, strict OpenSpec validation, and the canonical quality gate.
4. Roll back by removing the Event schema variants, mapping/dispatch branch, focused tests, and ECO-51 status/docs changes, plus reverting the isolated deterministic defect repair if rollback requires the exact pre-ECO-51 baseline. Feed and Audit require no data or protocol migration.
