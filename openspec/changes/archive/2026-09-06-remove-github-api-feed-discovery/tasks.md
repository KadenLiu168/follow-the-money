## 1. Transport Contract Tests

- [x] 1.1 Update `tests/test_feed_remote.py` to model only canonical `raw.githubusercontent.com/{repository}/main/feeds/` responses, assert the manifest is requested first, assert every request remains under that root, and assert no request reaches `api.github.com`; verify the changed transport test fails against the pre-change consumer.
- [x] 1.2 Remove commit-discovery-only cases while retaining or adapting HTTP/redirect/timeout/size, invalid manifest/artifact/schema/generation/identity, temporary-storage, and no-local-fallback regressions; verify the focused remote suite still exercises each fail-closed boundary.

## 2. Remote Consumer

- [x] 2.1 Simplify `src/follow_the_money/feed/remote.py` to build manifest and declared-artifact URLs directly from the closed repository, `main` branch, and `feeds` root, removing GitHub API discovery, commit-SHA parsing, and newly unused imports/constants/helpers; verify `uv run pytest tests/test_feed_remote.py tests/test_feed_prepare.py` passes.

## 3. Documentation and Acceptance

- [x] 3.1 Update `SKILL.md`, `README.md`, `README.zh-CN.md`, `docs/architecture.md`, and `docs/feed-contract.md` plus `tests/test_feed_documentation.py` to describe canonical-main raw retrieval, zero GitHub REST API access, unchanged validation, and terminal remote failure; verify `uv run pytest tests/test_feed_documentation.py` passes and no current runtime-contract documentation claims commit-pinned or Git reference API consumption.
- [x] 3.2 Run `.venv/bin/python scripts/quality_gate.py`, `openspec doctor`, `openspec validate remove-github-api-feed-discovery --strict`, and `openspec validate --all --strict`; verify every command passes without Feed schema, producer, Provider, Agent capability, credential, or fallback changes.
