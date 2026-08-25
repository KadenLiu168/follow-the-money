# ECO-32 Pre-Agent Baseline Acceptance Traceability

Status: Apply evidence complete; the final Phase-3 acceptance decision is
recorded as accepted below from the completed fresh evidence and gates.
This file is Change-local verification evidence, not a living capability,
runtime manifest, serialized contract, or Agent contract.

## Scope and frozen starting point

- Change: `strengthen-pre-agent-acceptance-gates` (supplied ECO-32 scope).
- Inspected at: `2026-08-25T10:32:31+08:00`.
- Inspected revision: `0281fde0cdc51e0c4a929e33cb375cdbdbb59fdd`.
- Initial worktree state: one untracked in-scope directory,
  `openspec/changes/strengthen-pre-agent-acceptance-gates/`, containing its
  `.openspec.yaml` metadata and four planning artifacts; no unrelated
  modification was present.
- OpenSpec store: none registered (`openspec store list --json` returned an
  empty store list); commands use the nearest repository-local root.
- Active Change set at Apply start: only
  `strengthen-pre-agent-acceptance-gates` (0/22 tasks complete).
- Linear read access: unavailable in this execution environment. The supplied
  ECO-32 scope places this Change after ECO-31 and before Phase 4; no Linear
  mutation was attempted. No dependency or scope conflict was discovered in
  the repository-local active Change set. Linear blocker/status confirmation
  remains an external follow-up, not evidence invented here.

The exact living capability directories inspected are:

- `openspec/specs/deterministic-core-retention/`
- `openspec/specs/feed-evidence-pipeline/`
- `openspec/specs/deterministic-research-engine/`

The expected Apply allowlist is this Change directory only. The living specs,
production source, tests, configuration, Providers, schemas, workflows,
dependencies, generated Feed data, archived Changes, deployment state, and
unrelated worktree content are out of scope.

## Trace legend

Each current Requirement appears exactly once below.

- `Disposition`: `current-positive` means the requirement describes an
  existing current surface; `current-negative` means it is an explicit
  absence, retention, or architecture invariant.
- `Caller status`: `live-production` means the positive production claim has a
  real entry/call path; `retained-no-caller` means the typed deterministic
  library is intentionally retained without production orchestration;
  `negative-invariant` means the row is proved by absence/boundary audit;
  `not-applicable` means caller wiring is not a claim for that row.
- `Focused evidence`: existing executable tests and/or a reproducible static
  audit. Structural OpenSpec validity is never sufficient by itself.
- `Result`: `accepted` is recorded only after the referenced fresh evidence
  and the final semantic review pass; `pending` means row evidence exists but
  the final complete gate/review is not yet closed; `blocked` records an
  evidence gap or contradiction; `rejected` records a current semantic
  contradiction.
- No legend value is runtime metadata and no trace row creates a serialized
  contract.

## Current Requirement inventory

The inventory was extracted from the exact `### Requirement:` headings in the
three living specs at the frozen revision. It contains 38 unique headings:

