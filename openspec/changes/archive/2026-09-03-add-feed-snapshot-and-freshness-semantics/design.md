## Context

See `proposal.md` for motivation and `specs/feed-evidence-pipeline/spec.md` for behavior. The current manifest-led bundle already owns the active product, integrity validation, logical identity, Provider outcomes, embedded resolved Provider contracts, and evidence items. It also already has the necessary time facts, but they are distributed correctly by meaning: payload fields carry observation/effective time, `source.published_at` / `source.updated_at` carry source time, Provider outcome `retrieved_at` carries response-return time, and manifest `generated_at` carries Feed generation time.

The existing Provider `freshness.policy` is only an opaque string. The current advancing window collects new evidence and intentionally uses the checkpoint—not the product—as continuity authority. Snapshot retention must therefore be an optional post-acquisition use of the already validated active bundle, not a second checkpoint, store, or planning authority.

## Goals / Non-Goals

**Goals:**

- Turn the existing Provider freshness declaration into the sole closed cadence contract.
- Select one current Provider evidence slice per successful run and label its freshness reproducibly.
- Carry an unchanged slice without mutating evidence identity, source time, or provenance.
- Preserve current Feed completeness, coverage, publication, ordering, and checkpoint ownership.
- Read the immediately preceding contract major long enough to seed the first freshness-capable bundle.

**Non-Goals:**

- Snapshot history, a snapshot database, per-item acquisition ledgers, unbounded slice merging, or a new runtime-state file.
- Guessing release calendars, holidays, or validity windows in Feed code.
- Changing Provider outcome admission, coverage/degradation semantics, retry behavior, or the advancing acquisition window.
- New Providers, CFTC activation, Host Agent behavior, intelligence output, or runtime orchestration.

## Decisions

### 1. Reuse existing timestamps and add no generic timestamp aliases

Do not add `data_as_of`, `source_updated_at`, `checked_at`, or another generated timestamp beside an equivalent existing value. Document these mappings:

- data observation/effective time: the existing payload-specific field (`market_data.observations[].as_of`, `flow.as_of`, `positioning.as_of`, `policy.effective_at`/`announced_at`, `macro_release.released_at`, `filing.filed_at`, `calendar.scheduled_at`, or `news.occurred_at` when present);
- source publication/update time: `source.updated_at` when supplied, otherwise `source.published_at`, without treating retrieval as a fallback source time;
- source knowledge eligibility time: `source.knowledge_available_at`;
- current check/retrieval time: the Provider outcome's existing `retrieved_at`;
- bundle generation time: manifest `generated_at`.

The Provider cadence contract selects `reference_time: data_as_of | source_updated_at | checked_at`. The evaluator resolves that selector through the existing closed payload/source fields. A missing or ambiguous selected value fails the candidate instead of falling back across meanings.

Alternative considered: add four normalized timestamps to every item. Rejected because it duplicates existing authorities, changes unchanged item bytes during carry-forward, and invites fabricated fallback values.

### 2. Replace the opaque policy string with the smallest structured cadence contract

Each Provider manifest uses:

```yaml
freshness:
  cadence: weekly | scheduled | event_driven | market_session
  reference_time: data_as_of | source_updated_at | checked_at
  valid_for_seconds: <positive integer, age-bounded cadences only>
```

The valid combinations are closed:

- `weekly` and `scheduled`: `data_as_of` or `source_updated_at`, plus `valid_for_seconds`;
- `market_session`: `data_as_of`, plus `valid_for_seconds`;
- `event_driven`: `checked_at`, with no `valid_for_seconds`.

All enabled shipped manifests must state values supported by their existing verified source contract; Apply must not infer values from Provider IDs or add a Feed lookup table. The resolved immutable Provider contract and its embedded snapshot expose the exact same structure.

Alternative considered: encode release schedules and exchange calendars now. Rejected because current Providers do not share one schedule model and ECO-77 only needs explicit deterministic validity; source-specific future schedule work can extend the Provider contract when required.

### 3. Put freshness beside Provider outcomes, not inside evidence items

Extend each new-major Provider outcome with one required semantic `freshness` object:

```json
{
  "cadence": "weekly",
  "status": "valid_unchanged",
  "origin_contract_hash": "<sha256 or null>",
  "carried_forward_from_run_id": "<prior run_id or null>"
}
```

`origin_contract_hash` is the hash of the embedded Provider contract under which the selected slice originated. It is null only for `no_snapshot` and `not_evaluated`. It remains unchanged across carries even if the current resolved Provider contract changes, making original contract provenance explicit rather than falsely attributing old items to the current contract. `carried_forward_from_run_id` names only the immediately preceding validated active bundle and is non-null only when the prior semantic slice bytes were selected.

Status is closed:

- `fresh`: a current selected slice is within its contract validity;
- `valid_unchanged`: an unchanged prior slice was selected and remains valid;
- `stale`: a present current or carried slice exceeds an age-bounded validity window;
- `no_snapshot`: acquisition is complete with no observation and no validated prior slice;
- `not_evaluated`: current acquisition is incomplete, so no fallback is attempted.

