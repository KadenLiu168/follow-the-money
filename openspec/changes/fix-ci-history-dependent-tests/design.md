## Context

See proposal.md - Why for motivation.

Current state (verified in the repository):

- `tests/test_feed_deployment.py` is the only test file that reads repository history. It defines `PRODUCTION_STATE_COMMIT = "f7095a5"` and materializes trusted production fixtures via `_git_blob()` (`git show <commit>:<path>`) and `_git_tree_names()` (`git ls-tree --name-only <commit>:<path>`), executed with `cwd=REPO_ROOT`.
- `.github/workflows/ci-quality-gate.yml`: the `test` job uses bare `actions/checkout@v4` (default `fetch-depth: 1`); the `classify_generated_state` job already uses `fetch-depth: 0`, but GitHub Actions jobs run in independent workspaces, so its history does not reach the `test` job.
- Repository size: ≈130 commits, near-zero pack size, so full-history fetch cost is negligible.

## Goals / Non-Goals

**Goals:**

- Give the `test` job's checkout complete repository history so `f7095a5` (and any object reachable from it) resolves on the Hosted Runner.
- Preserve the regression-test contract exactly: `PRODUCTION_STATE_COMMIT` stays `f7095a5`; fixtures stay real Git blobs, not synthetic copies.

**Non-Goals:**

- No change to `classify_generated_state` behavior, `generate-feed.yml`, any other workflow, or their shared semantics.
- No test, production-code, config, provider, schema, or documentation changes.
- No workflow refactoring, dependency upgrades, or Node deprecation handling.

## Decisions

**Decision 1: `fetch-depth: 0` on the `test` job's checkout (single-step fix).**

```yaml
test:
  ...
  steps:
    - uses: actions/checkout@v4
      with:
        fetch-depth: 0
```

Alternatives considered and rejected:

- *Fetch only `f7095a5` in a workflow step*: GitHub's server rejects fetches of arbitrary SHAs unless the repo allows it; more moving parts and fragile for a trusted-baseline contract that may later reference other commits.
- *Copy `f7095a5` blobs into a checked-in fixture directory*: weakens the guarantee that the baseline is the real production state; duplicates the authority for production history inside the repo.
- *Skip/xfail or rewrite the tests*: modifies the test contract to accommodate the CI environment — the direction of dependency is inverted.

Full-history checkout is the smallest, semantically correct alignment: the tests' stated runtime precondition is "the execution environment can resolve `f7095a5`", and `fetch-depth: 0` satisfies it directly.

**Decision 2: `contents: read` permission and all other workflow semantics stay unchanged.**

Full history does not change the security or credential-free posture; the runner already has read access to the same repository.

## Risks / Trade-offs

- [Risk] Full-history fetch adds CI time/cost → Negligible at ≈130 commits; observed pack size is near zero.
- [Risk] Someone later "optimizes" the checkout back to shallow → Regression returns immediately and visibly (the seven production-state tests fail in CI); the failure mode is loud, not silent.
- [Trade-off] `fetch-depth: 0` fetches more than strictly needed (only `f7095a5` is required today) → accepted for simplicity; no evidence the cost is meaningful at this repository size.

## Migration Plan

Single YAML edit in the `test` job; deploy by pushing to `main` and observing the `CI Quality Gate` run. Rollback is reverting the two-line `with:` block.

## Open Questions

None — the root cause and the fix are fully determined; the only remaining unknown (real CI passing) is resolved by the post-push verification step in tasks.md.
