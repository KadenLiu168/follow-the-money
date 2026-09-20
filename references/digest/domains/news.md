# News Presentation Contract

## Domain Purpose

Present validated `news` evidence as a factual account of the source document,
its bounded title or snippet, and its source-semantic occurrence time when
available. Preserve source identity and attribution. The list below is a
closed whitelist enforced by deterministic preparation; it does not authorize
facts outside the listed paths.

## Reader-Facing Unit

Preparation exposes one `news_publication` unit for each news item whose
membership it proves. The unit carries the closed unit domain `news`, its
`news_publication` unit type, the Provider identity, the item's closed source
provenance, an event-time semantic of kind `published_at`, the closed
supporting evidence, and a trace of the supporting Feed item IDs. The unit
identifier is the deterministic function of the unit type and those Feed item
IDs; a later multi-item unit would require an accepted shared identity before
extending that rule. A news item that is not proven current yields no unit.

## Current Membership

Membership is evaluated against the half-open Feed window
`[window.start, window.end)`. The only accepted authority is
`source.published_at`. A publication time inside the interval yields exactly
one current unit; an explicitly earlier publication time yields
`news/no_current_update`; a missing, invalid, at-or-after-end, or otherwise
unusable publication time yields `news/current_membership_unproven`. News
`occurred_at`, `source.updated_at`, and `source.knowledge_available_at` are
never substituted for the publication authority, and no other timestamp is
tried.

## Supporting Evidence

The closed whitelist below is the item-level inventory. Preparation maps it
into the unit without opening it: the item identifier becomes the unit trace,
`provider_id` becomes the unit Provider identity, the item `source.*` and
`source_lineage[].*` paths become the unit source provenance, and the
`payload.*` and `semantic_context.*` paths become the unit supporting evidence,
with `payload.*` nested under its payload member and `semantic_context.*` under
its semantic-context member. Nothing outside this inventory is exposed, and no
Feed item becomes a Digest statement by itself.

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
- `payload.source_content.text` (when present)
- `payload.source_content.format` (when present)
- `payload.source_content.truncated` (when present)
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

## Bounded Official Source Content

When a current unit carries `payload.source_content`, the Host Agent may
summarize factual statements and source-authored analysis explicitly present in
`payload.source_content.text`, always attributed to the item's source and
traceable to that unit and its Feed item. The text is a bounded extract of one
official document, not the document: when
`payload.source_content.truncated` is true the summary must not describe the
bounded text as the complete official document or infer facts from omitted
content. Extraction provenance (`extraction_method`, `document_sha256`) is Feed
validation fact and is never exposed or printed. Source wording is never a
Feed, Skill, or Host-Agent conclusion, and source content MUST NOT be used to
reconstruct an absent structured semantic field or to claim that omitted source
content is known.
