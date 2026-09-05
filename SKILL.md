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

Normal Skill invocation uses `scripts/skill/prepare-feed` to consume the
credential-free published Feed from `KadenLiu168/follow-the-money` `main`. It
resolves that branch once to one exact commit, retrieves the manifest and its
declared artifacts from that commit, validates them in temporary storage, and
emits the existing logical Feed. It never invokes the local producer or uses a
local fallback. GitHub Actions owns the producer path; the Skill also retains
its separate private on-demand Audit and Event Structuring invocation boundary.
The producer owns network access and deterministic Feed collection and
processing; the private boundary invokes only the explicitly addressed
deterministic Audit or Event Structuring operation. Within the
Skill boundary, the deterministic engine is an internal responsibility layer for
accepted typed/domain invariants, transformations, calculations, canonicalization,
ordering, and capability-local validation—not a third participant or an
Agent-callable endpoint. Other retained post-Feed libraries are not claimed as
entry-orchestrated production stages.

## Semantic capability surface

The semantic Skill capability surface is now defined as a closed catalog of six
families:

- Evidence Feed — `live-production`.
- Evidence and Event Structuring — `live-production` (on demand).
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
`audit.text`, `audit.claims`, and `event.structure`. It adds no orchestration,
retry, rewrite loop, or runtime registry. Integration beyond on-demand Audit and
Event Structuring remains deferred.

## Live / Retained / Deferred

The live repository capabilities are the evidence Feed and the independent,
on-demand Deterministic Audit and Event Structuring. The other post-Feed libraries are typed,
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
on stderr. Version 1 statically defines `audit.text`, `audit.claims`, and
`event.structure`. Successful responses carry the bounded deterministic Audit or
Event result; typed invocation errors are a separate response shape and process
failure. The contract provides no session, streaming, discovery, registry, remote
transport, shared state, hidden capability chaining, LLM runtime, or caller for
any capability other than on-demand Audit and Event Structuring.

The Phase 5 activation plan is approval for later Changes only:

- Evidence Feed remains live and unchanged.
- Deterministic Audit is `live-production` through its implemented private
  boundary and remains on demand.
- Evidence and Event Structuring is `live-production` through its implemented
  `event.structure` operation and remains on demand.
- Market Analytics and State, Confidence and Watchlist, and Scoring and Ranking
  remain deferred.

Market Analytics and State, Confidence and Watchlist, and Scoring and Ranking
remain `retained-no-production-caller`.

## Investment-assistance boundary

The digest may contain financial intelligence and uncertainty but must
**never** contain buy, sell, add, reduce, position-size, entry, exit,
stop-loss, or target-price instructions — in Chinese or English. If a step
fails, surface the exact stderr and stop — do not silently substitute a
partial digest or invent events. The retained `ClaimAuditor` may be applied
to any submitted text as a deterministic safety check.

## Scheduled generation boundary

- GitHub Actions runs the deterministic Feed on `ubuntu-latest` at `20 0 * * *`
  (08:20 Asia/Shanghai), or by `workflow_dispatch`, using `feeds/` for consumer
  products and `.feed-state/` for repository-backed runtime state. The first
  invocation may migrate legacy runtime files or bootstrap with zero Provider
  requests; normal arming uses the runtime checkpoint and lease. It does not
  invoke Host-Agent reasoning, Audit, Event Structuring, or retained
  market/scoring capabilities.
- The Feed reflects one fixed evidence cutoff captured from actual runtime
  before Provider requests; it never claims coverage through collection
  completion or a nominal schedule value. Payload observation/effective time,
  source publication/update time, Provider retrieval/check time, and Feed
  generation time remain distinct. Freshness and availability are explicit per
  Provider; only a complete successful check may carry an unchanged slice from
  the fully validated active bundle. A wholly blocked HTTP 401/403 Provider may
  produce a bounded degraded Feed without prior-slice carry-forward; other
  incomplete Provider work remains fatal.

The local producer entry `scripts/feed/follow-the-money-feed` is an explicitly
operated surface for hosted Actions, development, tests, Provider diagnostics,
and operator runs. It is not the normal Skill caller, and a remote failure is
terminal rather than a local fallback.

## Live path

```text
scripts/skill/prepare-feed              # consume one commit-pinned published
                                        # Feed, credential-free, no LLM anywhere
  -> host Agent: analyze the evidence and write the research digest
```

## Exit-code contract

- `0` complete success (healthy or degraded Feed; warnings on stderr/status)
- `1` runtime/domain/schema/reference/integrity/deadline/publication failure
- `2` usage/config/startup capability error

## Daily flow (scheduled or /money)

1. **Feed**: GitHub Actions publishes the current `feeds/feed-manifest.json`
   and its eight typed artifacts. Normal Skill invocation runs
   `scripts/skill/prepare-feed`, which resolves `main` once and consumes the
   complete manifest-led bundle from that pinned commit. It emits the
   healthy/degraded logical Feed on stdout; warnings and remote failure
   diagnostics are on stderr. A remote failure stops the invocation: there is
   no Provider collection, local producer, stale Feed, partial evidence, or
   local fallback.
2. **Evidence**: the commit-pinned consumer validates the canonical manifest,
   exact ordered inventory, every artifact, integrity, identity, provenance,
   Provider availability, and pipeline status in temporary storage, then emits
   only the existing logical Feed. Retrieval and commit time do not refresh
   evidence timestamps. Every item carries source provenance; the window,
   cutoff, and run identity are authoritative. Runtime continuity remains owned
   by the producer checkpoint; Git history is repository history only, not a
   historical Feed query API.
3. **Analysis**: the host Agent analyzes the evidence and writes the digest,
   citing the relevant Feed items. The private boundary is available only when
   the Host Agent explicitly addresses `audit.text`, `audit.claims`, or
   `event.structure`.

This flow does not claim that the minimal Feed entry orchestrates the retained
post-Feed libraries.

If a required non-exempt step fails, surface the exact stderr and stop. A
validated wholly blocked HTTP 401/403 Provider is an explicit degraded Feed
warning, not a hidden success. Partial output is worse than no output.

## Credentials

None. The Feed needs no credential, model, or network configuration beyond
the configured providers.

Configuration ownership is explicit: application values come from
`config/config.yaml`, Provider contract facts come from the owning
`providers/<provider_id>/manifest.yaml`, and enablement/coverage come from
`config/providers.yaml`; the Feed resolves one Provider contract before
runtime state or collection begins. See `docs/configuration.md`.
