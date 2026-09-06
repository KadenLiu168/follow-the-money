## 1. Regression Coverage

- [x] 1.1 Add a deterministic remote-consumer test with a gzip-encoded canonical artifact whose wire `Content-Length` exceeds its decoded manifest `size_bytes`, and verify the test reproduces the current rejection before the implementation change.
- [x] 1.2 Ensure focused tests still cover early oversized `Content-Length` rejection for responses without non-identity content encoding and decoded-stream overflow rejection; verify the relevant `tests/test_feed_remote.py` cases pass after the fix.

## 2. Remote Consumer Fix

- [x] 2.1 Update the shared remote response reader so `Content-Length` is compared with the decoded-byte limit only for absent or `identity` content encoding, while retaining the decoded streaming bound; verify `uv run pytest tests/test_feed_remote.py` passes.
- [x] 2.2 Run `scripts/skill/prepare-feed` against the canonical published Feed and verify it emits a complete validated logical Feed rather than the compressed `macro_release` size error, without invoking the local producer or writing persistent Feed state.

## 3. Repository Verification

- [x] 3.1 Run `.venv/bin/python scripts/quality_gate.py` and verify the canonical repository quality gate passes.
- [x] 3.2 Run `openspec doctor`, `openspec validate fix-compressed-feed-artifact-retrieval --strict`, and `openspec validate --all --strict`, and verify all OpenSpec checks pass.