| # | Capability | Exact current Requirement heading |
|---:|---|---|
| 1 | `deterministic-core-retention` | No embedded LLM runtime |
| 2 | `deterministic-core-retention` | Functional evidence-only Feed with one minimal internal invocation |
| 3 | `deterministic-core-retention` | Deterministic domain rules retained without production wiring |
| 4 | `deterministic-core-retention` | Deterministic provenance, validation, and audit capability retained |
| 5 | `deterministic-core-retention` | OpenSpec living baseline matches the active architecture |
| 6 | `deterministic-core-retention` | Baseline acceptance uses semantic trace evidence |
| 7 | `feed-evidence-pipeline` | Single authoritative production configuration |
| 8 | `feed-evidence-pipeline` | Credential-free verified provider contracts |
| 9 | `feed-evidence-pipeline` | Evidence-backed market mapping contract |
| 10 | `feed-evidence-pipeline` | Verified mappings gate canonical Feed identity |
| 11 | `feed-evidence-pipeline` | Market coverage is bounded by verified runnable capability |
| 12 | `feed-evidence-pipeline` | Durable collection coordination and rate discipline |
| 13 | `feed-evidence-pipeline` | Bounded command deadline and non-cancellable commit |
| 14 | `feed-evidence-pipeline` | Evidence-only deterministic Feed generation |
| 15 | `feed-evidence-pipeline` | Feed is the serialized external contract |
| 16 | `feed-evidence-pipeline` | Bounded canonical evidence and conservative deduplication |
| 17 | `feed-evidence-pipeline` | Provenance tiers and payload-specific time semantics |
| 18 | `feed-evidence-pipeline` | Raw bounded market history |
| 19 | `feed-evidence-pipeline` | Explicit degradation and coverage outcomes |
| 20 | `feed-evidence-pipeline` | Fixed advancing Feed window |
| 21 | `feed-evidence-pipeline` | Durable monotonic publication |
| 22 | `feed-evidence-pipeline` | Minimal internal Feed entry outcomes |
| 23 | `feed-evidence-pipeline` | Feed consumption rejects pipeline failure |
| 24 | `feed-evidence-pipeline` | Deterministic Feed aggregation and normalization |
| 25 | `feed-evidence-pipeline` | Feed semantic identity is separate from execution audit metadata |
| 26 | `feed-evidence-pipeline` | Feed audit timestamps are truthful lifecycle observations |
| 27 | `feed-evidence-pipeline` | Canonical serializer owns published Feed bytes |
| 28 | `feed-evidence-pipeline` | Publication is idempotent by semantic identity |
| 29 | `deterministic-research-engine` | Internal deterministic contracts and wiring status |
| 30 | `deterministic-research-engine` | Immutable evidence ledger |
| 31 | `deterministic-research-engine` | Deterministic entity resolution and candidate grouping |
| 32 | `deterministic-research-engine` | Canonical Event and family utilities |
| 33 | `deterministic-research-engine` | Deterministic market snapshot |
| 34 | `deterministic-research-engine` | Deterministic breadth, surprise, and Market State |
| 35 | `deterministic-research-engine` | Deterministic confidence and watchlist rules |
| 36 | `deterministic-research-engine` | Versioned deterministic scoring |
| 37 | `deterministic-research-engine` | Deterministic ranking and family penalty |
| 38 | `deterministic-research-engine` | Deterministic safety audit retained without orchestration |

The three-source heading count is 6 core + 22 Feed + 10 research = 38. There
are no duplicate headings across the current capabilities and no invented
heading.

## MODIFIED requirement inheritance check

The Change-local `MODIFIED` Requirement is named exactly
`Baseline acceptance uses semantic trace evidence`. Before evaluating the new
acceptance behavior, the three inherited scenarios were compared against the
current living block at `openspec/specs/deterministic-core-retention/spec.md`:

1. `Structural validation passes with stale semantics`
2. `Requirement trace is complete`
3. `Change scope is reviewed`

Each inherited scenario's name and `WHEN`/`THEN` content is preserved in the
Change-local delta; the comparison differed only by a trailing separator blank
line after the third inherited scenario. The delta then adds only the five new scenarios:
`Complete Pre-Agent baseline is evaluated`, `Production and retained caller
states are distinguished`, `Historical trace evidence is reused`, `Acceptance
evidence reveals a gap`, and `Future Skill-Agent contract remains deferred`.

## Fresh semantic trace

The following rows were re-derived from the current living specs and current
repository surfaces. Row-level `accepted` means the cited focused evidence is
currently sufficient for that row; the overall Phase-3 decision was recorded
only after the repository-wide and structural gates plus final review passed.

### `deterministic-core-retention`

