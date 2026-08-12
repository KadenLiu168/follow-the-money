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

## 2026-08-12 Change validation addendum

The following evidence was captured after implementing
`fix-multi-component-resolver-blocks`, with no archive, commit, or push action:

| Command | Exit | Fresh result |
| --- | ---: | --- |
| `.venv/bin/python -m pytest -q` | 0 | 565 tests collected and passed |
| `.venv/bin/python scripts/quality_gate.py` | 0 | unit/integration/security, workflow, CLI, ruff, format, mypy, and offline wheel build passed; `quality gate passed` |
| `.venv/bin/follow-the-money eval --mode offline --output /tmp/follow-the-money-offline-20260812.json` | 0 | 30 golden days; Recall@10 `31/31`, Top-3 Precision `30/30`, Duplicate Story Rate `0/31`, Unsupported Claim Rate `0/30`, Causal Overclaim Rate `0/0 not_applicable`; 0 provider calls, 0 LLM calls, 0 violations |
| `openspec validate fix-multi-component-resolver-blocks --strict` | 0 | Change is valid |
| `openspec validate --all --strict` | 0 | 4 passed, 0 failed |
| `openspec doctor` | 0 | OpenSpec root ok; no references declared |

Fresh requirement-to-code-to-test review confirmed: item-level aliases are
required by the closed schema and saved-output path; `resolve_block()` validates
all ownership and seed coverage before construction; Events are merged across
all packed components in canonical component order; unresolved groups remain
separate from analyst/selection/rendering and are persisted/replayed through
`pipeline/unresolved.json`; and no `block.components[0]`, alias inference,
partial merge, or unresolved audit omission remains in the pipeline path.

## `restore-production-story-family-resolution` pre-change baseline

The archived `fix-multi-component-resolver-blocks` Change is complete and its
settled boundary is the current baseline: `resolve_block(block, output, ledger,
resolver)` accepts item-level component aliases, validates the complete packed
block before construction, and returns Events plus normalized unresolved audit
data. This Change therefore owns only component-local family/pair materialization
and selection consumption; no block ownership contract is reopened.

The recorded inventory found 30 resolver outputs. One output,
`2024-03-20/resolver.json`, contains a valid non-`unknown` two-Event family and
one symmetric coexistence pair. The remaining 29 outputs contain only
`unknown`/singleton proposals and empty relation arrays. No top-level-only legacy
resolver output or invalid recorded relation was found; all 30 outputs remain
schema-valid candidates, with the 2024-03-20 fixture requiring end-to-end
selection assertions rather than semantic regeneration.

Before this Change's edits, the focused resolver/Event/selection/full-pipeline,
Bundle/replay, and evaluation suite passed 132 tests:

| Command | Exit | Result |
| --- | ---: | --- |
| `.venv/bin/python -m pytest -o addopts='' -q tests/test_resolution.py tests/test_events.py tests/test_scoring.py tests/test_gate_13_3.py tests/test_multi_component_resolver.py tests/test_gate_13_4.py tests/test_eval.py` | 0 | 132 passed in 27.86s |

## `restore-production-story-family-resolution` implementation evidence

The production resolver now has one component-local materialization result:
canonical Event IDs are built first, then non-`unknown` labels are partitioned
within that component and canonical family IDs are derived from sorted Event IDs.
`unknown` and non-unknown singleton labels remain Event-specific singleton
families. The full directed relation graph is validated atomically for exact
reciprocal declarations, family/component/response scope, relation count, and
canonical unordered pairs; violations surface as `ResolutionError` and are
wrapped by `run_pipeline` as `PipelineError` without partial Events.

Selection no longer accepts `distinct_first_member`. It receives immutable
canonical pair data, freezes eligible base order, and applies the 15-point
penalty only when the exact unordered pair with that family's frozen first
member is absent. The equivalent-order, non-transitive, threshold-crossing,
singleton, invalid-relation, live `run_pipeline`, and saved-replay tests cover
the restored branches without changing scoring weights, thresholds, tie-breaks,
or LLM passes.

The recorded 2024-03-20 family fixture was the only invalidated expected
artifact: its synthetic `fam_2024-03-20` key was replaced by the canonical
`fam_68abb01e081770fc5ffc88c11a69443e2eb063c3` derived from its two sorted Event
IDs. Its resolver output, reciprocal relation, Feed/source provenance, and
pass-output files were preserved. The new recorded-case test asserts the exact
pair, base priorities 80/75, exact-pair exemption, selected order, and a
separate 80/54 ordinary-family control where the 15-point penalty crosses the
compact threshold.

The independent review identified that the two-member golden day could not
demonstrate later-to-later non-transitivity. The checked-in
`evals/dataset/story_family_replay.json` fixture now records three related
Events with A-B and B-C pairs but no A-C pair; its replay assertion observes
80/75/54 base priorities, 80/75/39 final priorities, and C excluded after the
15-point penalty. The fixture contains a schema-valid resolver response with
canonical fact and Event IDs, and the live plus `saved_llm` `run_pipeline`
regression consumes that exact response before comparing canonical Events and
selection. Offline recorded-output validation also derives family and pair
semantics from resolver proposals and rejects disagreement with the manifest
instead of accepting an edited ranking trace alone.

## Final validation for `restore-production-story-family-resolution`

| Command | Exit | Result |
| --- | ---: | --- |
| `.venv/bin/python -m pytest -o addopts='' -q tests/test_resolution.py tests/test_events.py tests/test_scoring.py tests/test_gate_13_3.py tests/test_multi_component_resolver.py tests/test_gate_13_4.py tests/test_eval.py` | 0 | 149 passed in 19.24s |
| `.venv/bin/python scripts/quality_gate.py` | 0 | `quality gate passed`; workflow, CLI, Ruff, format, mypy, and offline wheel checks passed |
| `.venv/bin/follow-the-money eval --mode offline --output /tmp/follow-the-money-offline-20260812-stage3-story-family.json` | 0 | 30 golden days; Recall@10 `31/31`, Top-3 precision `30/30`, duplicate-story `0/31`, unsupported-claim `0/30`, violations `[]`; saved offline path made no provider/LLM calls |
| `openspec validate restore-production-story-family-resolution --strict` | 0 | Change valid |
| `openspec validate --all --strict` | 0 | 4 passed, 0 failed |
| `openspec doctor` | 0 | OpenSpec root ok; no references declared |

Fresh independent review completed with `Blocker=0`. Its High findings were
repaired: selection now isolates Decimal arithmetic; the three-member fixture
is schema-valid and is consumed by live and saved replay; and the resulting
evidence plus resolver-semantic evaluator checks cover ordinary penalty,
exact-pair exemption, and non-transitivity. The identified Medium findings were
also resolved by removing the bypassing legacy resolver helper and consuming
the configured `family_penalty`; the focused suite and complete quality gate
were rerun afterward.
