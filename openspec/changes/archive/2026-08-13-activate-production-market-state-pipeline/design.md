## Context

`state.py` already implements the v1 five-dimension classifier, but only isolated tests call it. The normal production path constructs a literal all-`unknown` object, while dashboard assembly forwards the last raw market level as `return_pct`. The Yahoo-compatible adapter preserves chronological observations but does not explicitly request daily history or establish completed-session eligibility. Configuration lists role session classes and separate calendars without binding each role to one calendar, and the required Market State editor slot is validated but its wording is not merged into `market_state.explanation`.

This is a cross-cutting correctness repair across provider acquisition, session alignment, deterministic analytics, editor evidence projection, and production integration. The frozen architecture remains script-first/LLM-last: all market facts, calculations, classification, identifiers, evidence ownership, and merge authority stay in scripts; the existing editor pass supplies wording only.

## Goals / Non-Goals

**Goals:**

- Make a successful normal Brief derive Market State from cutoff-safe Feed evidence rather than a constant.
- Use one replayable market snapshot as the authority for dashboard moves, anomalies, classifier inputs, missing reasons, and evidence provenance.
- Enforce exact completed-session and current-excluded Decimal semantics before any role contributes.
- Preserve event scoring and selection behavior and the existing four-pass LLM topology.
- Add production-path fixtures that fail if the classifier becomes disconnected again.

**Non-Goals:**

- Changing v1 vote thresholds, dimension minima, regime precedence, or the 13-role universe.
- Making Market State a scoring, selection, recommendation, trading, or portfolio input.
- Adding real-time/tick analytics, cross-day mutable caches, a market database, provider substitution, or a fifth LLM pass.
- Implementing the separately observed story-family, multi-component resolver, or repricing-magnitude defects.

## Decisions

### 1. Keep historical observations inside each immutable Feed

The Yahoo-compatible fetch will use explicit cutoff-derived `period1`/`period2` bounds and `interval=1d`, with an exact v1 lookback of 90 calendar days to seek at least 22 eligible sessions and the existing maximum of 260 normalized observations. The Brief process will never refetch or read an ambient market cache.

This preserves immutable Feed identity, bundle replay, cutoff auditability, and zero-call evaluation. A rolling database could reduce response size but would introduce cross-run state, migration, recovery, and replay dependencies that this repair does not need. Reusing the news Feed window is rejected because a 24- or 72-hour incremental window cannot support a 20-change reference window.

Before activation, every role mapping must be re-verified as the named economic instrument, not merely as a working Yahoo symbol. Verification covers symbol, unit, daily-close meaning, availability time, and recorded fixture. An unverified role fails closed as unavailable; it is never replaced by a similar tenor, index, future, or regional proxy.

### 2. Bind every role explicitly to a session policy

`MarketRole` will gain a required `session_id` that resolves to a configured `Session`. Existing policies will be reused where exact, and explicit 24/5, 24/7, exchange, rates, volatility, or commodity policies will be added where the current generic entries are insufficient. Configuration loading validates referential integrity and compatible role/session classes at startup.

For exchange calendars, a provider bar maps to one session label in the configured calendar and becomes eligible only after that session's close plus the verified lag. Continuous policies define their own daily boundary. There is at most one eligible observation per session label. The analytics builder compares the last 22 expected labels with the observed labels; any gap or duplicate makes that metric unknown. Treating provider timestamps as “available five minutes later” is rejected because a daily timestamp can denote the session label/open rather than a completed close.

### 3. Introduce one small deterministic market-snapshot boundary

A focused module will expose a pure builder conceptually equivalent to:

```python
build_market_snapshot(feed, config) -> MarketSnapshot
```

The immutable result owns:

- 13 dashboard projections in configured order;
- per-role current move, z-score, availability, and unknown reason;
- `role_zs`, `role_return_zs`, and `yield_change_zs`;
- equity breadth and latest eligible inverted surprise votes;
- contributing evidence IDs in deterministic order.

Price-like roles produce simple returns; yield roles produce basis-point changes. Twenty-two closes produce 21 changes: the last change is current and the preceding 20 are passed to `abnormal_move_z`. All intermediate arithmetic stays in the existing precision-50 Decimal context; quantization occurs only at serialization. The same z-score supplies dashboard anomaly status and classification, preventing two competing analytics paths.

Embedding this logic directly in `pipeline.py` is rejected because provider parsing, session validation, metrics, dashboard formatting, and classification inputs would become difficult to test independently. Extending `state.py` to parse Feed payloads is also rejected because the classifier should remain a small policy function over typed numeric inputs.

