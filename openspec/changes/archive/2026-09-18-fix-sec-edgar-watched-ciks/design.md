# Design: fix-sec-edgar-watched-ciks

## Context

See `proposal.md` — Why for the failure and scope. Constraints that shape the
approach:

- SEC is the sole `us_company_filings` coverage member and the complete SEC
  slice is fail-closed, so one bad watched CIK makes the Feed unpublishable.
- `watched_form4_issuers` and `watched_beneficial_ownership_filers` already
  enforce normalized ten-digit CIKs and duplicates; `watched_companies`
  enforced only "non-empty string" and uniqueness.
- Deterministic watched-CIK order is already produced at both consumption
  points by `sorted(cfg.watched_companies, key=lambda company: company.cik)`:
  `_production_adapters` (adapter construction) and `_feed_config_snapshot`
  (embedded snapshot), both in `src/follow_the_money/feed/cli.py`.
- The checked-in list order is deliberately not CIK order.

## Goals / Non-Goals

**Goals:**

- Correct the six wrong CIKs to identities verified against the official SEC
  submissions API and record that evidence.
- Make malformed or duplicate `watched_companies` CIKs fail static resolution
  before Provider work or persistent mutation.
- Pin the shipped CIK set so silent drift fails a regression instead of
  drifting an acquisition target.

**Non-Goals:**

- No change to SEC producer URL/parser logic or `validate.py` source-link policy.
- No checked-in CIK-order enforcement and no config reordering.
- No runtime repair, normalization, or deduplication of malformed CIKs.
- No change to canonical-bytes encoding or the digest algorithm; the config
  snapshot digest value changes only because the configured CIK set changes.
- No coverage, manifest, or slice-semantics change.

## Decisions

### D1: Verify CIKs against the official submissions API, not by firm name

Each watched CIK was resolved from
`https://data.sec.gov/submissions/CIK<10-digit-CIK>.json` on 2026-09-18 and the
returned `name` recorded in `references/provider-source-verification.md`.
Alternative — inferring CIKs from firm names or search pages — was rejected:
the observed failure was an identity mismatch (four old CIKs resolved to
unrelated persons or entities), so only the CIK-keyed official listing is
evidence. Live observation also corrected the proposal's initial claim that
`0001539579` was HTTP 404; it resolves to `Bien Janet Lynn`.

The configuration `name` is a presentation label, not verified identity:
`Berkshire Hathaway` intentionally differs from `BERKSHIRE HATHAWAY INC`. The
exact-set regression pins only CIKs.

### D2: Mirror existing CIK validation; do not add ordering enforcement

`_parse_watched_companies` gains `re.fullmatch(r"\d{10}", cik)` and keeps the
existing duplicate check, matching `watched_form4_issuers` and
`watched_beneficial_ownership_filers`. No order check is added: deterministic
order is already delivered by runtime `sorted()` at both consumption points, so
enforcing it in YAML would couple configuration churn to an invariant the
runtime already owns, and the spec requires snapshot order to be
runtime-derived and independent of list order.

Alternatives rejected:

- Reordering `config/config.yaml` into CIK order: produces the same snapshot
  bytes, adds churn, and would falsely suggest checked-in order is the ordering
  authority.
- Repairing or deduplicating at load time: the spec forbids silently
  correcting, deduplicating, or skipping malformed CIKs.

### D3: Pin the shipped set with an exact-set regression on the resolved config

`test_shipped_watched_company_ciks_are_exact_and_runtime_ordered` loads the
shipped production config, asserts the resolved CIK set equals the verified
set, asserts the checked-in order is not CIK order, and asserts the embedded
`_feed_config_snapshot` orders them ascending by CIK. The final assertion makes
the preceding one meaningful: a snapshot that echoed checked-in order fails.
This turns a future CIK edit into a deliberate two-place change (config plus
verified evidence/test constant) rather than silent drift.

`test_watched_company_cik_selection_is_fail_closed` copies the shipped contracts
to `tmp_path`, mutates one CIK to a non-ten-digit value and one to a duplicate,
and asserts `ConfigError`. Tests stay offline and deterministic; no fixture
carries the watched CIKs.

## Risks / Trade-offs

- [A future legitimate filer change fails the exact-set regression] → Intended:
  the change then updates both the verified evidence table and the constant,
  keeping the pinning auditable. Drift detection is the goal.
- [Config snapshot digest changes with the CIK correction] → Expected and
  necessary; the digest algorithm and canonical bytes are unchanged. Any
  persisted publication row keyed to the old snapshot must be republished.
- [A syntactically valid but wrong CIK still passes validation] → Correctness
  rests on the dated verified evidence plus the pinned exact set, not on format
  checks; format checks only reject structurally invalid values.
- [Runtime ordering depends on both consumption points calling `sorted()`] →
  The snapshot regression fails if snapshot ordering stops being
  runtime-derived; adapter construction uses the same `sorted()` and existing
  SEC slice tests cover the resolved watched-CIK completeness.

## Migration Plan

1. Correct the six CIKs in `config/config.yaml` (list order preserved).
2. Add the format check in `_parse_watched_companies`.
3. Record the verified identities in `references/provider-source-verification.md`.
4. Add the shipped exact-set/ordering and fail-closed regressions.
5. Run focused tests, the full suite, and `scripts/quality_gate.py`.

Rollback: revert the four touched files. Previous behavior (accepting
malformed CIKs and the wrong identities) restores exactly, at the cost of an
unpublishable Feed.

## Open Questions

None.
