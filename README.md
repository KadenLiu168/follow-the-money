# Follow the Money

Evidence-grounded financial research Skill for AI Agents: a deterministic,
credential-free evidence Feed from free China/US official and public sources,
plus a retained deterministic engine (ledger, candidate events, market
snapshot/state, watchlist, scoring/selection rules, safety audit) awaiting a
future Agent delivery contract.

The Agent understands, reasons, and expresses; `follow-the-money` supplies
facts, rules, deterministic computation, and verifiability.

## What this repository is

A Python 3.12 package that collects and publishes a schema-validated,
identity-bearing evidence-only Feed: run identity, one fixed evidence cutoff,
per-item provider provenance, canonical digests, and contract snapshots. No
credential, model, or LLM runtime exists anywhere in the repository.

The repository is in an intentional transitional state: the deterministic
core is live and tested, while the structured Agent contract over the core
(research/analysis/brief orchestration) is deferred to a future Change.

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
src/follow_the_money/  production package (deterministic engine)
scripts/feed/     minimal internal Feed entry: follow-the-money-feed
feeds/            published artifacts (daily/<date>/<run_id>.json, latest.json)
tests/            pytest suite (credential-free)
docs/             architecture, contracts, runbooks
.github/workflows/ hosted CI + scheduled Feed workflow template
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

## Current bootstrap boundary

This repository is **not** a Git checkout and is not yet initialized as one.
It contains no license file, no Git history, no remote, and no enabled
workflow. Those are separate, explicitly authorized deployment decisions.

## Real external scheduling boundary

The scheduled Feed workflow is a checked-in **template**: it requires a
separately provisioned dedicated self-hosted runner with a persistent shared
output root and durable rate state, plus an explicit opt-in gate, before any
provider request runs. Workflow enablement and external 08:30 scheduling are
deployment concerns, not claims made by this repository.

## Documentation

- `docs/architecture.md` — retained deterministic engine and transitional state
- `docs/feed-contract.md` — Feed schema, window/cutoff model, publication
- `docs/scoring.md` — deterministic scoring and selection contract
- Runbooks: `docs/runbooks/`