### 4. Derive breadth and surprise votes from cutoff-eligible Feed evidence

Breadth uses only the current simple returns of the exact three equity roles; zero returns remain observable but neither positive nor negative. The denominator is the observable subset, and zero observable members yields unknown.

For each exact v1 macro series, the builder selects the latest cutoff-eligible release by `(knowledge_available_at, evidence_id)`, computes normalized surprise with the existing versioned scale, maps `>= +0.5`, between, and `<= -0.5` to `+1/0/-1`, then inverts it for Inflation. Only successfully contributing releases enter Market State provenance. This reuses the existing surprise formula without coupling Market State to selected Events or analyst output.

### 5. Classify once and keep the result informational

`run_pipeline` constructs the snapshot once before editor projection and passes its maps to `classify_market_state` once. The returned regime/vector and configured-order missing roles replace the constant object. `state.py` missing-role accounting will consider all three input maps so yield roles are not falsely missing; all computable role z maps may include roles not directly consumed by a dimension so dashboard-only roles still have correct availability accounting.

The snapshot is not passed into scoring or selection. A regression oracle compares event score components, selected IDs, formats, and order before and after activation. The existing `_observable_z` placeholder is out of scope; sharing the snapshot with repricing scoring requires a separate contract because it changes event significance.

### 6. Append Market State evidence without renumbering event aliases

Selected-event evidence aliases retain their current order and values. Deduplicated Market State contributor evidence is appended afterward in configured role order followed by CPI/PCE/PPI order. The state slot receives at most eight allowed aliases and a closed source view; complete support remains in the run bundle even when the editor projection is bounded.

`market_state_explanation` becomes a factual editor claim. Merge copies its validated wording into `market_state.explanation` and strips internal `evidence_ids`, while regime, vector, and missing roles remain script-owned. This fixes the existing disconnected required slot and ensures the claim inventory and rendered explanation refer to the same text. A deterministic script fallback is rejected because normal mode already requires the editor slot and forbids fallback after an LLM failure.

### 7. Fail locally for unavailable data and globally for invalid contracts

Expected market absence, insufficient history, missing sessions, stale/current partial data, incompatible units, or zero reference standard deviation make only the dependent role metric unknown with a closed reason. Invalid configuration, ambiguous duplicate role ownership, malformed normalized records that should have failed Feed validation, editor authority violations, or replay divergence fail the run before publication.

This distinction allows honest `unknown` states during genuine data gaps without letting contract corruption masquerade as ordinary missing data.

## Risks / Trade-offs

- **[Provider daily timestamps do not uniformly mean session close]** → Derive eligibility from the configured session close and verified availability policy; fixture exact boundary behavior for every session class.
- **[A working symbol represents the wrong economic role]** → Require role-level contract re-verification and keep unverified mappings unavailable; never substitute proxies.
- **[Calendar selection for rates, FX, volatility, or commodities is inaccurate]** → Add explicit role bindings and holiday/boundary fixtures; fail startup on missing or incompatible policies and fail a metric closed on session gaps.
- **[Historical payloads enlarge every Feed]** → Use daily interval, a fixed bounded lookback, one item per role, and the existing 260-observation/50-MiB limits; do not add an unbounded cache.
- **[Market evidence renumbers existing event aliases and breaks recorded outputs]** → Append new aliases after existing event evidence and add replay regression fixtures.
- **[A non-`unknown` state accidentally affects ranking]** → Keep snapshot/classifier outputs out of scoring signatures and assert exact score/selection invariance.
- **[Partial availability yields misleading confidence]** → Preserve known dimensions independently, require existing Risk Appetite plus 4-of-5 coverage for a regime, and expose deterministic missing roles/reasons.

## Migration Plan

1. Add and validate explicit role/session bindings plus re-verified provider mappings and daily-history fixtures while leaving production classification disabled.
2. Add session-aligned snapshot analytics and unit tests for complete and fail-closed inputs.
3. Replace duplicated dashboard builders with the shared snapshot projection and validate Brief schema/rendering changes, including yield basis-point display.
4. Connect the classifier, Market State evidence aliases, and editor explanation merge behind the normal deterministic pipeline.
5. Run focused provider/market/editor/pipeline/replay tests, then the complete quality gate on the final revision.
6. Rollback is a code/config revert to the prior release; no persistent data migration is required because Feeds and bundles are immutable versioned artifacts. Previously published Briefs are not rewritten.

## Open Questions

None. Exact provider symbols and session bindings are implementation verification outputs governed by the fail-closed requirements above; any role that cannot be verified during Apply remains unavailable rather than being guessed.
