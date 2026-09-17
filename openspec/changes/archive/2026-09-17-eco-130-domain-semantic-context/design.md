## Context

See `proposal.md` for motivation and the two delta specs for observable behavior.

The current logical Feed is schema major v4. A Feed item is a closed object containing `id`, `provider_id`, `source`, `payload`, and optional duplicate lineage; the complete item already participates in canonical bytes and semantic identity. News, macro, and policy payloads are also closed, but `raw_metadata` is untyped. Current production adapters emit Federal Reserve/PBOC policy, BLS/NBS/SSE/SZSE news, and NBS macro releases when its normalized entry contains a series. Federal Reserve does not currently emit news, and BLS does not currently emit macro releases.

The `follow_the_money.semantic` package created by ECO-125 owns bounded canonical decimal construction and subtraction-based internal numeric facts. Its accepted contract deliberately excludes a generic semantic model and public serialization. ECO-130 can reuse those numeric guards, but must add its own closed published context without expanding ECO-125's responsibility.

Snapshot selection occurs after adapters have normalized items. Existing event-list Providers can carry a previously validated slice byte-for-byte and record its source run in `carried_forward_from_run_id`; a scheduled or weekly carried slice is `valid_unchanged` while within its cadence window and becomes `stale` after that window expires. Therefore an additive v4 field cannot be retrofitted onto either carried state without violating the accepted snapshot contract.

## Goals / Non-Goals

**Goals:**

- Add one small item-level context shape whose common envelope and domain extension are fully closed.
- Keep domain extraction pure, deterministic, Provider-local, and downstream of existing fetch/parse/provenance work.
- Make the initial mappings truthful for the evidence actually retained by the current adapters, including conservative fallbacks.
- Validate both context shape and cross-field consistency, and make newly acquired context part of existing Feed identity automatically.
- Roll out additively within v4 while preserving legacy reads and byte-identical carry-forward.

**Non-Goals:**

- A generic knowledge graph, entity resolver, ontology service, fact registry, rule engine, or semantic plugin framework.
- Fetching linked documents, expanding snippets, using another Feed, or changing Provider acquisition to obtain richer context.
- Reclassifying BLS news as macro, Federal Reserve policy as news, or changing any manifest payload declaration or Provider contract version.
- Giving the ECO-125 numeric fact types ownership of text, identity, time, comparison, classification, or wire serialization.
- Generating Digest prose or choosing its grouping, ordering, wording, compression, or emphasis.

## Decisions

### 1. Add one sibling `semantic_context` with a closed domain extension

Add optional `semantic_context` to the existing `feed_item` JSON Schema so the current reader remains able to validate pre-ECO-130 v4 items. The serialized shape is:

```text
semantic_context
├── version: 1
├── entities[]: {role, name, type}
├── event: {category, occurred_at}
├── numeric_facts[]: {metric, role, value, unit, unknown_reason}
└── extension
    ├── type: news          + document {title, type}
    ├── type: macro_release + indicator {id, name}, period (object or null), revision
    └── type: policy        + policy_type, action, effective_at, affected_scope[]
```

The schema uses one `$defs/semantic_context` with a closed `extension` union keyed by `type`. It does not add `NewsSemanticEvidence`, `MacroSemanticEvidence`, or `PolicySemanticEvidence` fields beside the payload. Arrays are bounded and use explicit total orders. Context text uses the existing normalization and bounded-field conventions. `numeric_facts.role` distinguishes `actual`, `consensus`, `previous`, `revision_previous`, and `revision_revised`; an unavailable fact keeps `value = null`, its unit, and the existing closed unknown reason.

The common envelope makes Host-Agent traversal stable. The typed extension avoids the opposite failure mode: an open generic `{name, value}` fact bag that could silently admit analysis or lose domain invariants.

Alternative considered: add semantic fields inside each payload. Rejected because it repeats a cross-domain envelope, makes future consumers branch earlier, and encourages parallel schemas.

Alternative considered: put every fact in one generic array. Rejected because indicator periods, documents, revisions, and policy effective dates have different invariants that require closed validation.

### 2. Use one minimal model and three pure Provider-local mappers

Add `semantic/context.py` as the common construction boundary. It owns the small immutable `SemanticContext` value, common field validation, ordering/deduplication, and conversion to ordinary dictionaries for canonical serialization. It may import ECO-125 numeric construction, but it does not import config, feed, or Provider adapters.

