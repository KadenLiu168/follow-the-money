## 1. Pin the Trust Gap with Failing Tests

- [x] 1.1 Add manifest/config tests proving `mapping_verified: true` without `verification_provenance`, `mapping_verified: false` without a non-empty `reason`, and forbidden mixed verification branches fail static resolution; run them first and record the expected RED failures.
- [x] 1.2 Add deterministic provenance tests for missing/absolute/escaping/cross-Provider repository paths, malformed or disallowed HTTPS references, tuple misassociation, and Yahoo chart `meta.symbol` mismatch; prove validation performs no verification network request.
- [x] 1.3 Add shipped-truth tests requiring every true mapping to satisfy the evidence invariant, every false mapping to retain a reason, CSI 300 not to remain verified from its missing reference, and existing false mappings not to be promoted.
- [x] 1.4 Add production-boundary tests proving only verified Yahoo mappings are planned, unverified roles cannot emit canonical `market_data.instrument_id`, all mappings remain in Provider snapshots, and an enabled market Provider with zero verified mappings fails while explicit disablement remains valid.
- [x] 1.5 Extend the ECO-26 pre-mutation regression pattern to prove every mapping-verification and market-coverage configuration failure precedes Provider requests, normal collection work, rate-registry mutation, dated publication, and `latest.json` replacement.
- [x] 1.6 Add coverage and retained-library regressions proving unsupported all-13/China-HK/cross-asset labels are absent, no role-level coverage behavior is introduced, and MarketSnapshot returns `unverified_mapping` even when a matching canonical-role Feed item is defensively supplied.

## 2. Enforce the Mapping Verification Contract

- [x] 2.1 Extend the existing manifest role-mapping parser and resolved Provider representation with the closed `verification_provenance` branch, exact allowed/required keys, non-empty values, and deterministic mapping order while preserving the full mapping record for snapshots.
- [x] 2.2 Implement repository-fixture validation with normalized repository-relative paths, owning-Provider containment, existence/file checks, resolved-path containment, and Yahoo chart `meta.symbol` identity validation for structured Yahoo fixture evidence.
- [x] 2.3 Implement `authoritative_https` syntax and policy validation against the owning manifest's existing exact contract/fetch/redirect/source-link URL authorities, rejecting non-HTTPS, credentials, fragments, ports, hosts, and query forms outside that policy without network I/O.
- [x] 2.4 Remove the unused canonical-role `source_provenance` compatibility source from strict config, `MarketRole`, and directly affected fixtures; retain and rerun config/manifest parity checks for `instrument`, `unit`, and `mapping_verified` so the manifest remains the execution authority.
- [x] 2.5 Add the existing-category startup rejection for an enabled market Provider whose resolved contract contains zero verified runnable mappings, preserving explicit Provider disablement as the supported no-work state.
- [x] 2.6 Run the focused manifest, config, normalization, and static startup tests and make the new contract tests GREEN without weakening closed-schema or Provider authority checks.

## 3. Migrate Shipped Mapping and Coverage Truth

- [x] 3.1 Add repository-fixture provenance to the S&P 500 Yahoo mapping and verify the checked-in fixture identifies `^GSPC` under the exact `yahoo_market` / `sp500` / `^GSPC` / `index` tuple.
- [x] 3.2 Change CSI 300 to `mapping_verified: false` in the authoritative manifest and its required compatibility mirror with a deterministic missing-evidence reason; retain the other eleven false mappings and verify every false mapping has a reason.
- [x] 3.3 Replace `china_hk_cross_asset_market` / `market_data_all_13_roles` with the narrow Provider-level `verified_market_data` coverage row and update only directly affected assertions, snapshots, comments, README/Skill capability text, or fixtures that otherwise overstate runnable breadth.
- [x] 3.4 Add an exact shipped mapping inventory assertion so future true/false/provenance/reason drift fails visibly rather than being derived from production output.

## 4. Gate Production Adapter Planning and Preserve Audit State

- [x] 4.1 Change Yahoo production planning to join the resolved manifest mappings to canonical roles after tuple parity validation and construct adapters only for verified mappings in existing canonical role order.
- [x] 4.2 Verify an unverified mapping has no production acquisition path that can assign its canonical role ID, without adding an item-level `mapping_verified` field or changing `feed.schema.json`.
- [x] 4.3 Preserve all verified and unverified mappings, verification provenance, and reasons in deterministic Provider contract snapshots; update expected semantic digests only where the intended contract/coverage truth changes and leave the identity algorithm unchanged.
- [x] 4.4 Run focused adapter-planning, Provider snapshot, Feed identity/digest, coverage, degradation, and publication tests and repair only ECO-27-attributable regressions.

## 5. Regression and Canonical Verification

- [x] 5.1 Run the focused MarketSnapshot suite and confirm the secondary `unverified_mapping` guard remains intact without adding a production MarketSnapshot caller.
- [x] 5.2 Run Feed determinism, normalization, identity/digest, failure/degradation, rate-state, and durable publication regression suites, confirming intentional capability corrections are the only behavioral changes.
- [x] 5.3 Run `uv sync --frozen --all-groups` and `.venv/bin/python scripts/quality_gate.py`; resolve only failures attributable to ECO-27.
- [x] 5.4 Run `openspec doctor`, `openspec validate enforce-verified-market-mappings --strict`, and `openspec validate --all --strict`, and confirm all living OpenSpec contracts remain valid.
- [x] 5.5 Review the final diff for one-authority provenance, no grandfathered true mapping, verified-only canonical Feed planning, truthful Provider-level coverage, unchanged Feed schema, no role-level coverage engine, no MarketSnapshot wiring, no Agent/LLM/runtime additions, and no unrelated or archived-Change edits.
