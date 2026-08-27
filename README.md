# Follow the Money

Evidence-grounded financial research Skill for AI Agents: a deterministic,
credential-free evidence Feed from free China/US official and public sources,
plus retained deterministic libraries (ledger, candidate events, market
snapshot/state, watchlist, scoring/ranking rules, safety audit). The semantic
Skill capability surface, responsibility boundary, and private on-demand Audit
invocation boundary are implemented; integration beyond Audit remains deferred.

The Agent understands, reasons, and expresses; `follow-the-money` supplies
facts, rules, deterministic computation, and verifiability.

## What this repository is

A Python 3.12 package whose live production path collects and publishes a
schema-validated, identity-bearing evidence-only Feed: run identity, one fixed
evidence cutoff, per-item provider provenance, canonical digests, and contract
snapshots. No credential, model, or LLM runtime exists anywhere in the
repository. A separate private one-shot boundary provides on-demand deterministic
Audit; the other retained libraries have no current production caller.

The retained deterministic libraries other than Audit are typed, reproducible,
independently tested, and reusable, but have no current production orchestration
caller. The Host Agent owns reasoning and narrative after consuming the Feed;
naming a retained capability does not add a production caller.

## Semantic capability surface

The closed semantic catalog has exactly six families:

- Evidence Feed — `live-production`.
- Evidence and Event Structuring — `retained-no-production-caller`.
- Market Analytics and State — `retained-no-production-caller`.
- Confidence and Watchlist — `retained-no-production-caller`.
- Scoring and Ranking — `retained-no-production-caller`.
- Deterministic Audit — `live-production` (on demand).

These are descriptive architecture labels, not runtime state, configuration,
serialized metadata, a capability registry, or workflow stages. The
repository/Skill owns the accepted deterministic behavior, invariants, and
capability-local validation; detailed behavior remains in the existing living
specs. The Host Agent owns research intent, interpretation, reasoning,
hypotheses, conclusions, working analysis, and narrative. The deterministic
engine is an internal Skill layer, not a third participant or Agent-callable
endpoint. A result is authoritative only within its governing spec; consumer
derivation outside that governing capability remains consumer/Agent-owned, and
boundary crossing or deterministic processing does not upgrade provenance,
verification, or authority. The runtime-neutral
`agent-grounding-validation-contract` defines semantic grounding, validation
authority, constrained output admissibility, unsupported assertions, and
semantic recovery. Evidence-reference presence alone does not establish
semantic support, deterministic success does not establish entailment or
complete answer validity, and the Host Agent owns semantic support assessment
and narrative emission while deterministic findings retain bounded Skill
authority. Known unsupported grounded assertions and unresolved applicable
critical findings are not admissible unchanged. The private one-shot Agent
invocation contract is implemented through `schemas/agent-invocation.schema.json`;
it defines only `audit.text` and `audit.claims`, with no orchestration, retry,
rewrite loop, or runtime registry.

## Accepted invocation contract and Phase 5 plan

The private Host-Agent boundary accepts one UTF-8 JSON request on stdin and
returns one JSON response on stdout; diagnostics belong on stderr. Version 1
has only `audit.text` and `audit.claims`. A successful response carries the
deterministic Audit result, including critical findings; typed invocation
errors are separate from capability results. There is no session, streaming,
discovery, registry, remote transport, shared state, automatic chaining, Event
operation, LLM runtime, or caller for any capability other than on-demand Audit.

The activation plan records the verified state: Feed remains live and unchanged;
Audit is `live-production` through its implemented private boundary; Evidence
and Event Structuring targets ECO-51 after Audit; Market Analytics and State,
Confidence and Watchlist, and Scoring and Ranking remain deferred and
`retained-no-production-caller`.

## Investment-assistance boundary

The retained safety audit (`ClaimAuditor`) flags prohibited trading
instructions (buy, sell, add, reduce, position-size, entry, exit, stop-loss,
target price — Chinese or English) with descriptive exceptions. Nothing here
is investment advice.

## Repository layout

```
config/           closed versioned YAML configuration (v1 defaults, no secrets)
providers/        provider contract manifests and fixture provenance
schemas/          JSON Schema 2020-12 contracts (Feed plus Agent invocation)
src/follow_the_money/  live Feed/Audit paths plus retained deterministic libraries
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
