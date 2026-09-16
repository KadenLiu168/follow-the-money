## Context

See `proposal.md` for motivation and `specs/deterministic-derived-metrics/spec.md` for the behavioral contract.

ECO-124 left two network-free Provider cores: `providers/sec_13f.py` parses, normalizes, aggregates and compares holdings, while `providers/cftc_cot.py` normalizes and compares weekly market rows. Both construct `{value, unit}` facts and calculate subtraction-based metrics, but each owns a near-duplicate conversion to canonical decimal strings. They import raw/canonical numeric validators from `feed/validate.py` and perform arithmetic through the ambient `decimal` context.

A read-only probe demonstrated the consequence: the same supported CFTC long/short input produced `123456788.123456788` at precision 28 and `123457000` at precision 6. Existing tests cover row-order determinism but do not isolate global decimal precision, rounding, traps, or flags.

The public Feed already has closed SEC-v2 and CFTC-v2 semantic payloads. This Change must therefore add an internal provenance model without adding another serialized envelope or changing the existing Provider contracts.

## Goals / Non-Goals

**Goals:**

- Establish one internal authority for bounded canonical numeric construction and owned-context arithmetic.
- Distinguish measured numeric facts from derived numeric facts.
- Retain each derived fact's concrete operation and ordered immutable input fact objects for local provenance and regression verification.
- Migrate the subtraction semantics shared by SEC deltas and CFTC net/deltas while preserving Provider-specific output assembly.
- Preserve exact SEC/CFTC v2 payload bytes and Feed identity for unchanged evidence.

**Non-Goals:**

- A complete semantic fact model, public semantic envelope, generic provenance schema, formula registry, expression evaluator, plugin system, or rule engine.
- Shared comparison, entity identity, matching, classification, missing-side, aggregation, or source-selection policy.
- A lifecycle for formula identifiers. CFTC's existing `noncommercial_long_minus_short` descriptor remains a Provider-specific contract constant.
- Feed schema, Provider manifest/version, configuration, snapshot, publication, Digest, or Host-Agent changes.
- Migration of unrelated legacy adapter numeric conversion solely for consistency.

## Decisions

### 1. Model only measured and derived numeric facts

Add a narrow `follow_the_money.semantic` package. A frozen measured-fact value carries a Provider-local name, canonical decimal value, unit, and immutable source-field support. A separate frozen derived-fact value carries its Provider-local name, canonical decimal value, unit, and derivation metadata.

Names and source fields are local provenance labels, not globally registered identifiers. Units remain explicit and subtraction requires exact equality; the primitive never converts units implicitly. Neither value type owns Feed serialization semantics. Provider code explicitly projects only the canonical value and unit into its existing payload.

Alternative considered: one generic `SemanticFact` supporting text, time, identity and comparison. Rejected because ECO-124 validates only shared numeric behavior and such a type would falsely imply a complete semantic layer.

Alternative considered: represent facts only as `{value, unit}` dictionaries. Rejected because immutable typed objects are needed to retain input references and make internal provenance directly verifiable without changing wire output.

### 2. Derivation metadata records execution but does not select it

A frozen derivation record contains a closed concrete operation and an ordered tuple of direct references to immutable measured or derived input fact objects. The initial shared semantic operation is subtraction: input zero is the minuend and input one is the subtrahend. The derivation function executes that operation directly and returns a derived fact carrying the record.

Direct object references preserve immediate input values, units, source support and any prior derivation chain without JSON-path resolution or hidden lookup state. Metadata remains in memory for Producer provenance assertions and tests and is discarded at Provider projection. It is not canonicalized or included in Feed identity.

No global formula-name map is introduced. The operation identifies what the shared code actually executed; a Provider-specific public descriptor remains independently fixed and validated by that Provider's existing contract. In particular, CFTC continues to publish its current formula descriptor, but the shared primitive neither creates nor manages that identifier.

Alternative considered: store input names or JSON Pointers. Rejected because verification would require a mutable external namespace or payload-shape lookup.

Alternative considered: dispatch arbitrary operations by `formula_id`. Rejected because it creates a formula registry and a second runtime authority.

### 3. Own decimal state at the lowest shared numeric boundary