| # | Requirement | Disposition | Implementation / invariant | Caller status | Focused executable or static evidence | Result |
|---:|---|---|---|---|---|---|
| 1 | No embedded LLM runtime | `current-negative` | `pyproject.toml`, `uv.lock`, `config/`, `.env.example`, package/import surface; removed modules/schemas and prompt/evaluation directories remain absent | `negative-invariant` | `tests/test_no_llm_contract.py`; `tests/test_workflows.py`; repository search for SDK, credential, prompt, model, and request surfaces | accepted |
| 2 | Functional evidence-only Feed with one minimal internal invocation | `current-positive` | `scripts/feed/follow-the-money-feed` forwards to `follow_the_money.feed.cli`; `feed/cli.py`, `feed/validate.py`, `feed/publish.py` provide typed exits, identity/provenance, schema validation, and dry-run/publication behavior | `live-production` | `tests/test_no_llm_contract.py`; `tests/test_feed_cli.py`; `tests/test_feed_pipeline.py`; `tests/test_gate_13_1.py`; `tests/test_workflows.py` | accepted |
| 3 | Deterministic domain rules retained without production wiring | `current-negative` | `scoring.py`, `selection.py`, and `audit.py` are retained typed libraries; Feed closure does not import them and no synthetic analysis inputs are supplied | `retained-no-caller` | `tests/test_scoring.py`; `tests/test_neutralize_selection_and_scoring_contract.py`; `tests/test_audit.py`; import-closure probe returned `[]` | accepted |
| 4 | Deterministic provenance, validation, and audit capability retained | `current-positive` plus retained internal capability | `canonical.py`, `schema.py`, `boundary.py`, `feed/validate.py`, `audit.py`, ledger/candidate/market/watchlist/scoring/ranking typed modules | `live-production` for Feed; `retained-no-caller` for post-Feed libraries | `tests/test_feed_boundary.py`; `tests/test_feed_determinism.py`; `tests/test_events.py`; `tests/test_engine.py`; `tests/test_market_snapshot.py`; `tests/test_audit.py` | accepted |
| 5 | OpenSpec living baseline matches the active architecture | `current-negative` | The three living specs plus the sole active Change describe Providers -> Feed -> Host Agent reasoning, retained no-caller libraries, and deferred future contract; no positive embedded runtime/fixed Agent topology | `negative-invariant` | `openspec doctor`; strict Change/all validation; current-facing docs and forbidden-surface audit recorded below | accepted |
| 6 | Baseline acceptance uses semantic trace evidence | `current-positive` process boundary | This Change-local trace contains the 38-row inventory, caller states, executable/static evidence, historical dispositions, and final gate record; it creates no runtime metadata | `not-applicable` | This file; focused suites; canonical quality gate; OpenSpec structural gates; final semantic review | accepted |

### `feed-evidence-pipeline`

