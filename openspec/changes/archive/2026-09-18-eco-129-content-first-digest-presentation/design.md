## Context

See `proposal.md` for motivation. The current `main` at ECO-128 completion already
uses the following ownership chain:

```text
validated Feed -> DigestContext -> Host Agent -> evidence-preserving Digest
```

`references/digest/presentation-contract.md` is the Host-Agent presentation
authority and already requires current-window updates together with status, cutoff,
coverage, provenance, freshness, warnings, degradation, and limitations. The shared
compression contract separately requires exact per-domain reconciliation,
consolidation traceability, and omission disclosure. Neither contract currently
states which information is the primary reading surface.

ECO-128 removed the old numbered Digest-output list from `SKILL.md`. The current
Skill therefore does not itself encode audit-first order and must remain a thin
orchestration boundary rather than becoming a second presentation authority.

## Goals / Non-Goals

**Goals:**

- Add one global semantic hierarchy that covers all five existing presentation
  domains without changing their domain-specific evidence rules.
- Make the hierarchy precise enough to distinguish healthy, degraded-but-usable,
  and valid-zero-update presentation.
- Preserve local provenance where semantic support requires proximity while moving
  only global audit metadata to secondary presentation priority.
- Lock the hierarchy with semantic static regressions that tolerate different valid
  formatting choices.

**Non-Goals:**

- Defining headings, heading levels, fixed section order, layout, or visual style.
- Changing domain contracts, the compression algorithm or accounting equation,
  `DigestContext`, preparation, failure handling, Feed schemas, Providers,
  collection, publication, validation, identity, or retrieval.
- Adding a renderer, template engine, prompt pipeline, model runtime, Agent
  orchestration, ranking, importance, significance, analysis, or filtering.

## Decisions

### 1. Put the hierarchy only in the global presentation contract

Add a dedicated content-first section to
`references/digest/presentation-contract.md`. It will define four concepts:

- the primary content surface;
- the secondary audit surface;
- the narrowly permitted material-degradation caveat; and
- valid zero-update behavior.

The existing global responsibility, missing-evidence, safety, and runtime-boundary
sections remain authoritative and will be adjusted only where needed to avoid
contradicting the new hierarchy.

Alternative considered: copy the hierarchy into `SKILL.md`. That would reverse the
ECO-128 ownership cleanup, create a second presentation authority, and allow the two
documents to drift.

### 2. Define semantic priority without defining document structure

“Primary surface” means the Digest first resolves what current Feed content is
available to read; “secondary audit surface” means all audit obligations remain
visible but do not dominate the normal entry into a healthy Digest. The contract
will explicitly say that these terms do not mandate a heading, fixed block, or
universal section order.

This permits local provenance, a material caveat, or another short supporting fact
to appear before or beside content when required by evidence integrity. It does not
permit a healthy Digest to lead with a full status, coverage, or reconciliation
report.

Alternative considered: prescribe “updates first, audit second” as a fixed ordered
template. That is mechanically testable but conflicts with the requested semantic
flexibility and mishandles degraded and zero-update states.

### 3. Separate a concise degradation caveat from complete audit context

A degraded-but-usable Feed may need an early caveat when a limitation materially
changes how the content can be understood. The caveat is limited to the relevant
data limitation. It cannot stand in for the complete degradation, warning,
freshness, availability, coverage, and limitation record, and it cannot imply that
the Feed is healthy.

Alternative considered: force all degradation details ahead of content. That
recreates audit-first presentation. Deferring every limitation until later is also
rejected because a reader could consume affected content without its material
qualification.

### 4. Treat zero presentable updates as a distinct truthful primary message

When the valid current Feed has no presentable updates, there is no content surface
to promote. The primary message is the absence of presentable current-window
updates. Status, cutoff, coverage, source availability, and limitations then make
the difference between a genuinely empty window and impaired collection auditable.
No historical, external, inferred, or fabricated item fills the gap.

Alternative considered: start with the ordinary audit report because there are no
updates. That obscures the user-facing answer and weakens the explicit no-content
guarantee.

### 5. Change compression priority, not compression semantics

`references/digest/compression.md` remains unchanged. Its equation,
consolidation-traceability rules, empty-domain accounting, and omission disclosure
all remain mandatory. The global presentation contract will clarify only that this
accounting is secondary audit information rather than the primary healthy-Feed
reading surface. Supporting provenance for a consolidated statement remains local
to that statement as needed.

Alternative considered: simplify or defer accounting to make the body more
content-forward. That would reduce auditability and violate the existing accepted
contract.

### 6. Test semantic ownership and invariants, not formatting

Focused regressions in `tests/test_digest_presentation_contract.py` will assert that
the global contract:

- identifies current-window updates as the primary substantive surface;
- retains status, cutoff, coverage, freshness, warnings, degradation, availability,
  reconciliation, traceability, omission disclosure, and limitations;
- limits an early degraded caveat and preserves complete audit context;
- defines truthful zero-update behavior with no fabricated content; and
- keeps content-first distinct from ranking, importance, analysis, and relevance
  filtering.

The same test file will keep `SKILL.md` free of presentation ordering. Tests will
not assert a particular Markdown heading used by a generated Digest, section count,
fixed output template, or exact final-Digest order.

## Risks / Trade-offs

- [Risk] “Primary” and “secondary” could be interpreted as hidden ranking of Feed
  items. -> Mitigation: define the distinction only between content and audit
  surfaces and explicitly prohibit item importance, ranking, significance, and
  relevance filtering.
- [Risk] An early degradation caveat could grow into a full audit preamble. ->
  Mitigation: require it to be concise, material to understanding, and separate from
  the complete secondary audit context.
- [Risk] Moving audit information later could separate facts from necessary source
  support. -> Mitigation: distinguish statement-local provenance and attribution
  from global Provider, coverage, and reconciliation metadata.
- [Risk] Static prose tests can become wording-sensitive. -> Mitigation: assert a
  small set of semantic ownership and invariant phrases without testing a final
  Markdown template.
- [Trade-off] Different compliant Host Agents may choose different layouts. This is
  intentional because the contract fixes semantic priority and evidence guarantees,
  not visual rendering.

## Migration Plan

1. Add focused failing assertions for the missing content-first hierarchy, degraded
   caveat, zero-update behavior, preserved audit obligations, and thin-Skill
   ownership.
2. Update only the global presentation contract until the focused regressions pass;
   do not edit runtime/data files or the shared compression/domain contracts.
3. Inspect the diff allowlist and confirm `SKILL.md` remains unchanged unless a
   current contradictory instruction is found and evidenced during Apply.
4. Run focused tests, strict target/all OpenSpec validation, `openspec doctor`, and
   the canonical quality gate.

Rollback is a direct revert of the presentation-contract and focused-test changes;
there is no schema, runtime, data, or publication migration.
