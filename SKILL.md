---
name: follow-the-money
description: |
  Evidence-grounded financial research Skill. Uses the published deterministic
  Feed to generate primary-source-backed financial research reports. Invoke
  when financial research requires validated evidence from follow-the-money.
---

# Follow the Money

Generate the requested research report from the validated published Feed.

## Execution rules

For normal research report requests:

```text
published Feed -> validation -> evidence analysis -> research report
```

Consume the published Feed through `scripts/skill/prepare-feed` under
[the Feed contract](references/feed-contract.md), then apply
[the safety boundary](references/safety-boundary.md) to the report. Use only the
validated output. Preserve valid degraded status and warnings; on retrieval or
validation failure, surface the exact stderr and stop. Never substitute local,
stale, or partial data.

For Feed metadata or capability inspection, load only the corresponding
reference and answer within that boundary. For an explicitly requested
Deterministic Audit or Event Structuring operation, use only its private one-shot
boundary. Do not automatically chain the Feed, private operations, or retained
capabilities.

GitHub Actions owns Provider collection and deterministic Feed production. The
Skill consumes that product; the Host Agent owns financial interpretation,
reasoning, conclusions, and narrative. Feed remains evidence, not intelligence
output.

## References

Load only what the request needs:

- [Architecture boundary](references/architecture-boundary.md) — ownership,
  caller topology, or runtime architecture questions.
- [Feed contract](references/feed-contract.md) — every normal research request;
  retrieval, validation, provenance, cutoff, freshness, and degradation rules.
- [Capability status](references/capability-status.md) — capability availability
  or explicit deterministic-operation requests.
- [Safety boundary](references/safety-boundary.md) — every generated report;
  grounding, unsupported claims, and investment-assistance limits.
