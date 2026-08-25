# Follow the Money

Evidence-grounded financial research Skill for AI Agents: a deterministic,
credential-free evidence Feed from free China/US official and public sources,
plus retained deterministic libraries (ledger, candidate events, market
snapshot/state, watchlist, scoring/ranking rules, safety audit). The future
Skill-Agent Contract remains undefined until the Pre-Agent Baseline Acceptance
gate passes.

The Agent understands, reasons, and expresses; `follow-the-money` supplies
facts, rules, deterministic computation, and verifiability.

## What this repository is

A Python 3.12 package whose live production path collects and publishes a
schema-validated, identity-bearing evidence-only Feed: run identity, one fixed
evidence cutoff, per-item provider provenance, canonical digests, and contract
snapshots. No credential, model, or LLM runtime exists anywhere in the
repository.

The retained deterministic libraries are typed, reproducible, independently
tested, and reusable, but they have no current production orchestration caller.
The Host Agent owns reasoning and narrative after consuming the Feed; the
future Skill-Agent Contract is not defined in the current baseline.

## Investment-assistance boundary

The retained safety audit (`ClaimAuditor`) flags prohibited trading
instructions (buy, sell, add, reduce, position-size, entry, exit, stop-loss,
target price — Chinese or English) with descriptive exceptions. Nothing here
is investment advice.

## Repository layout

```
config/           closed versioned YAML configuration (v1 defaults, no secrets)
providers/        provider contract manifests and fixture provenance
schemas/          JSON Schema 2020-12 contracts (feed.schema.json)
src/follow_the_money/  live Feed path plus retained deterministic libraries
scripts/feed/     minimal internal Feed entry: follow-the-money-feed
feeds/            published artifacts (daily/<date>/<run_id>.json, latest.json)
tests/            pytest suite (credential-free)
docs/             architecture, contracts, runbooks
.github/workflows/ hosted CI + scheduled Feed workflow template

Configuration authority and the single resolved Provider contract are documented
in [`docs/configuration.md`](docs/configuration.md).
```

## Quick start

```bash
uv sync --frozen --all-groups
uv run pytest            # full credential-free test suite
uv run python -m follow_the_money.feed.cli --dry-run
# or: scripts/feed/follow-the-money-feed --dry-run
```

## Exit-code contract (minimal internal Feed entry)

- `0` — healthy/degraded Feed success (warnings on stderr/status)
- `1` — generation/publication/schema/integrity failure
- `2` — usage, configuration, or startup-capability error

There is no public user-facing CLI product form: `brief`, `eval`, and
`replay` subcommands and the standalone console script were removed.

## Real external scheduling boundary

The scheduled Feed workflow is a checked-in **template**: it requires a
separately provisioned dedicated self-hosted runner with a persistent shared
output root and durable rate state, plus an explicit opt-in gate, before any
provider request runs. Workflow enablement and external 08:30 scheduling are
deployment concerns, not claims made by this repository.

## Documentation

- `docs/architecture.md` — live Feed path, retained capabilities, future boundary
- `docs/feed-contract.md` — Feed schema, window/cutoff model, publication
- `docs/scoring.md` — deterministic scoring and ranking contract
- Runbooks: `docs/runbooks/`
