# Normalize OpenSpec Baseline Trace Matrix

Status: Apply evidence, including a pre-Apply snapshot and post-task updates.
Date: 2026-08-13. This file is Change-local evidence; it is not a production
contract.

## Scope and pre-Apply inventory

The inventory was captured with `openspec list --json`, `openspec status
--change normalize-openspec-baseline --json`, `openspec instructions apply
--change normalize-openspec-baseline --json`, `find`, `rg`, and `git status`.
The project currently has two active Changes:

| Active Change | Status | Disposition at baseline normalization |
|---|---|---|
| `normalize-openspec-baseline` | 20 tasks, 0 complete | Current Apply scope |
| `implement-follow-the-money-repository` | 121 tasks, 121 complete | Superseded historical-only content; archive requires the separate authorization recorded in task 2.3 |

The pre-Apply canonical living capability set is:

- `deterministic-core-retention`
- `multi-component-resolver-block-processing`
- `production-story-family-resolution`
- `production-market-state-pipeline`

The intended post-Apply canonical set is exactly:

- `deterministic-core-retention`
- `feed-evidence-pipeline`
- `deterministic-research-engine`

The pre-Apply Change-local allowlist is the existing
`openspec/changes/normalize-openspec-baseline/` artifacts plus this matrix. The
planned implementation allowlist is limited to that Change's artifacts,
`openspec/specs/deterministic-core-retention/spec.md`, the two newly materialized
canonical specs, deletion of the three named stale living capability directories,
and, only after separate authorization, the archive operation for
`implement-follow-the-money-repository`. No source, test, configuration, schema,
provider manifest, workflow, generated Feed, dependency, deployment, or unrelated
file is in scope.

The unrelated pre-existing worktree state is preserved: `AUDIT-2026-08-12.md` is
deleted, with HEAD blob `3e77e2f702a4a0cb66bbb48f5481980e1b31cc14`, and is not part
of this Change.

At the post-task-2.3 snapshot, before the remediation Change was created, the only
active Change was `normalize-openspec-baseline`. The completed original Change was archived with
the exact command `openspec archive implement-follow-the-money-repository
--skip-specs` to
`openspec/changes/archive/2026-08-13-implement-follow-the-money-repository/`.
The CLI reported `Skipping spec updates (--skip-specs flag provided)`. A search
of `openspec/specs/` found none of its six original delta capabilities:
`brief-synthesis-and-audit`, `deterministic-evidence-engine`,
`event-analysis-and-ranking`, `feed-evidence-pipeline`,
`regression-evaluation`, or `semantic-event-resolution`.

## Current and active requirement disposition

The following inventory includes every current living requirement and every
requirement heading in the two active Changes at the pre-Apply snapshot. A
requirement listed as `historical-only` is not a current contract; it must not be
synced into canonical specs.

### Current living specs

| Capability | Requirement inventory | Disposition and evidence |
|---|---|---|
| `deterministic-core-retention` | `No embedded LLM runtime`; `Functional evidence-only Feed with one minimal internal invocation`; `Deterministic domain rules retained without production wiring`; `Deterministic provenance, validation, and audit capability retained` | Current. The post-runtime-removal contract is implemented by the minimal Feed entry and retained tested libraries. The two additional baseline-integrity requirements in this Change extend, but do not replace, these four requirements. |
| `multi-component-resolver-block-processing` | `Item-level resolver component ownership`; `Atomic block-wide semantic validation`; `Complete multi-component Event construction`; `Component-local family and coexistence boundaries`; `Unresolved resolver audit retention`; `Deterministic recording and replay` | Superseded and scheduled for living-directory deletion. The exact capability is archived at `openspec/changes/archive/2026-08-12-fix-multi-component-resolver-blocks/`; its resolver, Bundle, replay, and LLM-era production claims have no current caller. |
| `production-story-family-resolution` | `Resolver family semantics are materialized into canonical Events`; `Coexistence relations are validated and canonicalized fail closed`; `Production selection consumes canonical family and pair data`; `Family behavior is deterministic across live and replay execution` | Superseded and scheduled for living-directory deletion. The exact historical Change is archived at `openspec/changes/archive/2026-08-12-restore-production-story-family-resolution/`; pure Event/family utilities survive under `deterministic-research-engine`, without live/replay wiring. |
| `production-market-state-pipeline` | `Verified bounded daily market history`; `Explicit role session ownership and completed-observation eligibility`; `Single deterministic market snapshot`; `Deterministic breadth and macro-surprise inputs`; `Production classification before narrative explanation`; `Evidence-bounded editor explanation and authoritative merge`; `Informational non-effect and production-path regression proof` | Superseded and scheduled for living-directory deletion. The exact historical Change is archived at `openspec/changes/archive/2026-08-13-activate-production-market-state-pipeline/`; market utilities survive under `deterministic-research-engine`, without editor, Brief, Bundle, replay, or production orchestration claims. |

