## 1. Production-state fixtures

- [x] 1.1 Add a fixture builder that extracts the real `f7095a5` blobs (checkpoint, lease, rate-registry, all four scope files including `scope-3b806f91752a2756.json`, v3 `feed-manifest.json` and its inventoried artifacts) into a `tmp_path` runtime root, rewrites `root_identity` to the fixture root inside the builder only, and documents provenance (source commit + rewrite rule) in a docstring; verify the builder round-trips byte-identical payloads except the rewritten `root_identity`

## 2. Deployment-level regression tests

- [x] 2.1 Test E — `root_identity` consistency: `prepare` succeeds (mode=armed) when the registry `root_identity` equals the runtime root's `resolve()`, and fails closed with the existing typed error on any mismatch; verify with a focused `pytest` run
- [x] 2.2 Test A/A′ — armed recovery admission and window planning: established state + empty `feeds/` yields `mode=armed` with the restored checkpoint (cutoff 2026-09-08) preserved through preparation; and `plan_window` on that checkpoint with a current cutoff yields the bounded 72h bootstrap window with the explicit gap warning `[2026-09-08, window.start)`; verify with a focused `pytest` run
- [x] 2.3 Test B — migration input rejection: the real v3 bundle present as the active product makes `prepare` fail closed with the typed migration error (resolved contract is the sole `empty_valid_for_window` authority); verify with a focused `pytest` run
- [x] 2.4 Test C — retained scope continuity: `us_gov`, `china_gov`, `sec_edgar` keep their real `last_dispatch_wall` / `refill_wall_anchor` values through preparation (not bootstrap defaults); verify with a focused `pytest` run
- [x] 2.5 Test D — obsolete scope tolerance: a registered scope with no current policy (`yahoo_market`) is tolerated, its scope file is required, and a registry expecting it with the file missing fails closed; verify with a focused `pytest` run
- [x] 2.6 Test F — no migration branch for current products: a current v4 active product takes the normal (non-migration) preparation path; the migration branch is entered only when the active product is `schema_version == 3`; verify with a focused `pytest` run

## 3. State restoration

- [x] 3.1 Restore `.feed-state/` to the exact `f7095a5` blobs (including re-adding the `yahoo_market` scope file); verify `git diff f7095a5 -- .feed-state` is empty and the working tree contains all four scope files
- [x] 3.2 Empty `feeds/` by deleting the contaminated `feed-*-d2125e4e*.json` generation (no v3 bundle is restored); verify no `d2125e4e` artifacts and no `feed-manifest.json` remain in the working tree
- [x] 3.3 Confirm the restore commit changes only `.feed-state/` and `feeds/` paths (plus tests/docs), and that no restored file rewrites or bypasses `root_identity`

## 4. Verification

- [x] 4.1 Run the full local suite and static checks: `pytest`, `ruff`, `mypy`; all green
- [x] 4.2 Run `.venv/bin/python scripts/quality_gate.py`; passes
- [x] 4.3 Run `openspec validate restore-feed-production-state --strict`, `openspec validate --all --strict`, and `openspec doctor`; all pass with the deliberate `skip_specs` opt-out recorded
- [x] 4.4 Adversarial self-review against the proposal's forbidden-fixes list: no `/Users/kaden` → `/home/runner` hard-coded substitution, no `root_identity` validation change, no `.feed-state` deletion/bootstrap, no Aug-10 state accepted as baseline, no whole-repo revert, no Change 2 scope creep; record findings

  Findings (2026-09-18): worktree `rate-registry.json` still carries the verbatim `/home/runner/...` `root_identity` (the only rewrite lives inside the test fixture builder, targeting `tmp_path.resolve()`); `src/` untouched (`git status` shows only `.feed-state/`, `feeds/`, `tests/`, `docs/`, `openspec/` paths); checkpoint baseline is the real 2026-09-08 cutoff; no CI guards or `yahoo_market` deregistration added.
- [x] 4.5 Check `docs/runbooks/` for coverage of dispatch-triggered recovery runs; update only if the existing text does not cover them

## 5. Operational recovery (post-merge)

- [ ] 5.1 Push the change; confirm the CI path-exclusion applies to the restore commit's changed paths
- [ ] 5.2 Dispatch `generate-feed` once (armed run: prepare → collect → finalize); apply the D5 gate — verify the pushed product is v4 five-domain with a cutoff advancing from the 2026-09-08 baseline, the plan recorded the bounded 72-hour window with the explicit coverage-gap warning for `[2026-09-08T04:50:10.689Z, window.start)`, and `.feed-state/` retains the real state until finalize advances the checkpoint; if collect fails, triage it as a new independent Provider/runtime issue
