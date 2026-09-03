## 1. Versioned Provider Availability Contract

- [x] 1.1 Update logical Feed and manifest schemas for production major 3 with required `availability`, bounded `availability_reason`, `upstream_http_status`, and ordered `affected_coverage_groups`; retain major 2 reads and verify schema tests reject malformed/cross-field-invalid major 3 outcomes and unsupported major 1 products.
- [x] 1.2 Extend the Provider outcome model/serialization without changing evidence item or artifact schemas, and verify deterministic serialization plus major 2 compatibility tests pass.

## 2. Classification and Feed Decision

- [x] 2.1 Classify only structured HTTP 401/403 failures as `blocked` at the shared Provider execution boundary, preserve status/redacted reason, map timeout/parser/other failures to `failed`, and verify focused Provider/Feed tests cover 401, 403, timeout, parser error, and non-401/403 HTTP errors.
- [x] 2.2 Derive blocked exemption only for wholly failed zero-accepted outcomes, compute `max(0, configured minimum - blocked-exempt members)` without changing coverage configuration, and verify pipeline tests cover BLS/SSE-style mandatory-group exemption, all-members-blocked, optional CFTC blocking, mixed blocked/failed outcomes, partial access denial, and unchanged true coverage failures.
- [x] 2.3 Preserve freshness `not_evaluated` and prohibit prior-slice carry-forward for blocked Providers while retaining major 2 prior-bundle compatibility; verify focused snapshot/freshness tests cover blocked runs with and without prior evidence.

## 3. Validation, Publication, and Diagnostics

- [x] 3.1 Update semantic validation to enforce availability/status/reason/HTTP-status/coverage-group agreement and permit `degraded` only for valid blocked exemption; verify negative tests fail closed for forged blocked claims, wrong group lists, duplicate/unsorted groups, missing outcomes, and blocked-plus-partial data.
- [x] 3.2 Reuse existing healthy/degraded publication, dry-run, consumer, checkpoint, and runtime/publication separation paths for blocked degradation; verify focused CLI, bundle, boundary, deployment, and checkpoint tests show degraded success exits `0` while non-exempt failures exit `1` without publication.
- [x] 3.3 Render bounded deterministic Provider diagnostics with identity, availability, reason, and affected coverage in existing status and GitHub summary surfaces; verify ordering, redaction/bounds, malformed-status fallback, and non-gating diagnostics tests.

## 4. Contract Alignment and Verification

- [x] 4.1 Update only README/SKILL/docs capability claims affected by the new published behavior and schema major, if present, and verify repository search finds no stale claim that every planned Provider failure is always fatal.
- [x] 4.2 Run focused affected tests, then `openspec doctor`, `openspec validate add-provider-availability-aware-degradation --strict`, and `openspec validate --all --strict`; verify every command passes.
- [x] 4.3 Run `.venv/bin/python scripts/quality_gate.py` and verify the canonical repository quality gate passes without real-provider dry runs.