### Completed original Change (pre-Apply inventory)

All requirements below are `historical-only` for the normalized baseline. They
describe the original script-first/LLM-last proposal and implementation record;
they are not current requirements. The completed Change is now preserved at the
archive path recorded above and was not synced into canonical specs.

| Capability | Every requirement heading in the active Change | Disposition and evidence |
|---|---|---|
| `feed-evidence-pipeline` | `Configured evidence providers`; `Evidence-only Feed generation`; `Unified envelope and typed payload`; `Bounded evidence content`; `Stable identity and conservative deduplication`; `Source tiers and provenance`; `Raw lookback observations`; `Payload-specific temporal semantics`; `Graceful provider degradation`; `Actual Feed window and freshness metadata`; `Auditable publication`; `Feed CLI outcome contract` | Historical-only. The implemented subset is traced below from current `src/follow_the_money/feed`, `providers`, `schema.py`, and focused tests; current wording is represented only by this Change's new Feed spec. |
| `deterministic-evidence-engine` | `Latest Feed consumption and health assessment`; `Deterministic normalization and entity resolution`; `High-recall filtering and candidate blocking`; `Evidence Ledger construction`; `Deterministic market analytics`; `Deterministic surprise calculation`; `Reaction observability`; `Evidence confidence and conflicts`; `Targeted verification packet` | Historical-only. Retained deterministic pieces are traced below; the former downstream Brief/analyst pipeline and production caller claims are not current. |
| `semantic-event-resolution` | `Single configured LLM runtime`; `Typed LLM failure state machine`; `Untrusted evidence isolation`; `Candidate-block-only resolver input`; `Atomic event extraction`; `Resolver abstention`; `Resolver scope restrictions`; `Closed story-family and coexistence semantics`; `Evidence-bound event facts`; `Script-assigned canonical identity`; `Structured output enforcement` | Historical-only and superseded by removal of the embedded runtime. No LLM SDK, prompt, model credential, resolver request, or resolver entry path exists in the current production tree; pure Event/family identity helpers are traced below. |
| `event-analysis-and-ranking` | `Verified-packet financial analysis`; `Fact, mechanism, and implication separation`; `Bounded reaction attribution`; `Evidence-bound price-in assessment`; `Money-flow classification`; `Safe asset mapping`; `Categorical semantic scoring features`; `Versioned v1 scoring contract`; `Deterministic event significance`; `Deterministic morning relevance`; `Confidence gates`; `Deterministic final selection`; `Story-family redundancy control` | Historical-only. Typed scoring/selection libraries remain tested, but their analysis inputs are caller-supplied and no current Feed entry orchestrates them. |
| `brief-synthesis-and-audit` | `Fixed Morning Brief structure`; `Compact market dashboard`; `Data-derived market regime`; `Tiered event detail`; `Conditional flow section`; `Focused 24-hour watchlist`; `Concise Bottom Line`; `Structured synthesis and deterministic Markdown`; `Deterministic claim audit`; `LLM language audit`; `Investment-assistance safety boundary`; `Visible degraded and stale state`; `Brief CLI and replay outcomes`; `Separate deterministic degraded report`; `Replayable run audit bundle` | Historical-only. The current repository has no production Brief, editor, language-audit, Bundle, replay, or public Brief CLI path. `ClaimAuditor` remains a tested library only. |
| `regression-evaluation` | `Versioned golden-day dataset`; `Required scenario coverage`; `Core evaluation metrics`; `Ranking stability`; `Offline deterministic execution`; `Regression dimensions`; `Explicit credentialed prompt and model evaluation`; `Machine-readable and human-readable reports`; `Validation before scoring` | Historical-only. No live model evaluation or original evaluation workflow is a current contract; current quality evidence is repository/test evidence only. |

### This Change's proposed requirements

