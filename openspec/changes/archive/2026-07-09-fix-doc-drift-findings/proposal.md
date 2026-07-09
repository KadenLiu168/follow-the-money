## Why

The OpenSpec consistency audit (2026-07-09) found 16 drift issues. Seven of them are pure
documentation / tooling corrections with verified evidence and zero behavior change — they
are safe to fix immediately without any design decision. Leaving them unaddressed keeps the
project docs contradicting the code, which erodes the goal of OpenSpec-as-SSOT and misleads
any future reader (human or AI agent).

These are the "directly fixable" subset (F-04, F-09, F-10, F-11, F-14, F-15, F-16). The
remaining findings (F-01 through F-03, F-05 through F-08, F-12, F-13) require a design
decision and are intentionally out of scope here.

## What Changes

- **F-09**: Fix `references/data-formats.md` — `thirteenF` is not "one entry per filer (max 8)";
  upsert key is `filerCik + periodOfReport`, so one entry per filer per quarter (can exceed 8).
- **F-10**: Fix `README.md` and `references/architecture.md` — CI cron is `0 12 * * *` + `0 0 * * *`
  (UTC), not fixed "08:00 + 20:00 ET"; under DST it drifts by 1 hour. Relabel as "≈08:00 ET (DST-naive)".
- **F-11**: Fix `references/architecture.md` — local `fetch-feed` downloads 4 static files + per-year
  NDJSON discovered from manifest, not "5 data files".
- **F-14**: Set a Node version floor that matches actual syntax usage. `scripts/prepare-digest.js`
  uses `import ... with { type: 'json' }` (needs Node >= 20.19). Add `.nvmrc` (or raise
  `engines.node` in package.json) to `>=20.19.0`.
- **F-15**: Clarify `references/alert-rules.md` — "three-level classification" is a *behavior*
  taxonomy, not a 3-output classifier. `classify.js` returns only `alert` / `digest`;
  `merged alert` emerges from `merge-by-issuer` + `merge-amendments`; `intent` is written by
  the parsers, not by `classify`.
- **F-16**: Annotate `docs/code-quality-review-2026-07-08.md` — its 3 High items (H1/H2/H3) are
  already resolved by archived OpenSpec changes (`stdout-only-delivery`, `value-units-normalization`,
  `add-digest-time-seam`). Mark them resolved so the doc is no longer stale.
- **F-04**: Remove the duplicate "修订 {count} 次，" prefix in `prompts/format-alert.md`.
  `lib/alert/merge-amendments.js` already writes "N 次修订" into the summary, so the prompt
  prefix double-renders to "修订 3 次，3 次修订，…". One-line prompt edit, no behavior change.

## Capabilities

### New Capabilities

- `documentation-accuracy`: A meta-capability establishing that project docs (`references/`,
  `README.md`, `prompts/`, `docs/`) SHALL match implemented behavior. This change adds the
  requirement and the seven audit-corrected scenarios (F-04, F-09, F-10, F-11, F-14, F-15, F-16).
  Archiving this change creates `openspec/specs/documentation-accuracy/spec.md` — a small but
  real step toward the F-01 goal of docs-as-contract.

### Modified Capabilities

<!-- None. No existing openspec/specs/* requirement changes. -->

## Impact

- **Files edited**: `references/data-formats.md`, `references/architecture.md`, `references/alert-rules.md`,
  `README.md`, `docs/code-quality-review-2026-07-08.md`, `prompts/format-alert.md`, `package.json`,
  and a new `.nvmrc`.
- **No code logic changes**: all fixes are wording/annotation/tooling only.
- **No API or dependency changes** beyond the Node engine floor clarification in F-14.
- **Tests**: unaffected (no behavioral change). The existing suite (125 passing) remains green.
