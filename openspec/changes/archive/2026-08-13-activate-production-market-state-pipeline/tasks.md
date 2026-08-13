## 1. Role, Session, and Provider Contracts

- [x] 1.1 Add failing configuration fixtures for all 13 roles requiring a valid `session_id`, rejecting unknown or class-incompatible policies, duplicate role ownership, and any missing canonical role/order.
- [x] 1.2 Re-verify and fixture each role's exact provider symbol, economic identity, unit, daily-close semantics, session policy, availability lag, and source provenance; keep any role that cannot be verified explicitly unavailable rather than substituting a proxy.
- [x] 1.3 Implement required role-to-session configuration/model loading and the minimum additional exact session policies needed by the verified role contracts until the configuration fixtures pass.
- [x] 1.4 Add failing Yahoo-compatible adapter tests for explicit cutoff-derived 90-calendar-day `period1`/`period2`/`interval=1d` requests, bounded chronological observations, 260-item enforcement, and exclusion of a daily bar until session close plus availability lag.
- [x] 1.5 Implement the bounded daily-history fetch and completed-bar normalization without changing the news/calendar incremental Feed window or adding a market cache.

## 2. Deterministic Market Snapshot

- [x] 2.1 Add hand-calculated 22-close fixtures for price-like and yield roles covering exactly 21 changes, current-excluded 20-change references, hostile ambient Decimal context, exact anomaly `2.0` boundary, and output-only quantization.
- [x] 2.2 Add failing session-window fixtures for cutoff equality, current partial sessions, holidays, 24/5 and 24/7 boundaries, stale/post-cutoff observations, missing expected sessions, duplicate labels, wrong units, insufficient history, and zero reference standard deviation.
- [x] 2.3 Implement immutable per-role session alignment and metric construction using the existing simple-return, yield-basis-point-change, and `abnormal_move_z` formulas with closed deterministic unknown reasons.
- [x] 2.4 Add failing dashboard fixtures proving all 13 roles remain in configured order, missing roles remain visible, price-like roles show calculated returns, yield roles show basis-point changes, raw levels are never labeled as returns, and anomaly status reuses the classifier z-score.
- [x] 2.5 Extend the Brief dashboard schema/renderer only as needed for typed price-return versus yield-basis-point display, then implement the shared dashboard projection from the snapshot for normal and degraded paths.
- [x] 2.6 Add failing breadth and macro-surprise fixtures for the exact three-equity universe, observable-subset denominator, zero returns, zero observable members, latest cutoff-eligible CPI/PCE/PPI release selection, evidence-ID ties, exact `-0.5/+0.5` boundaries, inversion, incompatible units, unknown series, and post-cutoff exclusion.
- [x] 2.7 Implement deterministic equity breadth, latest-series surprise voting, classifier input maps, configured-order missing/unknown metadata, and contributor evidence ordering in one focused `MarketSnapshot` builder.

## 3. Classifier and Normal Pipeline Activation

- [x] 3.1 Add a failing classifier regression proving `missing_roles` considers `yield_change_zs`, remains in configured role order, and does not falsely mark available rate roles missing.
- [x] 3.2 Repair classifier missing-role accounting without changing vote thresholds, dimension minima, coverage denominator, regime precedence, or informational semantics.
- [x] 3.3 Add failing normal-pipeline fixtures with complete market observations for hand-calculated `risk_on`, `neutral`, and `risk_off` outputs plus insufficient-coverage input that preserves independently known dimensions.
- [x] 3.4 Replace the literal all-`unknown` production object by building one snapshot and invoking `classify_market_state` exactly once before editor slot allocation; keep snapshot/state values out of every scoring and selection signature.
- [x] 3.5 Add invariance assertions that identical event inputs retain exact score components, priorities, selected IDs, formats, and ordering after Market State activation.

## 4. Editor Explanation and Evidence Provenance

- [x] 4.1 Add failing alias-allocation tests proving selected-event aliases are unchanged, deduplicated Market State contributor aliases are appended in deterministic role-then-series order, the state slot exposes at most eight allowed aliases, and complete support remains in the bundle.
- [x] 4.2 Add failing merge/render/audit tests proving required editor wording becomes `market_state.explanation`, the rendered explanation equals the claim-inventory text, the claim is factual and evidence-backed, and regime/vector/missing roles remain immutable.
- [x] 4.3 Add adversarial tests rejecting editor-injected state fields, scores, URLs, unexposed aliases, or other authority expansion with no fallback publication.
- [x] 4.4 Implement bounded Market State evidence projection and authoritative explanation merge, then remove only the obsolete placeholder construction and duplicate dashboard helpers made unreachable by this Change.

## 5. Replay, Integration, and Final Gates

- [x] 5.1 Add deterministic replay coverage proving a stored Feed and recorded four-pass outputs reproduce the snapshot, classification, alias projection, authoritative Brief, and rendered bytes with zero provider/model calls.
- [x] 5.2 Run the focused provider, configuration, market, state, dashboard, editor, pipeline, bundle, and replay test suites and repair every reproducible regression within this Change's scope.
- [x] 5.3 Run `openspec validate activate-production-market-state-pipeline --strict`, schema checks, static/type/lint checks, the full test suite, and the repository quality gate on the final stable revision; record exact fresh outputs.
- [x] 5.4 Perform a fresh independent requirement-to-design-to-code-to-test review; fix all proven Blocker/High and necessary in-scope Medium findings, rerun invalidated gates, and leave unrelated audit findings unchanged and explicitly reported.