| # | Requirement | Disposition | Implementation / invariant | Caller status | Focused executable or static evidence | Result |
|---:|---|---|---|---|---|---|
| 7 | Single authoritative production configuration | `current-positive` | `config/load.py`, `config/model.py`, `config/config.yaml`, `config/providers.yaml`; Provider manifest authority and coverage matrix are resolved before normal execution | `live-production` | `tests/test_config.py`; `tests/test_config_provider_normalization.py`; `tests/test_provider_contract.py`; `tests/test_gate_13_1.py` | accepted |
| 8 | Credential-free verified provider contracts | `current-positive` | `providers/manifest.py`, `providers/adapters.py`, `providers/urls.py`, `config/load.py`; resolved verified Provider contract drives adapters, URLs, limits, rate, coverage, and snapshots | `live-production` | `tests/test_provider_contract.py`; `tests/test_config.py`; `tests/test_config_provider_normalization.py`; `tests/test_adapters.py`; `tests/test_gate_13_1.py` | accepted |
| 9 | Evidence-backed market mapping contract | `current-positive` | Manifest-owned `role_mappings`, mapping verification provenance, repository-bound fixtures, exact tuple and Yahoo `meta.symbol` checks in `config/load.py` and `providers/manifest.py` | `live-production` | `tests/test_provider_contract.py`; `tests/test_config_provider_normalization.py`; `tests/test_market_snapshot.py`; `tests/test_gate_13_1.py` | accepted |
| 10 | Verified mappings gate canonical Feed identity | `current-positive` | Resolved verified mappings and `provider_contracts` snapshot gate market capability; `market/snapshot.py` fails closed on unverified mappings; Feed identity uses canonical validated content | `live-production` | `tests/test_market_snapshot.py`; `tests/test_feed_boundary.py`; `tests/test_feed_determinism.py`; `tests/test_gate_13_1.py` | accepted |
| 11 | Market coverage is bounded by verified runnable capability | `current-positive` | Coverage matrix validation in `config/load.py`; `feed/plan.py` and `engine/feed_health.py` assess only verified runnable memberships and explicit disabled/optional policy | `live-production` | `tests/test_config_provider_normalization.py`; `tests/test_provider_contract.py`; `tests/test_feed_pipeline.py`; `tests/test_gate_13_1.py` | accepted |
| 12 | Durable collection coordination and rate discipline | `current-positive` | `providers/lock.py`, `providers/rate.py`, `providers/http.py`, and `feed/cli.py` coordinate lock, durable debit/reconcile, scope serialization, retry, and production dry-run behavior | `live-production` | `tests/test_provider_contract.py`; `tests/test_gate_13_1.py`; `tests/test_gate_13_2.py`; `tests/test_feed_cli.py` | accepted |
| 13 | Bounded command deadline and non-cancellable commit | `current-positive` | `feed/cli.py` anchors monotonic deadline/reserve; `feed/publish.py` checks reversible staging before admission and completes admitted rename/fsync without cancellation | `live-production` | `tests/test_gate_13_1.py`; `tests/test_gate_13_2.py`; `tests/test_feed_cli.py` | accepted |
| 14 | Evidence-only deterministic Feed generation | `current-positive` | Provider adapters normalize bounded evidence; `feed/validate.py` rejects intelligence fields; CLI path contains no LLM or analysis orchestration | `live-production` | `tests/test_feed_boundary.py`; `tests/test_adapters.py`; `tests/test_no_llm_contract.py`; `tests/test_gate_13_1.py` | accepted |
| 15 | Feed is the serialized external contract | `current-positive` | `schemas/feed.schema.json`, `schema.py`, `boundary.py`, `canonical.py`, `feed/validate.py`, and publication validation own schema/semantic/identity/digest checks | `live-production` | `tests/test_feed_boundary.py`; `tests/test_boundary.py`; `tests/test_feed_pipeline.py`; `tests/test_gate_13_2.py` | accepted |
| 16 | Bounded canonical evidence and conservative deduplication | `current-positive` | `unicode.py`, adapters, `feed/dedupe.py`, URL/source identity and numeric/schema validators enforce bounded normalized evidence, same-source near dedupe, and cross-source lineage | `live-production` | `tests/test_dedupe.py`; `tests/test_provider_contract.py`; `tests/test_adapters.py`; `tests/test_feed_boundary.py` | accepted |
| 17 | Provenance tiers and payload-specific time semantics | `current-positive` | Adapter normalization and Feed validation preserve provider/source/tier/kind/URL/knowledge/effective/retrieval/precision fields and apply cutoff rules by payload | `live-production` | `tests/test_adapters.py`; `tests/test_feed_boundary.py`; `tests/test_market_snapshot.py`; `tests/test_gate_13_1.py` | accepted |
| 18 | Raw bounded market history | `current-positive` | `YahooMarketAdapter` preserves bounded raw observations, units, sessions, availability, and missingness; snapshot consumes raw history without serializing interpretation | `live-production` for acquisition; `retained-no-caller` for analytics consumer | `tests/test_adapters.py`; `tests/test_market_snapshot.py`; `tests/test_market.py` | accepted |
| 19 | Explicit degradation and coverage outcomes | `current-positive` | `feed/plan.py`, `engine/feed_health.py`, and CLI retain accepted/rejected/provider/coverage outcomes, partial/degraded semantics, and fail on zero accepted evidence | `live-production` | `tests/test_feed_pipeline.py`; `tests/test_engine.py`; `tests/test_gate_13_1.py`; `tests/test_feed_cli.py` | accepted |
| 20 | Fixed advancing Feed window | `current-positive` | Lock-before-cutoff planning in `feed/plan.py`/`feed/cli.py`; latest validation, bootstrap/gap policy, half-open window, and strict cutoff advancement | `live-production` | `tests/test_feed_pipeline.py`; `tests/test_gate_13_2.py`; `tests/test_feed_cli.py` | accepted |
| 21 | Durable monotonic publication | `current-positive` | `feed/publish.py` owns validated candidate admission, create-only dated artifact, same-parent staging, fsync, atomic latest replacement, monotonic ownership, and failure recovery | `live-production` | `tests/test_feed_pipeline.py`; `tests/test_feed_determinism.py`; `tests/test_gate_13_2.py` | accepted |
| 22 | Minimal internal Feed entry outcomes | `current-positive` | Exactly one wrapper plus `feed.cli.main`; typed `FeedInputError`/`FeedExecutionError`, parser exit 2, and dry-run no-publication contract | `live-production` | `tests/test_feed_cli.py`; `tests/test_no_llm_contract.py`; `tests/test_workflows.py` | accepted |
| 23 | Feed consumption rejects pipeline failure | `current-positive` retained consumer boundary | `engine/feed_health.py` separates structural validity from healthy/degraded consumability and rejects `pipeline.status == failure` | `retained-no-caller`; no Feed or downstream Agent entry calls this library | `tests/test_engine.py`; `tests/test_feed_boundary.py`; source call-site and Feed import-closure audit | accepted |
| 24 | Deterministic Feed aggregation and normalization | `current-positive` | `feed/cli.py`, `feed/plan.py`, and `feed/dedupe.py` order provider outcomes by ID and items by `(knowledge_available_at, id)` before survivor/lineage/final serialization | `live-production` | `tests/test_feed_determinism.py`; `tests/test_feed_pipeline.py` | accepted |
| 25 | Feed semantic identity is separate from execution audit metadata | `current-positive` | `feed/validate.py` and `canonical.py` own explicit semantic projection, digest, and cutoff-derived run identity; runtime timestamps are excluded from semantic identity | `live-production` | `tests/test_feed_determinism.py`; `tests/test_feed_boundary.py` | accepted |
| 26 | Feed audit timestamps are truthful lifecycle observations | `current-positive` | `feed/cli.py` captures collection start, cutoff, provider return, completion, and generation at observed lifecycle boundaries, retaining null retrieval for no response | `live-production` | `tests/test_feed_determinism.py`; `tests/test_feed_boundary.py`; `tests/test_gate_13_2.py` | accepted |
| 27 | Canonical serializer owns published Feed bytes | `current-positive` | Shared `canonical_bytes()` is used by Feed production and `feed/publish.py`; publication rejects non-canonical candidate bytes | `live-production` | `tests/test_feed_determinism.py`; `tests/test_feed_pipeline.py` | accepted |
| 28 | Publication is idempotent by semantic identity | `current-positive` | `feed/publish.py` validates existing dated semantic identity, retains immutable stored bytes, repairs latest from retained bytes, and fails closed on mismatch | `live-production` | `tests/test_feed_determinism.py`; `tests/test_feed_pipeline.py`; `tests/test_gate_13_2.py` | accepted |

