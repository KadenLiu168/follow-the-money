# Capability Status

## Live production

- Evidence Feed — normal published-Feed consumption.
- Deterministic Audit — independent, explicit, on-demand private invocation.
- Evidence and Event Structuring — independent, explicit, on-demand private
  invocation.

## Retained without a production caller

- Market Analytics and State.
- Confidence and Watchlist.
- Scoring and Ranking.

These labels describe architecture, not runtime metadata, configuration, a
capability registry, or workflow stages. A retained capability remains typed,
deterministic, reproducible, and independently tested, but must not be
automatically wired or chained merely because it exists.

Detailed semantics remain governed by the applicable living specs under
`openspec/specs/`. The private invocation schema statically exposes only
`audit.text`, `audit.claims`, and `event.structure`.
