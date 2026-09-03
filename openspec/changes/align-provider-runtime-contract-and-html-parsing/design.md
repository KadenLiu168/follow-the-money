## Context

See `proposal.md` for motivation and `specs/feed-evidence-pipeline/spec.md` for required behavior. Provider manifests already resolve `user_agent` into `ProviderEntry`, and every concrete adapter routes requests through `BaseAdapter._fetch`; however, that boundary currently forwards only caller-supplied headers. SEC EDGAR compensates locally, creating inconsistent behavior. Shared HTML extraction currently takes the first regex match and constructs a `datetime` without validating that the captured month and day form a real calendar date.

The correction must remain inside the existing deterministic, credential-free Provider architecture. It must not change URL admission, provenance, acquisition windows, retries, rate state, deadlines, coverage, or Feed publication/failure decisions.

## Goals / Non-Goals

**Goals:**

- Make the resolved Provider contract the sole request user-agent authority at the shared fetch boundary.
- Preserve optional adapter-specific non-identity headers.
- Validate HTML date candidates individually and continue deterministically after malformed candidates.
- Reproduce both hosted defects with offline regression tests.

**Non-Goals:**

- Adding request configuration, a header policy abstraction, a new parser dependency, or Provider-specific parsing forks.
- Catching broad parser or Provider exceptions and converting them to successful/empty outcomes.
- Improving external Provider availability or changing any orchestration policy.

## Decisions

### 1. Merge request headers once at the shared adapter boundary

`BaseAdapter._fetch` will build the outbound header mapping from adapter-supplied headers, remove any case-insensitive `User-Agent` entry, and then install the exact resolved contract value under one canonical `User-Agent` key before calling the existing bounded fetch helper. This keeps additional headers while ensuring differently cased keys cannot become a second identity authority.

The SEC EDGAR adapter will use the same shared behavior rather than redundantly supplying the contract user-agent itself. Its endpoint and resulting request metadata remain unchanged.

**Alternative considered:** apply defaults in `bounded_fetch`. Rejected because that transport helper has no resolved Provider contract and accepting another user-agent input there would duplicate authority or broaden the change beyond Provider adapters.

### 2. Validate each date candidate instead of wrapping whole-index parsing

The shared HTML extractor will retain its current source precedence: separated dates in link text, then separated dates in the target, then compact dates in the existing combined candidate source. It will inspect matches in stable left-to-right order, attempt calendar construction for each match, skip only candidates rejected as invalid calendar dates, and select the first valid candidate. A link with no valid candidate remains absent from extracted entries.

Only candidate-level calendar validation is suppressed. Decode failures and other genuine acquisition/normalization failures continue through existing typed boundaries. URL joining remains candidate construction only; existing Provider URL validation still decides whether normalized evidence is admissible.

**Alternative considered:** replace the parser with Beautiful Soup, lxml, or Provider-specific selectors. Rejected because the standard-library parser and regex approach already covers supported formats; a dependency or per-Provider parsing architecture is unnecessary for candidate validation.

### 3. Test at the existing injected-client and adapter seams

Extend the existing fake client to record request headers, then test normal propagation, non-identity header merging, case-insensitive override prevention, and SEC compatibility. Add compact production-shaped PBOC/NBS-style link fixtures containing navigation links, invalid dates, and multiple candidates. Assertions will cover exact deterministic output and absence of incidental `ValueError` while retaining existing typed fetch-failure tests.

**Alternative considered:** use hosted Providers as the regression suite. Rejected because network behavior is non-deterministic and cannot distinguish repository defects from upstream failures.

## Risks / Trade-offs

- [Header names are case-insensitive but Python mappings are not] → remove all caller keys whose lowercase form is `user-agent` before adding the authoritative canonical key.
- [Skipping invalid date candidates could admit a later incidental valid token] → retain the existing source precedence and left-to-right ordering, and require the same non-empty link fields and downstream URL/evidence validation.
- [A broad exception handler could hide real Provider defects] → catch only calendar-value rejection around individual candidate construction.
- [Hosted runs can still fail after the fix] → treat post-delivery hosted execution as verification of local defect removal, not proof that external Providers always succeed.

## Migration Plan

No data or configuration migration is required. Deliver the contract delta, minimal adapter/parser correction, and offline regressions together; run focused tests and the canonical repository quality gate before merge. Rollback is the code-and-spec revert because no persisted format or runtime state changes.