Freshness is semantic and enters `content_digest`; `retrieved_at` remains audit-only. Stale does not silently rewrite Provider completeness, coverage, or pipeline status. It is explicit evidence state for consumers, separate from whether acquisition completed.

Alternative considered: a new top-level `provider_snapshots` collection. Rejected because it would duplicate Provider ordering/identity already owned by `provider_outcomes`.

### 4. Select one bounded Provider slice after current acquisition

After all current Provider work is terminal, apply this deterministic selection per Provider:

1. If current acquisition is incomplete under existing rules, emit `not_evaluated`; do not load a prior slice for that Provider.
2. If any current accepted item has a new stable identity or differs canonically from the prior item under that identity, select the current Provider slice only.
3. Otherwise, if every current accepted item has an exact canonical semantic match and a fully validated active bundle contains a prior slice for the same Provider, reuse that entire prior semantic slice unchanged.
4. Otherwise select no items and emit `no_snapshot` for complete empty acquisition.
5. Evaluate the selected slice under the current cadence contract and fixed cutoff; retain its original contract hash when carried.

The prior bundle is loaded once through the existing manifest-first full validator and must be healthy or accepted degraded. Items are partitioned by `provider_id` and retain existing deterministic global ordering after all slices are selected. A same-ID source revision is a current change, not unchanged evidence: canonical semantic comparison detects changed payload, source timestamps, provenance, or lineage. The current slice replaces the prior slice when new or revised evidence exists; no union creates Feed history.

Alternative considered: read checkpoint-linked dated products or introduce a snapshot file under `.feed-state/`. Rejected because the active manifest already identifies the validated product and the checkpoint must remain only a cutoff/run identity authority.

### 5. Failure remains a failure before carry-forward can matter

Carry-forward is downstream of existing outcome and completeness assessment. `failed`, `partial`, `skipped`, non-permitted `empty`, missing, duplicate, ambiguous, or identity-mismatched acquisition keeps its current failure path, receives freshness `not_evaluated`, and cannot select prior evidence. The failed candidate may remain available in memory for diagnostics, but publication and checkpoint advancement remain blocked and the prior active bundle remains unchanged.

Alternative considered: publish a stale carried snapshot with a warning after acquisition failure. Rejected because it masks loss of current source coverage and violates the existing fail-closed trust boundary.

### 6. Advance the logical/manifest major while keeping artifacts stable

New production advances the logical Feed and manifest schema major because freshness is a new required semantic field. Domain artifact envelopes and evidence payload shapes do not change, so their physical schema major stays unchanged. Validators accept both the immediately preceding and new logical/manifest majors; only the new major is producible.

A valid preceding-major active bundle may seed a carried slice. Its existing `provider_contracts[].hash` becomes `origin_contract_hash`; the new candidate computes freshness from the current verified cadence contract without altering the prior items. Invalid or unsupported prior bundles are simply unavailable for carry-forward and never weaken current acquisition rules.

Alternative considered: add optional fields while retaining the old major. Rejected because optional freshness would permit new products that cannot satisfy the ECO-77 contract while still claiming the same closed schema version.

### 7. Preserve deterministic identity and validation closure

The semantic Provider outcome projection gains cadence, status, origin contract hash, and carry-forward run ID. Audit `retrieved_at` remains excluded. Candidate construction verifies a carried origin hash against the validated prior embedded contract; standalone schema and semantic validation enforce hash syntax, status/nullability combinations, current Provider/outcome identity, valid reference-time selection, cutoff ordering, and stable item IDs/provenance. Reversing Provider completion, prior-item, or current-item order must produce identical selected slices, freshness results, global item order, digest, and run ID.

No new dependency is needed; existing canonical serialization, bundle loading, provider contract snapshots, identity, and validation paths own the behavior.

## Risks / Trade-offs

- [A configured validity window is wrong for a source] → Require it in the verified Provider manifest and test resolved/embedded parity; do not supply a code default.
- [Event-driven evidence can be old] → It remains `valid_unchanged` only after a successful current check, while original source times stay visible; later source-specific expiry requires a separately verified contract change.
- [A Provider contract changes while old evidence is carried] → Preserve `origin_contract_hash` and evaluate under the current cadence contract instead of relabeling provenance.
- [A stale slice coexists with a healthy acquisition outcome] → Keep both explicit because acquisition completeness and evidence age answer different questions; do not overload existing pipeline semantics.
- [Old consumers cannot read the new required fields] → Treat the producer change as a major-version migration and retain preceding-major reads only, not dual production.

## Migration Plan

1. Add dual-read logical/manifest schema validation and new-major production, leaving domain artifact schemas unchanged.
2. Resolve structured cadence contracts for every existing enabled Provider and include them in deterministic Provider snapshots.
3. On the first new-major run, validate the active preceding-major bundle as the optional prior-slice input; preserve each carried slice's embedded origin contract hash.
4. Publish only a fully validated new-major candidate through the existing atomic manifest boundary and advance the unchanged checkpoint only after accepted ownership.
5. Roll back before new-major publication by reverting code/config. After new-major publication, roll back code and the corresponding generated Feed state together; do not make an old producer reinterpret or overwrite an unsupported active major.
