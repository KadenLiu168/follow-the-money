## 1. CI checkout fix

- [x] 1.1 In `.github/workflows/ci-quality-gate.yml`, add `fetch-depth: 0` to the `test` job's `actions/checkout@v4` step (a `with:` block) and verify `git diff` shows no other functional changes
- [x] 1.2 Verify workflow YAML validity via the project's existing workflow validation: run `actionlint -config-file .github/actionlint.yaml` (or the repository's equivalent quality-gate validation) and confirm no new errors for `ci-quality-gate.yml`

## 2. Local verification of the Git-history precondition

- [x] 2.1 In a full-history clone, verify `git cat-file -e f7095a5^{commit}` succeeds, `git ls-tree --name-only f7095a5:.feed-state` lists the historical production state files, and `git show f7095a5:.feed-state/feed-checkpoint.json` reads the blob

## 3. Regression test verification

- [x] 3.1 Run the seven affected production-state tests in `tests/test_feed_deployment.py` (`test_production_state_fixture_round_trips_blobs_except_root_identity`, `test_fixture_root_identity_passes_and_mismatch_fails_closed`, `test_restored_state_arms_with_checkpoint_continuity_and_bounded_window`, `test_real_v3_product_as_migration_input_fails_closed`, `test_retained_scopes_keep_real_dispatch_state_through_preparation`, `test_obsolete_yahoo_market_scope_is_tolerated_and_required`, `test_current_v4_product_takes_normal_preparation_path`) and verify all pass
- [x] 3.2 Verify test semantics are untouched: `PRODUCTION_STATE_COMMIT = "f7095a5"` remains, `_git_blob()` / `_git_tree_names()` still read the real historical commit, and no test was skipped, xfailed, or rewritten

## 4. Full local quality gate

- [x] 4.1 Run `uv sync --frozen --all-groups` and `uv run pytest -q` and verify the full suite passes
- [x] 4.2 Run the repository's canonical quality gate (`.venv/bin/python scripts/quality_gate.py`) and verify it passes

## 5. CI verification on GitHub

- [ ] 5.1 Push to `main`, confirm the new `CI Quality Gate` run passes all steps (`classify_generated_state`, `Validate GitHub Actions semantics`, `Clean install`, `Credential-free test suite`, `Validate workflows and entry points`), and confirm the log no longer contains `fatal: Not a valid object name f7095a5`
