# Architecture Boundary

## Responsibilities

```text
Evidence providers
      -> GitHub Actions deterministic Feed production
      -> published evidence Feed
      -> Skill validation
      -> Host Agent reasoning
      -> grounded research report
```

GitHub Actions owns Provider collection and deterministic Feed processing. Normal
Skill invocation consumes the published Feed through
`scripts/skill/prepare-feed`; it never invokes the local producer. The Host Agent
owns research intent, financial interpretation, reasoning and judgment,
hypotheses, conclusions, working analysis, and user-facing narrative.

The repository/Skill owns facts, provenance, accepted deterministic semantics,
transformations, calculations, canonicalization, ordering, and capability-local
validation. The deterministic engine is an internal responsibility layer, not a
third participant or an Agent-callable endpoint.

A Skill-produced result is authoritative only for the exact guarantees of its
governing living spec. Consumer-modified, supplemented, interpreted, or derived
values are consumer- or Host-Agent-owned. Boundary crossing and deterministic
processing do not upgrade provenance, verification, or authority.

## Independent private boundary

The Host Agent may explicitly and independently invoke Deterministic Audit or
Event Structuring through the private one-shot process contract in
`schemas/agent-invocation.schema.json`: one UTF-8 JSON request on stdin and one
UTF-8 JSON response on stdout, with diagnostics on stderr. Version 1 statically
dispatches only `audit.text`, `audit.claims`, and `event.structure`.

This boundary provides no session, streaming, discovery, runtime registry,
remote transport, shared state, hidden chaining, retry or rewrite loop. Audit,
Event Structuring, and Feed do not form a mandatory sequence. Retained
capabilities have no production orchestration caller.

## Hard boundaries

Unless an accepted OpenSpec Change explicitly requires otherwise, preserve the
credential-free Provider-to-Feed-to-Host-Agent architecture. Add no embedded LLM
runtime, model SDK, LLM request path, API-key/model configuration, application
prompt pipeline, fixed Agent delivery pipeline, standalone public CLI product,
automatic trading or investment execution, or placeholder wiring for retained
libraries.

The authoritative contracts are the living specs under `openspec/specs/`.
