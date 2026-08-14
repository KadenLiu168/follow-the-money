## Context

`normalize-openspec-baseline` materialized the intended current Feed contracts and
then reopened three tasks during fresh Stage 3 review. The runtime currently skips
`CollectionLock` and `RateRegistry` whenever `dry_run=True`, checks the second-285
boundary before publication staging rather than after it, and replaces latest in
submission order without comparing the normative ownership tuple.

These are one high-risk coordination/publication lifecycle problem. The repository
already has the required lock, rate-state, monotonic-clock, staging, fsync,
no-replace dated commit, and Feed identity primitives; the repair should compose
those existing primitives rather than introduce a new persistence layer or public
surface.

## Goals / Non-Goals

**Goals:**

- Ensure every production-adapter request, including `--dry-run`, runs under the
  same output-root lock and durable rate-state lifecycle.
- Put the final pre-commit admission check after candidate staging and required
  staging `fsync`, immediately before the first irreversible rename.
- Make latest converge on the maximum `(evidence_cutoff_at, content_digest)` tuple
  regardless of candidate submission order.
- Preserve dated artifacts, idempotent recovery, typed failures, durability
  uncertainty, and the non-cancellable commit boundary.
- Add focused tests that fail against the pre-Change implementation and protect all
  three repaired semantics.
- Refresh the dependent baseline trace only after the implementation evidence is
  current and passing.

**Non-Goals:**

- Change Feed JSON Schema, `run_id`, `content_digest`, provider contracts, rate
  policy, concurrency limits, financial calculations, or CLI exit categories.
- Add a public CLI, daemon, database, cross-host coordinator, or new dependency.
- Change fixture-only dry-run behavior unless needed to make its no-publication
  contract explicit.
- Archive, commit, push, deploy, or mutate generated production Feed data.
- Refactor provider execution or filesystem publication outside the three proven
  gaps.

## Decisions

### 1. Coordinate based on possible production sends, not publication intent

`run_feed` will derive one explicit coordination condition: a normal run always
coordinates, and a dry run coordinates when it uses the production adapter registry
(`providers_fn is None`). Under that condition it acquires `CollectionLock` before
planning/cutoff and initializes `RateRegistry` after successful planning exactly as
a publishing run does. Dry run still returns before `publish_feed`, so no dated or
latest artifact is created.

Fixture-injected dry runs remain lightweight because they cannot perform a real
production-adapter send. This preserves deterministic unit-test injection without
weakening the production boundary.

Alternative considered: make every fixture dry run create lock/rate files. Rejected
because the contract specifically protects real sends, and forcing infrastructure
writes into pure fixtures adds no production safety.

### 2. Admit commit inside the publisher after durable staging

Keep one publication function rather than add a new public prepare/commit API.
`publish_feed` will use the already injectable monotonic clock plus an explicit
pre-commit deadline. It will stage the required bytes, complete staging file and
directory `fsync`, then perform one final deadline check immediately before the
first dated or latest rename. If the candidate misses admission, it removes staging
files, raises typed `pre_commit_deadline_exceeded`, and leaves dated/latest paths
unchanged.

After admission, rename and post-rename parent-directory `fsync` run without further
deadline cancellation. Idempotent recovery that needs to replace latest follows the
same stage → pre-commit fsync → admission → replace sequence.

Alternative considered: retain only the caller-side check. Rejected because time can
advance during staging and `fsync`. Alternative considered: split preparation and
commit across modules. Rejected because a second API would widen the state machine
without improving the single-process atomic boundary.

### 3. Derive latest ownership from validated Feed bytes

The publisher will derive the candidate ownership key from the canonical
`evidence_cutoff_at` and `content_digest` fields and read the current latest key
before replacement. The candidate dated artifact remains create-only and durable;
latest is replaced only when the candidate key is greater than the current key.
A lower key leaves latest unchanged. An equal key is idempotent only when the
validated content is identical; incompatible equal ownership fails closed.

The existing output-root collection lock remains the serialization boundary for
production publication. The tuple comparison is not a substitute for that lock; it
makes recovery and externally prepared candidate ordering deterministic inside the
serialized boundary.

Alternative considered: compare file SHA-256 or submission time. Rejected because
neither implements the declared `(evidence_cutoff_at, content_digest)` ownership
contract. Alternative considered: encode ownership in a separate sidecar. Rejected
because the validated Feed already carries both authoritative fields.

### 4. Test semantic mutations, not only happy paths

Focused tests will prove:

- a production-registry dry run acquires the lock and performs durable debit and
  reconciliation while creating no dated/latest Feed;
- a fixture-only dry run remains publication-free;
- advancing the monotonic clock during staging past second 285 prevents every
  rename and removes staging files;
- once admitted, a commit may cross second 300 without cancellation;
- equal-cutoff/different-digest candidates submitted in both orders produce the
  same latest bytes while retaining both dated artifacts;
- older candidates and idempotent recovery cannot regress latest ownership.

Tests must assert latest content and filesystem mutations, not merely the existence
of dated artifacts or aggregate suite success.

## Risks / Trade-offs

- **[Dry-run now writes coordination infrastructure]** → Limit this to production
  adapters and document that no Feed artifacts are written; rate-state writes are
  required because a real request was attempted.
- **[A deadline failure occurs after expensive staging]** → This is intentional:
  staging is reversible and must be measured inside the reserve; clean all stage
  files before returning the typed failure.
- **[Malformed current latest cannot provide an ownership key]** → Fail closed; the
  production planning path already validates latest before provider calls.
- **[A stale candidate commits a dated artifact but not latest]** → Preserve that
  historical artifact and return an explicit non-replacement result; never delete a
  durable dated commit to fabricate rollback.
- **[Tests accidentally rely on arbitrary raw bytes]** → Use minimal valid Feed
  fixtures for ownership tests so the test boundary matches the production
  contract.

## Migration Plan

1. Add failing focused tests for the three Stage 3 findings.
2. Repair production dry-run coordination without changing publication behavior.
3. Move final deadline admission into publication after staging `fsync`.
4. Add validated tuple comparison before latest replacement and cover recovery and
   both submission orders.
5. Run focused tests, the complete repository quality gate, OpenSpec target/all
   strict validation, and a fresh independent Stage 3 review.
6. After those gates pass, refresh `normalize-openspec-baseline` traceability and
   reclose only its three reopened tasks.

Rollback is code/spec/test-only before delivery: revert this Change's scoped files.
Do not delete durable Feed artifacts or mutate an operational output root as part of
validation or rollback.

## Open Questions

None. The current living Feed contract determines the required behavior.
