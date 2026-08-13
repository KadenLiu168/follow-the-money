# Architecture

Follow the Money is a deterministic, credential-free evidence engine. The
project owns no LLM capability: no SDK dependency, no prompt files, no
model/API-key configuration, no LLM request code, and no live evaluation.
The future architecture (recorded as direction, not yet implemented) is:

```text
Feed / Providers → deterministic prepare → ResearchContext → Agent →
AgentAnalysis → deterministic validate + score + select → BriefContext →
Agent → Brief → deterministic claim/evidence validation
```

This Change keeps exactly the deterministic core that the future prepare and
validation stages need, and nothing that exists only to serve the removed
four-pass LLM contract.

## Retained deterministic engine

```text
providers/ (adapters, HTTP, rate, lock, manifest)
  -> feed/ (plan, dedupe, validate, publish, minimal internal entry)
  -> evidence ledger (ledger.py)
  -> candidate events (engine/candidates.py, engine/entities.py,
                       engine/title.py, events.py)
  -> market snapshot/state (market/, state.py)
  -> watchlist (watchlist.py)
  -> scoring/selection rules (scoring.py, selection.py)  [no caller yet]
  -> ClaimAuditor safety audit (audit.py)                [no caller yet]
  -> canonical digests, schema validation, build fingerprint
     (canonical.py, schema.py, boundary.py)
```

Every retained structure is reproducible from the same inputs and protected by
the contract appropriate to its boundary. The Feed is the current serialized
external contract: it is validated against `schemas/feed.schema.json` plus
semantic, identity, and digest checks. Internal deterministic structures such
as the ledger, candidate blocks, market snapshot/state, watchlist, scoring
intermediates, and selection inputs use typed Python interfaces, domain
invariants/validation, and deterministic tests; they do not require a
standalone JSON Schema each.

## Modules

| Module | Responsibility |
| --- | --- |
| `config/` | Closed versioned YAML configuration and strict validation (no credentials) |
| `schemas/` | JSON Schema 2020-12 contracts (`feed.schema.json`) |
| `providers/` | Contract manifests, adapters, HTTP/rate/lock discipline |
| `feed/` | Feed planning, deduplication, validation, publication, minimal entry |
| `engine/` | Feed health, entity resolution, candidate blocks, title similarity |
| `events.py` | Canonical Event/family ID derivation (pure, script-owned) |
| `market/` | Decimal formulas, surprise, confidence |
| `ledger.py` | Frozen evidence ledger |
| `state.py` / `watchlist.py` | Market state vector and 24-hour watchlist |
| `scoring.py` / `selection.py` | Deterministic significance/priority/selection (library, no caller) |
| `audit.py` | `ClaimAuditor` safety lexicon audit (library, no caller) |
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
- **Scripts own** every deterministic object: run identity, evidence cutoff,
  canonical Event IDs, ledger, market analytics, surprise, confidence,
  significance, Morning Relevance, Brief Priority, selection, story-family
  penalties, market state, watchlist, and the Feed publication decision.
- **URLs are credential-free** and validated against the owning provider's
  embedded contract before hashing, retention, or publication.
- **The safety audit flags trading instructions** (buy/sell/add/reduce/
  position-size/entry/exit/stop/target), in Chinese or English, with
  descriptive false-positive exceptions.

## Transitional state

This repository is honest about its state: the deterministic core is live and
tested, but no production caller supplies analysis inputs to the retained
rules, and no placeholder architecture fakes them. The structured Agent
delivery contract (ResearchContext / AgentAnalysis / BriefContext shapes,
schemas, or validation) is deliberately not designed in this Change.

## Non-goals

Real-time/tick data, automatic trading, portfolio construction, historical
event memory, cross-day stitching, any embedded LLM capability, paid
financial-data provider dependencies, or a public user-facing CLI product.
