# Stage 1 readiness review — repaired

Result: **修改后适合实施**. Workflow profile: **high-risk**. Stage 1 only; no Apply.

This supersedes the initial “暂不适合实施” conclusion. The user requested repair of the identified readiness findings. Proposal, design, delta spec and all affected tasks now state the same bounded solution; no implementation task is marked complete.

## Scope and refreshed evidence

Git still contains only the pre-existing untracked Change directory and no tracked implementation diff. Current OpenSpec status reports all four planning artifacts complete, with 0/43 implementation tasks complete. Refreshed CLI apply context identifies the same proposal/design/spec/tasks paths. Rechecked the affected `providers/http.py`, `feed/plan.py`, `feed/snapshot.py`, configuration parsing, manifest unit parsing/embedding, and accepted availability/coverage requirements. Existing broader review evidence remains applicable because those implementation files have not changed.

The authoritative SEC unit transition was verified against the official Federal Register final rule; quotations, URLs, response status, observed hash and limitations are recorded in `source-verification.md`. Linear remains unavailable through the provided tools; external issue scope/dependency status has not been independently confirmed.

## Requirement → implementation/test trace

| Requirement | Design decision | Tasks | Current constraint / implementation seam | Planned verification |
| --- | --- | --- | --- | --- | --- |
| Every real send independently managed | 1–2 | 1.1–1.5 | cli.py currently owns rate/concurrency around entire fetch | Two-send debit, deadline, host/global gates, redirects, exact reconciliation |
| Typed failures and truthful response observation | 1 | 1.2, 1.4 | bounded_fetch currently wraps every client exception | FetchError passthrough, RateStateError hard exit, HTTP-date clock, last response retained after timeout/cancellation |
| Partial resource acquisition is non-exempt | 1, 3, 5 | 1.4, 4.6, 5.4, 6.3 | fetched/accepted do not reveal intermediate successes; existing partial state already prevents exemption | First-resource versus later-resource 401/403, zero accepted, redirect-only denial, retry progress/recovery, terminal-unit failure |
| SEC exact CIK completeness depends on outcome | 5 | 4.4, 4.6, 6.3 | Unconditional equality would reject legitimate blocked-exempt or diagnostic candidates | Complete exact-set, incomplete valid subset only on failure, blocked-exempt zero items/degraded, empty watched set |
| v4 bounded v1 read/v2 production evolution | 7, Migration Plan | 2.1–2.6, 4.7, 5.7 | Global v1 loader; no semantic dispatch today | Test-local v2 contracts before activation; each manifest bump and working producer in one commit; final two v2/six v1 |
| SEC deterministic selection/holdings | 4, 6 | 3.1–3.5, 4.2–4.3 | Existing fixture lacks precise selection and INFORMATION TABLE data | Exact form/cutoff, key matching/aggregation, missing previous, identity ambiguity, bounded exact arithmetic |
| SEC verified source-unit normalization | 6, source-verification.md | 2.2–2.4, 3.2, 4.3, 4.7, 6.1 | Old manifest units are empty; raw value assumed thousands in initial design | Closed manifest map, filing-date cross-check, 2023-01-03 boundary, late report, cross-regime conversion, descriptor/null validation |
| SEC/CFTC-v2 whole-state carry admission | 10 | 4.5, 5.7, 6.3 | snapshot.py currently allows current-subset matching | A-H→A-G deletion, additions, empty selection, changed A retaining B-H, alias-only change, same-date CFTC market deletion, equal-set carry and legacy regressions |
| CFTC complete current/previous evidence | 8–9 | 5.1–5.7 | Current adapter fetches 100 rows; fixture lacks market code/spreading | Official query/row provenance, two dates, complete pagination, code matching, arithmetic/cutoff, no previous-only markets |
| Canonical identity / original source time / consumer evidence | 4, 8, 10–11 | 6.1–6.6 | Existing payload projection already includes semantic additions | Semantic fact/config/unit descriptor mutation, permutations, original timestamps, no Host-Agent arithmetic/network/history |
| Truthful docs and final gates | Migration Plan | 7.1–7.7 | Accepted specs remain current contract until explicit sync/archive | Quality gate after implementation; doctor/strict validation; three final scope/trust/consumer reviews |

## Findings and resolutions

### B1 — Resolved in planning: partial requests cannot become blocked-exempt

Initial evidence: `ProviderOutcome.blocked_exempt` depends on terminal state and accepted/rejected counters; `_run_adapter()` updates those counters only after a whole fetch. Submissions/discovery success followed by HTTP 403 could otherwise look like a failed/blocked zero-item Provider.

Repair: track partial successful resource progress independently, propagate it through typed failure, accumulate unresolved progress across retries, and serialize existing partial/blocked state on terminal denial even with zero accepted/rejected. Preserve genuine no-progress denial and redirect-only denial exemptions. Define successful retry recovery and terminal-unit failure behavior. No public outcome field or fabricated counter is added. SEC validation now distinguishes complete exact sets, blocked-exempt empty slices, and nonpublishable diagnostic subsets. Tests explicitly exercise SEC/CFTC later-request denial.

