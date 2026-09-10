# Configuration

Configuration is closed and credential-free. `config/config.yaml` owns Feed
runtime limits and roots. `config/providers.yaml` owns activation and coverage.
Provider-specific facts remain in `providers/<provider>/manifest.yaml`.

## Surviving configuration

- Feed window, deadline, concurrency, response, item, serialization, and lock
  limits;
- output, runtime-state, and run roots;
- rate-registry persistence contract;
- source-family provenance;
- SEC watched-company CIK filters;
- exactly eight required Provider activation entries;
- exactly five required coverage groups.

The required Providers are Federal Reserve, BLS, PBOC, NBS, SSE, SZSE, SEC EDGAR,
and CFTC. CFTC is enabled and required with minimum one in
`cftc_positioning`.

Each Provider manifest owns identity, verification evidence, authentication and
protocol, fetch/redirect/source-link policy, charset/content type, limits, rate
policy, pagination, empty-window semantics, implemented payload types, cadence,
and fixture provenance. All shipped manifests are HTTPS and credential-free.

Unknown keys, removed analytics/Agent fields, unsupported Provider IDs,
missing required values, disabled required Providers, over-declared payloads,
and invalid coverage fail closed before requests or normal rate-state mutation.
The loader does not provide hidden defaults for surviving normative values.

## Removed configuration

There is no configuration for Agent invocation, Audit/Event processing,
entities, market roles or sessions, Market State, watchlists, scoring/ranking,
calendar horizons, flow, Yahoo, model credentials, or Brief-era runtime policy.
