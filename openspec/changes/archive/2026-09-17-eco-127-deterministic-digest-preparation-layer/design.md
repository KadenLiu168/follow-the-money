## Context

See `proposal.md` for motivation. Today `scripts/skill/prepare-feed` executes
`follow_the_money.feed.remote`, which retrieves a manifest-led bundle, reconstructs
and fully validates one logical Feed, writes canonical Feed JSON to stdout, and
writes degraded warnings to stderr. `SKILL.md` then requires the Host Agent to
navigate that complete object and apply the static ECO-126 presentation hierarchy.

The accepted Feed is already the sole serialized evidence contract. Its five-domain
item order, Provider outcomes, pipeline status, warnings, coverage gap, freshness,
provenance, `run_id`, and `content_digest` are validated before remote consumption
returns. ECO-127 must reuse that boundary without changing publication or creating a
parallel evidence model.

ECO-126 made its Markdown field lists normative and deliberately prohibited runtime
selection. ECO-127 intentionally revises that decision: closed field eligibility is
now enforced before Agent consumption, while recommended representation, semantic
support, compression choices, and prose remain Host-Agent responsibilities.

## Goals / Non-Goals

**Goals:**

- Give the Host Agent one typed, versioned and canonically serialized context whose
  evidence is completely derived from one validated current Feed.
- Make domain dispatch and ECO-126 closed-field eligibility deterministic and
  testable without parsing presentation Markdown at runtime.
- Preserve exact Feed identity, source traceability, missing-evidence semantics,
  status, warnings, Provider coverage, availability, and freshness.
- Keep the new layer non-persisted and subordinate to Feed evidence authority.

**Non-Goals:**

- Defining another JSON Schema, publication artifact, checkpoint, cache, or durable
  compatibility surface independent of the Skill invocation.
- Making prose, editorial grouping, consolidation, omission, compression accounting,
  semantic entailment, or final Digest output deterministic.
- Adding data enrichment, title parsing, `raw_metadata` interpretation, external
  lookups, historical comparisons, a model runtime, prompts, or orchestration.
- Refactoring Feed retrieval, validation, publication, Providers, or configuration.

## Decisions

### 1. Add one bounded preparation entry after existing Feed consumption

The Skill launcher will invoke a Digest preparation entry. That entry will call the
existing `consume_published_feed()` exactly once and will project only the returned
validated object. Retrieval, manifest/inventory checks, artifact checks, Feed schema
and semantic validation, provenance checks, and identity validation remain owned by
the existing Feed modules.

```text
canonical published bundle
        |
        v
consume_published_feed()
        |
        v
validated logical Feed
        |
        v
prepare DigestContext
        |
        v
canonical JSON stdout --> Host Agent --> Digest
```

The projection helper will remain private to the preparation module; the supported
entry always obtains its input from `consume_published_feed()`. Tests may exercise
the pure helper with already-valid deterministic fixtures. This avoids introducing
a public raw-dictionary path that could bypass the canonical consumer.

Alternative considered: make preparation reimplement or partially repeat Feed
validation. Rejected because it creates drift at the trust boundary. Alternative
considered: add a nominal `ValidatedFeed` wrapper throughout the bundle API. Rejected
as disproportionate churn for a single bounded caller.

### 2. Use immutable code-level types and one explicit context version

The preparation module will define frozen, slotted types for the top-level context,
status/coverage view, Provider view, domain view, and projected evidence item. Nested
evidence containers will be defensively frozen or constructed as immutable values so
callers cannot mutate the prepared context before serialization.

Version 1 will serialize an explicit `context_version` together with the Feed binding:

```text
context_version
feed.schema_version
feed.run_id
feed.content_digest
feed.window
feed.evidence_cutoff_at
status
providers[]
domains[]
```

The five domain entries always appear in the accepted order and contain `total` plus
their projected items in the validated Feed's relative order. Provider entries retain
validated Provider order. No preparation timestamp, local build value, environment
value, or nondeterministic mapping/set traversal enters the context.

Serialization will first produce the single documented mapping projection and then
use `canonical_bytes()`. The same Feed and context version therefore produce identical
bytes. A future shape change requires a deliberate version change, spec update, and
compatibility decision; v1 will not silently accept or emit another shape.

Alternative considered: return the logical Feed with helper methods. Rejected because
the Agent would still perform evidence selection. Alternative considered: add a JSON
Schema. Rejected because it would look like a second evidence artifact contract and
would duplicate guarantees already established by validated Feed construction plus
the code-level type.

### 3. Project exact Feed paths rather than invent Digest evidence fields

Each domain projector will explicitly construct the common identity/provenance fields
and its ECO-126-permitted payload and optional `semantic_context` shape. Output keeps
the existing Feed path names and nesting wherever possible; it does not rename facts,
derive friendly aliases, or translate them into presentation claims. Filing subtype
branches remain inside the one filing projector, matching the one-domain-owner rule.

