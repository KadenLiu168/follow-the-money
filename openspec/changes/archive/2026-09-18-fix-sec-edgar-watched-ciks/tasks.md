## 1. Correct watched-company CIKs

- [x] 1.1 Correct the 6 wrong CIKs in `config/config.yaml` `watched_companies` to the
  verified SEC identities (Oaktree `0000949509`, Baupost `0001061768`, Coatue
  `0001135730`, Tiger Global `0001167483`, Scion `0001649339`, ARK `0001697748`);
  preserve the existing list order and the two already-correct entries (Berkshire
  `0001067983`, Pershing Square `0001336528`); verify the resolved config snapshot
  contains exactly the 8 verified CIKs

## 2. Tighten watched-companies config validation

- [x] 2.1 In `src/follow_the_money/config/load.py` `_parse_watched_companies`, add a
  `re.fullmatch(r"\d{10}", cik)` format check (fail closed with `ConfigError`) and
  keep the existing duplicate check; mirror the `watched_form4_issuers` format/duplicate
  behavior. Do NOT add an ordering enforcement (runtime `sorted()` on
  `cfg.watched_companies` in `feed/cli.py` — adapter construction and
  `_feed_config_snapshot` — already delivers deterministic CIK order)
- [x] 2.2 Verify a non-ten-digit CIK raises `ConfigError` and a duplicate CIK raises
  `ConfigError` with a focused `pytest` run

## 3. SEC identity verification evidence

- [x] 3.1 Add/update `references/provider-source-verification.md` documenting each
  watched company's official SEC identity: the verified CIK, the SEC submissions API
  name returned, and the verification source (`https://data.sec.gov/submissions/CIK<cik>.json`)
  for all 8 watched companies

## 4. Regression tests

- [x] 4.1 Add a shipped watched-CIK exact-set regression that asserts the resolved
  production `watched_companies` CIK set equals the 8 verified CIKs, so any silent
  drift in a shipped CIK fails the test; in the same regression assert the embedded
  Feed configuration snapshot orders the 8 CIKs ascending by normalized CIK, proving
  the ordering is runtime-derived given the checked-in list order is not CIK order
- [x] 4.2 Add config-validation regressions: a non-ten-digit CIK and a duplicate CIK
  each fail closed; verify with a focused `pytest` run

## 5. Verification

- [x] 5.1 Run focused tests for the touched modules; then the full suite: `pytest`,
  `ruff`, `mypy`; all green
- [x] 5.2 Run `.venv/bin/python scripts/quality_gate.py`; passes
- [x] 5.3 Run `openspec validate fix-sec-edgar-watched-ciks --strict` and
  `openspec validate --all --strict`; all pass
- [x] 5.4 Confirm scope: no SEC producer URL logic touched, no `validate.py`
  source-link regex touched, no digest/canonical-bytes change, SEC complete-slice
  fail-closed semantics and coverage policy unchanged
