# Proposal

## Why

Add monitored Weibo posts to the existing current information digest without turning social commentary into verified financial conclusions or making official-source publication depend on a session Cookie. The user accepts unrecovered failed Social windows, provided the current digest necessarily discloses the acquisition failure and missing window.

## What Changes

- **BREAKING**: Evolve logical Feed/manifest from 5 to 6, artifacts from 2 to 3, and DigestContext from 2 to 3. Append `social` to the five existing domains; publish exactly six artifacts, including empty Social.
- Retain the eight required credential-free core Providers and their existing blocked-exemption behavior. Add only optional `weibo_social`, with a configuration-owned account registry initially selecting `dan_bin_weibo` / `1249424622` / 但斌.
- Use external `dataabc/weibo-crawler` pinned at `a3bfe515e9886b84151c609debdc636cbb0e9730`, never as identity, window, health, checkpoint, rate, scheduling, or evidence authority. Force `remove_html_tag=0`, Cookie-based acquisition, isolated temporary output, source-time normalization and FTM half-open filtering.
- Admit a whole Social Provider slice only after positive completion verification. Approved acquisition failures discard that slice and degrade an otherwise publishable Feed; internal integrity, configuration, global deadline and durable-state failures remain fatal.
- Keep the sole advancing Feed checkpoint. Publish no carried Social evidence, backfill, or per-account state. Failed Social windows advance with accepted degraded publication and are not automatically recovered.
- Project one current Social post into one reader unit. Require current-digest disclosure of Social failure, affected configured accounts, window, sanitized reason and no automatic backfill, even when there are no current updates. Add no email, issue, push, or historical reminder channel.
- Gate backend integration on a concrete per-send control seam and positive completion evidence; gate production activation on offline verification, licensing/content-use disposition and controlled hosted acceptance. A raw subprocess plus final JSON is not an approved bypass.
- Restrict P0 to originals and reshares with bounded referenced context; omit optional media metadata and separate link extraction. No X, comments collection, semantic clustering, automatic login, crawler source modification/vendoring, generic framework or model runtime.

## Capabilities

### New Capabilities

- `social-evidence`: Closed Weibo account, acquisition, Secret, completeness and Social payload contracts within the sole Evidence Feed capability, not a new public product.

### Modified Capabilities

- `feed-evidence-pipeline`: Six-domain versions, optional Social acquisition, unchanged core safety, no-backfill continuity, hosted operation and bounded v5 migration.
- `digest-preparation-contract`: DigestContext v3, Social current units, four-way Social status and structured failure limitations.
- `digest-presentation-contract`: Social attribution and mandatory current-window failure disclosure without interpreting or executing source content.
- `skill-capability-surface`: One Feed with eight credential-free core Providers and one optional credentialed extension.
- `deterministic-core-retention`: Six-domain core and truthful credential-boundary documentation, retaining credential-free configuration/import.
- `information-digest-invocation`: v3 handoff and current-digest-only Social failure notification.
- `skill-agent-responsibility-boundary`: v3 responsibility boundary and non-omittable Social limitations.

## Impact

Implementation will affect configuration models/loaders, Provider manifest resolution and registry, focused Weibo modules, managed-request integration, Feed orchestration/health/freshness/snapshot logic, schemas, bundle/migration/deployment/remote validation, Digest preparation, the existing `generate-feed.yml`, tests and current-facing documentation including `AGENTS.md`, `SKILL.md` and the Social presentation reference. Main specs and production files are not modified by this proposal workflow.

The user's supplied colleague plan and the `weibo-acquisition-spike-handoff.md` summary are accepted prior findings, not independently reproduced evidence. The original report, fixture files, branch and backend checkout are unavailable in the inspected workspace. Reconstruct test cases with honest provenance; do not label synthetic fixtures as historical captures. No live acquisition is authorized by creating this Change. No Linear tool/issue is available in this session; attach an execution issue if the project supplies one.

Unresolved external constraints include the reported absence of a crawler license, permission to republish Social text, manual Cookie lifecycle, anti-bot behavior and the existence of a safe supported integration seam. These are explicit gates, not assumed capabilities or authorization to broaden scope.