The implementation will not parse Markdown, implement a generic dotted-path language,
or load a second YAML/JSON rule registry. Explicit projection code is the enforceable
runtime owner; the ECO-126 references remain the human-reviewable normative inventory.
Focused contract tests will compare the implementation's declared eligible path
inventory with those references so either side cannot drift silently.

Missing optional keys remain absent; explicit null and unavailable typed objects remain
unchanged. Copying only a value while dropping its unit, status, reason, derivation, or
source reference is prohibited when the applicable domain contract treats those fields
as one evidence object.

Alternative considered: recursively copy every schema-valid item field except
`raw_metadata`. Rejected because future Feed additions would silently become Agent
evidence. Alternative considered: parse ECO-126 Markdown at runtime. Rejected because
documentation syntax is not a safe production parser or runtime authority.

### 4. Prepare status and coverage without making presentation choices

The status view will retain Feed window/cutoff binding, pipeline status, warnings, and
the structured coverage gap. Provider views will use an explicit allowlist sufficient
for completion, availability, affected coverage groups, accepted/rejected counts, and
freshness/continuity limitations. Domain totals are exact counts of projected items;
all five domains remain present at zero.

Preparation does not decide which item is individually summarized, consolidated, or
omitted. Those counts depend on Host-Agent output choices. The Host Agent receives the
deterministic total and must reconcile its three presentation categories under the
existing compression contract.

Alternative considered: pre-group or preselect items for compression. Rejected because
topic grouping and omission are editorial decisions and would invite hidden ranking or
importance semantics.

### 5. Keep Feed identity as the only evidence authority

Every context carries the exact `schema_version`, `run_id`, `content_digest`, window,
and cutoff of its source Feed. Every projected evidence item carries its original item
ID, Provider ID, eligible source provenance, and eligible lineage. The context makes no
claim that is not a copy or deterministic structural fact such as a domain count.

The repository will write context bytes only to stdout. It will not publish, cache,
checkpoint, reload, compare, or use them for Feed identity. External capture of command
stdout does not make the context a repository-managed persistent artifact.

Alternative considered: include the full Feed inside the context. Rejected because it
would preserve the very unfiltered surface ECO-127 is intended to remove and would
duplicate a large evidence object without adding authority.

### 6. Preserve exact failure ownership and the no-model boundary

Retrieval and Feed-validation errors remain the existing typed remote-consumption
errors and keep the `prepare-feed:` stderr surface. Projection invariant failures will
use one preparation-specific typed error and produce no stdout. Valid degraded warnings
remain present in the context and may also retain the existing stderr warning behavior;
stderr is diagnostic, while the context is the Agent's complete structured input.

The module performs no prose operation and imports no model, prompt, rendering,
orchestration, scoring, ranking, market, or historical-state capability. Existing
negative runtime/import tests will be extended to cover the new entry.

## Risks / Trade-offs

- [Risk] The code projector and ECO-126 Markdown inventory drift. -> Maintain one
  implementation-declared eligible-path inventory and focused parity tests; require
  both to change deliberately when eligibility changes.
- [Risk] A code-level Agent interface without JSON Schema may be mistaken for an
  uncontracted object. -> Give it explicit immutable types, `context_version`, exact
  deterministic serialization tests, and OpenSpec requirements while documenting that
  it is not an independent evidence schema.
- [Risk] Projection can accidentally strip evidence qualifiers. -> Test null, absent,
  unavailable, units, reasons, derivations, source references, and each filing subtype
  with representative valid fixtures.
- [Risk] Context versioning becomes a general compatibility framework. -> Ship only
  version 1 and fail closed; add no registry, negotiation, migration, or multi-version
  parser until a concrete accepted change requires one.
- [Risk] Provider outcome projection understates degradation. -> Characterize every
  current outcome state and freshness form, then test healthy, blocked-degraded,
  carried, empty, and coverage-gap cases.
- [Risk] Changing stdout breaks current Skill instructions or tests. -> Treat the
  change as explicit invocation migration and update only direct consumers and truthful
  current-facing documentation; retain `consume_published_feed()` for Feed-owned use.

## Migration Plan

1. Characterize the current `prepare-feed` success, degraded, and failure surfaces and
   add failing context-contract tests without changing Feed behavior.
2. Add immutable context types, fixed v1 structure, domain/status/Provider projectors,
   Feed binding, and canonical serialization behind a new preparation entry.
3. Change the Skill launcher from raw Feed emission to context emission while keeping
   canonical remote consumption and failure propagation unchanged.
4. Update ECO-126 references, `SKILL.md`, architecture and invocation documentation to
   distinguish deterministic evidence preparation from Host-Agent presentation.
5. Run focused tests, the canonical quality gate, and strict OpenSpec validation.

Rollback restores the launcher to raw Feed emission and removes the new preparation
module and its direct documentation/tests. No Feed, schema, published artifact,
checkpoint, configuration, or persistent state migration is required.
