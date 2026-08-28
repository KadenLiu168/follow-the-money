## 1. Canonical Event Regressions

- [x] 1.1 Add three focused regressions in `tests/test_events.py` for a null first canonical fact, all-null key facts, and partially-null key facts; explicitly prove the intended fact is `key_fact_ids[0]` where ordering matters.
- [x] 1.2 Run the three focused regressions before implementation and confirm each fails for the targeted projection mismatch.

## 2. Canonical Event Repair

- [x] 2.1 Update only the effective-time projection logic in `build_event()` so the economic projection uses the first canonical key fact and common time requires identical non-null value and precision across every key fact; leave `multiple_effective_times` unchanged.
- [x] 2.2 Run the focused regressions and the complete `tests/test_events.py` suite, including existing non-null and mixed-precision determinism coverage.

## 3. Agent Invocation Integration

- [x] 3.1 Add one nullable `event.structure` smoke regression in `tests/test_agent_invocation_runtime.py` proving the first canonical fact's null value and declared precision survive adapter projection, schema validation, and serialization without adding adapter business logic.
- [x] 3.2 Run the complete Agent invocation regression suite and verify the DTO, schema, and contract version remain unchanged.

## 4. Repository Validation

- [x] 4.1 Run the full pytest suite with `.venv/bin/python -m pytest` and confirm Event, Agent invocation, Audit, and Feed regressions pass.
- [x] 4.2 Run `openspec doctor`, `openspec validate fix-nullable-event-effective-time-projections --strict`, and `openspec validate --all --strict`.
- [x] 4.3 Run `.venv/bin/python scripts/quality_gate.py` and `git diff --check`, then confirm the final diff changes no out-of-scope production, schema, adapter, or archived-Change files.
