## Why

The canonical published Feed consumer rejects valid small artifacts when `raw.githubusercontent.com` applies gzip and the encoded HTTP `Content-Length` is larger than the manifest-declared canonical artifact size. This currently prevents normal `/money` invocation even though the decoded artifact bytes, exact size, and digest are valid.

## What Changes

- Define manifest `size_bytes` as the size of the transfer-decoded canonical artifact bytes consumed and validated by the Feed bundle boundary.
- Prevent an encoded wire `Content-Length` from being compared directly with that decoded artifact limit while retaining bounded streaming and exact final size and digest validation.
- Add a regression covering a valid gzip response whose encoded length exceeds its decoded manifest size.
- Preserve fail-closed behavior for oversized decoded responses, exact-size mismatches, digest mismatches, redirects, HTTP errors, and incomplete bundles.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `feed-evidence-pipeline`: Clarify and enforce remote artifact size validation across HTTP content encoding so valid canonical bundles remain consumable without weakening transport or integrity checks.

## Impact

- Remote consumer: `src/follow_the_money/feed/remote.py`.
- Focused regression coverage: `tests/test_feed_remote.py` and, only if launcher behavior needs explicit coverage, `tests/test_feed_prepare.py`.
- No Feed schema, manifest shape, canonical serialization, Provider, producer, dependency, credential, fallback, or Host Agent orchestration change.
