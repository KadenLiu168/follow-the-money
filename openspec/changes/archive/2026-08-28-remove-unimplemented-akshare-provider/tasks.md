## 1. Pin the intended provider set in tests

- [x] 1.1 Confirm the linked Linear issue's scope, milestone, and `blockedBy` / `blocks`; recheck active Changes and sequence or isolate the known `simplify-strict-config-resolution` overlap before editing shared configuration tests. Stop for scope review if Linear is missing or blocked, or if the shared-test baseline is ambiguous.
- [x] 1.2 Update exact shipped-provider count, manifest-set, registry-completeness, and concrete-adapter expectations to the nine implemented providers; remove only AKShare-specific disabled/unverified/coverage/import assertions and stale comments.
- [x] 1.3 Confirm the general synthetic config tests still reject enabled unverified providers and unverified mandatory-coverage members; do not replace them with a fake shipped provider.
- [x] 1.4 Run `.venv/bin/python -m pytest tests/test_config.py tests/test_manifest_registry.py tests/test_adapters.py tests/test_gate_13_1.py` before implementation and confirm the updated provider-count and manifest-set expectations fail against the retained AKShare scaffold.

## 2. Remove the live scaffold

- [x] 2.1 Delete `providers/akshare/manifest.yaml` and the AKShare entry from `config/providers.yaml`, leaving all six coverage rows, members, minimums, capabilities, and optional flags unchanged.
- [x] 2.2 Remove `[project.optional-dependencies].akshare` from `pyproject.toml` and run `uv lock` so AKShare and dependencies reachable only from that extra disappear from `uv.lock`; do not hand-edit the lockfile or change unrelated dependency constraints.
- [x] 2.3 Remove only the `pid != "akshare"` manifest filter from `build_registry`; preserve the explicit concrete adapter mapping and existing resolved-runtime enablement filtering.

## 3. Verify the cleanup and unchanged contracts

- [x] 3.1 Run `.venv/bin/python -m pytest tests/test_config.py tests/test_manifest_registry.py tests/test_adapters.py tests/test_gate_13_1.py` and verify exact shipped-provider, concrete-adapter, general unverified-provider, mandatory-coverage, provenance, and manifest-completeness checks pass.
- [x] 3.2 Run `uv sync --frozen --all-groups`, verify live source/config/tests/docs/packaging/provider paths and `uv.lock` contain no AKShare scaffold reference, and confirm archived Changes plus this planning record were not rewritten for residue removal.
- [x] 3.3 Run `.venv/bin/python scripts/quality_gate.py`, `openspec doctor`, `openspec validate remove-unimplemented-akshare-provider --strict`, `openspec validate --all --strict`, and `git diff --check`; record the actual results without archiving, committing, pushing, or updating Linear.