The requirements below are `current` after Apply materialization, subject to the
remaining structural and semantic gates. Their implementation and focused-test
trace is recorded in the next section.

The post-materialization structural checks passed: the three stale living spec
files and their now-empty directories were removed; canonical living directories
are exactly `deterministic-core-retention`, `feed-evidence-pipeline`, and
`deterministic-research-engine`; no empty capability directory remains; the two
new canonical specs have the same requirement-heading set as their Change-local
deltas; and the canonical Feed spec contains no whole-word `public`, `model`,
`Brief`, `Bundle`, `replay`, `Agent`, or `LLM` term. Existing
`deterministic-core-retention` requirements and scenarios were preserved, with
only the two new requirements appended.

| Capability | Requirement inventory | Disposition |
|---|---|---|
| `feed-evidence-pipeline` | `Credential-free verified provider contracts`; `Durable collection coordination and rate discipline`; `Bounded command deadline and non-cancellable commit`; `Evidence-only deterministic Feed generation`; `Feed is the serialized external contract`; `Bounded canonical evidence and conservative deduplication`; `Provenance tiers and payload-specific time semantics`; `Raw bounded market history`; `Explicit degradation and coverage outcomes`; `Fixed advancing Feed window`; `Durable monotonic publication`; `Minimal internal Feed entry outcomes` | Current canonical Feed contract, traced below. |
| `deterministic-research-engine` | `Internal deterministic contracts and wiring status`; `Immutable evidence ledger`; `Deterministic entity resolution and candidate grouping`; `Canonical Event and family utilities`; `Deterministic market snapshot`; `Deterministic breadth, surprise, and Market State`; `Deterministic confidence and watchlist rules`; `Versioned deterministic scoring`; `Deterministic selection and family penalty`; `Deterministic safety audit retained without orchestration` | Current canonical retained-library contract, traced below. |
| `deterministic-core-retention` | `OpenSpec living baseline matches the active architecture`; `Baseline acceptance uses semantic trace evidence` | Current baseline-integrity guardrail, with the four existing post-runtime-removal requirements retained unchanged. |

### Explicitly deferred scope

`ResearchContext`, `AgentAnalysis`, `BriefContext`, Agent schemas, Agent
orchestration, and the future Brief contract are deferred/non-goal direction only.
They are not current shapes, serialized contracts, or runtime behaviors. The
historical active Change's positive model-era requirements are classified above as
historical-only, not deferred current scope.

## Proposed Feed requirement trace

