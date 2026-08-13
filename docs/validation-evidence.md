# Validation Evidence — remove-standalone-runtime (2026-08-13)

Scope: removal of the embedded LLM runtime and the public CLI product form,
retention of the deterministic core. All commands below were run fresh in the
repository after the Change's edits.

## Final gates (task 8.2)

| Gate | Command | Result |
| --- | --- | --- |
| Spec-driven change validity | `openspec validate remove-standalone-runtime --strict` | `Change 'remove-standalone-runtime' is valid` |
| Full test suite | `uv run pytest -q` | `403 passed in 23.97s` |
| Lint | `uv run ruff check src tests scripts` | `All checks passed!` |
| Format | `uv run ruff format --check src tests scripts` | `63 files already formatted` |
| Type check | `uv run mypy src scripts` | `Success: no issues found in 41 source files` |
| Workflow validation | `uv run python scripts/validate_workflows.py` | `workflow contracts valid` |
| Minimal entry help | `uv run python -m follow_the_money.feed.cli --help` | exit 0; exposes `--config/--output-root/--dry-run/--cutoff/--window-start/--status-file` |
| Wheel build | `uv build --offline --wheel --out-dir /tmp/follow-the-money-dist` | built `follow_the_money-0.1.0-py3-none-any.whl` |
| Repository quality gate | `uv run python scripts/quality_gate.py` | `quality gate passed` |

## Removed surface (git history retains everything)

- LLM runtime: `openai` dependency, `llm.py`, `prompts/`, `llm:`/`audit_severity:`
  config sections, `LlmRuntime`/`PassConfig`/`AuditSeverity`, LLM environment
  variables, `eval_live.py`.
- Public CLI / orchestration: `cli.py`, `__main__.py`, `[project.scripts]`,
  `brief_cli.py`, `pipeline.py`, `scripts/skill/follow-the-money-skill`.
- Old four-pass contract layer: `analysis.py`, `editor.py`, `brief.py`,
  `render.py`, `engine/resolution.py`, `audit_language_findings`, and schemas
  `resolver-output`, `analyst-output`, `editor-output`, `language-audit-output`,
  `event`, `analysis`, `verified-event-packet`, `brief`, `degraded-report`,
  `run-manifest`. `boundary.py` lost its packet-assembly functions (sole
  consumer was `pipeline.py`); `events.py` retained as pure deterministic
  functions without the deleted `event.schema.json`.
- Eval/provenance machinery: `eval_offline.py`, `eval_metrics.py`,
  `evals/dataset/` (feeds, sources, pass_outputs, outputs, manifest,
  story-family replay), `scripts/build_golden_dataset.py`,
  `scripts/refresh_golden_sources.py`, `bundle.py`.

## Retained surface (credential-free)

- Feed collection: `feed/`, `providers/`, `ledger.py`, `canonical.py`,
  `unicode.py`, `schema.py`, `boundary.py` (build fingerprint),
  `engine/candidates.py`, `engine/entities.py`, `engine/feed_health.py`,
  `engine/title.py`, `events.py`, `market/`, `state.py`, `watchlist.py`.
- No-caller deterministic core with tests: `scoring.py`, `selection.py`,
  `audit.py` (`ClaimAuditor` + safety lexicon).
- Minimal internal Feed entry: `main()` on `feed/cli.py` behind
  `scripts/feed/follow-the-money-feed`; exit codes 0/1/2 preserved.
- Regression contract `tests/test_no_llm_contract.py` audits: no `openai`
  in `pyproject.toml`/`uv.lock`, no `prompts/`, no `evals/`, no removed
  modules/schemas, no `llm:`/`audit_severity:` config, no `OPENAI_*` env;
  configuration loads credential-free; the minimal entry publishes a
  validating Feed; retained rules stay deterministic and LLM-free.
