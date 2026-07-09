## Context

Three medium findings from `docs/code-quality-review-2026-07-08.md` remain open:

- **M4** — `README.md` 🅱️ step 4 (L165) says running `prepare-digest.js | print.js` yields "一份 markdown 摘要". In reality `prepare-digest.js` writes `JSON.stringify(out)` and `print.js` only does `console.log(text)`. Markdown rendering exists only in 🅰️ agent mode (LLM applies `prompts/`).
- **M5** — `.github/workflows/aggregate.yml` runs `npm ci` → `node scripts/aggregate.js` → commit, with no `npm test`. A regression (e.g. the old H3 integration failure) would ship to `main` without warning.
- **M6** — `lib/aggregate/pipeline-a.js:36` calls `upsert13FFiling(feedPath, entry)` inside its filing loop. Each call does a full `readFeedJson` + `writeFeedJson` of the entire feed (O(N × feed size)). The in-memory `feed` is already kept in sync (L39-41), so the per-iteration disk write is redundant. `upsert13FFiling` has a single caller (`runPipelineA`) and is covered by `tests/store/feed-json.test.js` (history merge) and `tests/aggregate/pipeline-a.test.js`.

Constraints: stay on `main`, no feature branch, no behavior change, no scope creep beyond these three items.

## Goals / Non-Goals

**Goals:**
- Make README 🅱️ honest about JSON output.
- Add a real test gate to the aggregator CI.
- Eliminate the loop-internal full-file rewrite while preserving exact feed content, `valueUnit` stamping, history merge, and stats.

**Non-Goals:**
- No `scripts/render.js` / markdown renderer for 🅱️ mode (out of scope; 🅱️ is for developers who want raw control).
- No change to `value-units-normalization` math or `normalizeValueUnits`.
- No other review items (M1-M3 already done; L1-L10 untouched).

## Decisions

**D1 (M6) — extract a pure `merge13FFiling`, keep `upsert13FFiling` as a disk wrapper, write once in `pipeline-a`.**
Rationale: the current `upsert13FFiling` body already contains all the merge logic (stamp `valueUnit: 'thousands'` → find existing by `filerCik + periodOfReport` → history dedupe-by-accession merge → `computeStats` → `writeFeedJson`). Lifting that body verbatim into a pure `merge13FFiling(feed, entry) => feed` preserves semantics exactly. `upsert13FFiling(path, entry)` becomes `writeFeedJson(path, merge13FFiling(readFeedJson(path), entry))` — identical behavior for any single-shot caller and for the existing tests. `pipeline-a` then calls `merge13FFiling` per new filing (in memory) and `writeFeedJson(feedPath, feed)` once after the loop. Writing O(1) instead of O(N) per run.
Alternatives considered: (a) in-place mutating helper — rejected, impure/ harder to test; (b) drop `upsert13FFiling` entirely and inline in `pipeline-a` — rejected, breaks the existing `upsert13FFiling` API/tests and the `value-units-normalization` contract that names it as a writer.

**D2 (M4) — doc-only clarification, no renderer.**
Rationale: the smallest honest fix; matches the project's "🅱️ = developer raw control" positioning and the review's option (b).

**D3 (M5) — add `npm test` step in `aggregate.yml`.**
Rationale: the only workflow that touches `main` feed data; a gate here is the pragmatic fix the review suggested. Relies on the now-hermetic test suite (H3 fixed by `add-digest-time-seam` via `FTM_NOW` injection; CI uses Node 24).

## Risks / Trade-offs

- **[M6] Crash mid-run loses the whole run's updates** → Mitigation: `pipeline-a` is idempotent (driven by `state.seenFilings` + in-memory sync); a re-run re-derives the same entries. Acceptable — no partial-corruption risk because the final `writeFeedJson` is still atomic (tmp+rename).
- **[M6] History-merge semantics must be byte-identical** → Mitigation: `merge13FFiling` reuses the exact existing body; `tests/store/feed-json.test.js` already asserts the merge; add an explicit `merge13FFiling` test and a `pipeline-a` end-to-end "single write" assertion.
- **[M5] A flaky/failing test blocks feed updates** → Mitigation: desired gate behavior; suite is deterministic and green locally (152 pass). If CI ever flakes, that's a test bug to fix, not a reason to skip the gate.
- **[M4] None** — doc-only.