| Proposed requirement | Current implementation evidence | Focused test evidence |
|---|---|---|
| Credential-free verified provider contracts | `src/follow_the_money/config/load.py`, `config/model.py`, `providers/manifest.py`, `providers/urls.py`, `providers/adapters.py`; `scripts/feed/follow-the-money-feed` and `feed/cli.py` load the verified registry without model credentials | `tests/test_provider_contract.py`, `tests/test_config.py`, `tests/test_adapters.py`, `tests/test_no_llm_contract.py`, `tests/test_gate_13_1.py` |
| Durable collection coordination and rate discipline | `feed/cli.py` derives `coordinates_run = not dry_run or providers_fn is None`, acquires `CollectionLock` before cutoff/latest planning, and initializes/uses `RateRegistry` for production-adapter dry runs as well as publishing runs; `providers/lock.py`, `providers/rate.py`, `providers/http.py` own the durable primitives | `tests/test_provider_contract.py` rate/registry/crash-recovery cases; `tests/test_gate_13_1.py` retry/rate cases; `tests/test_gate_13_2.py::test_production_dry_run_coordinates_and_reconciles_rate_state`, lock/concurrency/cancellation cases; `tests/test_feed_cli.py::test_dry_run_publishes_nothing` proves fixture dry runs remain write-light |
| Bounded command deadline and non-cancellable commit | `feed/cli.py` anchors the command-start monotonic deadline, reserves the final 15 seconds, passes its injected clock and absolute admission boundary into `publish_feed`; `feed/publish.py` stages and fsyncs reversibly, checks admission immediately before the first rename, and performs admitted rename/post-rename fsync without cancellation | `tests/test_gate_13_1.py` retry/deadline cases; `tests/test_gate_13_2.py::test_staging_crossing_admission_boundary_refuses_before_any_rename`, `test_idempotent_recovery_crossing_admission_keeps_dated_only`, `test_admitted_commit_crossing_nominal_deadline_is_not_cancelled`, late-result and process-concurrency cases |
| Evidence-only deterministic Feed generation | `feed/cli.py` performs provider fetch, normalization, dedupe, validation, and publication; `feed/validate.py` rejects intelligence fields; no LLM runtime is imported | `tests/test_no_llm_contract.py`, `tests/test_feed_boundary.py`, `tests/test_adapters.py`, `tests/test_gate_13_1.py` |
| Feed is the serialized external contract | `schema.py`, `schemas/feed.schema.json`, `feed/validate.py`, `canonical.py`, `boundary.py`, and `feed/publish.py` validate schema, semantic invariants, embedded contracts, digest, and cutoff-derived identity | `tests/test_feed_boundary.py`, `tests/test_feed_pipeline.py`, `tests/test_boundary.py`, `tests/test_gate_13_2.py` |
| Bounded canonical evidence and conservative deduplication | `unicode.py`, `feed/dedupe.py`, `providers/adapters.py`, and typed schema/config validation enforce NFC, bounded fields, numeric guards, canonical values, URL identity, same-source near dedupe, and cross-source lineage | `tests/test_dedupe.py`, `tests/test_provider_contract.py`, `tests/test_adapters.py`, `tests/test_config.py` |
| Provenance tiers and payload-specific time semantics | Adapter normalization and `feed/validate.py` retain provider/source/tier/kind/URL/knowledge/effective/retrieval/precision fields and apply payload-specific cutoff rules | `tests/test_adapters.py`, `tests/test_feed_boundary.py`, `tests/test_market_snapshot.py`, `tests/test_gate_13_1.py` |
| Raw bounded market history | `providers/adapters.py` (`YahooMarketAdapter`) preserves bounded chronological raw observations and session/availability metadata; `market/snapshot.py` consumes raw history deterministically | `tests/test_adapters.py` Yahoo bounded-history/session cases; `tests/test_market_snapshot.py` history, session, duplicate, unit, and cutoff cases |
| Explicit degradation and coverage outcomes | `feed/plan.py`, `engine/feed_health.py`, and `feed/cli.py` calculate provider/coverage outcomes, retain valid partial items, publish degraded status when allowed, and fail closed on zero accepted items | `tests/test_feed_pipeline.py` coverage/degradation cases; `tests/test_engine.py` Feed health cases; `tests/test_gate_13_1.py` fixture-backed healthy/degraded run cases |
| Fixed advancing Feed window | `feed/plan.py` and `feed/cli.py` lock before cutoff, validate latest, use the bootstrap lookback or previous cutoff, enforce half-open/advancing windows, and keep persisted UTC/Schedule metadata | `tests/test_feed_pipeline.py` bootstrap/latest/non-advancing/gap cases; `tests/test_gate_13_2.py` cutoff/invalid-latest/no-mutation cases |
| Durable monotonic publication | `feed/publish.py` performs same-parent staging, file/directory fsync, create-only dated commit, atomic latest replacement, idempotent recovery, and explicit durability uncertainty; it derives validated `(evidence_cutoff_at, content_digest)` ownership and replaces latest only for the greater tuple | `tests/test_feed_pipeline.py` publication/idempotency cases; `tests/test_gate_13_2.py::test_equal_cutoff_different_digest_both_orders`, `test_older_candidate_keeps_newer_latest_and_dated_artifact`, `test_same_run_recovery_does_not_regress_newer_latest`, `test_incompatible_equal_owner_fails_closed`, `test_malformed_current_latest_ownership_fails_closed`, fsync, crash-recovery, no-replace, stale-candidate, and stage-cleanup cases |
| Minimal internal Feed entry outcomes | `scripts/feed/follow-the-money-feed` is the sole wrapper for `python -m follow_the_money.feed.cli`; typed `FeedInputError`/`FeedExecutionError` determine exits and `--dry-run` avoids publication | `tests/test_feed_cli.py`, `tests/test_no_llm_contract.py`, `tests/test_workflows.py` |

## Existing core requirement trace

