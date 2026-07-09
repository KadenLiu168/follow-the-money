## Context

The 2026-07-09 OpenSpec consistency audit produced 16 findings. This change resolves the
seven findings that are pure documentation / tooling corrections with verified evidence and
no behavioral change:

- **F-04** — duplicate "修订 N 次" in alert render (`prompts/format-alert.md` + `merge-amendments.js`)
- **F-09** — wrong "max 8" claim in `references/data-formats.md`
- **F-10** — wrong fixed-ET cron claim in `README.md` + `references/architecture.md`
- **F-11** — wrong "5 data files" claim in `references/architecture.md`
- **F-14** — `engines.node` floor below actual syntax requirement
- **F-15** — ambiguous "three-level classification" in `references/alert-rules.md`
- **F-16** — stale code-quality-review doc (resolved items unmarked)

All targets were read directly during the audit; the proposed edits align prose with the
verified code behavior. No source modules are modified.

## Goals / Non-Goals

**Goals:**
- Make `references/`, `README.md`, `prompts/`, and `docs/` consistent with the actual code.
- Pin the Node engine floor so `prepare-digest.js` (`import ... with { type: 'json' }`) runs.

**Non-Goals:**
- No changes to runtime behavior, APIs, or data formats.
- No OpenSpec spec (`openspec/specs/*`) is created or modified — this is a docs/tooling fix.
- The remaining 9 findings (F-01–F-03, F-05–F-08, F-12, F-13) are deliberately excluded;
  they need a design decision and are tracked separately.

## Decisions

1. **F-04 — remove the prompt prefix, keep `merge-amendments` summary.**
   The summary produced by `lib/alert/merge-amendments.js` already contains "N 次修订".
   Removing the redundant `修订 {count} 次，` prefix from `prompts/format-alert.md` is the
   smallest, lowest-risk fix and keeps the merge logic as the single source of the phrasing.
   Alternative (move phrasing into prompt, strip from JS) rejected: it would duplicate the
   count logic and risk divergence again.

2. **F-10 / F-11 — describe actual UTC cron and actual file set.**
   State the literal cron (`0 12 * * *` + `0 0 * * *` UTC) and label it "≈08:00 ET (DST-naive)";
   state "4 static files + per-year NDJSON from manifest". No attempt to make the schedule
   DST-correct (that is a separate, behavior-changing decision outside this change).

3. **F-14 — add `.nvmrc` at `20.19.0`** rather than only bumping `engines.node`.
   `.nvmrc` gives a concrete, tool-consumable pin for local dev and CI; `engines.node` is
   also raised to `>=20.19.0` for npm-enforced clarity.

4. **F-15 — clarify taxonomy, do not change code.**
   Document that "three-level" is a behavior taxonomy; `classify.js` returns `alert`/`digest`;
   `merged alert` is emergent; `intent` is parser-written. Clarifies without touching logic.

5. **F-16 — add "Resolved by …" notes** to the existing review doc; do not rewrite it.

## Risks / Trade-offs

- [Risk] Editing docs without running a full doc lint could leave minor markdown drift.
  → Mitigation: changes are single-sentence wording/annotation edits; reviewed before commit.
- [Risk] Raising `engines.node` to `>=20.19.0` could surprise a contributor on older Node.
  → Mitigation: `prepare-digest.js` already requires 20.19; the pin only makes the real floor explicit.
- [Risk] F-04 wording still double-renders if `merge-amendments` output format later changes.
  → Mitigation: the prompt now relies solely on the summary; one source of truth.

## Migration Plan

Pure doc/tooling edits. No migration or rollback beyond `git revert` of the changed files.
