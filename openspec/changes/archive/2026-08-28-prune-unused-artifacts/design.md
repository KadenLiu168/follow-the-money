## Context

See `proposal.md` for motivation. The named Python artifacts have definitions but no current source, test, documentation, or production callers; `_client_cache` is never read or written; the Yahoo metadata expression discards its value; and repository tooling invokes plain `pytest` without coverage-plugin options. The cleanup crosses several modules and generated dependency metadata, but it must not alter any accepted deterministic or serialized contract.

Two other active untracked Changes share files with this Change: `simplify-strict-config-resolution` also targets `feed/cli.py`, and `remove-unimplemented-akshare-provider` also targets `pyproject.toml` and `uv.lock`. Neither has implementation edits yet. Apply must refresh that baseline and sequence or isolate shared-file work rather than combining scopes.

## Goals / Non-Goals

**Goals:**

- Make every deletion traceable to repository-wide caller evidence immediately before Apply.
- Preserve runtime behavior by deleting only definitions, declarations, and expressions with no observable effect.
- Let `uv` derive the minimal lockfile change after removing the direct `pytest-cov` requirement.
- Use existing behavior tests and repository checks to detect observable regressions without creating a permanent negative internal-API contract.

**Non-Goals:**

- Proving behavior equivalence between, merging, or renaming similar helpers.
- Replacing the removed symbols, cache declaration, expression, or dependency with new abstractions.
- Treating retained libraries without production callers as dead code.
- Changing public exports, provider mappings, schemas, configuration loading, runtime orchestration, or domain semantics.

## Decisions

### 1. Reconfirm each deletion at Apply time and fail closed on compatibility evidence

Search exact symbol names across current source, tests, docs, configuration, scripts, and active OpenSpec Changes before editing. Historical archived Changes may mention the names but are not callers. If any current caller or public compatibility commitment is found, stop deletion of that symbol and move compatibility handling to a separate deprecation or contract Change.

Alternative: trust the planning-time audit alone. Rejected because the checkout may change before Apply.

### 2. Delete artifacts in place without replacement wiring

Remove the six unused symbols and imports made unused by those exact removals. Delete `_client_cache` but retain `_client_for()` exactly as direct per-call `httpx.Client` construction. Delete only Yahoo's discarded metadata expression; do not otherwise restructure normalization.

Alternative: implement the apparent cache or reuse the unused metadata. Rejected because either would add new behavior outside cleanup scope.

### 3. Regenerate dependency metadata through `uv`

Remove only the direct `pytest-cov` entry from the dev dependency group, then run `uv lock`. Accept transitive package removal only as resolved by `uv`; do not hand-edit package records or upgrade unrelated dependencies.

Alternative: manually prune `uv.lock`. Rejected because the resolver, not the Change, owns transitive dependency truth.

### 4. Use existing behavioral suites and repository checks

Use exact-name searches to review the cleanup diff, then use existing focused and repository tests to prove observable behavior, including `_client_for()` construction, Yahoo normalization, Feed identity, Provider provenance, rate persistence, Audit/Event, coverage semantics, and retained capabilities. Do not add a source-text test that permanently forbids internal names when no accepted requirement owns their absence.

Alternative: add per-symbol runtime tests, source-text absence assertions, or new public API assertions. Rejected because removed code has no runtime contract and extra test scaffolding would recreate the false surface this Change removes.

## Risks / Trade-offs

- [An undocumented external consumer imports a named symbol] → Treat any compatibility evidence as a stop condition; do not claim a behavior-preserving cleanup for that symbol.
- [Another active Change edits a shared file first] → Refresh Git/OpenSpec state immediately before Apply, then sequence or isolate shared-file changes and inspect only this Change's attributable diff.
- [`uv lock` changes unrelated versions] → Inspect the lock diff and reject unrelated upgrades; rerun the ordinary locked environment and quality gates.
- [Removing a no-effect line masks adjacent Yahoo changes] → Keep the adapter diff to that one expression and rely on existing Yahoo normalization tests.

## Migration Plan

1. Re-run current caller and tooling-usage searches; stop on contradictory compatibility evidence.
2. Apply the surgical source deletions, then remove `pytest-cov` and regenerate `uv.lock` with `uv lock`.
3. Run focused regressions, CLI help, and the canonical repository/OpenSpec validation gates; inspect the complete diff for scope and behavior drift.
4. No data migration or deployment sequence is required. Rollback is the ordinary source-and-lockfile revert before any separately authorized delivery.
