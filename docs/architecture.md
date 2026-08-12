# Architecture

Follow the Money is a script-first, LLM-last daily financial intelligence
pipeline: deterministic collection, normalization, analytics, scoring,
selection, and validation stay outside prompts; the LLM is limited to four
bounded passes.

## Pipeline and trust boundaries

```text
GitHub Feed (evidence only, no LLM)
  -> local deterministic evidence engine
  -> constrained semantic resolution
  -> canonical events and verified packets
  -> constrained financial analysis
  -> deterministic ranking and selection
  -> deterministic Chinese Markdown rendering
  -> deterministic claim audit
  -> constrained language audit
  -> publication plus local audit bundle
```

The Feed is stateless from the Skill's perspective: a normal run consumes
only `feeds/latest.json`. Immutable dated Feeds and local run bundles exist
solely for audit, debugging, replay, and evaluation and are never inputs to
the normal daily Skill. Rolling analytics use bounded raw lookback
observations embedded in the latest Feed.

## Modules

| Module | Responsibility |
| --- | --- |
| `config/` | Closed versioned YAML configuration and strict validation |
| `schemas/` | JSON Schema 2020-12 contracts (serialized authority) |
| `providers/` | Contract manifests and source adapters |
| `feed/` | Feed planning, deduplication, validation, publication, CLI |
| `engine/` | Feed health, entity resolution, candidate graph, resolution |
| `market/` | Decimal formulas, surprise, confidence |
| `llm.py` | One-model Responses API adapter with typed failure states |
| `analysis.py` | Analyst-output → Analysis merge (script-owned) |
| `scoring.py` / `selection.py` | Deterministic significance/priority/selection |
| `state.py` / `watchlist.py` | Market state vector and 24-hour watchlist |
| `brief.py` / `render.py` / `audit.py` | Brief assembly, Markdown, claim audit |
| `bundle.py` | Atomic run audit bundles and replay |
| `eval_*` | Offline metrics/gates and credentialed live evaluation |

## Trust boundaries

- **LLM cannot** choose IDs, knowledge/effective instants, labels, scores,
  statuses, ordering, URLs, or facts. It returns only bounded wording,
  membership proposals, and closed categorical features.
- **Scripts own** every deterministic object: canonical Event IDs,
  `fully_known_at`, display labels, ledger, market analytics, surprise,
  confidence, significance, Morning Relevance, Brief Priority, final
  selection, story-family penalties, market state, watchlist, claim
  inventory, rendered bytes, and the publication decision.
- **URLs are credential-free** and validated against the owning provider's
  embedded contract before hashing, retention, or rendering.
- **Every prose/reason/wording field** is strict-UTF-8, Unicode-scalar,
  NFC-normalized, single-line, and rejects `Cc`/`Cf`/`Cs`/`Zl`/`Zp`.
- **The Brief never contains trading instructions** (buy/sell/add/reduce/
  position-size/entry/exit/stop/target), in Chinese or English.

## Non-goals

Real-time/tick data, automatic trading, portfolio construction, historical
event memory, cross-day stitching, multi-model routing, model ensembles,
automatic fallback, Bloomberg-equivalent coverage, or a hard dependency on
paid financial-data providers.
