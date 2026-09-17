# Policy Presentation Contract

## Domain Purpose

Present validated `policy` evidence as a factual account of the issuing source,
document title, announcement time, effective date, and explicitly supplied
scope. Preserve the distinction between announcement and effect. The list below
is a closed whitelist enforced by deterministic preparation; it does not
authorize facts outside the listed paths.

## Evidence Fields

The closed whitelist for a `policy` item is:

- `id`
- `provider_id`
- `source.id`
- `source.name`
- `source.tier`
- `source.kind`
- `source.url`
- `source.published_at`
- `source.updated_at`
- `source.knowledge_available_at`
- `source.original_publisher`
- `source.syndication_origin`
- `source_lineage[].id`
- `source_lineage[].provider_id`
- `source_lineage[].source_id`
- `source_lineage[].original_publisher`
- `source_lineage[].syndication_origin`
- `payload.type`
- `payload.title`
- `payload.announced_at`
- `payload.effective_at`
- `semantic_context.version` (when present)
- `semantic_context.entities[].role` (when present)
- `semantic_context.entities[].name` (when present)
- `semantic_context.entities[].type` (when present)
- `semantic_context.event.category` (when present)
- `semantic_context.event.occurred_at` (when present)
- `semantic_context.numeric_facts[].metric` (when present)
- `semantic_context.numeric_facts[].role` (when present)
- `semantic_context.numeric_facts[].value` (when present)
- `semantic_context.numeric_facts[].unit` (when present)
- `semantic_context.numeric_facts[].unknown_reason` (when present)
- `semantic_context.extension.type` (when present)
- `semantic_context.extension.policy_type` (when present)
- `semantic_context.extension.action` (when present)
- `semantic_context.extension.effective_at` (when present)
- `semantic_context.extension.affected_scope[]` (when present)

`semantic_context` is optional and must match `payload.type = policy` when it
is present. Legacy items may omit it. An absent or empty affected scope does
not authorize an inferred market or policy scope.

## Recommended Representation

Name the issuing source, state the validated title and announcement time, and
state the effective date or bounded affected scope only when explicitly
present. Describe a specific action or policy type from semantic context as a
source-supported document fact. A generic official-policy-announcement action
describes the document act, not a purpose or effect.

Null, explicitly unavailable, absent, or legacy-omitted evidence remains
missing. Do not reconstruct or infer an effective date, scope, purpose, effect,
or action from a title, announcement time, another item, historical Feed,
external knowledge, or `raw_metadata`.

## Forbidden Interpretation

Do not add importance, anomaly, ranking, causality, sentiment, direction,
market impact, signal, prediction, investment judgment, recommendation, or
trading instruction. Do not infer policy purpose, implementation result,
affected market, or consequence from an announcement. `raw_metadata` and every
unlisted field are outside the presentation evidence. Source-authored analysis
may be summarized only with clear attribution and without upgrading its
authority.
