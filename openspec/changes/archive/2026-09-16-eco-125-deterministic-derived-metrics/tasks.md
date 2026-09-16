## 1. Baseline and Compatibility Characterization

- [x] 1.1 Run `uv sync --frozen --all-groups`, `openspec validate eco-125-deterministic-derived-metrics --strict`, and the existing focused SEC/CFTC/Feed determinism tests; verify the frozen environment resolves and record the pre-change commands that pass before editing production code.
- [x] 1.2 Add representative pre-migration characterization tests for complete SEC 13F and CFTC COT v2 payload dictionaries and canonical bytes, including SEC matched/current-only/previous-only holdings and CFTC available/unavailable comparisons; verify the tests pass against the current implementation before replacing arithmetic.
- [x] 1.3 Add failing regressions that process supported SEC aggregation/conversion/deltas and CFTC net/deltas under deliberately different ambient decimal precision, rounding, flags and traps; verify they expose context-dependent behavior without mutating expected Provider semantics.

## 2. Internal Measured and Derived Numeric Primitives

- [x] 2.1 Add failing focused tests for immutable measured numeric facts carrying Provider-local names, canonical values, units and source-field support; cover existing raw/canonical numeric bounds, nonnegative admission, negative zero, malformed/non-finite values, and explicit exclusion of non-numeric semantic concerns.
- [x] 2.2 Add failing focused tests for derived numeric facts carrying subtraction metadata and ordered direct references to immutable measured or derived input fact objects; verify minuend/subtrahend ordering, immediate recomputation, chained inputs, immutability, unequal-unit rejection, and absence of global-name/path lookup.
- [x] 2.3 Implement the narrow `src/follow_the_money/semantic/` measured-fact, derived-fact and derivation types plus owned-context canonical parsing/normalization/arithmetic; verify the focused primitive tests pass and no formula registry, expression evaluator, comparator or identity abstraction exists.
- [x] 2.4 Move the raw-token and persisted-canonical numeric guards behind the semantic numeric authority while retaining narrow compatibility entry points from `feed.validate`; verify existing `tests/test_feed_boundary.py` numeric admission/rejection behavior and error categories remain unchanged.
- [x] 2.5 Add owned-context arithmetic cases for exact addition, subtraction and power-of-ten scaling used by the two Provider cores; verify ambient context state is neither read nor mutated and inexact, rounded, overflowed or out-of-contract results fail closed.

## 3. SEC 13F Migration

- [x] 3.1 Refactor SEC measured amount/value construction and matched current-minus-previous deltas to use the shared facts and subtraction derivation, while using owned low-level arithmetic for duplicate aggregation and the existing filing-date unit conversion; verify `tests/test_sec_13f.py` passes.
- [x] 3.2 Add SEC internal-provenance assertions proving each migrated delta retains the subtraction operation and ordered current/previous fact objects during normalization, while Provider projection emits only the existing holding fields; verify no generic fact or derivation metadata appears in the payload.
- [x] 3.3 Run SEC adapter, complete-slice, Feed validation and characterization regressions; verify security identity, full-outer comparison, amount-based classification, unavailable semantics, source provenance, ordering, exact payload dictionaries and canonical bytes remain unchanged.

## 4. CFTC COT Migration

- [x] 4.1 Refactor CFTC source metrics, net non-commercial derivation and current-minus-previous deltas to use the shared measured/derived facts and owned subtraction; verify `tests/test_cftc_cot.py` passes.
- [x] 4.2 Add CFTC internal-provenance assertions proving net uses ordered long/short facts and deltas use ordered current/previous facts, including chained derived-net delta verification; verify metadata is internal and needs no registry or external lookup.
- [x] 4.3 Run CFTC adapter, activation, Feed validation and characterization regressions; verify market-code matching, current-only universe, unavailable semantics, existing `noncommercial_long_minus_short` Provider descriptor, exact payload dictionaries and canonical bytes remain unchanged.

## 5. Cross-Boundary Regression and Final Verification

- [x] 5.1 Add or extend Feed determinism tests to compare SEC/CFTC semantic output, canonical item bytes, `content_digest` and cutoff-derived `run_id` across ambient decimal contexts; verify identical evidence remains byte-identical and changed evidence still changes identity.
- [x] 5.2 Add a closed-surface regression that rejects or detects any generic fact/derivation field in Provider projection and inspect the production import graph; verify comparison, identity, formula descriptor lifecycle and payload assembly remain Provider-specific and no new runtime/configuration authority exists.
- [x] 5.3 Run `.venv/bin/python -m pytest` for the new semantic tests plus `tests/test_sec_13f.py`, `tests/test_sec_snapshot_slice.py`, `tests/test_cftc_cot.py`, `tests/test_cftc_activation.py`, `tests/test_adapters.py`, `tests/test_feed_boundary.py`, and `tests/test_feed_determinism.py`; verify all focused tests pass without network access.
- [x] 5.4 Run `.venv/bin/python scripts/quality_gate.py`, `openspec doctor`, `openspec validate eco-125-deterministic-derived-metrics --strict`, and `openspec validate --all --strict`; verify all canonical gates pass and report only checks actually executed.
- [x] 5.5 Review the final diff against ECO-125 scope; verify no Feed schema, Provider manifest/version, configuration, canonical identity, snapshot/publication, Host-Agent, comparison abstraction, entity-identity abstraction, formula registry or generic semantic framework change was introduced.
