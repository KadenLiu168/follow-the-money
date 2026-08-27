---
name: follow-the-money
description: |
  Evidence-grounded financial research Skill for AI Agents: deterministic,
  credential-free evidence Feed from free China/US official and public
  sources, plus a retained deterministic engine (ledger, canonical events,
  market state, watchlist, scoring/ranking rules, safety audit). Triggers
  on "/money", on a schedule, or when the user asks for a money/flow/macro
  research digest backed by primary sources.
---

# Follow the Money — Skill Orchestration Contract

This Skill uses the local repository's minimal internal Feed entry and its
separate private on-demand Audit invocation boundary. The Feed entry owns
network access and deterministic Feed collection and processing; the Audit
boundary invokes only the accepted deterministic Audit operation. Within the
Skill boundary, the deterministic engine is an internal responsibility layer for
accepted typed/domain invariants, transformations, calculations, canonicalization,
ordering, and capability-local validation—not a third participant or an
Agent-callable endpoint. Other retained post-Feed libraries are not claimed as
entry-orchestrated production stages.

## Semantic capability surface

The semantic Skill capability surface is now defined as a closed catalog of six
families:

- Evidence Feed — `live-production`.
- Evidence and Event Structuring — `retained-no-production-caller`.
- Market Analytics and State — `retained-no-production-caller`.
- Confidence and Watchlist — `retained-no-production-caller`.
- Scoring and Ranking — `retained-no-production-caller`.
- Deterministic Audit — `live-production` (on demand).

These labels describe architecture only. They are not runtime state, serialized
metadata, configuration, a capability registry, or workflow stages. The
repository/Skill owns the accepted deterministic behavior and invariants of
these families; detailed behavior remains governed by the existing
`feed-evidence-pipeline` and `deterministic-research-engine` living specs.

The responsibility boundary is semantic. The Host Agent owns research intent,
financial interpretation, reasoning and judgment, Agent hypotheses and
conclusions, working analysis, and user-facing synthesis and narrative. The
Skill owns the accepted deterministic semantics, invariants, and capability-local
validation of these families. A Skill-produced result is authoritative only for
the exact guarantees of its governing living spec; a consumer-modified,
supplemented, interpreted, or derived value outside that governing capability is
consumer-owned or Host-Agent-owned.
Agent-originated assertions remain Agent-owned, and crossing the boundary or
processing them deterministically does not upgrade their provenance,
verification, or authority. The runtime-neutral
`agent-grounding-validation-contract` defines semantic grounding, validation
authority, constrained output admissibility, unsupported assertions, and
semantic recovery. The Host Agent assesses semantic support and owns the
operational emission decision; the Skill owns the correctness and meaning of
accepted deterministic findings only within their governing specs. An evidence
reference alone is not semantic support, and deterministic success does not
prove entailment or complete answer validity. Known unsupported grounded
assertions and unresolved applicable critical findings are not admissible
unchanged. The implemented private Agent invocation contract is defined in
`schemas/agent-invocation.schema.json`; it statically dispatches only
`audit.text` and `audit.claims`. It adds no orchestration, retry, rewrite loop,
or runtime registry. Integration beyond on-demand Audit remains deferred.

## Live / Retained / Deferred

The live repository capabilities are the evidence Feed and the independent,
on-demand Deterministic Audit. The other post-Feed libraries are typed,
deterministic, reproducible, independently tested, and reusable, but they
intentionally have no current production orchestration caller. Naming a retained
family does not add or require a production caller.

The host Agent is expected to:

1. Collect the evidence Feed (below), then
2. Perform the financial analysis and produce the research digest itself,
   grounding factual claims in the Feed's evidence and provenance.

Do not invent future Agent objects, schemas, stages, ordering, or placeholder
wiring in the meantime.

## Implemented private invocation contract

The private Host-Agent boundary is a one-shot local process contract: one UTF-8
JSON request on stdin and one UTF-8 JSON response on stdout; diagnostics belong
on stderr. Version 1 statically defines only `audit.text` and `audit.claims`.
Successful responses carry the deterministic Audit result, including critical
findings; typed invocation errors are a separate response shape and process
failure. The contract provides no session, streaming, discovery, registry, remote
transport, shared state, hidden capability chaining, Event operation, LLM runtime,
or caller for any capability other than on-demand Audit.

The Phase 5 activation plan is approval for later Changes only:

- Evidence Feed remains live and unchanged.
- Deterministic Audit is `live-production` through its implemented private
  boundary and remains on demand.
- Evidence and Event Structuring targets ECO-51 after Audit.
- Market Analytics and State, Confidence and Watchlist, and Scoring and Ranking
  remain deferred.

Event Structuring, Market Analytics and State, Confidence and Watchlist, and
Scoring and Ranking therefore remain `retained-no-production-caller`.

## Investment-assistance boundary

The digest may contain financial intelligence and uncertainty but must
**never** contain buy, sell, add, reduce, position-size, entry, exit,
stop-loss, or target-price instructions — in Chinese or English. If a step
fails, surface the exact stderr and stop — do not silently substitute a
partial digest or invent events. The retained `ClaimAuditor` may be applied
to any submitted text as a deterministic safety check.

## Non-Go boundary (do not claim)

- GitHub Actions does **not** invoke this Skill at 08:30. External scheduling
  is configured by the deployment environment after Feed publication.
- The Feed reflects one fixed evidence cutoff captured before provider
  requests; it never claims coverage through collection completion or a
  nominal 08:30 value.

## Live path

```text
scripts/feed/follow-the-money-feed      # evidence-only Feed, deterministic,
                                        # credential-free, no LLM anywhere
  -> host Agent: analyze the evidence and write the research digest
```

## Exit-code contract

- `0` complete success (healthy or degraded Feed; warnings on stderr/status)
- `1` runtime/domain/schema/reference/integrity/deadline/publication failure
- `2` usage/config/startup capability error

## Daily flow (scheduled or /money)

1. **Feed**: `scripts/feed/follow-the-money-feed` (or
   `uv run python -m follow_the_money.feed.cli`). Exit 0 with healthy or
   degraded Feed; warnings are on stderr and in status. A Feed failure means
   no digest should be produced from it.
2. **Evidence**: read `feeds/latest.json` (or the dated
   `feeds/daily/<date>/<run_id>.json`). Every item carries source provenance;
   the window, cutoff, and run identity are authoritative.
3. **Analysis**: the host Agent analyzes the evidence and writes the digest,
   citing the relevant Feed items. The independent Audit boundary is available
   only when the Host Agent explicitly addresses `audit.text` or `audit.claims`.

This flow does not claim that the minimal Feed entry orchestrates the retained
post-Feed libraries.

If a required step fails, surface the exact stderr and stop. Partial output
is worse than no output.

## Credentials

None. The Feed needs no credential, model, or network configuration beyond
the configured providers.

Configuration ownership is explicit: application values come from
`config/config.yaml`, Provider contract facts come from the owning
`providers/<provider_id>/manifest.yaml`, and enablement/coverage come from
`config/providers.yaml`; the Feed resolves one Provider contract before
runtime state or collection begins. See `docs/configuration.md`.