| Existing requirement | Current implementation evidence | Focused test evidence |
|---|---|---|
| No embedded LLM runtime | `pyproject.toml`, `config/`, `scripts/feed/follow-the-money-feed`, and the package import surface contain no runtime SDK/request/config coupling; the minimal entry uses deterministic Feed/provider code | `tests/test_no_llm_contract.py::test_repo_has_no_llm_surface`, `test_package_imports_without_llm_sdk`, `test_shipped_config_loads_credential_free`, `test_minimal_entry_publishes_validating_feed` |
| Functional evidence-only Feed with one minimal internal invocation | `scripts/feed/follow-the-money-feed` is the sole wrapper; `feed/cli.py::main`/`run_feed` implements typed exits, schema/identity validation, publication, and dry-run | `tests/test_feed_cli.py`, `tests/test_feed_pipeline.py`, `tests/test_no_llm_contract.py`, `tests/test_gate_13_1.py` |
| Deterministic domain rules retained without production wiring | `scoring.py`, `selection.py`, and `audit.py` are deterministic libraries; the minimal Feed import probe returned `[]` for those modules and no production caller supplies synthetic analysis inputs | `tests/test_scoring.py`, `tests/test_no_llm_contract.py::test_retained_rules_deterministic_and_llm_free`; import-closure probe above |
| Deterministic provenance, validation, and audit capability retained | `canonical.py`, `schema.py`, `feed/validate.py`, `boundary.py`, and `audit.py` enforce Feed identity/digest/schema and safety invariants; internal structures remain Python contracts | `tests/test_feed_boundary.py`, `tests/test_boundary.py`, `tests/test_events.py`, `tests/test_market_snapshot.py`, `tests/test_no_llm_contract.py` |

## Proposed deterministic research trace and caller audit

The minimal Feed entry import probe was run as:

```text
uv run python -c 'import sys; import follow_the_money.feed.cli; names=[n for n in sys.modules if n == "follow_the_money.ledger" or n.startswith(("follow_the_money.events", "follow_the_money.engine", "follow_the_money.market", "follow_the_money.watchlist", "follow_the_money.scoring", "follow_the_money.selection", "follow_the_money.audit"))]; print(names)'
[]
```

Therefore the following post-Feed libraries are retained and tested, but have no
production orchestration caller. The Feed path's actual imports are limited to
Feed planning/validation/publication, canonical/boundary/config/schema, provider
HTTP/manifest/lock/rate/adapter modules, and Feed dedupe.

| Proposed requirement | Current implementation evidence | Focused test evidence and caller disposition |
|---|---|---|
| Internal deterministic contracts and wiring status | `ledger.py`, `events.py`, `engine/`, `market/`, `watchlist.py`, `scoring.py`, `selection.py`, `audit.py` are typed deterministic modules; only Feed/provider modules are in the minimal entry import closure | `tests/test_events.py`, `test_engine.py`, `test_market*.py`, `test_state.py`, `test_scoring.py`, `test_no_llm_contract.py`; no post-Feed production caller |
| Immutable evidence ledger | `ledger.py` typed FACT/CLAIM/OBSERVATION/INFERENCE entries and `events.py` seed/key-fact rules | `tests/test_events.py` ledger identity, duplicate, unknown, origin, and ordering cases; retained library only |
| Deterministic entity resolution and candidate grouping | `engine/entities.py` and `engine/candidates.py` implement closed aliases, stable raw identity, canonical-fact and exact-entity/time/predicate graph rules, canonical ordering, and capacity errors | `tests/test_engine.py` alias, ambiguity, node/edge, component, packing, and capacity cases; retained library only |
| Canonical Event and family utilities | `events.py` implements canonical Event IDs, key facts, `fully_known_at`, display templates, singleton family IDs, and unordered pairs | `tests/test_events.py` Event/family/pair/display cases; pure utility only, not resolver/live/replay wiring |
| Deterministic market snapshot | `market/snapshot.py` and `market/formulas.py` implement role order, returns/basis points, z-scores, unknown reasons, evidence IDs, and Decimal formulas | `tests/test_market_snapshot.py`, `tests/test_market.py`; retained library only |
| Deterministic breadth, surprise, and Market State | `market/snapshot.py`, `market/surprise.py`, and `state.py` implement breadth, tie-broken macro releases, surprise votes, coverage, and regime classification | `tests/test_market_snapshot.py`, `tests/test_market.py`, `tests/test_state.py`; no editor/Brief/Bundle/replay caller |
| Deterministic confidence and watchlist rules | `market/confidence.py` and `watchlist.py` implement tier/family/conflict confidence, horizon filtering, ordering, and sparse outcomes | `tests/test_market.py`, `tests/test_state.py`; no production Brief caller |
| Versioned deterministic scoring | `scoring.py` and `market/formulas.py` own closed maps, weights, Decimal context, coverage, relevance, and priority | `tests/test_scoring.py`, `tests/test_state.py`; inputs remain caller-supplied; no Feed orchestrator |
| Deterministic selection and family penalty | `selection.py` applies eligibility, frozen order, family penalty, pair exemption, thresholds, limits, and sparse reporting | `tests/test_scoring.py`; no production resolver or selection caller |
| Deterministic safety audit retained without orchestration | `audit.py::ClaimAuditor` enforces claim identity/evidence/trading-instruction rules and fails closed without rewriting | `tests/test_no_llm_contract.py::test_retained_rules_deterministic_and_llm_free`; no production Brief or Agent validation caller |

