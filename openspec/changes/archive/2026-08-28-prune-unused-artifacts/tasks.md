## 1. Reconfirm Scope and Baseline

- [x] 1.1 Refresh Git/OpenSpec state; search exact target names and the Yahoo no-effect expression across current source, tests, docs, scripts, configuration, public exports, and active OpenSpec Changes; confirm each target has no caller or compatibility commitment. Sequence or isolate the known `feed/cli.py` and `pyproject.toml`/`uv.lock` overlaps, and stop any deletion if contrary compatibility evidence or an unresolved shared-file conflict appears.
- [x] 1.2 Confirm repository scripts, CI, docs, pytest configuration, and the canonical quality gate do not invoke `pytest-cov` or coverage-plugin options, and run the affected existing Provider, rate, Feed client, Yahoo normalize, Audit, and Event tests as a pre-change baseline.

## 2. Remove Runtime Artifacts

- [x] 2.1 Delete `OutcomeCounters`, `ProviderRegistry.enabled_ids()`, `RateRegistry.initialized_scopes()`, `normalize_host_for_hash()`, `utc_now_iso()`, `utf8_byte_length()`, `_client_cache`, and Yahoo's discarded `result.get("meta") or {}` expression; remove only imports made unused by these deletions and add no replacement abstraction or behavior.
- [x] 2.2 Run the affected existing tests GREEN; inspect `_client_for()` and Yahoo adapter diffs to confirm direct client creation and normalization behavior are otherwise unchanged.

## 3. Remove the Unused Development Dependency

- [x] 3.1 Remove only `pytest-cov` from the `pyproject.toml` dev dependency group, run `uv lock`, and verify the lock diff contains only resolver-derived removal of that direct requirement and packages no longer transitively needed, with no unrelated version upgrades.
- [x] 3.2 Run `uv sync --frozen --all-groups`; leave the complete plain-pytest, CLI, lint, format, type-check, and build verification to the canonical quality gate after the diff is stable.

## 4. Final Contract and Repository Verification

- [x] 4.1 Re-run exact-name searches and confirm there are no source definitions or source/test/doc import/caller references; allow only planning-history mentions.
- [x] 4.2 Run `.venv/bin/python scripts/quality_gate.py`, `openspec doctor`, `openspec validate prune-unused-artifacts --strict`, `openspec validate --all --strict`, and `git diff --check`; inspect the final diff against the proposal non-goals and record any unresolved compatibility risk or follow-up issue.
