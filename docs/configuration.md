# Configuration authority

The Feed resolves checked-in configuration before creating runtime state.

| Source | Authority |
| --- | --- |
| `config/config.yaml` | application identity and paths, time/freshness policy, Feed limits and global ceilings, scoring, Market State, calendar, safety lexicon, rate-registry contract, sessions, source families, entities, watched companies, and the canonical role registry |
| `providers/<provider_id>/manifest.yaml` | Provider identity and contract version, verification evidence, authentication/protocol, hosts and source-link rules, charset/content type, request/response limits, rate, timing/units/freshness, pagination, empty-window semantics, existing mapping declarations, and fixture provenance |
| `config/providers.yaml` | versioned Provider enablement policy and the complete multi-row coverage matrix |

`ProviderEntry` is the single resolved contract consumed by adapters, rate and
host planning, coverage assessment, and the redacted `provider_contracts`
snapshot. A retained registry field is a validation-only compatibility mirror;
it cannot control runtime behavior. Coverage membership comes only from matrix
rows, so a Provider may belong to multiple groups.

`output_root` and `runtime_state_root` are separate required application paths.
The former is the consumer Feed product root (`feeds/`); the latter owns the
collection lock, RateRegistry, deployment lease, and Feed continuity checkpoint
(`.feed-state/`). Runtime layout is excluded from the Feed semantic
configuration snapshot.

This remains an evidence-only, credential-free Provider → Feed → Host Agent
boundary. It does not perform mapping research or introduce an Agent/LLM
runtime.
