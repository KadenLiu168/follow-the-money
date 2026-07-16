## 1. Format fix (unblock feed first)

- [x] 1.1 Run `npm run format` (`prettier --write .`); confirm via `git status` that ONLY these 3 files change: `scripts/check-alerts.js`, `tests/lib/resolve-prompts.test.js`, `tests/fixtures/13d-html-shape.html`
- [x] 1.2 Run `npm run format:check` and confirm the whole repo passes (exit 0)
- [x] 1.3 Run `npm test` and confirm the `<br>`→`<br/>` reformat of `13d-html-shape.html` does not break `tests/parsers/thirteen-dg.test.js`
- [x] 1.4 Commit the 3 formatted files (e.g. `style: prettier --write 3 unformatted files`)

## 2. Add dedicated CI workflow

- [x] 2.1 Create `.github/workflows/ci.yml` with triggers `push` to `main` and `pull_request` to `main`; steps: `actions/checkout@v5` → `actions/setup-node@v5` (`node-version-file: .nvmrc`, `cache: npm`) → `npm ci` → `npm test` → `npm run lint` → `npm run format:check`
- [x] 2.2 Confirm no `continue-on-error` on the gate steps so the workflow fails on any non-zero exit

## 3. Simplify aggregate workflow

- [x] 3.1 Edit `.github/workflows/aggregate.yml`: remove the `npm test`, `npm run lint`, and `npm run format:check` steps; keep `checkout` → `setup-node` → `npm ci` → `node scripts/aggregate.js` → commit/push
- [x] 3.2 Confirm `aggregate.yml` no longer references the three gate scripts

## 4. Verify

- [ ] 4.1 Push and confirm `ci.yml` runs green on the push trigger
- [ ] 4.2 Trigger `aggregate.yml` (schedule or `workflow_dispatch`) and confirm it fetches and commits feed data without being blocked by format/lint/test
- [x] 4.3 (optional) `openspec validate ci-gate-and-format` passes for this change
