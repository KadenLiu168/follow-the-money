## MODIFIED Requirements

### Requirement: Durable collection coordination and rate discipline
Before reading the current latest Feed or capturing the cutoff, collection SHALL
acquire one exclusive lock in the explicit output root and hold it through
publication. Provider dispatch SHALL use the persistent closed output-root registry
and per-scope rate state, durably debit and install the crash-conservative provisional
cooldown before every possible send, reconcile controlled outcomes without refunding
the send, honor valid `Retry-After`, and fail closed on missing, corrupt, unknown, or
unrecoverable active state. This coordination SHALL apply to every production-adapter
send, including a run requested with `--dry-run`. Collection SHALL enforce the
configured global and per-host concurrency limits, stable provider-ID result order,
sequential pagination unless the manifest proves otherwise, and cancellation with no
late Feed mutation.

#### Scenario: Two entries share one output root
- **WHEN** a second process starts with the same output root while the first holds the collection lock
- **THEN** it waits without consuming provider concurrency and plans from the latest state only after lock acquisition, or fails typed `collection_lock_timeout` before any provider call

#### Scenario: A dispatched process crashes
- **WHEN** a process exits after the durable pre-send debit and before controlled reconciliation
- **THEN** the next process retains the debit and provisional cooldown instead of resetting the scope or assuming no request occurred

#### Scenario: Provider completions are reordered
- **WHEN** identical provider fixtures complete under different schedules within the concurrency limits
- **THEN** normalized provider outcomes and Feed bytes remain in stable provider-ID order

#### Scenario: Production dry run can send a request
- **WHEN** `--dry-run` dispatches an enabled production adapter that may contact its verified host
- **THEN** the run acquires the output-root collection lock and durably debits and reconciles rate state exactly as a publishing run, while creating no dated or latest Feed artifact

### Requirement: Bounded command deadline and non-cancellable commit
The minimal Feed entry SHALL enforce the existing 300-second command-start monotonic
deadline with an exact 15-second pre-commit reserve. Lock waits, rate waits,
pagination, retries, request attempts, reversible processing, and staging `fsync`
SHALL fit before second 285. Once a fully staged candidate is admitted to filesystem
commit by second 285, rename and parent-directory `fsync` SHALL run to their normal
result without cancellation or rollback; completion after second 300 MAY only add
`commit_elapsed_overrun` to external status or stderr and SHALL NOT change the
already hashed Feed bytes.

#### Scenario: No attempt fits before the reserve
- **WHEN** the next wait or request attempt cannot complete within the remaining pre-commit budget
- **THEN** collection stops with the typed deadline outcome before that attempt begins

#### Scenario: Staging crosses the reserve boundary
- **WHEN** candidate staging or its required pre-commit `fsync` advances the monotonic clock to or beyond second 285
- **THEN** publication removes reversible staging files and fails typed `pre_commit_deadline_exceeded` before any dated or latest rename

#### Scenario: Commit crosses the nominal deadline
- **WHEN** a candidate is fully staged and admitted before second 285 but durable commit completes after second 300
- **THEN** commit finishes without cancellation or rollback and reports the overrun only outside the immutable Feed payload

### Requirement: Durable monotonic publication
Before publication, a healthy or degraded candidate SHALL pass Feed schema,
semantic, provenance, identity, and digest validation. Publication SHALL create the
immutable dated `feeds/daily/YYYY-MM-DD/<run_id>.json` artifact before atomically
replacing `feeds/latest.json`, using unpredictable same-parent staging, create-only
writes, file and directory `fsync`, atomic no-replace dated rename, same-directory
latest replacement, and parent-directory `fsync`. It SHALL be idempotent for the
same run and SHALL use the maximum `(evidence_cutoff_at, content_digest)` tuple for
latest ownership independently of candidate submission order. Failure or durability
uncertainty SHALL remain explicit and SHALL NOT fabricate rollback guarantees.

#### Scenario: Valid candidate publishes
- **WHEN** all validation succeeds and durable filesystem primitives are available
- **THEN** the immutable dated artifact becomes durable before latest is replaced and both carry the same validated Feed

#### Scenario: Latest replacement fails
- **WHEN** the dated artifact is durable but latest replacement fails
- **THEN** the previous valid latest remains unchanged and the run reports a retryable publication failure without deleting the dated artifact

#### Scenario: Stale candidate reaches publication
- **WHEN** an older valid externally prepared candidate is submitted after a newer latest Feed
- **THEN** it may retain its immutable dated artifact but cannot replace the newer latest Feed

#### Scenario: Equal-cutoff variants arrive in either order
- **WHEN** two valid candidates have the same `evidence_cutoff_at`, different `content_digest` values, and are submitted in either order
- **THEN** both immutable dated artifacts remain and latest deterministically contains the candidate with the lexicographically greater canonical `content_digest`