### B2 — Resolved in planning: both complete-state v2 Providers require exact current/prior identity sets

Initial evidence: snapshot.py's `changed` predicate checks current items against prior but ignores removed prior identities. A-H→A-G could therefore carry H back into the Feed. The original design prohibited changing this seam.

Repair: proposal and design explicitly authorize one equality predicate for the two resolved complete-state Provider versions, SEC v2 and CFTC v2. Follow-up inspection found the same cause when a CFTC same-date report correction removes a market without changing remaining items, so the shared fix covers that sibling path rather than leaving a known source-integrity gap. Removed/added identities select the whole current slice; an empty watched set removes prior SEC evidence, while an empty CFTC report still fails. No member-level merge, storage schema change, generic framework, or change to any v1/other six Provider event-list semantics is permitted. Tasks cover shrink/add/empty/unchanged/alias, same-date CFTC correction and legacy regression cases.

### F1 — Resolved in planning: manifest activation follows working production

Initial evidence: Task 2.5 upgraded checked-in manifests before Tasks 3–5 implemented semantic producers, contradicting the migration plan.

Repair: Task 2 retains v1 production manifests and uses test-local v2 contracts. Task 4.7 atomically activates the complete SEC vertical slice; Task 5.7 does the same for CFTC. Each intermediate commit advertises only implemented semantics; completion requires both Providers at v2.

### F2 — Resolved in planning: typed transport errors remain typed

Initial evidence: bounded_fetch erased FetchError metadata and wrapped RateStateError into ordinary Provider errors; Task 1.4 allowed only helper extraction.

Repair: Task 1.4 explicitly permits narrow typed passthrough/translation and progress metadata changes. Design defines sole rate transitions, hard persistence failures, one injected-clock Retry-After parse, and last concrete response observation across later failures. Focused tests cover these paths through bounded_fetch, not only a directly tested managed client.

### F3 — Regulatory unit verified; parser/fixture verification explicitly gated

Initial evidence: the old manifest had no unit authority and its sole fixture lacked INFORMATION TABLE values. The proposed field name did not establish the raw unit.

Repair: official SEC final rule 2022-13936 section II.C.2.c and II.D/footnote 115 establishes the filing-date transition effective 2023-01-03. Retain canonical USD thousands, apply identity conversion before the transition and exact USD/1000 afterwards, and preserve current/previous filing dates and typed source-unit/formula descriptors. Closed v2 manifest entries, exact arithmetic, cross-transition and conflicting-authority tests are specified. Actual production-shaped filing/format verification is an explicit gate before v2 activation, not a falsely completed task. Direct SEC document access returned 403; official Federal Register text was successfully inspected.

## Remaining implementation constraints / tradeoffs

- No known unresolved major design blocker remains from this review. This is readiness of the plan, not proof that implementation or tests pass.
- Read recent submissions only; do not add historical traversal or quietly broaden non-XML parser support.
- Verify SEC/CFTC production-shaped fixtures and query contracts before activating v2 manifests. If authoritative source evidence contradicts this plan, stop and revise the Change rather than infer facts.
- CFTC publication remains a declared deterministic rule, not an observed timestamp; no stronger freshness assertion is introduced.
- Preserve five domains, eight Providers, evidence-only output, credential-free operation, public CLI boundaries, durability and fail-closed publication.
- Only SEC/CFTC-v2 complete-state carry admission is changed; do not generalize it to any v1 or other Provider event-list semantics.
- Source evidence notes are planning provenance; authoritative runtime declarations belong in Provider manifests during Apply. Accepted specs and archive are untouched here.

## Validation

Executed after the final proposal/design/spec/tasks repair:

- `openspec doctor`: passed; root OK, no declared references.
- `openspec validate eco-124-semantic-current-change-evidence --strict`: passed.
- `openspec validate --all --strict`: 7 passed, 0 failed; informational long-requirement notices only.
- `git diff --check`: passed for tracked files.
- `git diff --no-index --check /tmp/eco124-before openspec/changes/eco-124-semantic-current-change-evidence`: no whitespace diagnostics; exit 1 denotes the expected untracked Change content differences against the pre-repair copy.

Changed only six files inside this Change: proposal.md, design.md, tasks.md, specs/feed-evidence-pipeline/spec.md, review.md, and new source-verification.md. All 43 implementation tasks remain unchecked. No test suite, environment sync, or full project quality gate was run for this documentation-only repair; those remain implementation tasks. No business code, tests, runtime configuration, schemas, accepted specs or archived Changes were modified.

## Stage 3 post-implementation independent review

Result: **修复后通过**. One fresh reviewer with no inherited conversation reviewed the complete uncommitted diff against every requirement and scenario; its findings were then re-verified independently against source and the live upstream dataset before repair. Every repair below was proven to be discriminated by its test through a temporary code revert.

