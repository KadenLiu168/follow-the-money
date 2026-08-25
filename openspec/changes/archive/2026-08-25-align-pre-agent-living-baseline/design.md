## Context

See `proposal.md` for motivation. ECO-31 aligns current-facing architecture claims; it does not change system behavior.

The pre-proposal audit produced the following source-of-truth disposition:

| Source | Current evidence | ECO-31 disposition |
| --- | --- | --- |
| Current implementation | `scripts/feed/follow-the-money-feed` forwards to `follow_the_money.feed.cli`. Its transitive local import closure contains Feed, Provider, configuration, schema, canonicalization, Unicode, and build-boundary modules, but not ledger, candidate/event, market/state, watchlist, scoring, selection, or audit modules. `pyproject.toml` exposes no console script and contains no LLM SDK. | Preserve runtime and caller graph unchanged. |
| `deterministic-core-retention` | Requires no embedded LLM runtime, one evidence-only Feed invocation, retained deterministic rules without production wiring, and an undefined future Agent Contract. | Already aligned; no delta. |
| `feed-evidence-pipeline` | Defines the credential-free Provider/Feed production behavior and declares the Feed to be evidence-only and the serialized external contract. | Already aligned; no delta. |
| `deterministic-research-engine` | Defines retained internal deterministic Python contracts and says only modules imported by the minimal Feed path may be called production-wired. | Already aligned; no delta. |
| Existing tests | `tests/test_no_llm_contract.py`, `tests/test_workflows.py`, `tests/test_neutralize_selection_and_scoring_contract.py`, and `tests/test_audit.py` already enforce the absent LLM/public-CLI surface, minimal Feed entry, and absence of scoring/ranking/audit production wiring. Focused domain suites independently exercise retained libraries. | Reuse as evidence; do not change test behavior. |
| `docs/architecture.md` | Defines `ResearchContext`, `AgentAnalysis`, and `BriefContext` in a concrete future sequence; depicts retained modules as one arrow-connected topology; calls the whole deterministic core live. | Replace with Live / Retained / Future vocabulary. |
| `SKILL.md` | Says the minimal Feed entry performs every deterministic step and calls the full deterministic core live. | Narrow the entry claim to Feed collection and Feed processing. |
| `README.md` / `README.zh-CN.md` | Describes the deterministic core as live, which can make tested retained libraries appear production-orchestrated. | Distinguish the live Feed path from retained tested no-caller libraries in both languages. |
| `pyproject.toml` description | Groups canonical Events, ledger, market state, scoring, and audit under the evidence-only Feed description, which implies those retained libraries are Feed stages. | Describe the Feed and retained no-caller libraries separately without changing dependencies or build configuration. |

The audit found no equivalent concrete future contract in other current-facing Markdown. Historical artifacts under `openspec/changes/archive/` contain superseded terminology by design and are not current requirements.

## Goals / Non-Goals

**Goals:**

- Give every edited current-facing artifact the same three-state vocabulary: Live, Retained, and Future.
- Make production-wired a caller-graph claim rather than a synonym for implemented or tested.
- Preserve exact current living requirements by declaring a zero-delta Change with `skip_specs: true`.
- Keep English and Chinese README claims semantically equivalent.
- Make the Apply diff mechanically auditable through a narrow documentation allowlist and existing verification gates.

**Non-Goals:**

- Defining names, schemas, stages, call counts, adapters, or orchestration for a future Skill-Agent Contract.
- Changing Feed behavior, serialization, Provider/configuration ownership, schemas, financial rules, or any retained library.
- Adding production callers, placeholder wiring, a new architecture capability, or an ECO-31-specific test/gate framework.
- Rewriting historical Change artifacts or dated validation evidence.

## Decisions

### 1. Use a zero-delta OpenSpec Change

Set `skip_specs: true` and create no files under this Change's `specs/` directory. The three living specs already express every relevant behavior and architecture invariant; a new or modified requirement would duplicate accepted contracts and contradict the instruction to modify them only after a proven semantic conflict.

Alternatives rejected:

- Modify `deterministic-core-retention`: rejected because it already requires the Live / Retained / Future distinction and explicitly leaves the future Agent Contract undefined.
- Add a documentation-alignment capability: rejected because documentation truthfulness is not a new runtime capability, and a permanent living spec would add a parallel architecture contract.
- Add stronger acceptance scenarios: rejected because ECO-32 owns formal acceptance-gate strengthening.

### 2. Define production status through the current entry closure

