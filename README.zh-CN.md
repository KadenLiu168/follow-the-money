# Follow the Money（追踪资金）

面向 AI Agent 的证据驱动金融研究 Skill：一个确定性、免凭据的纯证据 Feed，
来自免费的中美官方与公开来源；同时保留确定性引擎（证据台账、候选事件、
市场快照/状态、关注列表、打分/选择规则、安全审计）。语义层的 Skill
capability surface、responsibility boundary 与 private on-demand Audit 和 Event
Structuring invocation boundary 已实现；Audit 与 Event Structuring 之外的
Skill-Agent integration 仍 deferred。

Agent 负责理解、推理与表达；`follow-the-money` 提供事实、规则、确定性计算
与可验证性。

## 这个仓库是什么

一个 Python 3.12 包，当前 live production path 负责采集并发布 schema 校验、
携带身份的纯证据 Feed：运行身份、单一固定证据截止时间、逐条 provider 来源、
规范摘要与契约快照。仓库中不存在任何凭据、模型或 LLM runtime。独立的 private
one-shot boundary 提供 on-demand deterministic Audit 和 Event Structuring；其他
retained library 仍没有 production caller。

Audit 与 Event Structuring 之外的保留确定性库是 typed、可复现、独立测试且可复用的，
但当前没有 production orchestration caller。Host Agent 在消费 Feed 后负责推理与叙事；
命名 retained capability 不会增加 production caller。

## 语义 capability surface

当前 closed semantic catalog 恰好包含六个 family：

- Evidence Feed — `live-production`。
- Evidence and Event Structuring — `live-production`（on demand）。
- Market Analytics and State — `retained-no-production-caller`。
- Confidence and Watchlist — `retained-no-production-caller`。
- Scoring and Ranking — `retained-no-production-caller`。
- Deterministic Audit — `live-production`（on demand）。

这些是描述 architecture 的标签，不是 runtime state、configuration、serialized
metadata、capability registry 或 workflow stage。repository/Skill 只拥有这些
family 已接受的 deterministic behavior、invariants 与 capability-local validation；
详细行为仍由现有 living specs 负责。Host Agent 负责 research intent、
interpretation、reasoning、hypotheses、conclusions、working analysis 与 narrative；
deterministic engine 是 Skill 内部责任层，不是第三参与者或 Agent-callable endpoint。
结果只在 governing spec 保证的范围内具有 authority；在该 governing capability
之外由 consumer 派生的值归 consumer/Agent 所有，跨边界或 deterministic processing 不会提升 provenance、
verification 或 authority。runtime-neutral 的
`agent-grounding-validation-contract` 现在定义 semantic grounding、validation
authority、受约束的 output admissibility、unsupported assertion 与 semantic
recovery。仅有 evidence reference 不代表 semantic support，deterministic
success 也不代表 entailment 或 complete answer validity；Host Agent 负责
semantic support assessment 与 narrative emission，deterministic finding 只在
其 governing spec 范围内保留 Skill authority。已知缺少支持的 grounded
assertion 与尚未解决且适用的 critical finding 不得 unchanged 输出。private
one-shot Agent invocation boundary 已实现，仅提供 `audit.text`、`audit.claims`
与 `event.structure`，不包含 orchestration、retry、rewrite loop 或 runtime
registry。

## 已接受的 invocation contract 与 Phase 5 计划

private Host-Agent boundary 从 stdin 接收一个 UTF-8 JSON request，并向 stdout
返回一个 JSON response；diagnostics 只能写入 stderr。Version 1 定义
`audit.text`、`audit.claims` 与 `event.structure`。成功 response 携带 bounded
deterministic Audit 或 Event result；typed invocation error 与 capability result
分离。这里没有 session、streaming、discovery、registry、remote transport、
shared state、automatic chaining、LLM runtime，且除 on-demand Audit 与 Event
Structuring 外没有其他 capability caller。

activation plan 记录已验证状态：Feed 保持 live 且不变；Audit 通过已实现的
private boundary 处于 `live-production`；Evidence and Event Structuring 通过已实现的
`event.structure` operation 处于 `live-production` 且保持 on demand；Market
Analytics and State、Confidence and Watchlist、Scoring and Ranking 仍 deferred
且保持 `retained-no-production-caller`。

## 投资协助边界

保留的安全审计（`ClaimAuditor`）会标记被禁止的交易指令（买入、卖出、加仓、
减仓、仓位、入场、离场、止损、止盈、目标价——中文或英文），并带描述性
豁免。本仓库内容不构成投资建议。

## 目录结构

```
config/          封闭的版本化 YAML 配置（v1 默认值，无任何密钥）
providers/       provider 契约 manifest 与 fixture 来源记录
schemas/         JSON Schema 2020-12 契约（Feed 与 Agent invocation）
src/follow_the_money/  live Feed/Audit/Event 路径与保留的确定性库
scripts/feed/    最小内部 Feed 入口：follow-the-money-feed
feeds/           当前 consumer Feed 产物（latest.json）
.feed-state/     仓库持久化的 lock、RateRegistry、lease 与 checkpoint
tests/           pytest 测试套件（无需凭据）
docs/            架构、契约、runbook
.github/workflows/ 托管 CI 与已启用的定时 Feed 工作流

配置 authority 与单一 resolved Provider contract 见
[`docs/configuration.md`](docs/configuration.md)。
```

## 快速开始

```bash
uv sync --frozen --all-groups
uv run pytest            # 全量免凭据测试
uv run python -m follow_the_money.feed.cli --dry-run
# 或：scripts/feed/follow-the-money-feed --dry-run
```

## 退出码契约（最小内部 Feed 入口）

- `0` — 健康或降级 Feed 成功（警告在 stderr/status）
- `1` — 生成/发布/schema/完整性失败
- `2` — 用法、配置或启动能力错误

不存在公开的用户面向 CLI 产品形态：`brief`、`eval`、`replay` 子命令与
独立 console script 均已移除。

## 定时 Feed 边界

GitHub Actions 使用 `ubuntu-latest` 在 `20 0 * * *`（Asia/Shanghai 08:20）
运行免凭据 Feed，也支持 `workflow_dispatch`。`feeds/` 只保存 consumer product，
`.feed-state/` 保存仓库持久 runtime state。首次 invocation 可能执行零 Provider
请求的 legacy migration 或 bootstrap；正常 arming 与未完成运行恢复使用记录的
checkpoint 和 lease 保守边界。`evidence_cutoff_at` 取实际运行时刻，不取名义调度时刻。
checkpoint 负责 runtime continuity；Git history 只是仓库历史，不是 Feed archive 或
historical query API。在宣称部署可运行前，必须验证 Actions `contents: write` 与分支策略；
Host Agent 对 Feed 的消费和推理仍是之后独立的动作。

## 文档

- `docs/architecture.md` — live Feed 路径、保留能力与未来边界
- `docs/feed-contract.md` — Feed schema、窗口/截止模型、发布
- `docs/scoring.md` — 确定性打分与 ranking 契约
- 操作手册：`docs/runbooks/`
