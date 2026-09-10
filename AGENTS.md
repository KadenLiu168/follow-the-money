# AGENTS.md

本文件约束在 `follow-the-money` 仓库中执行开发、审查和 OpenSpec 迭代的 coding
agent。coding agent 负责代码、测试、规格和文档；Host Agent 只消费已发布 Feed 并
负责 evidence-preserving 的信息摘要表达。

## 1. Architecture Boundary

本仓库只有一个能力：credential-free、deterministic、typed、evidence-only 的
五域 Evidence Feed。当前边界为：

```text
Published Feed
      ↓
Feed validation
      ↓
Host Agent summarization/formatting
      ↓
Evidence-based information digest
```

Feed 只发布 `news`、`macro_release`、`policy`、`positioning` 和 `filing`。生产计划
只包含 Federal Reserve、BLS、PBOC、NBS、SSE、SZSE、SEC EDGAR 和 CFTC 八个必需的
verified、credential-free Provider。CFTC 是 minimum-one 的必需 weekly positioning
coverage。

Skill 只消费当前 validated published Feed，不接收公司、资产、主题、时间范围或
研究问题，也不读取历史 Feed 或 checkpoint。Host Agent 可以进行 grouping、heading、
ordering、consolidation 和 compression，但不得把 presentation choice 变成重要性、
因果、market impact、prediction、投资或交易判断。

不得引入 model/LLM runtime、credential/API-key request path、prompt pipeline、
Agent orchestration、standalone public CLI、自动交易或投资执行能力。运行时不得
恢复已移除的 evidence domain 或分析能力。

## 2. Sources of Truth

不同信息源承担不同职责：

* `openspec/specs/` 是当前 accepted contract；
* `openspec/changes/` 是当前未归档 contract delta；
* `openspec/changes/archive/` 只保存历史记录，不是当前 requirement；
* `src/`、`tests/`、`config/`、`providers/`、`schemas/`、`scripts/` 描述实际实现；
* README、`SKILL.md`、`docs/` 和 `references/` 只能描述真实的当前能力。

发生 Linear、OpenSpec、代码、测试或文档冲突时，明确区分 current implementation、
accepted contract、planned delta 和 future direction；不得静默选择，也不得在 scope
外扩大 Change。不要把 `AGENTS.md` 变成 domain spec 的第二真相源。

## 3. Iteration Rules

一个 Linear execution issue 对应一个 OpenSpec Change。实现前检查相关 issue（如可用）、
Change proposal/spec/design/tasks、受影响代码、测试、配置和文档。依赖只依据显式
`blockedBy`/`blocks` 或明确 architecture gate，不依据编号或 milestone 名称推断。
不要提前实现后续需求。

## 4. Implementation Invariants

Deterministic core 必须保持 deterministic、reproducible、credential-free、typed、
testable，并在 trust boundary fail-closed。不得弱化：

* verified provenance、source time 与 freshness；
* fixed cutoff/window、coverage、degradation 和完整 Provider outcomes；
* deterministic ordering、Feed identity/digest 和 canonical bytes；
* manifest-led atomic publication、checkpoint、lease、rate safety 和 typed exits；
* evidence-only Feed 与 Host-Agent evidence-preserving digest boundary。

Feed 不是 intelligence output，不得加入 analysis、ranking、regime、asset impact、
recommendation 或 trading instruction。不得把 unknown/unverified 数据伪装成 verified，
不得添加 hidden fallback 或 duplicated runtime authority。

## 5. Configuration and Providers

配置和 Provider manifest 是 trust boundary。保持 credential-free default operation、
closed contract、verified provenance 和运行时与 authoritative manifest/config 一致。
配置必须显式解析所有 surviving normative fields；unknown、removed、unsupported、
missing、unverified 或 over-declared 内容必须在 Provider work 和持久化 mutation 前
失败。

Provider manifests 是 Provider identity/version、verification、HTTPS URL policy、
source-link policy、charset/content limits、rate policy、pagination、empty semantics、
implemented payload types、cadence 和 fixture provenance 的 authority。`config/config.yaml`
负责应用/Feed字段，`config/providers.yaml` 负责 activation/coverage；不得创建第二个
独立 authority。

## 6. Scope and Contract Alignment

只修改当前 issue 必需的 implementation、对应 tests、必要 contract/config/schema/docs，
以及 proposal 明确要求的重构。不要顺手重构无关代码、升级无关依赖、添加 speculative
adapter/framework，或修改 archived Change。Contract 变化应检查并同步：

```text
openspec/specs/  schemas/  tests/  docs/  references/  SKILL.md  README*.md
```

## 7. Verification

开发期间先运行与修改直接相关的 focused tests。需要完整环境时运行：

```bash
uv sync --frozen --all-groups
```

iteration 完成前运行 canonical quality gate：

```bash
.venv/bin/python scripts/quality_gate.py
```

OpenSpec Change 完成前运行：

```bash
openspec doctor
openspec validate <change-name> --strict
openspec validate --all --strict
```

`--dry-run` 仍可能访问真实 Provider 并修改 rate state；只有在 output root 明确安全
且确需验证真实 execution boundary 时运行。普通测试使用 deterministic fixtures，不
依赖网络。不得声称未实际执行的检查已经通过。

## 8. Final Review and Completion Report

完成前确认：scope 和 blocker 满足；Feed 仍为五域、八 Provider、evidence-only；没有
model/credential/orchestration runtime；deterministic、provenance、freshness、coverage、
publication、identity 和 fail-closed guarantees 未削弱；tests、specs、implementation
和 docs 一致；未解决风险已说明。

完成报告简洁说明：

1. 实现了什么；
2. 修改了哪些 contract/architecture boundary；
3. 实际执行的验证及结果；
4. unresolved conflict/risk；
5. 是否发现应由后续 issue 处理的问题。

完成标准是：

```text
Linear scope + accepted OpenSpec delta + implementation + tests + truthful documentation
```

彼此一致。
