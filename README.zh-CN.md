# Follow the Money（追踪资金）

面向 AI Agent 的证据驱动金融研究 Skill：一个确定性、免凭据的纯证据 Feed，
来自免费的中美官方与公开来源；同时保留确定性引擎（证据台账、候选事件、
市场快照/状态、关注列表、打分/选择规则、安全审计）。语义层的 Skill
capability surface 与 responsibility boundary 已定义；具体的 Skill-Agent
integration 仍然 deferred。

Agent 负责理解、推理与表达；`follow-the-money` 提供事实、规则、确定性计算
与可验证性。

## 这个仓库是什么

一个 Python 3.12 包，当前 live production path 负责采集并发布 schema 校验、
携带身份的纯证据 Feed：运行身份、单一固定证据截止时间、逐条 provider 来源、
规范摘要与契约快照。仓库中不存在任何凭据、模型或 LLM runtime。

保留的确定性库是 typed、可复现、独立测试且可复用的，但当前没有 production
orchestration caller。Host Agent 在消费 Feed 后负责推理与叙事；命名 retained
capability 不会增加 production caller。

## 语义 capability surface

当前 closed semantic catalog 恰好包含六个 family：

- Evidence Feed — `live-production`。
- Evidence and Event Structuring — `retained-no-production-caller`。
- Market Analytics and State — `retained-no-production-caller`。
- Confidence and Watchlist — `retained-no-production-caller`。
- Scoring and Ranking — `retained-no-production-caller`。
- Deterministic Audit — `retained-no-production-caller`。

这些是描述 architecture 的标签，不是 runtime state、configuration、serialized
metadata、capability registry 或 workflow stage。repository/Skill 只拥有这些
family 已接受的 deterministic behavior、invariants 与 capability-local validation；
详细行为仍由现有 living specs 负责。Host Agent 负责 research intent、
interpretation、reasoning、hypotheses、conclusions、working analysis 与 narrative；
deterministic engine 是 Skill 内部责任层，不是第三参与者或 Agent-callable endpoint。
结果只在 governing spec 保证的范围内具有 authority；在该 governing capability
之外由 consumer 派生的值归 consumer/Agent 所有，跨边界或 deterministic processing 不会提升 provenance、
verification 或 authority。ECO-35 仍负责 grounding、final-output validation、
unsupported-claim、acceptance、retry、rewrite 与 recovery policy。Agent-facing
schema、invocation、orchestration 与 runtime implementation 仍 deferred。

## 投资协助边界

保留的安全审计（`ClaimAuditor`）会标记被禁止的交易指令（买入、卖出、加仓、
减仓、仓位、入场、离场、止损、止盈、目标价——中文或英文），并带描述性
豁免。本仓库内容不构成投资建议。

## 目录结构

```
config/          封闭的版本化 YAML 配置（v1 默认值，无任何密钥）
providers/       provider 契约 manifest 与 fixture 来源记录
schemas/         JSON Schema 2020-12 契约（feed.schema.json）
src/follow_the_money/  live Feed 路径与保留的确定性库
scripts/feed/    最小内部 Feed 入口：follow-the-money-feed
feeds/           发布产物（daily/<date>/<run_id>.json、latest.json）
tests/           pytest 测试套件（无需凭据）
docs/            架构、契约、runbook
.github/workflows/ 托管 CI 与定时 Feed 工作流模板

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

## 真实外部调度边界

定时 Feed 工作流是仓库内的**模板**：运行前必须单独准备一台带标签的专用
self-hosted runner，配置持久化共享输出根与持久速率状态，并显式打开 opt-in
开关。工作流启用与外部 08:30 调度是部署事项，本仓库不作此类承诺。

## 文档

- `docs/architecture.md` — live Feed 路径、保留能力与未来边界
- `docs/feed-contract.md` — Feed schema、窗口/截止模型、发布
- `docs/scoring.md` — 确定性打分与 ranking 契约
- 操作手册：`docs/runbooks/`
