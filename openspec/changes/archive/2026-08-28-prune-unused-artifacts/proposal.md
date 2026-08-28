## Why

Repository-wide caller-chain inspection found internal symbols, a declared-but-unused cache, a no-effect expression, and an unused development dependency that provide no current behavior or contract. Removing these artifacts reduces false API, caching, and test-capability signals without changing deterministic domain behavior.

## What Changes

- Remove the unreferenced internal symbols `OutcomeCounters`, `ProviderRegistry.enabled_ids()`, `RateRegistry.initialized_scopes()`, `normalize_host_for_hash()`, `utc_now_iso()`, and `utf8_byte_length()`, together with imports made unused by those removals.
- Remove the unused `feed.cli._client_cache` declaration while preserving `_client_for()` direct `httpx.Client` creation.
- Remove Yahoo normalization's no-effect `result.get("meta") or {}` expression.
- Remove the unused `pytest-cov` development dependency and regenerate `uv.lock` through `uv` dependency resolution.
- Do not merge similar helpers, delete retained deterministic capabilities, change serialized contracts, or add replacement abstractions.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This Change sets `skip_specs: true` because it removes unused internal and tooling artifacts without changing accepted requirements or externally observable domain behavior.

## Impact

- Source: `src/follow_the_money/providers/base.py`, `src/follow_the_money/providers/rate.py`, `src/follow_the_money/providers/urls.py`, `src/follow_the_money/events.py`, `src/follow_the_money/unicode.py`, `src/follow_the_money/feed/cli.py`, and `src/follow_the_money/providers/adapters.py`.
- Tests: existing Feed identity, Provider provenance, rate persistence, Audit/Event, Yahoo normalization, coverage, and retained-capability tests remain authoritative behavior checks; no new contract is created solely to forbid future internal names.
- Tooling: `pyproject.toml` and generated `uv.lock`; plain `pytest`, `ruff`, `mypy`, CLI help, and the canonical quality gate remain unchanged.
- Active Change overlap: `simplify-strict-config-resolution` also targets `feed/cli.py`, while `remove-unimplemented-akshare-provider` also targets `pyproject.toml` and `uv.lock`; Apply must sequence or isolate their edits and must not absorb either Change.
- Compatibility: the removals assume the named unexported symbols have no out-of-repository API commitment. Apply must stop for any symbol if contrary compatibility evidence is found and handle deprecation or contract changes separately.
- No Feed, Provider adapter mapping, Audit, Event Structuring, rate-state persistence, provenance, ordering, failure semantics, JSON Schema, runtime architecture, or production caller behavior changes.