## Negative architecture and retired-capability audit

| Audit | Evidence | Disposition |
|---|---|---|
| Minimal Feed production entry | `scripts/feed/follow-the-money-feed` forwards only to `follow_the_money.feed.cli`; the CLI imports Feed/provider infrastructure and not post-Feed research modules | Positive current Feed wiring only |
| Removed LLM/model surface | `tests/test_no_llm_contract.py` covers repository surface/import/config/entry behavior; current runtime import probe contains no LLM package; the active original Change's LLM/model requirements are historical-only | No current LLM contract; historical text remains only until authorized archive, then under `openspec/changes/archive/` |
| Public CLI, Brief, resolver, analyst, editor, language-audit, Bundle/replay | No corresponding current runtime entry or import; the three current `production-*`/resolver specs are stale and their archived Changes are identified above | Retire living capability claims; preserve archive history |
| Future Agent objects | `ResearchContext`, `AgentAnalysis`, `BriefContext`, Agent schemas, Agent orchestration, and future Brief are named only in this Change's explicit deferred/non-goal text | Deferred, no current contract |
| Retired capability history | Archived Change directories and hashes below exist before deletion; they are not to be edited | Historical evidence preserved |

### Post-archive forbidden-surface audit

At that normalization snapshot, the audit searched current specs and the only active
Change for LLM SDK/request,
model/API-key, prompt, token/retry/reasoning, public CLI, resolver/analyst/editor,
language-audit, Brief, Bundle/replay, and live-model evaluation terms. The only
current-spec hits are explicit negative architecture invariants, retained-library
caller boundaries, or the explicitly deferred Agent Contract names. The canonical
Feed spec has no whole-word `public`, `model`, `Brief`, `Bundle`, `replay`, `Agent`,
or `LLM` hit. The archived original Change and the three archived stale Changes are
excluded from this current/active audit and remain historical evidence.

The future-scope audit found `ResearchContext`, `AgentAnalysis`, `BriefContext`,
Agent schemas, and Agent orchestration only in the core negative scenario and this
Change's explicit deferred/non-goal evidence; no current shape or orchestration
requirement exists. The research spec's Agent references are negative caller-status
statements, not an Agent schema or runtime contract.

## Structural and quality gate evidence

The original baseline Apply structural gates after canonical materialization passed:

| Gate | Command | Result |
|---|---|---|
| OpenSpec doctor | `openspec doctor --json` | `healthy: true`, empty status |
| This Change strict validation | `openspec validate normalize-openspec-baseline --strict --json` | 1/1 valid, 0 failed |
| All strict validation | `openspec validate --all --strict --json` | 4/4 valid, 0 failed; only informational long-requirement messages |
| Repository quality gate | `uv run python scripts/quality_gate.py` | exit 0; pytest, workflow, CLI, ruff, format, mypy, offline wheel build; final output `quality gate passed` |

The pre-remediation path classifier over `git status --porcelain=v1 --untracked-files=all`
returned no out-of-allowlist path. All changed paths are the explicit Change
artifacts, the authorized original-Change archive move, the three stale living
spec deletions, the three canonical spec paths, or the pre-existing unrelated
`AUDIT-2026-08-12.md` deletion. No production code, tests, configuration, JSON
Schema, provider manifest, workflow, generated Feed data, dependency, or deployment
file changed.

That checkpoint also confirmed that the first 66 lines of canonical
`deterministic-core-retention/spec.md` are byte-identical to HEAD, no untracked
Change/spec file has trailing whitespace, `git diff --check` is clean, the only
active Change at that time was `normalize-openspec-baseline`, and the canonical living capability
set is exactly the three directories listed above.

