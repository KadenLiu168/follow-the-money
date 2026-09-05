## Context

See `proposal.md` for motivation. The producer already constructs a validated `FeedBundle` containing the exact canonical manifest and artifact bytes before it distinguishes source failure, dry-run success, and publication. The configured `max_serialized_feed_bytes` is validated and embedded in the Feed configuration snapshot but currently has no admission check. The current product is the complete manifest-led bundle rather than the pre-bundle logical Feed mapping.

## Goals / Non-Goals

**Goals:**

- Enforce one deterministic byte limit at the producer's existing pre-publication boundary.
- Measure the exact canonical bytes that the producer would publish.
- Preserve source-failure diagnostics and all existing publication atomicity behavior.

**Non-Goals:**

- No new size configuration, schema field, reusable sizing abstraction, or error category.
- No Provider response/item-limit, remote transport, consumer validation, Feed identity, bundle layout, checkpoint, lease, rate, retry, or deployment workflow change.

## Decisions

### 1. Measure the complete canonical bundle

After `build_bundle()` succeeds, compute the candidate size as `len(bundle.manifest_bytes)` plus `len(data)` for every value in `bundle.artifact_bytes`. These are the exact bytes owned by the canonical serializer and publication path, so the check neither estimates object memory nor reserializes the logical Feed.

Alternatives rejected:

- Measuring `canonical_bytes(feed)` retains the obsolete single-document interpretation and does not bound the product actually stored and transported.
- Measuring staged filesystem files adds I/O and moves failure later than necessary.
- Applying 50 MiB per artifact permits the complete product to exceed the configured Feed limit.

### 2. Check only candidates eligible for success

Keep the existing source-completeness failure return authoritative. For healthy or degraded candidates, perform the size check after that branch and before both dry-run success and `publish_feed()`. Equality is accepted; only totals greater than the configured value fail.

The existing `FeedExecutionError` boundary is sufficient for a deterministic configuration/product admission failure. The error will report the actual and configured byte counts. No new type or helper is needed for one sum and one comparison.

Alternatives rejected:

- Checking before the source-failure branch can replace more useful Provider/source diagnostics for a candidate that can never be published.
- Checking only inside publication would let oversized dry-runs report success and would couple a product rule to filesystem mutation.

### 3. Keep the remote consumer unchanged

This Change makes the canonical producer honor its existing product configuration. It does not turn the value into a remote transport rule or add another consumer-side authority. Remote retrieval remains bounded by validated manifest-declared artifact sizes and existing bundle validation.

## Risks / Trade-offs

- [Existing custom configurations relied on oversized publication] -> Fail explicitly at the already configured limit; operators can deliberately change that authoritative producer configuration.
- [Bundle wrapper overhead makes a formerly near-limit logical Feed fail] -> Count the actual published product, with an exact-boundary regression documenting the inclusive limit.
- [A future bundle layout changes physical overhead] -> Continue measuring the exact canonical bytes returned by the bundle builder rather than maintaining a parallel estimate.

## Migration Plan

1. Add focused regressions using a deliberately small configured limit for below, equal, and above-boundary candidates, plus source-failure precedence and no-publication checks.
2. Add the minimal producer admission check between the existing source-failure and dry-run/publication branches.
3. Run focused Feed tests, the canonical repository quality gate, OpenSpec strict validation, and whitespace checks without a real Provider dry-run.

Rollback removes the producer admission check and its focused regressions. No persisted data or schema migration is required, and existing valid active bundles remain unchanged throughout.
