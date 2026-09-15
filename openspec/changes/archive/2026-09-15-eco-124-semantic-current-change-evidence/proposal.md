## Why

SEC 13F-HR and CFTC COT evidence currently expose only shallow current records, leaving the Host Agent to inspect `raw_metadata`, retrieve history, or calculate cross-period changes. ECO-124 proves, through two bounded Provider-specific vertical slices, that the deterministic Producer can publish directly usable current state, previous comparable evidence, and reproducible change without weakening the Evidence Feed trust contract.

## What Changes

- Add a managed Provider HTTP boundary so every real upstream send, including redirect hops and pagination, independently obeys durable rate debit/reconciliation, deadline, global concurrency, per-target-host concurrency, host policy, response limits, and Provider identity requirements.
- Publish one cutoff-bounded exact `13F-HR` semantic filing item for every configured watched company, including official company identity, the current INFORMATION TABLE, previous comparable filing provenance, deterministic security-key aggregation, and amount-based change classification.
- Publish deterministic CFTC Legacy Futures-Only current/previous weekly positioning by contract market code, including typed long, short, spreading, open-interest, net, and reproducible delta metrics.
- Keep Feed schema major v4 and add bounded Provider-contract-v1 read compatibility while requiring the new semantic structures from SEC and CFTC Provider contract v2 producers.
- Embed the watched-company selection in the Feed configuration snapshot so SEC v2 validation can prove that the current SEC slice is complete and unique by configured CIK.
- Preserve whole-Provider-slice replacement without history merging. Add a narrow SEC/CFTC v2 complete-state carry-forward condition requiring equal current/prior item identity sets and canonical content, so removing watched CIKs or removing a CFTC market from a corrected same-date report cannot restore prior members; preserve all legacy event-list and empty-check behavior.
- Preserve genuine first-response blocked exemption, but classify access denial after successful sub-request/page evidence as partial and non-exempt even before item normalization. Preserve typed transport/rate failures and actual response-observation times.
- Normalize SEC reported value into USD thousands using the verified filing-date-based 2023-01-03 unit transition, retain typed unit/conversion provenance, and activate each v2 manifest only with its complete working producer.
- Keep the Feed evidence-only: no model runtime, generic semantic framework, ranking, market interpretation, prediction, recommendation, trading signal, or Host-Agent historical lookup is introduced.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `feed-evidence-pipeline`: Extend the existing five-domain Feed contract with per-send managed transport and Provider-specific SEC 13F/CFTC current-change semantic evidence while preserving v4 compatibility and snapshot guarantees.

## Impact

- Provider transport/orchestration: `src/follow_the_money/providers/session.py`, `src/follow_the_money/providers/http.py`, and `src/follow_the_money/feed/cli.py`.
- Provider-specific deterministic logic and adapters: SEC 13F and CFTC COT modules, adapters, manifests, and fixtures.
- Feed contracts: `schemas/feed.schema.json`, configuration snapshots, Provider contract-version resolution, semantic validation, canonical identity, and bundle compatibility tests.
- Bounded lifecycle fixes: acquisition-progress outcome mapping in `feed/cli.py`/`providers/http.py` and SEC/CFTC-v2-only whole-slice equality admission in `feed/snapshot.py`; no persisted snapshot schema or public CLI change.
- Tests and truthful documentation for the affected Feed boundary, Provider behavior, snapshot behavior, and Host-Agent consumption contract.
- No new external credential, model runtime, public CLI, evidence domain, or generic enrichment dependency.
