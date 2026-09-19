## Context

See `proposal.md` for motivation. The current implementation creates a frozen v1 context containing full Provider outcomes and five `DigestDomain` collections, projects every Feed item, and asserts that projected totals equal Feed item count. Static presentation guidance and regression tests then require visible individual/consolidated/omitted reconciliation.

The canonical consumer already returns one fully validated Feed with deterministic item order, Feed identity, Provider freshness, availability, coverage, and closed domain payloads. SEC validation distinguishes complete watched-company Form 13F state from current-window Form 4 and beneficial-ownership accessions. CFTC v2 supplies complete market rows and a conservative row publication boundary, but the Agent-facing evidence has no accepted shared report identity; constructing a report from same-Provider, same-date rows would violate the requested no-heuristic grouping boundary.

## Goals / Non-Goals

**Goals:**

- Make v2 the single normal Agent-facing context and retain exact Feed binding and canonical determinism.
- Construct current reader units only when a closed domain authority proves membership in `[window.start, window.end)`.
- Keep complete non-current evidence out of every Agent-facing content collection while retaining compact conditions needed for accurate reader disclosure.
- Preserve closed field eligibility, claim-to-unit-to-Feed traceability, source authority, and fail-closed consumption.
- Make the large-reference-state/few-current-update case a first-class regression.

**Non-Goals:**

- Changing Feed schemas, Provider contracts, acquisition, snapshot selection, publication, remote validation, Feed identity, or persistence.
- Adding content dereferencing, semantic topic/event inference, report packaging heuristics, scoring, ranking, top-N selection, personalization, analysis, rendering, prompting, model invocation, or orchestration.
- Keeping parallel v1 and v2 normal Host-Agent handoffs or migrating persisted Digest artifacts.

## Decisions

### 1. Replace rather than wrap the v1 context

`DigestContext` remains a frozen, slotted, non-persisted code-level type, but normal preparation emits only version `2` with this logical shape:

```json
{
  "context_version": 2,
  "feed": {
    "schema_version": 4,
    "run_id": "...",
    "content_digest": "...",
    "window": {"start": "...", "end": "..."},
    "evidence_cutoff_at": "..."
  },
  "content": {"updates": []},
  "status": {"domains": [], "limitations": []}
}
```

There is no `domains[].items[]`, `providers[]`, `reference_state`, `unresolved_items`, or separate v1 payload. Reusing the existing typed/canonical seam is smaller and preserves caller topology; wrapping v1 would continue exposing the exhaustive surface and invite Host-Agent reclassification.

### 2. Use accession/item-level units in the first version

The closed unit types are `news_publication`, `macro_release`, `policy_document`, `positioning_report`, and `sec_filing`. In this Change, news, macro, policy, and SEC units each trace to exactly one top-level Feed item. Form 4 entries, Form 13F holdings, and beneficial-ownership snapshots remain nested supporting evidence.

`unit_id` is a deterministic structural identifier formed from the unit type and ordered supporting Feed item IDs. For the initial one-item units, an inspectable form such as `<unit-type>:<feed-item-id>` avoids an unnecessary second hash while remaining distinct from Feed item identity. A future multi-item unit must define an accepted shared identity before extending this rule.

Alternative rejected: treating each Feed item, CFTC row, holding, or transaction as a reader update. That preserves v1 cardinality and fails the product goal.

### 3. Membership is a closed per-domain function

All time comparisons use the half-open interval `[window.start, window.end)`. Named authorities are:

| Domain/unit | Membership authority | Event-time kind |
|---|---|---|
| news publication | `source.published_at` | `published_at` |
| macro release | `payload.released_at` | `released_at` |
| policy document | `payload.announced_at` | `announced_at` |
| SEC filing | `payload.accepted_at` | `accepted_at` |

An authority inside the interval emits a unit; an explicitly earlier authority yields no current update; a missing, invalid, at-or-after-end, legacy-insufficient, or otherwise unusable authority yields `current_membership_unproven`. No alternative timestamp is tried. This deliberately distinguishes “proved old” from “not proved current.”

Form 13F is evaluated by acceptance time even though Feed validity intentionally retains one latest watched-company state before cutoff. Current Form 4 and beneficial-ownership validators already guarantee window membership, but preparation still applies the same explicit rule rather than relying on subtype assumptions. `previous_snapshot` is never independently traversed into units.

Alternative rejected: using `knowledge_available_at` for every domain. It is a Feed selection/order field and would erase domain-specific publication semantics.

### 4. CFTC stays status-only until the Feed has explicit report identity

Provider freshness is evaluated for the whole selected slice. Non-null carry provenance yields `carried_reference_state`; stale freshness yields `stale_reference_state`; otherwise the current rows yield `current_membership_unproven`. A common row `as_of` and the adapter-derived row publication boundary are not combined into a new report identity. The compact descriptor may retain the common source-supported `data_as_of` only when deterministically equal across the selected slice.

