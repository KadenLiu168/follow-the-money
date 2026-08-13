# Follow the Money（追踪资金）

面向 AI Agent 的证据驱动金融研究 Skill：一个确定性、免凭据的纯证据 Feed，
来自免费的中美官方与公开来源；同时保留确定性引擎（证据台账、候选事件、
市场快照/状态、关注列表、打分/选择规则、安全审计），等待未来的 Agent
交付契约。

Agent 负责理解、推理与表达；`follow-the-money` 提供事实、规则、确定性计算
与可验证性。

## 这个仓库是什么

一个 Python 3.12 包，采集并发布 schema 校验、携带身份的纯证据 Feed：运行
身份、单一固定证据截止时间、逐条 provider 来源、规范摘要与契约快照。仓库
中不存在任何凭据、模型或 LLM runtime。

仓库处于刻意的过渡状态：确定性核心已上线并有测试，而基于核心的结构化
Agent 契约（研究/分析/简报编排）留给未来的 Change。

## 投资协助边界

保留的安全审计（`ClaimAuditor`）会标记被禁止的交易指令（买入、卖出、加仓、
减仓、仓位、入场、离场、止损、止盈、目标价——中文或英文），并带描述性
豁免。本仓库内容不构成投资建议。

## 目录结构

```
config/          封闭的版本化 YAML 配置（v1 默认值，无任何密钥）
providers/       provider 契约 manifest 与 fixture 来源记录
schemas/         JSON Schema 2020-12 契约（feed.schema.json）
src/follow_the_money/  生产代码包（确定性引擎）
scripts/feed/    最小内部 Feed 入口：follow-the-money-feed
feeds/           发布产物（daily/<date>/<run_id>.json、latest.json）
tests/           pytest 测试套件（无需凭据）
docs/            架构、契约、runbook
.github/workflows/ 托管 CI 与定时 Feed 工作流模板
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

## 当前引导边界

本仓库**不是** Git checkout，也尚未初始化为 Git 仓库：没有 license 文件、
没有 Git 历史、没有远端、没有已启用的工作流。这些属于另行明确授权的部署决策。

## 真实外部调度边界

定时 Feed 工作流是仓库内的**模板**：运行前必须单独准备一台带标签的专用
self-hosted runner，配置持久化共享输出根与持久速率状态，并显式打开 opt-in
开关。工作流启用与外部 08:30 调度是部署事项，本仓库不作此类承诺。

## 文档

- `docs/architecture.md` — 保留的确定性引擎与过渡状态
- `docs/feed-contract.md` — Feed schema、窗口/截止模型、发布
- `docs/scoring.md` — 确定性打分与选择契约
- 操作手册：`docs/runbooks/`
