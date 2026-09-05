## Why

The configured `max_serialized_feed_bytes` value is recorded in each Feed but is not enforced before publication. A producer can therefore build and publish a bundle larger than its declared product limit, turning a deterministic trust-boundary failure into potentially unbounded memory, disk, transport, or repository growth.

## What Changes

- Define the serialized Feed size as the sum of the canonical manifest bytes and every canonical artifact byte in the complete published bundle.
- Require every otherwise publishable healthy or degraded candidate to remain within `max_serialized_feed_bytes` before dry-run success or publication.
- Fail closed with a typed producer failure when the limit is exceeded, without publishing or replacing the active bundle.
- Preserve an existing `pipeline.status = failure` outcome as authoritative rather than replacing its source-completeness diagnostics with the publication-size check.
- Leave Provider response limits, bundle schemas, remote consumer transport, and manifest-declared artifact retrieval bounds unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `feed-evidence-pipeline`: Make the configured serialized Feed product limit an enforced producer publication boundary for the complete manifest-led bundle.

## Impact

- Producer implementation and focused regressions in `src/follow_the_money/feed/cli.py` and `tests/test_feed_cli.py`.
- Living `feed-evidence-pipeline` contract and the generated delta spec for this Change.
- No schema, Provider adapter, GitHub Actions, remote consumer, Feed identity, checkpoint, lease, rate/retry, or dependency change.