Add `semantic/news.py`, `semantic/macro.py`, and `semantic/policy.py` as pure mapping modules. Each receives only the validated `provider_id`, normalized payload/source, and the already parsed source record needed for explicit facts. It performs no I/O and returns a `SemanticContext`. Adapters remain responsible for fetch, decoding, source-record parsing, URL/provenance, and payload assembly; immediately after assembling a payload/source pair they invoke the matching mapper and attach `context.to_dict()`.

This keeps the current small Provider protocol and orchestration unchanged. It also lets mapper fixtures run without Feed construction or network state.

Alternative considered: a new enrichment pipeline between Provider orchestration and snapshot selection. Rejected because it creates a second dispatch/orchestration layer and would have to rediscover Provider-local evidence that the adapter already has.

Alternative considered: implement mappings inline in every adapter. Rejected because common validation, ordering, and forbidden-boundary checks would be duplicated, while the three domain modules are already justified by materially different fields.

### 3. Start with conservative closed mappings over current evidence

Provider identity supplies the official organization only where it is source-supported. Exact URL/title/identifier rules may select a more specific closed category; otherwise the mapper uses a documented factual document-act fallback, never a guessed real-world effect.

Initial mapping behavior is bounded as follows:

| Current output | Required base mapping | Optional exact refinement |
| --- | --- | --- |
| BLS `news` | BLS subject; `official_statistical_release`; `news_release` document | Known release identifiers such as CPI or Employment Situation select a closed event category and explicit referenced indicator entity |
| NBS `news` | NBS subject; `official_statistical_release`; `statistical_release` document | Only exact known title/series tokens add referenced entities |
| SSE/SZSE `news` | issuing exchange subject; `official_exchange_notice`; `exchange_notice` document | Only an exact retained identifier/title rule may refine category or references |
| NBS `macro_release` | closed series-id-to-display-name map; payload period or explicit null; ordered actual/consensus/previous facts | Explicit same-period previous/revised source fields produce `revision`; previous-period observations never do |
| Federal Reserve `policy` | Federal Reserve issuer; generic `official_policy_announcement` fallback | Exact FOMC/monetary release identity selects `monetary_policy` and `monetary_policy_statement` or another closed factual action |
| PBOC `policy` | PBOC issuer; generic `official_policy_announcement` fallback | Exact retained wording may select `reserve_requirement_announcement` or `open_market_operations_announcement` |

For news, referenced entities can be empty. For policy, `effective_at` is copied only from explicit normalized evidence and `affected_scope` can be empty. For macro, a series outside the closed mapping fails context construction, while a null `payload.observation_period` is retained as `extension.period = null` rather than becoming an invented label or a construction failure. Current NBS `previous` remains a previous observation, not a revision. The revision structure is populated only when one source record explicitly provides both sides for the same period.

The specific vocabularies and field bounds live once in the common context module/schema; mapping tables select values from that vocabulary rather than define another runtime authority in manifests. Tests pin each mapping and fallback.

Alternative considered: broad regex/NLP extraction from arbitrary titles and snippets. Rejected because it is difficult to prove, language-sensitive, and can turn presentation text into unverified entity or policy claims.

Alternative considered: fetch the linked release body for better facts. Rejected because it changes Provider request counts, rate/deadline behavior, fixtures, and verified contracts beyond ECO-130.

### 4. Validate construction, wire shape, and cross-field consistency separately

Construction validates the immutable model before serialization. JSON Schema then closes every published object and vocabulary. `feed/validate.py` adds semantic checks that:

- context extension type equals `payload.type` and is absent from filing/positioning;
- event times equal the corresponding normalized payload time (`occurred_at`, `released_at`, or `announced_at`), including allowed null only for news;
- news document title equals the retained payload title;
- macro indicator ID, nullable period, and actual/consensus/previous numeric facts agree with the retained payload where those payload fields exist;
- policy effective time agrees with `payload.effective_at` and issuer agrees with the Provider mapping;
- entity/fact/scope total order, uniqueness, numeric bounds, and forbidden analytical keys hold recursively.

Revision and exact referenced-entity facts cannot always be duplicated in the legacy payload; their construction tests therefore pin them directly to source fixtures, while wire validation still enforces their closed shape and numeric rules. `raw_metadata` remains neither an input expected of the Host Agent nor a place to duplicate semantic context.