The sole live repository topology will be documented as:

```text
Evidence Providers
      ↓
Deterministic Evidence Feed
      ↓
Host Agent reasoning and narrative
      ↓
Grounded research output
```

The Feed side includes only work currently reached through the minimal entry: configuration resolution, Provider planning/fetching, normalization, deduplication, validation, identity/digest construction, health assessment, and publication. The Host Agent consumes the resulting evidence and owns financial interpretation and expression.

Retained modules will be shown as a flat capability inventory, not as arrow-connected production stages. Each will be described as typed, deterministic, reproducible, independently tested, reusable, and intentionally permitted to lack a current production orchestration caller.

### 3. Keep the future boundary deliberately content-free

Current-facing documents may say only that a future Skill-Agent Contract will define how Agent-owned reasoning interacts with retained deterministic capabilities after Pre-Agent Baseline Acceptance. They must not positively define object names, serialized shapes, stage ordering, invocation count, runtime topology, ownership adapters, or placeholder schemas.

The names `ResearchContext`, `AgentAnalysis`, and `BriefContext` may appear in the ECO-31 Change artifacts as prohibited stale examples and in archived history, but not as positive current-facing architecture definitions.

### 4. Apply the vocabulary surgically by artifact

- `docs/architecture.md`: replace the concrete future pipeline; separate the live path from the retained inventory; revise module/trust-boundary wording that implies all deterministic objects are production-wired; replace the transitional paragraph with an undefined-future statement.
- `SKILL.md`: change the opening contract so the minimal entry owns network access and deterministic Feed processing only; keep the two-step Feed-to-Agent flow; state explicitly that retained libraries are not invoked by that entry unless the Host Agent deliberately uses a library API in a future contract. Do not prescribe such use now.
- `README.md` and `README.zh-CN.md`: replace “deterministic core is live and tested” / “确定性核心已上线并有测试” with equivalent wording that identifies the Feed production path as live and the other deterministic libraries as tested but not production-orchestrated.
- `pyproject.toml`: narrow only the package `description` so the Feed and retained libraries are not collapsed into one live surface; do not change dependencies, build configuration, or entry points.
- Other current-facing documentation: edit only if a final scoped search finds another positive current claim equivalent to the confirmed stale statements. Historical records remain excluded.

### 5. Treat current tests as evidence, not ECO-31 implementation surface

No test is changed unless the Apply audit finds a concrete assertion that requires the stale future topology or claims a retained library is production-wired. The proposal audit found none.

Apply verification will reuse:

- `tests/test_no_llm_contract.py` for absent LLM/model/config/public-CLI surfaces, credential-free configuration, and minimal Feed behavior;
- `tests/test_workflows.py` for the single workflow invocation surface;
- `tests/test_neutralize_selection_and_scoring_contract.py` for no scoring/ranking production caller;
- `tests/test_audit.py` for no legacy or production audit wiring;
- existing retained-library suites for independent deterministic coverage;
- `.venv/bin/python scripts/quality_gate.py` as the canonical repository gate.

No real-network Feed dry run is needed because ECO-31 changes no execution boundary and `--dry-run` can mutate rate state.

### 6. Constrain Apply to an explicit allowlist

The expected Apply diff is limited to:

- `docs/architecture.md`
- `SKILL.md`
- `README.md`
- `README.zh-CN.md`
- the `pyproject.toml` package `description` only
- this Change's planning/task status files

Any proposed change to living specs, tests, runtime code, configuration, Providers, schemas, workflows, deployment, dependencies or other build metadata, archived Changes, or dated evidence must stop the Apply and be reported as a newly discovered scope conflict rather than silently absorbed.

## Risks / Trade-offs

- [Risk] “Retained” could be read as deprecated or inert. → State positively that these libraries are typed, deterministic, reproducible, tested, and reusable; only current production orchestration is absent.
- [Risk] A flat retained inventory could obscure that some Feed infrastructure is itself deterministic. → Define Live by reachability from the minimal Feed entry, not by whether a module is deterministic.
- [Risk] Stale terminology can remain in historical files and make broad searches noisy. → Scope final current-facing searches explicitly, report archived matches as historical, and never rewrite them.
- [Risk] English and Chinese summaries can drift semantically. → Review the two README paragraphs side by side and require the same Live / Retained / Future distinctions.
- [Risk] Documentation-only edits could accidentally imply new Host Agent runtime behavior. → Keep future wording boundary-only and forbid new object names, call sequences, adapters, schemas, or invocation requirements.