## Fresh Stage 3 blocker resolution and separate finalization

The three semantic blockers identified by the fresh Stage 3 review are repaired
in `fix-feed-coordination-and-publication-contracts`. Current evidence is:

| Resolved blocker | Implementation and focused-test evidence |
|---|---|
| Production-adapter `--dry-run` skipped collection coordination and durable rate state | `feed/cli.py` coordinates when production adapters may send; `tests/test_gate_13_2.py::test_production_dry_run_coordinates_and_reconciles_rate_state` observes lock acquisition, durable debit/reconcile state, and no Feed artifact. Fixture-injected dry runs retain their no-publication/no-rate-registry behavior. |
| Caller-only second-285 admission allowed staging/fsync to overrun the reserve | `run_feed` passes the injected monotonic clock and absolute boundary; `feed/publish.py` checks only after reversible staging and directory fsync. `test_staging_crossing_admission_boundary_refuses_before_any_rename` and `test_idempotent_recovery_crossing_admission_keeps_dated_only` prove typed refusal, zero rename, and cleanup; `test_admitted_commit_crossing_nominal_deadline_is_not_cancelled` proves the admitted commit is non-cancellable. |
| Latest replacement depended on submission order for equal cutoff | `feed/publish.py` validates canonical ownership keys and selects the maximum `(evidence_cutoff_at, content_digest)` tuple, retaining dated artifacts and failing closed on incompatible equal ownership. `test_equal_cutoff_different_digest_both_orders`, `test_older_candidate_keeps_newer_latest_and_dated_artifact`, `test_same_run_recovery_does_not_regress_newer_latest`, and `test_incompatible_equal_owner_fails_closed` cover submission-order, stale-candidate, recovery, and equal-owner mutations. |

Fresh independent Stage 3 review found and repaired one necessary Medium evidence
gap by adding `test_same_run_recovery_does_not_regress_newer_latest`; that test
passes on the repaired implementation and fails on the isolated old implementation.
After the final test and trace edits, the complete quality gate passed with 418
tests plus workflow, CLI, Ruff lint/format, mypy, and offline wheel build. OpenSpec
doctor is healthy, both target strict validations pass 1/1, all strict validation
passes 5/5 with informational long-requirement findings only, and `git diff
--check` is clean. Both active Changes have all tasks closed, and no unresolved
Blocker, High, or necessary Medium remains.

The three former semantic blockers are resolved and both Changes are recommended
for separately authorized archive. Final archive of this baseline Change MUST use:

```bash
openspec archive normalize-openspec-baseline --skip-specs
```

The canonical living specs were materialized during Apply; a normal archive would
attempt to apply duplicate `ADDED Requirements`. Commit, push, and delivery remain
separate authorized actions.

## Archived stale-capability file identities captured before deletion

These SHA-256 values are the pre-Apply archive identities. Task 3.1 must capture
the same values after living-directory deletion.

