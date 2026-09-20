# Policy Presentation Contract

## Domain Purpose

Present validated `policy` evidence as a factual account of the issuing source,
document title, announcement time, effective date, and explicitly supplied
scope. Preserve the distinction between announcement and effect. The list below
is a closed whitelist enforced by deterministic preparation; it does not
authorize facts outside the listed paths.

## Reader-Facing Unit

Preparation exposes one `policy_document` unit for each policy item whose
membership it proves. The unit carries the closed unit domain `policy`, its
`policy_document` unit type, the Provider identity, the item's closed source
provenance, an event-time semantic of kind `announced_at`, the closed supporting
evidence, and a trace of the supporting Feed item IDs. The unit identifier is
the deterministic function of the unit type and those Feed item IDs. A policy
item that is not proven current yields no unit.

## Current Membership

Membership is evaluated against the half-open Feed window
`[window.start, window.end)`. The only accepted authority is
`payload.announced_at`. An announcement time inside the interval yields exactly
one current unit; an explicitly earlier announcement time yields
`policy/no_current_update`; a missing, invalid, at-or-after-end, or otherwise
unusable announcement time yields `policy/current_membership_unproven`.
`payload.effective_at` is retained only as supporting evidence inside that one
unit, and policy type, action, and affected scope never become additional
updates.

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
