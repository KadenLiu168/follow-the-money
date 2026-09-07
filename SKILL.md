---
name: follow-the-money
description: |
  Evidence-grounded financial research Skill. Uses the published deterministic
  Feed to generate primary-source-backed financial research reports. Invoke
  when financial research requires validated evidence from follow-the-money.
---

# Follow the Money

Generate the requested research report from the validated published Feed.

## Skill invocation flow

1. Read [references/feed-contract.md](references/feed-contract.md) and
   [references/safety-boundary.md](references/safety-boundary.md).
2. Run `scripts/skill/prepare-feed` to retrieve and validate the published Feed.
3. If retrieval or validation fails, surface the exact stderr and stop. Preserve
   degraded status and warnings; never substitute local, stale, or partial data.
4. Analyze only the validated evidence. Distinguish evidence from interpretation,
   cite the relevant Feed items, state material coverage or freshness limits, and
   produce the user-facing research report.

```text
published Feed -> validation -> Host Agent analysis -> research report
```

GitHub Actions owns Provider collection and deterministic Feed production. The
Skill consumes that product; the Host Agent owns financial interpretation,
reasoning, conclusions, and narrative. Feed remains evidence, not intelligence
output.

For an explicitly requested deterministic Audit or Event Structuring operation,
use only the corresponding private one-shot boundary. Do not automatically chain
it with the Feed or any retained capability.

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