Alternative considered: rely on JSON Schema alone. Rejected because schema cannot prove payload/context equality, deterministic order, or Provider-specific issuer/series consistency.

### 5. Keep v4 and distinguish consumer compatibility from current production admission

`semantic_context` is optional at the base v4 schema/consumer boundary. Extend `validate_feed` with an explicit current-production admission mode. Normal bundle reads keep compatibility mode: omission is accepted for an otherwise valid v4 item, but any present context is fully validated. Feed construction and `build_bundle` use production mode.

Production mode requires context for every affected-domain Provider slice except when all omitted items belong to a fully validated prior slice proven by a non-null `carried_forward_from_run_id`. The existing freshness authority independently determines whether that carried slice is `valid_unchanged` or `stale`; neither state causes in-place enrichment. Once complete current acquisition replaces the slice, every affected item must have context. This check uses existing outcome/freshness state; no producer version, manifest hash, date cutoff, hidden flag in published data, or Provider contract bump becomes a new authority.

Alternative considered: require context unconditionally and rewrite the active legacy slice. Rejected because it breaks current bundle readability or byte-identical snapshot provenance and could prevent publication until all event Providers emit a new item.

Alternative considered: bump the whole Feed to v5. Rejected because the additive field and bounded legacy omission do not justify migrating manifest/artifact majors, active publication, remote consumption, and all current fixtures.

Alternative considered: leave production and consumer validation identical. Rejected because it cannot both read a legacy omission and fail closed when a newly acquired current item omits required context.

### 6. Reuse existing identity and keep item IDs stable

No identity algorithm needs a semantic-context special case. The existing logical semantic projection includes normalized full items, and artifacts serialize those same items. Attaching context before deduplication/snapshot selection therefore makes it participate in item bytes, artifact hashes, `content_digest`, and `run_id` automatically.

Provider adapters continue to derive `item.id` from their current stable source identity. A corrected semantic fact changes content/digest/run identity but not the event's source identity. Tests pin same-input canonical bytes, changed-context identity, unchanged global item ordering, and legacy carry behavior.

Alternative considered: include a context digest in the item ID. Rejected because that would turn a content correction into a new source event and weaken current deduplication/snapshot semantics.

## Risks / Trade-offs

- [Current RSS/index evidence is shallow, so some contexts remain generic and revisions/effective dates are often absent] → Use factual closed fallbacks/nulls and do not fetch documents or infer facts; richer extraction requires a separately reviewed Provider-contract change.
- [Exact title/URL rules can stop matching when publishers change wording] → Keep a safe Provider-specific document-act fallback where the issuer/subject remains proven, pin representative fixtures, and fail closed where a required macro series has no safe fallback.
- [Provider-as-subject can be false for a notice about another actor] → Use it only for source-supported issuing/acting roles; do not label title-mentioned parties without an exact retained rule, and allow empty references.
- [Optional v4 schema could hide a Producer regression] → Use explicit production admission in both Feed construction and bundle building, plus tests that only legacy slices with non-null `carried_forward_from_run_id` can omit context, whether their independently evaluated status is `valid_unchanged` or `stale`.
- [A new context fact changes canonical identity for unchanged source payload] → Treat this as the intended one-time semantic contract activation; keep source item IDs stable and do not rewrite carried legacy bytes.
- [Common context can grow into an open semantic framework] → Keep vocabularies and extension union closed, require an OpenSpec contract for new fields/domains, and leave filing/positioning semantics in their existing typed payloads.

## Migration Plan

1. Add focused mapper/model tests first, including deterministic repetition, ambient decimal context, safe fallbacks, missing optional facts, forbidden keys, and explicit revision versus previous-period behavior.
2. Add the optional closed v4 schema field and consumer semantic validation; verify all existing v4 fixtures still read unchanged and malformed present context fails.
3. Attach context in each current adapter path and enable production admission. Verify newly acquired/replacement items require context while a proven contextless legacy slice remains byte-identical through both `valid_unchanged` and carried `stale` states.
4. Confirm full Feed/artifact canonical identity, bundle round-trip, snapshot/carry, remote-consumer, and documentation behavior, then run the canonical quality and OpenSpec gates.

Rollback can remove context attachment and production admission while retaining reader support for already published valid context. Because published bundles are immutable and the field participates in identity, rollback must continue to read context-bearing v4 bundles; it must not rewrite or silently strip an active bundle.
