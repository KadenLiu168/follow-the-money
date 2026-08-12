# Final Validation Evidence

Captured on 2026-08-11 (Asia/Shanghai) after the provider, dataset, workflow,
Bundle/replay, evaluation, and quality-gate repairs. Commands below were run
from `/Users/kaden/follow-the-money`; current code, tests, and these outputs are
the acceptance evidence, while the older pre-repair handoff remains historical
review metadata only.

## Repository boundary and scope

- `git rev-parse --show-toplevel` exited `128` with `fatal: not a git repository`.
  No Git repository was initialized and no Git diff is available.
- The superseded pre-Apply handoff recorded the non-Git baseline as the
  OpenSpec root plus pre-existing local skill files, with no application code.
  The current non-Change inventory is limited to the Change's declared
  application scope: `src/`, `scripts/`, `config/`, `schemas/`, `providers/`,
  `prompts/`, `tests/`, `evals/`, `docs/`, `.github/workflows/`, package and
  README files, `pyproject.toml`, `uv.lock`, and `.gitignore`. Pre-existing
  `.claude/`, `.codex/`, `.workbuddy/`, and `openspec/config.yaml` were
  preserved. Generated caches, coverage data, and build artifacts are excluded
  from the source inventory.
- A repository text scan found no credential value or API key; the only
  `OPENAI_API_KEY` match is the intentional blank value in the credential-free
  hosted workflow.

## OpenSpec verification

| Command | Exit | Result |
| --- | ---: | --- |
| `openspec validate implement-follow-the-money-repository --strict` | 0 | Change is valid |
| `openspec validate --all --strict` | 0 | 1 passed, 0 failed |
| `openspec doctor` | 0 | OpenSpec root ok; no references declared |
| `openspec verify` | 1 | Installed CLI returns `error: unknown command 'verify'`; project gates 13.1–13.7 are the applicable Verify gates |

## Executed quality evidence

| Command | Exit | Evidence |
| --- | ---: | --- |
| `.venv/bin/pytest -o addopts=''` | 0 | 548 passed in 45.52s |
| `.venv/bin/follow-the-money eval --mode offline` | 0 | 30 unique golden days, 31 Feed items, 62 hashed source snapshots, 120 referenced four-pass files, 8 categories, 0 violations, 0 provider calls, 0 LLM calls |
| `.venv/bin/python scripts/validate_workflows.py` | 0 | workflow contracts valid |
| `.venv/bin/follow-the-money --help` | 0 | feed/brief/eval/replay commands exposed |
| `.venv/bin/ruff check src tests scripts` | 0 | All checks passed |
| `.venv/bin/ruff format --check src tests scripts` | 0 | 86 files already formatted |
| `.venv/bin/python -m mypy src scripts` | 0 | 56 source files checked |
| `uv build --offline --wheel --out-dir /tmp/follow-the-money-dist` | 0 | wheel built successfully without network access |
| `.venv/bin/python scripts/quality_gate.py` | 0 | complete quality gate passed |

Offline evaluation reported these gate values: Recall@10 `31/31 = 1.0`, Top-3
Precision `30/30 = 1.0`, Duplicate Story Rate `0/31 = 0.0`, Unsupported Claim
Rate `0/30 = 0.0`, and Causal Overclaim Rate `0/0 not_applicable`.

## Fresh independent review matrix

| Requirement family | Current implementation evidence | Test/validation evidence |
| --- | --- | --- |
| Feed/provider contracts and publication | `src/follow_the_money/feed/`, `src/follow_the_money/providers/`, real CLI path; eight mandatory adapters plus verified-optional CFTC | `tests/test_gate_13_1.py`, provider contract/manifest tests, full suite |
| Deterministic engine and normal Brief | `pipeline.py`, `brief_cli.py`, four prompt files, Responses API adapter | `tests/test_gate_13_3.py`, full suite |
| Atomic bundles and replay | `bundle.py`, recorded-clock replay and drift checks | `tests/test_gate_13_4.py` |
| Regression evaluation | 30 unique-date Feed fixtures, 62 hashed primary-source snapshots, 30 output fixtures with 120 referenced resolver/analyst/editor/language-audit files, strict four-pass schemas and Feed-backed cross-reference validation | `tests/test_gate_13_5.py`, offline CLI report |
| Workflow safety and scoped publication | both workflow YAML files plus executable validator | `tests/test_gate_13_6.py`, workflow validator |
| Repository quality and scope | `scripts/quality_gate.py`, no Git initialization, preserved pre-existing files | `tests/test_gate_13_7.py`, 548 passed, strict OpenSpec checks |

The historical review handoff is superseded by the current implementation and
validation evidence above. Two fresh independent reviews on this stable
revision found B=0 and H=0. They retained a nonblocking Medium around the
un-injected system clock used only for HTTP-date `Retry-After` parsing; one
review also noted the theoretical absence of an absolute return bound for a
non-cooperative injected adapter, while the production `httpx.Client` remains
timeout-bounded. Archive, commit, and push remain separate actions requiring
explicit authorization.
