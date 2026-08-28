## Context

See `proposal.md` for motivation. Canonical key facts are already ordered by `key_fact_ids`; `build_event()` currently conflates that ordered collection with a filtered collection of non-null effective times. The Agent adapter only projects the canonical Event result and its schema already accepts a null effective-time value with a declared precision.

## Goals / Non-Goals

**Goals:**

- Keep one canonical effective-time implementation in Event construction.
- Separate first-key-fact economic projection from the all-key-facts common-time predicate.
- Preserve deterministic non-null behavior and existing mixed-precision coverage.

**Non-Goals:**

- Do not redefine `multiple_effective_times` for nullable inputs.
- Do not change Event identity, key-fact ordering, `fully_known_at`, story families, coexistence, labels, DTOs, schemas, contract versions, or Agent ownership.
- Do not add a helper framework, service, API, or production caller.

## Decisions

### Derive the economic projection directly from the first canonical key fact

Use the first item in the already ordered key-fact collection for both value and precision, including when the value is null. This preserves the accepted ordering contract and prevents value and precision from coming from different facts.

Alternative: select the first non-null effective time. Rejected because null describes the canonical fact's time value; it does not remove that fact from ordering.

### Evaluate common time across every key fact

Create `common_effective_time` only when the first canonical value is non-null and every key fact has that same value and precision. Any null value therefore makes the projection absent.

Alternative: compare only known values. Rejected because agreement among a subset does not satisfy the all-key-facts contract.

### Preserve the existing multiple-time computation

Leave the current `multiple_effective_times` inputs and result unchanged. Its nullable semantics are not part of this correction and would require a separate contract decision.

### Test the canonical boundary first and the adapter once

Add three focused Event regressions for the nullable cases and one `event.structure` smoke regression proving that adapter projection, schema validation, and serialization preserve the canonical result. Do not duplicate all domain cases at the transport boundary.

## Risks / Trade-offs

- Existing consumers may have observed the incorrect first-non-null or synthetic-precision result → retain the DTO and contract version because the change restores already accepted semantics rather than introducing a new shape.
- Accidental changes to `multiple_effective_times` could expand scope → assert only the requested projections and leave its production expression untouched.