Alternative rejected: group rows by CFTC Provider plus `as_of` or `source.published_at`. Although deterministic for current data, it is exactly the same-provider/same-date grouping heuristic excluded by scope and creates an identity absent from Agent-facing Feed evidence.

### 5. Status is scoped and aggregate, never an evidence side channel

Scopes are closed and ordered: domain-wide scopes for news, macro release, and policy; `cftc` for positioning; and `form13f`, `form4`, and `beneficial_ownership` for filing. For ordinary scopes, aggregation uses this precedence:

1. any eligible unit -> `current_updates_available`;
2. otherwise any unproven candidate -> `current_membership_unproven`;
3. otherwise any explicitly old candidate -> `no_current_update`;
4. otherwise -> `domain_empty`.

CFTC carry/stale rules override ordinary positioning aggregation. Status contains no reference items or counts. This provides enough distinction for zero-update prose without rebuilding a domain audit table.

`provider_unavailable` is normally represented as a limitation rather than duplicated as domain status because BLS, for example, currently maps to `news` while its configured coverage group is broader. Preparation must not reclassify BLS as `macro_release` merely to phrase a limitation.

### 6. Limitations are closed projections, not copied diagnostics

The initial limitation codes are `provider_unavailable` and `coverage_gap`. Provider unavailability retains only `provider_id` and sorted `affected_coverage_groups`; coverage gaps retain their structured Feed bounds. Raw warnings, availability reasons, HTTP status, attempted/fetched/accepted/rejected counts, and full outcome/freshness rows stay in the Feed.

This is sufficient for currently consumable degraded Feeds, whose accepted degraded path is a blocked-exempt Provider, while avoiding a second generic diagnostics surface. If a future consumable Feed introduces another degraded condition, its descriptor requires a deliberate contract update.

### 7. Preserve canonical source order

Updates retain validated Feed item order rather than being resorted by event time or Provider. Status uses fixed domain and scope order. Limitations use fixed code order followed by Provider ID or exact gap bounds. Construction uses no unordered-set iteration in serialized output.

This keeps deterministic preparation structural. Readability reordering remains a Host-Agent operation and cannot be mistaken for importance.

### 8. Evolve the existing whitelist instead of adding a schema

The existing domain projection helpers and documented eligible-path inventory remain the source for closed supporting evidence, but their output is reorganized into units with separate `source`, `event_time`, `evidence`, and `trace` fields. Domain references gain `Reader-Facing Unit`, `Current Membership`, and `Supporting Evidence` sections. `raw_metadata` and future fields remain excluded.

No JSON Schema is added because the context remains a construction-guaranteed, non-persisted consumption interface. Dataclass invariants and focused tests cover closed enums, types, freezing, and serialization.

### 9. Change the presentation contract from item accounting to claim support

The Host Agent receives only prepared current units as substantive input. It may group current units only for presentation using source or explicit document/event type, summarize, consolidate supported repetition, choose headings and readability order, and format. It no longer classifies currentness, interprets reference state, or accounts for every Feed item.

Every presented factual claim must remain supported by one or more units and traceable to their Feed item IDs and source provenance. Internal IDs need not be printed to the reader. The absence of a Feed item from the Digest says nothing about importance, relevance, validity, or significance.

## Risks / Trade-offs

- [A valid source event has no accepted membership timestamp] -> emit `current_membership_unproven`; do not silently use a weaker timestamp.
- [Current CFTC publication is reader-relevant but lacks shared report identity] -> disclose compact unproven-current status and defer report units until the Feed contract explicitly supplies identity.
- [Status becomes another audit matrix] -> keep scopes closed, omit counts and items, and make Host-Agent disclosure conditional rather than mandatory for every descriptor.
- [Removing raw warnings hides material degradation] -> derive closed Provider-unavailable and coverage-gap limitations from validated structured fields and fail planning/tests if a consumable degraded state lacks a supported descriptor.
- [Large current SEC filings still produce large units] -> retain their required supporting evidence because the filing itself is current; do not introduce ranking, truncation, or entry-level updates.
- [Legacy valid v4 items lack newer optional fields] -> classify missing membership authority as unproven and preserve only evidence actually present; never reconstruct it.

## Migration Plan

1. Add v2 typed structures and domain classification beside projection helpers only as an implementation staging step.
2. Replace normal `prepare_digest_context()` and CLI output with v2; do not expose a v1/v2 switch or parallel Host-Agent inputs.
3. Update focused regressions for exact v2 shape, membership, units, compact status, limitations, traceability, and byte determinism, including a production-shaped large-reference fixture.
4. Rewrite static presentation/domain references and normal-skill documentation, then remove tests that require exhaustive reconciliation and replace them with non-exhaustiveness and claim-traceability assertions.
5. Run focused suites, the canonical quality gate, and OpenSpec strict validation. Rollback is a code/docs revert because no persisted artifact or Feed contract is migrated.
