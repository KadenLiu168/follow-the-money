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

## Semantic capability surface

ECO-33 defines one closed semantic catalog. These are capability families, not
sequential production stages or API boundaries:

| Capability family | Execution status | Detailed contract |
| --- | --- | --- |
| Evidence Feed | `live-production` | `feed-evidence-pipeline` |
| Evidence and Event Structuring | `retained-no-production-caller` | `deterministic-research-engine` |
| Market Analytics and State | `retained-no-production-caller` | `deterministic-research-engine` |
| Confidence and Watchlist | `retained-no-production-caller` | `deterministic-research-engine` |
| Scoring and Ranking | `retained-no-production-caller` | `deterministic-research-engine` |
| Deterministic Audit | `retained-no-production-caller` | `deterministic-research-engine` |

Capability ownership means repository/Skill ownership of accepted deterministic
behavior and invariants. It does not allocate operational responsibility between
the Skill and Host Agent. The status labels are descriptive architecture
metadata only: they are not runtime state, serialized fields, configuration, a
capability registry, or a promise that every named family is production-wired.

The retained libraries are typed, deterministic, reproducible, independently
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

Provider adapters and manifests, HTTP clients, collection locks and rate-state
machinery, configuration loaders, canonical serialization and digest helpers,
publication filesystem mechanics, title-similarity primitives, internal helper
functions, and individual Python structure layouts remain implementation
machinery rather than stable Host-Agent capabilities. They may change without a
semantic capability-surface change when the owning deterministic behavior and
invariants remain intact.

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

## Deferred integration boundary

The semantic capability surface above is defined by ECO-33, but the concrete
Skill-Agent integration remains deferred. ECO-34 owns responsibility, mutation,
and trust decisions; ECO-35 owns grounding, validation ownership,
unsupported-claim, retry, and rewrite decisions. Agent-facing objects and
schemas, invocation protocols, adapters, orchestration topology, call counts,
ordering, and runtime implementation remain deferred beyond ECO-33. This
repository does not define them here.

## Non-goals

Real-time/tick data, automatic trading, portfolio construction, historical
event memory, cross-day stitching, any embedded LLM capability, paid
financial-data provider dependencies, or a public user-facing CLI product.
