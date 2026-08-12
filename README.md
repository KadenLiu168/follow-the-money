# Follow the Money

Deterministic daily financial intelligence: an evidence-only Feed from free
China/US official and public sources, canonical atomic events, constrained
LLM analysis, and a fixed Chinese Morning Money Brief — script-first, LLM-last.

## What this repository is

A complete Python 3.12 application that turns free public financial evidence
into a daily 08:30 Asia/Shanghai Morning Money Brief. Every important factual
claim is traceable to a source; deterministic work (collection, normalization,
deduplication, analytics, scoring, selection, validation) never happens inside
a prompt; the LLM is limited to four bounded passes: semantic event
resolution, verified-packet financial analysis, structured editorial
synthesis, and a final language audit.

## Investment-assistance boundary

The Brief provides financial intelligence and uncertainty. It **never**
contains direct buy, sell, add, reduce, position-size, entry, exit, stop-loss,
or target-price instructions — in Chinese or English, in structured or
rendered output. Nothing here is investment advice.

## Repository layout

```
config/           closed versioned YAML configuration (v1 defaults)
providers/        provider contract manifests and fixture provenance
schemas/          JSON Schema 2020-12 contracts (serialized authority)
prompts/          four LLM pass prompts
src/follow_the_money/  production package
scripts/feed/     thin wrapper: follow-the-money-feed
scripts/skill/    thin wrapper: follow-the-money-skill
feeds/            published artifacts (daily/<date>/<run_id>.json, latest.json)
runs/             local audit bundles (ignored by Git)
tests/            pytest suite (credential-free)
evals/            golden-day fixtures and evaluation reports
docs/             architecture, contracts, runbooks
.github/workflows/ hosted CI + scheduled Feed workflow template
```

## Quick start

```bash
uv sync --frozen --all-groups
uv run pytest            # full credential-free test suite
uv run follow-the-money feed --dry-run
```

## CLI exit-code contract

- `0` — complete requested success
- `1` — runtime/domain/schema/reference/integrity/deadline/publication/delivery failure
- `2` — CLI usage, configuration, missing required credential, startup capability error

Subcommands: `feed`, `brief`, `eval`, `replay`. See `docs/` for details.

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

- `docs/architecture.md` — pipeline and trust boundaries
- `docs/feed-contract.md` — Feed schema, window/cutoff model, publication
- `docs/scoring.md` — deterministic scoring and selection contract
- `docs/evaluation.md` — offline/live regression evaluation
- Runbooks: `docs/runbooks/`
