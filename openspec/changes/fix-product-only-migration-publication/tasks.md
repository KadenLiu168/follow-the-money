## 1. Reproduce Migration Staging Boundaries

- [x] 1.1 Add a temporary-repository regression for established `.feed-state/` plus tracked `feeds/latest.json` and no legacy runtime paths under `feeds/`; reproduce the current nonexistent-pathspec failure before the fix, then verify corrected publication commits the exact intended path set.
- [x] 1.2 Add or strengthen a complete legacy runtime-state migration regression; verify exact tracked legacy runtime deletions remain in the generated-state commit.
- [x] 1.3 Add regressions that remove a required current runtime or manifest-inventoried path, and that present an untracked `feeds/latest.json`; verify publication fails closed without silently omitting required state or removing an untracked legacy product.

## 2. Correct Product-Only Migration Publication

- [x] 2.1 Require `feeds/latest.json` to be tracked before removal, restrict optional legacy runtime deletion candidates to exact paths tracked by the repository index, and leave required current runtime and bundle paths mandatory; verify the product-only and complete-legacy regressions pass.
- [x] 2.2 Preserve generic publication safeguards for unrelated pre-staged paths, unexpected staged paths, empty staging, non-force push, and push conflict; verify the existing Git publication tests remain unchanged and pass.

## 3. Verify Repository Contracts

- [x] 3.1 Run `.venv/bin/python -m pytest tests/test_feed_deployment.py tests/test_feed_deployment_separation.py tests/test_workflows.py` and verify migration, Git safety, zero-network ordering, and workflow regressions pass.
- [x] 3.2 Run `.venv/bin/python scripts/quality_gate.py` and verify the canonical repository quality gate passes.
- [x] 3.3 Run `openspec doctor`, `openspec validate fix-product-only-migration-publication --strict`, and `openspec validate --all --strict`; verify all OpenSpec checks pass.

## 4. Verify Hosted Lifecycle

- [ ] 4.1 After explicit authorization for the external repository mutation, trigger the hosted Feed workflow and verify product-only migration publishes the exact generated-state commit, deletes `feeds/latest.json`, performs zero Provider requests, and exits before collection.
- [ ] 4.2 After migration completion and any existing recovery boundary, trigger the next hosted invocation and record whether normal arming and collection execute; hand that evidence to the separate `align-provider-runtime-contract-and-html-parsing` Change without modifying or completing its verification as part of this Change, and do not treat external Provider success as unconditional.
