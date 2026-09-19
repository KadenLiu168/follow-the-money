## 1. Characterize the v2 Contract with Focused Regressions

- [x] 1.1 Replace v1 shape assertions with frozen, slotted `DigestContext` v2 contract tests for exact `feed`, `content.updates`, and `status` surfaces; verify `domains`, `providers`, `reference_state`, and `unresolved_items` are absent and unsupported versions fail closed.
- [x] 1.2 Add news, macro, and policy membership regressions covering `[window.start, window.end)`, exact `event_time.kind`, before-window exclusion, missing/unusable authority, no timestamp fallback, and one-item/one-unit supporting evidence; verify the focused preparation tests fail before implementation and pass afterward.
- [x] 1.3 Add SEC regressions proving old Form 13F yields only `form13f/no_current_update`, a current Form 13F is one unit with holdings as evidence, a multi-entry Form 4 is exactly one unit, and a current 13D/G with `previous_snapshot` is exactly one unit; verify no nested evidence becomes a second update.
- [x] 1.4 Add CFTC regressions for carried, stale, and fresh-but-report-identity-unproven slices; verify no market row enters `content.updates`, compact status preserves supported `data_as_of`, and no Provider/date grouping creates a report unit.
- [x] 1.5 Add compact status and limitation regressions for fixed scope/state ordering, domain empty versus no-current versus unproven-current, BLS unavailable coverage, structured coverage gaps, and exclusion of raw warnings, HTTP diagnostics, Provider counts, domain totals, and reference counts.
- [x] 1.6 Add a production-shaped regression with hundreds of positioning reference rows, old watched Form 13F items, few current news/policy items, and a Provider limitation; verify only eligible current units plus compact status/limitations are serialized.

## 2. Implement Deterministic DigestContext v2

- [x] 2.1 Replace the v1 domain/provider dataclasses with the minimum frozen v2 Feed binding, update-unit, source/event/evidence/trace, domain-status, limitation, content, and context types; verify closed values, immutable nested structures, exact mapping shape, and canonical serialization with focused tests.
- [x] 2.2 Implement closed news, macro, policy, and SEC membership classifiers and unit builders using only the specified authorities and existing eligible-field projection helpers; verify unit IDs derive deterministically from unit type plus ordered Feed item IDs and current units preserve validated Feed order.
- [x] 2.3 Implement SEC subtype scope aggregation so Form 13F, Form 4, and beneficial ownership remain accession-level, historical comparison evidence remains nested, and old holdings never leak through status; verify the SEC focused regressions pass.
- [x] 2.4 Implement CFTC carry/stale/unproven status derivation from validated Provider freshness plus supported `data_as_of`, without report grouping or row projection; verify all positioning regressions pass.
- [x] 2.5 Implement deterministic domain-status aggregation and closed `provider_unavailable`/`coverage_gap` limitation projection with fixed ordering; verify every validated Feed item is classified internally without exposing exhaustive item accounting.
- [x] 2.6 Switch `prepare_digest_context()` and `scripts/skill/prepare-feed` to the single v2 output path, remove the normal v1 handoff and warning-table assumptions, and verify one canonical remote consumption still occurs with unchanged typed failure behavior.
- [x] 2.7 Prove same validated Feed plus context version `2` yields byte-identical units, identities, status, limitations, and canonical JSON under repeated construction and perturbed pre-normalization inputs.

## 3. Align Presentation Contracts and Documentation

- [x] 3.1 Rewrite `references/digest/presentation-contract.md` and `references/digest/compression.md` around `content.updates`, conditional compact status/limitations, claim-level traceability, non-exhaustiveness, and the removal of per-domain individual/consolidated/omitted reconciliation; verify static contract regressions reject the old formula and complete-audit requirement.
- [x] 3.2 Evolve all five domain references with `Reader-Facing Unit`, `Current Membership`, and `Supporting Evidence` sections while preserving closed field inventories, missing-evidence behavior, source authority, and forbidden financial interpretation; verify implementation and reference whitelists remain exactly aligned.
- [x] 3.3 Update `SKILL.md`, `references/feed-contract.md`, safety/architecture/feed-contract documentation, READMEs, and runbooks that describe v1 or exhaustive projection so the normal path names v2 and the Host Agent consumes only prepared updates; verify no normal-path documentation retains conflicting v1 or reconciliation semantics.
- [x] 3.4 Update presentation, caller-boundary, documentation, no-LLM, and safety regressions to enforce Host-Agent ownership of summarization/grouping/ordering/formatting but not membership, reference-state classification, or omission accounting; verify no affirmative importance, ranking, market-impact, prediction, recommendation, or trading behavior is introduced.

## 4. Verify Scope and Quality Gates

- [x] 4.1 Run the focused Digest preparation, presentation-contract, Feed documentation, caller-boundary, determinism, and safety suites and record exact passing commands/results.
- [x] 4.2 Run `.venv/bin/python scripts/quality_gate.py` and verify the canonical repository gate passes without modifying Feed products or persistent runtime state.
- [x] 4.3 Run `openspec doctor`, `openspec validate reader-first-deterministic-digest-structuring --strict`, and `openspec validate --all --strict`; verify the Change and all living contracts are coherent.
- [x] 4.4 Inspect the final scoped diff and verify Feed schemas, Provider/configuration/acquisition, canonical Feed bytes, publication, identity, persistent state, and model/orchestration boundaries are unchanged; document any deferred report-identity or source-enrichment gap without implementing it.