### `deterministic-research-engine`

| # | Requirement | Disposition | Implementation / invariant | Caller status | Focused executable or static evidence | Result |
|---:|---|---|---|---|---|---|
| 29 | Internal deterministic contracts and wiring status | `current-negative` plus retained library | `ledger.py`, `engine/`, `events.py`, `market/`, `state.py`, `watchlist.py`, `scoring.py`, `selection.py`, `audit.py` are typed/tested; Feed path does not import post-Feed modules | `retained-no-caller` | `tests/test_engine.py`; `tests/test_events.py`; `tests/test_market.py`; `tests/test_market_snapshot.py`; `tests/test_state.py`; `tests/test_scoring.py`; `tests/test_audit.py`; closure probe | accepted |
| 30 | Immutable evidence ledger | `current-positive` library | Frozen `LedgerEntry`/`Ledger`, stable fact IDs, duplicate rejection, typed origin/lineage/conflict fields in `ledger.py` and `events.py` | `retained-no-caller` | `tests/test_events.py` | accepted |
| 31 | Deterministic entity resolution and candidate grouping | `current-positive` library | `engine/entities.py`, `engine/candidates.py`, and title utilities implement registry membership, exact boundaries, deterministic Components/grouping, and no transport envelope/packing | `retained-no-caller` | `tests/test_engine.py`; `tests/test_neutralize_selection_and_scoring_contract.py` | accepted |
| 32 | Canonical Event and family utilities | `current-positive` library | `events.py` derives stable Event IDs, key facts, knowledge times, family IDs, unordered pairs, and display labels from typed ledger facts | `retained-no-caller` | `tests/test_events.py` | accepted |
| 33 | Deterministic market snapshot | `current-positive` library | `market/snapshot.py` and `market/formulas.py` use verified mappings, bounded sessions/history, Decimal formulas, explicit unknown reasons, and evidence IDs | `retained-no-caller` | `tests/test_market.py`; `tests/test_market_snapshot.py` | accepted |
| 34 | Deterministic breadth, surprise, and Market State | `current-positive` library | `market/surprise.py`, `market/snapshot.py`, and `state.py` provide deterministic votes, coverage, tie-breaking, and informational regime with no scoring effect | `retained-no-caller` | `tests/test_market.py`; `tests/test_market_snapshot.py`; `tests/test_state.py` | accepted |
| 35 | Deterministic confidence and watchlist rules | `current-positive` library | `market/confidence.py` and `watchlist.py` implement tier/family/conflict confidence, horizon filtering, deterministic order, and sparse outcomes | `retained-no-caller` | `tests/test_market.py`; `tests/test_state.py` | accepted |
| 36 | Versioned deterministic scoring | `current-positive` library | `scoring.py` and `market/formulas.py` own closed maps, weights, Decimal context, freshness, relevance, priority, and neutral configuration names | `retained-no-caller` | `tests/test_scoring.py`; `tests/test_neutralize_selection_and_scoring_contract.py`; `tests/test_no_llm_contract.py` | accepted |
| 37 | Deterministic ranking and family penalty | `current-positive` library | `selection.py` applies closed confidence/coverage eligibility, frozen ordering, family penalty/pair exemption, stable ties, and no historical Brief limits | `retained-no-caller` | `tests/test_scoring.py`; `tests/test_neutralize_selection_and_scoring_contract.py` | accepted |
| 38 | Deterministic safety audit retained without orchestration | `current-positive` library plus negative boundary | `audit.py` exposes typed workflow-neutral text/structured audit, fail-closed identity/evidence/ownership checks, and no rewrite/orchestration | `retained-no-caller` | `tests/test_audit.py`; `tests/test_no_llm_contract.py`; audit boundary/static caller assertions | accepted |