```text
ce09aa8a7e84963f39e89c29067fa37eebde711c5ce3426da3c8f0976ee178cf  openspec/changes/archive/2026-08-12-fix-multi-component-resolver-blocks/.openspec.yaml
fe22b05999edd0a00627186d6795fdac5b189b8add6a5cdcbb4bfe3b2425f817  openspec/changes/archive/2026-08-12-fix-multi-component-resolver-blocks/design.md
b342a605fdffe14a375ad8ce3588bfe0b6b9de0378e8d3a4bfbe11b61afb04bf  openspec/changes/archive/2026-08-12-fix-multi-component-resolver-blocks/proposal.md
a53ea0cd8dbab248ac222bfa71ed831f0a4fab3a1c6e594e4f60f2981690f3d8  openspec/changes/archive/2026-08-12-fix-multi-component-resolver-blocks/specs/multi-component-resolver-block-processing/spec.md
6e7e553ddfb2e06992114354398e6f5cd4799c662d36546571d880f881bcfa40  openspec/changes/archive/2026-08-12-fix-multi-component-resolver-blocks/tasks.md
ce09aa8a7e84963f39e89c29067fa37eebde711c5ce3426da3c8f0976ee178cf  openspec/changes/archive/2026-08-12-restore-production-story-family-resolution/.openspec.yaml
4e69ffbe74c5fd7066e5f1e8803e13c4a5e3b528bd8b70439c9554a79cee7419  openspec/changes/archive/2026-08-12-restore-production-story-family-resolution/design.md
d29f3cd7b118e770be49a98cd3cb141f89fda5bf2d6e9082e9005e6f57df22eb  openspec/changes/archive/2026-08-12-restore-production-story-family-resolution/proposal.md
63c6eb5945f42f73ffeb0af73698ee72554e95a12df44a809c1788635a1cacda  openspec/changes/archive/2026-08-12-restore-production-story-family-resolution/specs/production-story-family-resolution/spec.md
2a965bd6a9238b3ce60f3f7d586c692e35ed99b5948e119de8041ccc2b2fec52  openspec/changes/archive/2026-08-12-restore-production-story-family-resolution/tasks.md
ce09aa8a7e84963f39e89c29067fa37eebde711c5ce3426da3c8f0976ee178cf  openspec/changes/archive/2026-08-13-activate-production-market-state-pipeline/.openspec.yaml
6ed347f30babcd7ba33554ea1db07c3a36c8cadfb6a4cf8c317210415918cb81  openspec/changes/archive/2026-08-13-activate-production-market-state-pipeline/design.md
50dcf6cb45892cca79fa43856389921e8525981eca4afd5ef602c3130b8fc45f  openspec/changes/archive/2026-08-13-activate-production-market-state-pipeline/proposal.md
7e45adb91b80d21581ad0e5b2261ce3f3ed5b2c97f373a927878a63a9158cb04  openspec/changes/archive/2026-08-13-activate-production-market-state-pipeline/specs/production-market-state-pipeline/spec.md
3ca5bf57b2a37c3e9305e40dd5839539f0557e5ded0093af3208045c6d7bba79  openspec/changes/archive/2026-08-13-activate-production-market-state-pipeline/tasks.md
```

The newly created archive preserved the original active-Change file identities:

```text
f41f2bc28ec1d7aab73d26bb7222e7e03ea9138b5ac97f86aa97812e52abbef3  openspec/changes/archive/2026-08-13-implement-follow-the-money-repository/.openspec.yaml
a4b420ab0561ec32eaec7a64d720712cc4d713e8f29c1df92f3deec9df9d5d9a  openspec/changes/archive/2026-08-13-implement-follow-the-money-repository/design.md
caf090982168269f098cf3d18e679b4bb8a396e8d2bdf4741adad74f9cdf6335  openspec/changes/archive/2026-08-13-implement-follow-the-money-repository/proposal.md
f535fb33ac9aa7f478d894a0ddfd1d4efd1d169d933f6627d40759cb5fded8fe  openspec/changes/archive/2026-08-13-implement-follow-the-money-repository/specs/brief-synthesis-and-audit/spec.md
373c4f2314c4511ed8236367a34b8fb0ca0123e239cd847218024fe500212202  openspec/changes/archive/2026-08-13-implement-follow-the-money-repository/specs/deterministic-evidence-engine/spec.md
21e60403d42b8e10d1d6f4f7b4a4e36d4d3b532534b7e1e0cf89e5e3b7e83f2e  openspec/changes/archive/2026-08-13-implement-follow-the-money-repository/specs/event-analysis-and-ranking/spec.md
3948e611aa41c7f5745b8312a1a31b2b252a8ceeb90382e421e4fe0b93f1321d  openspec/changes/archive/2026-08-13-implement-follow-the-money-repository/specs/feed-evidence-pipeline/spec.md
c376fc422ab211cb2467e00263ebf2abbb5dc21220aa972c0f4c07fc7035db62  openspec/changes/archive/2026-08-13-implement-follow-the-money-repository/specs/regression-evaluation/spec.md
0a45713f3aa3303da32e216bf73920de2238b332a437d3addaebf7b15832923c  openspec/changes/archive/2026-08-13-implement-follow-the-money-repository/specs/semantic-event-resolution/spec.md
5c15fb08cb2447a25083989a6434e80f5baa2465988369394b184aa07fff6fec  openspec/changes/archive/2026-08-13-implement-follow-the-money-repository/tasks.md
```

The archived stale-capability hashes above were reverified from the filesystem
before final acceptance with:

```bash
find openspec/changes/archive/2026-08-12-fix-multi-component-resolver-blocks \
  openspec/changes/archive/2026-08-12-restore-production-story-family-resolution \
  openspec/changes/archive/2026-08-13-activate-production-market-state-pipeline \
  -type f -print | sort | xargs sha256sum
```