Move the existing raw-token and persisted-canonical guards behind the semantic numeric boundary, preserving the current 64-byte, 24-significant-digit, exponent, magnitude, finite-number and negative-zero rules. Existing `feed.validate` entry points may remain narrow compatibility re-exports so callers and focused boundary tests do not churn, but their implementation authority is the semantic core.

Every context-sensitive operation, including normalization, addition, subtraction and exact power-of-ten scaling used by the migrated cores, runs inside a fresh owned local context with sufficient precision and explicit traps. Results are canonicalized and revalidated after arithmetic. The core rejects inexact or rounded results rather than accepting context-dependent output. It does not mutate or rely on the caller's decimal context or flags.

Only subtraction becomes shared semantic derivation in this Change because both ECO-124 slices use it. Lower-level exact addition and scaling may support SEC aggregation and filing-date unit normalization to close the ambient-context defect, but they do not create a configurable derivation vocabulary or move SEC policy into the shared layer.

Alternative considered: raise global decimal precision at process startup. Rejected because global state remains mutable, affects unrelated code, and cannot prove isolation.

Alternative considered: retain duplicate Provider helpers but wrap each in `localcontext`. Rejected because it leaves two authorities for the same canonical numeric contract and does not create the requested reusable fact/derivation seam.

### 4. Keep comparison and identity in the Provider cores

SEC continues to choose `(CUSIP, put/call, amount type)` keys, aggregate duplicate rows, perform a full-outer comparison, emit previous-only holdings, and classify matched amount changes. CFTC continues to match by contract market code, emit only current markets, omit previous-only markets, and avoid a generic change classifier.

The shared layer receives already named numeric facts and returns exact numeric results. It does not receive snapshots, comparable keys, entity identifiers, join policies or classification labels.

Alternative considered: parameterize one snapshot comparator with join, missing-side and classification policies. Rejected because the two validated consumers intentionally differ; parameterization would be a premature rule engine. Form 4, 13D/13G or another third consumer must provide additional evidence before revisiting this boundary.

### 5. Pin compatibility before migration

Before replacing Provider arithmetic, add characterization assertions for representative SEC and CFTC semantic payloads and their canonical bytes under the current implementation. Then add primitive tests and migrate one Provider at a time. Each migration must pass its focused pure-core tests plus Feed validation and identity regressions.

Tests vary ambient decimal precision, rounding, flags and traps and compare both internal facts and final Provider output. Internal derivation tests assert operation, input order, immutable references, unit compatibility and recomputation. Public tests assert that no generic fields appear and existing CFTC/SEC descriptors and classifications remain unchanged.

Alternative considered: rely only on existing field-level tests. Rejected because they do not prove byte compatibility or ambient-context isolation.

## Risks / Trade-offs

- [Direct fact-object references can form a large provenance tree] -> Retain only immediate immutable inputs and only for values calculated during one Provider normalization; do not serialize or persist the graph.
- [A shared numeric module could become a generic semantic framework] -> Keep accepted types numeric-only, expose only operations required by the two existing slices, and leave names, source meaning and projection with Providers.
- [Moving validators can accidentally change errors or imports] -> Preserve current bounds and compatibility entry points, and pin accepted/rejected boundary cases before moving authority.
- [Byte-parity tests can be brittle] -> Pin only representative canonical Provider projections required by the compatibility contract, while retaining semantic invariant tests for broader behavior.
- [Owned precision may expose previously rounded values as failures] -> Treat that as required fail-closed behavior, add explicit regression inputs, and do not silently preserve context-dependent rounding.
- [Internal metadata and CFTC's public formula descriptor could be mistaken for one authority] -> Keep them structurally separate and test that Provider projection supplies the existing descriptor independently.

## Migration Plan

1. Characterize existing SEC/CFTC payloads and canonical bytes before changing arithmetic.
2. Add the internal measured/derived fact types, derivation metadata, owned numeric operations and focused provenance/context-isolation tests.
3. Move canonical numeric validation authority behind the shared boundary while preserving existing validation entry points.
4. Migrate SEC numeric construction and deltas without changing comparison, identity, provenance projection or payload assembly.
5. Migrate CFTC numeric construction, net and deltas without changing market selection or its existing public formula descriptor.
6. Run focused Provider, Feed validation, determinism and identity tests, then the canonical quality gate and strict OpenSpec validation.

Rollback reverts the semantic package and both Provider migrations together. Because no persisted or wire format changes, rollback requires no Feed, checkpoint, manifest or configuration migration.