## Minimal Feed entry and caller-graph audit

The actual current entry is `scripts/feed/follow-the-money-feed`, which
executes `uv run python -m follow_the_money.feed.cli`. The repository's checked
workflow and quality-gate call sites are `.github/workflows/test.yml`,
`.github/workflows/generate-feed.yml`, and `scripts/quality_gate.py`; the CLI
itself calls `run_feed()` and no other production entry is exposed. The parser
has no subparser and `pyproject.toml` has no `[project.scripts]` section.

The current Feed/provider/config import surfaces contain no imports of
`ledger`, `events`, `engine`, `market`, `watchlist`, `scoring`, `selection`, or
`audit`. The reproducible probe

```text
.venv/bin/python -c 'import sys; import follow_the_money.feed.cli; names=[n for n in sys.modules if n == "follow_the_money.ledger" or n.startswith(("follow_the_money.events", "follow_the_money.engine", "follow_the_money.market", "follow_the_money.watchlist", "follow_the_money.scoring", "follow_the_money.selection", "follow_the_money.audit"))]; print(names)'
```

returned `[]`. The retained-library tests independently assert no Feed or
production call into retained scoring/ranking, and audit tests assert no Feed
or entry-path auditor wiring. A source call-site search likewise finds
`engine/feed_health.py` only in focused tests, not in a production entry.
Therefore every row marked `live-production` above has an actual caller, while
retained Feed consumption, ledger, candidate/event,
market/state, watchlist, scoring/ranking, and `ClaimAuditor` capabilities are
explicitly `retained-no-caller`; no placeholder or synthetic wiring was added.

## Historical and superseded disposition

The archived `2026-08-14-normalize-openspec-baseline/traceability.md` was used
only as seed material. Its historical rows were reconciled against the current
living headings, current source/tests, all later archived Changes listed below,
and the caller probe. The following exact former Requirement headings remain
explicitly `historical-superseded`; none is a current requirement and the
archived files were not edited.

