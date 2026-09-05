# Follow the Money

Evidence-grounded financial research Skill for AI Agents: a deterministic,
credential-free evidence Feed from free China/US official and public sources,
plus retained deterministic libraries (ledger, candidate events, market
snapshot/state, watchlist, scoring/ranking rules, safety audit). The semantic
Skill capability surface, responsibility boundary, and private on-demand Audit
and Event Structuring invocation boundary are implemented; integration beyond
Audit and Event Structuring remains deferred.

The Agent understands, reasons, and expresses; `follow-the-money` supplies
facts, rules, deterministic computation, and verifiability.

## What this repository is

A Python 3.12 package whose hosted production path collects and publishes a
schema-validated, identity-bearing evidence-only Feed, while normal Skill
invocation consumes that published Feed from one commit-pinned `main` snapshot:
run identity, one fixed
evidence cutoff, per-item provider provenance, canonical digests, contract
snapshots, and explicit per-Provider freshness and availability results. Concrete HTTP 401/403 source denials can be published as bounded degraded diagnostics; other Provider incompleteness remains fatal. Payload observation /
effective time, source publication/update time, Provider retrieval/check time,
and Feed generation time remain distinct. A valid unchanged slice may be
carried only after complete acquisition from the fully validated active bundle;
blocked or failed Provider acquisition never carries prior evidence. No credential, model, or LLM runtime
exists anywhere in the repository. A separate private one-shot boundary provides on-demand deterministic
Audit and Event Structuring; the other retained libraries have no current
production caller.

The retained deterministic libraries other than Audit and Event Structuring are
typed, reproducible, independently tested, and reusable, but have no current
production orchestration caller. The Host Agent owns reasoning and narrative
after consuming the Feed; naming a retained capability does not add a
production caller.

## Semantic capability surface

The closed semantic catalog has exactly six families:

- Evidence Feed — `live-production`.
- Evidence and Event Structuring — `live-production` (on demand).
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
it defines only `audit.text`, `audit.claims`, and `event.structure`, with no
orchestration, retry, rewrite loop, or runtime registry.

## Accepted invocation contract and Phase 5 plan

The private Host-Agent boundary accepts one UTF-8 JSON request on stdin and
returns one JSON response on stdout; diagnostics belong on stderr. Version 1
defines `audit.text`, `audit.claims`, and `event.structure`. A successful
response carries the bounded deterministic Audit or Event result; typed
invocation errors are separate from capability results. There is no session,
streaming, discovery, registry, remote transport, shared state, automatic
chaining, LLM runtime, or caller for any capability other than on-demand Audit
and Event Structuring.

The activation plan records the verified state: Feed remains live and unchanged;
Audit is `live-production` through its implemented private boundary; Evidence
and Event Structuring is `live-production` through its implemented
`event.structure` operation and remains on demand; Market Analytics and State,
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
schemas/          JSON Schema 2020-12 contracts (logical Feed, typed bundle, Agent invocation)
src/follow_the_money/  live Feed/Audit/Event paths plus retained deterministic libraries
scripts/feed/     minimal internal Feed entry: follow-the-money-feed
scripts/skill/    normal Skill entry: prepare-feed (remote-only consumer)
feeds/            active Feed bundle (feed-manifest.json plus eight typed artifacts)
.feed-state/      repository-backed lock, RateRegistry, lease, and checkpoint
tests/            pytest suite (credential-free)
docs/             architecture, contracts, runbooks
.github/workflows/ hosted CI + active scheduled Feed workflow

Configuration authority and the single resolved Provider contract are documented
in [`docs/configuration.md`](docs/configuration.md).
```

## Quick start

```bash
uv sync --frozen --all-groups
uv run pytest            # full credential-free test suite
scripts/skill/prepare-feed       # normal Skill: canonical logical Feed on stdout
# hosted/development/diagnostic/operator producer check:
scripts/feed/follow-the-money-feed --dry-run
```

## Exit-code contract (minimal internal Feed entry)

- `0` — healthy/degraded Feed success (warnings on stderr/status)
- `1` — generation/publication/schema/integrity failure
- `2` — usage, configuration, or startup-capability error

There is no public user-facing CLI product form: `brief`, `eval`, and
`replay` subcommands and the standalone console script were removed.

## Published Feed consumption

Normal Skill invocation uses only `scripts/skill/prepare-feed`. It resolves
`KadenLiu168/follow-the-money` `main` once through the public Git reference API,
then retrieves `feeds/feed-manifest.json` and exactly its declared artifacts
from that exact commit. Retrieval is credential-free, temporary, and does not
write `feeds/` or `.feed-state/`; the logical Feed contains no transport
metadata or consumer-age policy.

The consumer accepts healthy and valid degraded bundles, preserves their exact
warnings and Provider availability metadata, and rejects `pipeline.status:
failure` or any invalid/incomplete bundle. A remote failure is terminal: there
is no Provider collection, stale local substitution, partial evidence, or local fallback.
The local producer remains available only for hosted Actions,
development, tests, Provider diagnostics, and explicit operator execution.

## Scheduled Feed boundary

GitHub Actions runs the credential-free Feed producer on `ubuntu-latest` at
`20 0 * * *` (08:20 Asia/Shanghai), or through `workflow_dispatch`. It uses
`feeds/` only for the current consumer bundle and `.feed-state/` for
repository-backed runtime state. Normal Skill consumers use the separate
commit-pinned remote entry above; they do not invoke Providers or local
generation. The producer's local loader discovers `feed-manifest.json` first; a
fully validated `latest.json` is read only when the manifest is absent. The first invocation may perform a zero-Provider legacy migration
or bootstrap; normal arming and incomplete-run recovery use the recorded
checkpoint and conservative lease boundary. `evidence_cutoff_at` is captured
from actual runtime, not from the nominal schedule; retrieval and generation
timestamps do not refresh old observations. Checkpoint state owns runtime
continuity; Git history is repository history, not a Feed archive or query API.
Verify Actions `contents: write` and branch policy before calling deployment
operational; Host-Agent consumption and reasoning remain a separate later action.

## Documentation

- `docs/architecture.md` — live Feed path, retained capabilities, future boundary
- `docs/feed-contract.md` — Feed schema, window/cutoff model, publication
- `docs/scoring.md` — deterministic scoring and ranking contract
- Runbooks: `docs/runbooks/`
