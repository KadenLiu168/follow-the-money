## 1. Remove the LLM runtime

- [x] 1.1 Remove the `openai` dependency from `pyproject.toml` and regenerate the lock file.
- [x] 1.2 Delete `src/follow_the_money/llm.py` and the `prompts/` directory.
- [x] 1.3 Remove the `llm:` and `audit_severity:` sections from `config/config.yaml`; drop `LlmRuntime`/`PassConfig` from `config/model.py` and their loading/startup rejection from `config/load.py`.
- [x] 1.4 Remove the LLM environment variables (`OPENAI_API_KEY`, `OPENAI_MODEL`, organization/project, per-pass timeouts) from `.env.example`.
- [x] 1.5 Delete `src/follow_the_money/eval_live.py`.

## 2. Remove the public CLI and LLM orchestration

- [x] 2.1 Delete `src/follow_the_money/cli.py`, `src/follow_the_money/__main__.py`, and the `[project.scripts] follow-the-money` entry from `pyproject.toml`.
- [x] 2.2 Delete `src/follow_the_money/brief_cli.py` and `src/follow_the_money/pipeline.py`.
- [x] 2.3 Add a minimal `main()` to `src/follow_the_money/feed/cli.py` preserving the current feed arguments (config/output-root/dry-run/cutoff/status-file) and exit-code contract; repoint `scripts/feed/follow-the-money-feed` to it (no public CLI); delete `scripts/skill/follow-the-money-skill`.

## 3. Remove the old four-pass contract layer

- [x] 3.1 Delete `src/follow_the_money/analysis.py`, `editor.py`, `brief.py`, and `render.py`.
- [x] 3.2 Remove the language-audit pass mapping from `src/follow_the_money/audit.py`, retaining `ClaimAuditor` and the safety lexicon.
- [x] 3.3 Delete `src/follow_the_money/engine/resolution.py` (sole production consumer was `pipeline.py`).
- [x] 3.4 Delete the old-contract schemas from `schemas/`: `resolver-output`, `analyst-output`, `editor-output`, `language-audit-output`, `event`, `analysis`, `verified-event-packet`, `brief`, `degraded-report`, `run-manifest`; retain `feed` and any schema still consumed by the retained engine and its tests.

## 4. Remove LLM-era evaluation and provenance machinery

- [x] 4.1 Delete `src/follow_the_money/eval_offline.py` and `src/follow_the_money/eval_metrics.py`.
- [x] 4.2 Delete the golden-dataset four-pass fixtures (recorded LLM outputs, replay contracts, `evals/dataset/pass_outputs/`) and `scripts/build_golden_dataset.py`; keep `evals/dataset/sources/` only where retained tests consume it, otherwise delete.
- [x] 4.3 Delete `scripts/refresh_golden_sources.py`.
- [x] 4.4 Delete `src/follow_the_money/bundle.py` (brief run-bundles and replay).

## 5. Retain the deterministic core

- [x] 5.1 Keep `scoring.py` and `selection.py` with their tests; remove imports of deleted modules and confirm they have no production caller.
- [x] 5.2 Keep the `ClaimAuditor` safety audit with its tests; delete `audit_language_findings`.
- [x] 5.3 Keep `ledger.py`, `boundary.py`, `canonical.py`, `unicode.py`, `schema.py`, `engine/candidates.py`, `engine/entities.py`, `engine/feed_health.py`, `market/`, `watchlist.py`, `state.py`, `feed/`, and `providers/`; remove imports of deleted modules.
- [x] 5.4 Update `config/model.py` and `config/load.py` so the surviving configuration loads credential-free and fails closed on deterministic contracts only.

## 6. Test suite surgery

- [x] 6.1 Delete tests exercising removed modules: LLM adapter tests, brief-chain and gate tests that depend on the four-pass pipeline, resolver/analyst/editor merge tests, live/offline evaluation tests, and bundle replay tests.
- [x] 6.2 Adjust retained tests (config, feed pipeline, market, scoring, selection, audit) for the removed LLM configuration surface.
- [x] 6.3 Add regression tests for the retained no-LLM contract: configuration loads without credentials, the minimal Feed entry publishes a validating Feed, and the retained rules (scoring/selection/ClaimAuditor) remain deterministic and LLM-free.

## 7. Docs, Skill, and workflows

- [x] 7.1 Rewrite `SKILL.md` for the transitional state: collect the evidence Feed, hand evidence to the host Agent, defer the structured Agent contract and fixed Brief pipeline to a future Change.
- [x] 7.2 Update READMEs and `.env.example` to the credential-free deterministic engine.
- [x] 7.3 Update or delete `docs/architecture.md` and `docs/evaluation.md` to the retained engine; keep `feed-contract.md` and `scoring.md` accurate.
- [x] 7.4 Update `scripts/quality_gate.py` (remove the CLI `--help` check, adjust commands) and `.github/workflows/` for the surviving surface.

## 8. Final gates

- [x] 8.1 Run the focused retained test suites and repair every regression within this Change's scope.
- [x] 8.2 Run `openspec validate remove-standalone-runtime --strict`, schema checks, static/type/lint checks, the full test suite, and the repository quality gate; record exact fresh outputs.
- [x] 8.3 Perform a fresh requirement-to-design-to-code-to-test review against this proposal; fix all proven Blocker/High and necessary in-scope Medium findings and rerun invalidated gates.