| Historical capability / source | Explicit historical-superseded Requirement headings |
|---|---|
| `multi-component-resolver-block-processing` | Item-level resolver component ownership; Atomic block-wide semantic validation; Complete multi-component Event construction; Component-local family and coexistence boundaries; Unresolved resolver audit retention; Deterministic recording and replay |
| `production-story-family-resolution` | Resolver family semantics are materialized into canonical Events; Coexistence relations are validated and canonicalized fail closed; Production selection consumes canonical family and pair data; Family behavior is deterministic across live and replay execution |
| `production-market-state-pipeline` | Verified bounded daily market history; Explicit role session ownership and completed-observation eligibility; Single deterministic market snapshot; Deterministic breadth and macro-surprise inputs; Production classification before narrative explanation; Evidence-bounded editor explanation and authoritative merge; Informational non-effect and production-path regression proof |
| historical `feed-evidence-pipeline` from `implement-follow-the-money-repository` | Configured evidence providers; Evidence-only Feed generation; Unified envelope and typed payload; Bounded evidence content; Stable identity and conservative deduplication; Source tiers and provenance; Raw lookback observations; Payload-specific temporal semantics; Graceful provider degradation; Actual Feed window and freshness metadata; Auditable publication; Feed CLI outcome contract |
| `deterministic-evidence-engine` | Latest Feed consumption and health assessment; Deterministic normalization and entity resolution; High-recall filtering and candidate blocking; Evidence Ledger construction; Deterministic market analytics; Deterministic surprise calculation; Reaction observability; Evidence confidence and conflicts; Targeted verification packet |
| `semantic-event-resolution` | Single configured LLM runtime; Typed LLM failure state machine; Untrusted evidence isolation; Candidate-block-only resolver input; Atomic event extraction; Resolver abstention; Resolver scope restrictions; Closed story-family and coexistence semantics; Evidence-bound event facts; Script-assigned canonical identity; Structured output enforcement |
| `event-analysis-and-ranking` | Verified-packet financial analysis; Fact, mechanism, and implication separation; Bounded reaction attribution; Evidence-bound price-in assessment; Money-flow classification; Safe asset mapping; Categorical semantic scoring features; Versioned v1 scoring contract; Deterministic event significance; Deterministic morning relevance; Confidence gates; Deterministic final selection; Story-family redundancy control |
| `brief-synthesis-and-audit` | Fixed Morning Brief structure; Compact market dashboard; Data-derived market regime; Tiered event detail; Conditional flow section; Focused 24-hour watchlist; Concise Bottom Line; Structured synthesis and deterministic Markdown; Deterministic claim audit; LLM language audit; Investment-assistance safety boundary; Visible degraded and stale state; Brief CLI and replay outcomes; Separate deterministic degraded report; Replayable run audit bundle |
| `regression-evaluation` | Versioned golden-day dataset; Required scenario coverage; Core evaluation metrics; Ranking stability; Offline deterministic execution; Regression dimensions; Explicit credentialed prompt and model evaluation; Machine-readable and human-readable reports; Validation before scoring |

Subsequent archived Changes were reconciled as follows:

| Archived Change | Current effect and disposition |
|---|---|
| `2026-08-15-make-feed-deterministic-and-truthful` | Its Feed ordering, semantic identity, truthful timestamps, canonical bytes, and idempotent publication deltas are current rows 24–28; current implementation and tests supersede the archived delta wording. |
| `2026-08-23-normalize-config-and-provider-contracts` | Its authoritative configuration, resolved Provider contract, coverage, URL, rate, and startup deltas are current rows 7–12; the archived Change remains history. |
| `2026-08-24-align-scoring-decimal-contract` | Its Decimal/scoring contract is represented by current rows 36–37 and current scoring tests; no production caller was introduced. |
| `2026-08-24-enforce-owned-decimal-context-in-scoring-components` | Its owned Decimal context is represented by current rows 33–37 and current market/scoring tests; no production wiring was introduced. |
| `2026-08-24-enforce-verified-market-mappings` | Its verified mapping/provenance and fail-closed market snapshot behavior are represented by current rows 9–11 and 33; no second registry or caller was introduced. |
| `2026-08-24-neutralize-selection-and-scoring-contract` | Its removal of Brief/morning aliases and neutral ranking contract is represented by current rows 36–37; retained libraries remain no-caller. |
| `2026-08-24-remove-resolver-transport-residue` | Its Components-only candidate boundary is represented by current row 31; no Resolver transport or production caller was restored. |
| `2026-08-25-align-pre-agent-living-baseline` | It established the current three-capability set and current-facing no-LLM/Future boundary; current rows 1, 5, 6 and this fresh trace revalidate those claims. |
| `2026-08-25-generalize-deterministic-audit-boundary` | Its workflow-neutral typed audit boundary is represented by current row 38 and current audit tests; no Agent schema, runtime, or production caller was added. |

## Current-facing documentation and architecture audit

The current-facing `AGENTS.md`, `SKILL.md`, `README.md`,
`README.zh-CN.md`, `docs/architecture.md`, `docs/feed-contract.md`,
`docs/configuration.md`, `docs/scoring.md`, `docs/validation-evidence.md`, and
both runbooks were inspected. They consistently describe Evidence Providers ->
deterministic Feed -> Host Agent reasoning, credential-free operation, Feed as
the evidence boundary, retained post-Feed libraries with no current caller,
and the future Skill-Agent Contract as undefined/deferred. They do not
positively define an Agent-facing object, serialized Agent schema, runtime,
invocation protocol, fixed orchestration topology, embedded LLM, public CLI
product, or automatic trading capability.

