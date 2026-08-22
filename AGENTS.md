# AGENTS.md

本文件约束在 `follow-the-money` 仓库中执行开发、审查和 OpenSpec 迭代的 coding agent。

这里的 **coding agent** 与产品中的 **Host Agent** 不同：

* coding agent：修改和审查代码、测试、规格与文档。
* Host Agent：消费本仓库能力，负责金融理解、推理和表达。

本文件是开发协作约束，不是产品运行时 Agent contract。

## 1. Architecture Boundary

`follow-the-money` 是面向 Host Agent 的金融研究 Skill，核心是 credential-free deterministic evidence engine。

当前 live production path：

```text
Evidence providers
      ↓
Deterministic Feed
      ↓
Host Agent reasoning
      ↓
Grounded research output
```

仓库负责事实、provenance、确定性规则、计算与验证；Host Agent 负责分析和叙事。

除非当前已批准的 OpenSpec Change 明确要求，不得引入：

* embedded LLM runtime / model SDK / LLM request path
* API key / model configuration
* application-runtime prompt pipeline
* Resolver / Analyst / Editor / Brief 固定流水线
* standalone public CLI product
* 自动交易或投资执行能力
* 为补全 pipeline 而 fake-wire retained deterministic libraries

Post-Feed deterministic libraries 暂无 production caller 是合法状态。

## 2. Sources of Truth

不同信息源承担不同职责，不设置简单的全局优先级。

### Linear

定义当前 iteration 的：

* Goal / In Scope / Out of Scope
* milestone
* status
* `blockedBy` / `blocks`

### OpenSpec

* `openspec/specs/`：当前 accepted contract
* `openspec/changes/`：当前未归档 contract delta
* `openspec/changes/archive/`：历史记录，不是当前 requirement

### Code and Tests

描述当前实际实现。

根据变更范围检查：

```text
src/follow_the_money/
tests/
config/
providers/
schemas/
scripts/
```

### Docs and Skill

`README*`、`SKILL.md`、`docs/` 必须只描述真实存在的当前能力。

### Conflicts

如果 Linear、OpenSpec、代码、测试或文档不一致：

1. 明确指出冲突；
2. 区分 current implementation、accepted contract、planned delta 和 future direction；
3. 不得静默选择其中一方；
4. 只有当前 issue scope 包含该问题时才修复；
5. scope 外问题记录出来，不扩大当前 Change。

不要把 `AGENTS.md` 扩展成 OpenSpec 的平行规格；具体 domain behavior 以 living specs 为准。

## 3. Iteration Rules

本项目遵循：

```text
1 Linear execution issue = 1 OpenSpec Change
```

开始 iteration 前：

1. 阅读 Linear issue；
2. 检查 milestone 和 blocking relations；
3. 阅读相关 living specs；
4. 检查 active Changes 是否冲突或重叠；
5. 定位相关 implementation / tests / config / schemas / docs；
6. 明确：

   * 当前已有能力
   * 当前 Gap
   * 本 issue 要解决的 Gap
   * explicit non-goals / future work

### Dependency

不得根据 ECO 编号或 milestone 名称自行推断严格串行顺序。

执行顺序以：

1. Linear 显式 `blockedBy` / `blocks`
2. 项目明确 architecture gate

为准。

没有依赖冲突、修改边界独立的工作可以并行。

不得因为后续需求已经可预见而提前实现。

## 4. Architecture Gates

在 Pre-Agent Baseline Acceptance 明确通过前，不得定义或实现：

```text
ResearchContext
AgentAnalysis
BriefContext
Agent runtime orchestration
fixed Agent delivery pipeline
replacement LLM pipeline
```

Future architecture 可以作为方向存在，但不是 current contract。

Skill–Agent Contract 被正式接受前，也不得自行设计 Phase 5 runtime architecture。

不要为未来 contract 提前增加 schema、adapter、placeholder 或 speculative abstraction。

## 5. Implementation Invariants

Deterministic core 必须保持：

