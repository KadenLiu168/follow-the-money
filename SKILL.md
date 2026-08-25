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

This Skill uses the local repository's minimal internal Feed entry. That entry
owns network access and deterministic Feed collection and processing; the Skill
runtime stays a thin coordinator and never re-implements Feed logic. Retained
post-Feed libraries are not claimed as entry-orchestrated production stages.

## Semantic capability surface

The semantic Skill capability surface is now defined as a closed catalog of six
families:

- Evidence Feed — `live-production`.
- Evidence and Event Structuring — `retained-no-production-caller`.
- Market Analytics and State — `retained-no-production-caller`.
- Confidence and Watchlist — `retained-no-production-caller`.
- Scoring and Ranking — `retained-no-production-caller`.
- Deterministic Audit — `retained-no-production-caller`.

These labels describe architecture only. They are not runtime state, serialized
metadata, configuration, a capability registry, or workflow stages. The
repository/Skill owns the accepted deterministic behavior and invariants of
these families; detailed behavior remains governed by the existing
`feed-evidence-pipeline` and `deterministic-research-engine` living specs.

The semantic surface does not allocate operational responsibility between the
Skill and Host Agent. ECO-34 remains responsible for responsibility, mutation,
and trust decisions; ECO-35 remains responsible for grounding, validation,
unsupported-claim, retry, and rewrite decisions. Agent-facing schemas,
invocation, orchestration, and runtime implementation remain deferred beyond
ECO-33.

## Live / Retained / Deferred

The live repository path is the evidence Feed. Retained post-Feed libraries are
typed, deterministic, reproducible, independently tested, and reusable, but
they intentionally have no current production orchestration caller. Naming a
retained family does not add or require a production caller.

The host Agent is expected to:

1. Collect the evidence Feed (below), then
2. Perform the financial analysis and produce the research digest itself.

Do not invent future Agent objects, schemas, stages, ordering, or placeholder
wiring in the meantime.

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
3. **Analysis**: the host Agent analyzes the evidence and writes the digest.
   No other repository entry exists.

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