Historical terminology found in source comments/docstrings or archived Change
text is not treated as a current positive contract. Current tests and the
caller probe reject actual runtime/import/wiring surfaces; no documentation or
architecture contradiction requiring out-of-scope edits was found.

## Existing executable evidence

All commands below were run against the frozen revision plus only the
Change-local trace/task edits. No real-network Feed dry run was used.

| Evidence category | Exact command | Result |
|---|---|---|
| Locked environment | `uv sync --frozen --all-groups` | exit 0; package rebuilt/installed |
| Production Feed focused regressions | `.venv/bin/python -m pytest -q tests/test_gate_13_1.py tests/test_gate_13_2.py tests/test_feed_determinism.py tests/test_feed_boundary.py tests/test_feed_pipeline.py tests/test_feed_cli.py tests/test_provider_contract.py tests/test_workflows.py` | exit 0; 205 collected and all reached 100% |
| Retained-library focused regressions | `.venv/bin/python -m pytest -q tests/test_engine.py tests/test_events.py tests/test_market.py tests/test_market_snapshot.py tests/test_state.py tests/test_scoring.py tests/test_neutralize_selection_and_scoring_contract.py tests/test_audit.py` | exit 0; 222 collected and all reached 100% |
| Architecture/no-LLM regressions | `.venv/bin/python -m pytest -q tests/test_no_llm_contract.py tests/test_workflows.py tests/test_neutralize_selection_and_scoring_contract.py tests/test_audit.py` | exit 0; 64 collected and all reached 100% |

The canonical repository-wide command was:

```text
.venv/bin/python scripts/quality_gate.py
```

It exited 0 and printed `quality gate passed`. Its fresh run reached 100% on
the 607-test repository suite, then passed `scripts/validate_workflows.py`,
CLI help, Ruff check, Ruff format check (`67 files already formatted`), mypy
(`Success: no issues found in 41 source files`), and the offline wheel build.

The required structural commands also exited 0:

| Gate | Actual result |
|---|---|
| `openspec doctor` | Root and OpenSpec root both `ok`; no references declared |
| `openspec validate strengthen-pre-agent-acceptance-gates --strict` | Change is valid |
| `openspec validate --all --strict` | 4 passed, 0 failed (3 living specs + this Change) |

## Final diff and allowlist review

After the gates, `git status --short --untracked-files=all` listed only these
Change-local paths:

- `openspec/changes/strengthen-pre-agent-acceptance-gates/.openspec.yaml`
- `openspec/changes/strengthen-pre-agent-acceptance-gates/design.md`
- `openspec/changes/strengthen-pre-agent-acceptance-gates/proposal.md`
- `openspec/changes/strengthen-pre-agent-acceptance-gates/specs/deterministic-core-retention/spec.md`
- `openspec/changes/strengthen-pre-agent-acceptance-gates/tasks.md`
- `openspec/changes/strengthen-pre-agent-acceptance-gates/traceability.md`

`git diff --name-only` and `git diff --cached --name-only` were empty because
the Change is still untracked; the explicit untracked allowlist above contains
all worktree paths. Change-local trailing-whitespace search returned `none`.
No living spec, production code, test, configuration, Provider, schema,
financial formula, workflow, dependency, CI/deployment file, generated Feed,
archived Change, or unrelated worktree path changed. No real-network dry run,
Linear mutation, archive, commit, or push was performed.

## Scope and acceptance gate record

The final semantic review found no conflict among the supplied ECO-32 scope,
the 38 living Requirements, current implementation/tests/caller graph, current
facing docs, and the architecture boundary. Every row has current focused or
static evidence; every positive production claim has a real caller; every
retained post-Feed capability remains explicitly no-caller; and no future
Skill-Agent contract or runtime surface was introduced.

Final Phase-3 decision: **accepted**. All 38 current rows are accepted, the
focused regressions and 607-test canonical gate passed, all required OpenSpec
structural gates passed, and the final semantic/diff review found no
contradiction or unresolved evidence gap. Living-spec synchronization, Linear
status changes, archive, commit, push, and Phase-4 Skill-Agent Contract work
remain untouched and require separate authorization.