* deterministic
* reproducible
* credential-free
* typed
* testable
* fail-closed at trust boundaries

不得弱化 living specs 已定义的：

* provenance
* verification
* evidence-only boundary
* identity / digest
* deterministic ordering
* coverage / degradation semantics
* typed failure handling

Feed 是 evidence contract，不是 intelligence output。

不要在 Feed 中加入金融分析、ranking、market regime、asset impact 或投资判断。

Retained libraries，包括 ledger、candidate/event、market、watchlist、scoring、selection、`ClaimAuditor`，可以没有 production orchestration caller。

“没有 caller”本身不能作为删除或接线理由。

内部 Python structure 也不应仅为了形式完整而增加 external JSON Schema；只有明确建立 serialized boundary 的 Change 才设计对应 contract。

## 6. Configuration, Providers and Safety

配置与 provider 属于 trust boundary。

相关修改必须保持：

* credential-free default operation
* closed and explicit contracts
* verified provenance
* fail-closed validation
* runtime behavior 与 authoritative contract 一致

不得增加 hidden fallback、duplicated truth source，或把 unknown / unverified 内容伪装成 verified。

仓库提供金融研究能力，不提供确定性交易指令。

`ClaimAuditor` 应保持 deterministic safety capability，不得演变成 LLM policy layer 或自动文本重写系统。

## 7. Scope and Contract Alignment

遵守最小必要变更原则。

可以修改：

* 当前 issue 必需的 implementation
* 对应 tests
* 必需的 config / provider / schema / contract
* 为保持事实一致必须同步的 docs / SKILL
* proposal 明确要求的重构

不要：

* 顺手重构无关模块
* 提前实现后续 ECO
* 添加 speculative framework
* 因无 caller 删除 retained capability
* 为测试方便弱化 production invariant
* 做无关 dependency upgrade
* 修改 archived Change 来改写历史

Contract-changing modification 应检查是否需要同步：

```text
openspec/specs/
openspec/changes/
schemas/
tests/
docs/
SKILL.md
README.md
README.zh-CN.md
```

不要只修改 implementation 而留下 stale contract 或 capability claim。

## 8. Verification

开发期间先运行与当前修改直接相关的 focused tests。

准备环境：

```bash
uv sync --frozen --all-groups
```

最终 repository quality gate：

```bash
.venv/bin/python scripts/quality_gate.py
```

不要用较弱的自定义检查集合替代 canonical quality gate。

OpenSpec Change 完成前检查：

```bash
openspec doctor
openspec validate <change-name> --strict
openspec validate --all --strict
```

### Feed Dry Run

`--dry-run` 不是完全无副作用的测试。

它可能访问真实 provider，并持久修改 rate state。

仅在确实需要验证真实 Feed execution boundary，且运行环境与 output root 明确安全时执行：

```bash
uv run python -m follow_the_money.feed.cli --dry-run
```

普通测试优先使用 deterministic fixtures，不依赖真实网络。

不得声称未实际执行的检查已经通过。

## 9. Final Review

完成前确认：

* Linear blocker 已满足；
* 没有超出当前 issue scope；
* 没有引入 LLM / model / credential runtime；
* 没有把 future Agent Contract 当成 current contract；
* Feed 仍保持 evidence-only；
* deterministic / fail-closed invariants 未被削弱；
* provenance / verification claim 真实；
* retained libraries 未被误删或 fake-wire；
* tests 覆盖当前 contract delta；
* specs、implementation、tests 和 docs 一致；
* 未解决冲突和风险已明确说明。

## 10. Completion Report

完成工作后简洁说明：

1. 实现了什么；
2. 修改了哪些 contract / architecture boundaries；
3. 实际执行了哪些验证及结果；
4. 是否存在 unresolved conflict / risk；
5. 是否发现应由后续 Linear issue 处理的问题。

不要把“代码可以运行”等同于 iteration 完成。

完成标准是：

```text
Linear scope
+ accepted OpenSpec delta
+ implementation
+ tests
+ truthful documentation
```

彼此一致。