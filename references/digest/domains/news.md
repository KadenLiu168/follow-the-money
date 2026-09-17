# News Presentation Contract

## Domain Purpose

Present validated `news` evidence as a factual account of the source document,
its bounded title or snippet, and its source-semantic occurrence time when
available. Preserve source identity and attribution. The list below is a
closed whitelist enforced by deterministic preparation; it does not authorize
facts outside the listed paths.

## Evidence Fields

The closed whitelist for a `news` item is:

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
- `payload.snippet`
- `payload.occurred_at`
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
- `semantic_context.extension.document.title` (when present)
- `semantic_context.extension.document.type` (when present)

`semantic_context` is optional and must match `payload.type = news` when it is
present. Legacy items may omit it. `semantic_context.numeric_facts` may be
empty, and an unavailable value remains unavailable.

## Recommended Representation

State the source name or publisher, the validated title or bounded snippet,
the source publication or occurrence time when present, and a traceable source
URL. Use semantic context only for the supported subject, event/document fact,
numeric observation, and source-semantic time actually present. Preserve
duplicates and source lineage as provenance rather than treating editorial
ordering as importance.

Null, explicitly unavailable, absent, or legacy-omitted evidence remains
missing. Do not reconstruct or infer it from a title, snippet, another item,
historical Feed, external knowledge, or `raw_metadata`.

## Forbidden Interpretation

Do not add importance, anomaly, ranking, causality, sentiment, direction,
market impact, signal, prediction, investment judgment, recommendation, or
trading instruction. Do not infer an actor, intent, consequence, event meaning,
or significance from open-ended wording. `raw_metadata` and every unlisted
field are outside the presentation evidence. Source-authored analytical wording
may be summarized only with clear attribution and without upgrading its
authority.
