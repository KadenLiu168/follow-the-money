# Architecture

Follow the Money is a deterministic, credential-free evidence engine. The
project owns no LLM capability: no SDK dependency, no prompt files, no
model/API-key configuration, no LLM request code, and no live evaluation.
The only live production path is:

```text
Evidence Providers
      ↓
Deterministic evidence Feed
      ↓
Host Agent reasoning and narrative
      ↓
Grounded research output
```

The Feed entry owns configuration resolution, Provider planning and fetching,
normalization, deduplication, validation, identity/digest construction, health
assessment, and publication. The Feed remains evidence-only: the Host Agent
owns financial interpretation and narrative.

## Retained capabilities

The following are retained deterministic capabilities, not sequential
production stages:

- Evidence ledger and candidate/event utilities
- Market snapshot/state and watchlist
- Scoring/ranking rules
- `ClaimAuditor` safety audit

Each retained library is typed, deterministic, reproducible, independently
tested, and reusable. A retained library may intentionally have no current
production orchestration caller; no placeholder caller supplies synthetic
inputs to make it appear live.

The Feed is the current serialized external contract: it is validated against
`schemas/feed.schema.json` plus semantic, identity, and digest checks. Internal
structures such as the ledger, candidate Components/grouping, market
snapshot/state, watchlist, scoring intermediates, and ranking inputs use typed
Python interfaces, domain invariants/validation, and deterministic tests; they
do not require a standalone JSON Schema each.

## Modules

| Module | Responsibility |
| --- | --- |
| `config/` | Closed versioned YAML configuration and strict validation (no credentials) |
| `schemas/` | JSON Schema 2020-12 contracts (`feed.schema.json`) |
| `providers/` | Contract manifests, adapters, HTTP/rate/lock discipline |
| `feed/` | Feed planning, deduplication, validation, publication, minimal entry |
| `engine/` | Retained entity resolution, candidate Components, and title similarity |
| `events.py` | Retained pure canonical Event/family ID derivation |
| `market/` | Decimal formulas, surprise, confidence |
| `ledger.py` | Frozen evidence ledger |
| `state.py` / `watchlist.py` | Market state vector and 24-hour watchlist |
| `scoring.py` / `selection.py` | Retained deterministic significance/priority/ranking libraries |
| `audit.py` | Retained `ClaimAuditor` safety lexicon audit library |
| `boundary.py` | Application build fingerprint (consumed by the Feed) |

Removed with the LLM runtime: `llm.py`, `pipeline.py`, `brief_cli.py`,
`analysis.py`, `editor.py`, `brief.py`, `render.py`,
`engine/resolution.py`, `eval_*`, `bundle.py`, the public CLI, and their
schemas/tests. Recoverable only from git history.

## Trust boundaries

- **The repository never reads a credential or knows a model.** Configuration
  loading succeeds with no credential configured and fails closed only on
  deterministic contracts (providers, scoring, sessions, roles, safety
  lexicon).
- **The live Feed entry owns** run identity, evidence cutoff, provider
  collection, evidence normalization, Feed validation, and the Feed publication
  decision. It does not invoke every retained deterministic library.
- **Retained libraries own** their typed inputs, domain invariants, and
  deterministic calculations; their production orchestration caller status is
  explicit rather than inferred from implementation or test coverage.
- **URLs are credential-free** and validated against the owning provider's
  embedded contract before hashing, retention, or publication.
- **The safety audit flags trading instructions** (buy/sell/add/reduce/
  position-size/entry/exit/stop/target), in Chinese or English, with
  descriptive false-positive exceptions.

## Future boundary

The future Skill-Agent Contract remains undefined until the Pre-Agent Baseline
Acceptance gate passes. This repository does not define future Agent objects,
schemas, stages, call counts, ordering, adapters, or orchestration here.

## Non-goals

Real-time/tick data, automatic trading, portfolio construction, historical
event memory, cross-day stitching, any embedded LLM capability, paid
financial-data provider dependencies, or a public user-facing CLI product.