### Fixed

- **Blocker — CFTC spreading column name.** Real rows carry `noncomm_postions_spread_all` (misspelled upstream); the code read only `noncomm_positions_spread_all`, which does not exist, so `_number(None)` failed closed on every real row. The fixtures had reproduced the corrected spelling, which is why the suite stayed green. Fixed the lookup, corrected all three fixtures, and added `test_official_column_names_are_consumed`, `test_checked_in_fixtures_reproduce_the_official_row_shape`, and `test_missing_spreading_column_fails_closed`.
- **Blocker — CFTC items collapsed by Feed deduplication.** Every market item carried the same dataset landing page as `source.url`, and `deduplicate_items` collapses same-URL records into one survivor, so any report with two or more markets silently published one item. Each item now points at its own official Socrata row URL. `design.md` Decision 9 was corrected to match. Regression: `test_corrected_same_date_cftc_report_removes_market_without_carry` fails with 2 items when the complete-state gate is disabled.
- **High — SEC v2 contract checks were skipped for zero-item Providers.** `_validate_versioned_semantics` iterated only Providers that had items, so an embedded SEC v2 contract without a watched-company snapshot validated. It now iterates the union of item Providers and embedded v2 Providers. Regression: `test_v4_sec_v2_contract_requires_watched_snapshot_without_sec_items`.
- **High — three rate regressions were skipped with a coverage claim that did not hold.** `test_provider_session.py` had no reconcile-failure case. The three cases are re-expressed against the current architecture (managed-client reconcile failure with exactly one reconcile and no refund; rate-state and rate-wait failures at the orchestration boundary) with no skips remaining.
- **Medium — no CLI-level test could detect loss of the complete-state carry gate wiring.** Added the two-run corrected-report regression above.
- **Medium — the partial-resource blocked mapping had no CLI-level test.** Added `test_denial_after_partial_resource_progress_is_blocked_without_exemption`, which fails when the orchestration stops reading `acquisition_progress`.
- Corrected the stale CFTC manifest provenance claim and recorded the verified upstream row shape, including the misspelling and the per-row URL, in `source-verification.md`.

### Rate budget — measured and pinned

Measured 2026-09-15 with the real `RateRegistry`, the resolved production manifests, and an injected clock: SEC 24 sends cost a **115.0s** rate floor, CFTC **22.0s**, and each of the other six Providers **1.0s**, against a 285s pre-commit budget. The accepted tradeoff in design.md ("fail incomplete rather than bypass rate policy") therefore holds with roughly 140s of headroom for network time, retries, and processing.

`test_sec_v2_send_shape_respects_the_rate_floor_and_fits_the_pre_commit_budget` now pins both halves of the invariant against the resolved config and manifest: the floor must still be 23 intervals (so per-send spacing cannot be lost) and it must fit the budget (so a lowered deadline, raised interval, or grown watched set cannot silently make SEC unacquirable). Raising `minimum_interval_seconds` to 30 makes it fail as intended.

### market_and_exchange_names — design corrected, contract unchanged

Design Decision 9 listed `market_and_exchange_names` in `market_identity`, but the implementation publishes only `cftc_contract_market_code` and `contract_market_name` (`raw_metadata: {}`).

Resolved by correcting the design text rather than expanding the published contract. The field is not required by the delta spec, which asks only for typed market identity; it was never typed evidence, since v1 retained it solely inside `raw_metadata`, which the consumer contract forbids the Host Agent to parse; and the code's display-name fallback already prevents any row from being unidentifiable. The design sentence now states that fallback explicitly so code and artifact agree on what `contract_market_name` holds. Adding the field to the closed schema would have been speculative contract growth with no requirement behind it. Reversible if typed exchange identity is wanted later, but that is a Feed contract change, not an ECO-124 defect.
- `config/__init__.py` lazy re-export: the root cause is the `config.load -> providers.manifest -> config.model` cycle that the new `providers/session.py` import order triggers. Necessary, but undocumented in design/tasks.

### Validation

- `.venv/bin/python -m pytest tests/` → 352 passed, 0 skipped (was 342 passed, 3 skipped).
- `.venv/bin/python scripts/quality_gate.py` → passed (pytest, workflow contracts, CLI, lint, format, mypy, offline wheel build).
- `openspec validate eco-124-semantic-current-change-evidence --strict` → valid. `openspec validate --all --strict` → 7 passed, 0 failed. `openspec doctor` → exit 0. This CLI has no `openspec verify` subcommand, so that command is not applicable.
- Live upstream verification of the CFTC dataset row shape and the per-row resource URL, recorded in `source-verification.md`.

### Open before archive

- Tasks 1.5, 2.6, 3.5, 4.7, 5.7 and 6.6 require recorded independent/intermediate commits; the working tree still has none, so those checkboxes are not yet truthful. This needs explicit commit authority.
- The `market_identity` field question above needs a decision.
