# Follow the Money（追踪资金）

确定性驱动的每日金融情报管线：从免费的中美官方与公开来源生成纯证据 Feed，
构建规范原子事件，经受限 LLM 分析，产出固定格式的中文《晨间资金简报》。
原则是"脚本优先、LLM 殿后"（script-first, LLM-last）。

## 这个仓库是什么

一套完整的 Python 3.12 应用，把免费的公开金融证据加工为每日 08:30
（Asia/Shanghai）的《晨间资金简报》。每条重要事实主张都能追溯到来源；
确定性工作（采集、归一化、去重、市场统计、打分、选择、校验）绝不出现在
prompt 里；LLM 只承担四个受限环节：语义事件解析、验证包的财务分析、
结构化编辑合成、以及最终语言审计。

## 投资协助边界

简报提供金融情报与不确定性提示，**绝不**包含直接的中文或英文买入、卖出、
加仓、减仓、仓位、入场、离场、止损、目标价等指令——无论出现在结构化字段
还是渲染文本中。本仓库内容不构成投资建议。

## 目录结构

```
config/          封闭的版本化 YAML 配置（v1 默认值）
providers/       provider 契约 manifest 与 fixture 来源记录
schemas/         JSON Schema 2020-12 契约（序列化权威）
prompts/         四个 LLM 环节的 prompt
src/follow_the_money/  生产代码包
scripts/feed/    薄包装：follow-the-money-feed
scripts/skill/   薄包装：follow-the-money-skill
feeds/           发布产物（daily/<date>/<run_id>.json、latest.json）
runs/            本地审计 bundle（Git 忽略）
tests/           pytest 测试套件（无需凭据）
evals/           黄金日 fixture 与评估报告
docs/            架构、契约、runbook
.github/workflows/ 托管 CI 与定时 Feed 工作流模板
```

## 快速开始

```bash
uv sync --frozen --all-groups
uv run pytest            # 全量免凭据测试
uv run follow-the-money feed --dry-run
```

## CLI 退出码契约

- `0` — 请求完整成功
- `1` — 运行时/领域/schema/引用/完整性/期限/发布/交付失败
- `2` — 用法、配置、缺失必需凭据、启动能力错误

子命令：`feed`、`brief`、`eval`、`replay`。详见 `docs/`。

## 当前引导边界

本仓库**不是** Git checkout，也尚未初始化为 Git 仓库：没有 license 文件、
没有 Git 历史、没有远端、没有已启用的工作流。这些属于另行明确授权的部署决策。

## 真实外部调度边界

定时 Feed 工作流是仓库内的**模板**：运行前必须单独准备一台带标签的专用
self-hosted runner，配置持久化共享输出根与持久速率状态，并显式打开 opt-in
开关。工作流启用与外部 08:30 调度是部署事项，本仓库不作此类承诺。

## 文档

- `docs/architecture.md` — 管线与信任边界
- `docs/feed-contract.md` — Feed schema、窗口/截止模型、发布
- `docs/scoring.md` — 确定性打分与选择契约
- `docs/evaluation.md` — 离线/在线回归评估
- 操作手册：`docs/runbooks/`
