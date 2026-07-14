# follow-the-money

> **追踪美国"聪明钱"的真实动作 — 直接来自 SEC 公开数据。**

每天把 8 位顶级基金经理的持仓变动 + 全美激进股东 13D/G 申报，做成可读的中文/英文摘要推送给你。

---

## 怎么用

这个项目是一个 **agent skill**：让 AI agent 加载 `SKILL.md`，agent 读完说明书后自己读数据、渲染、推送。推荐用 🅰️ agent 模式，绝大多数用户只需这一步。

---

## 🅰️ 用 AI agent 跑（推荐）

### 原理

`SKILL.md` 是一份"说明书"，告诉 agent 怎么一步步完成任务。agent 读完说明书后，自己去读数据、自己渲染、自己推送。

```
你  ──说──▶  agent  ──读──▶  SKILL.md（说明书）
                          ──读──▶  feed-13f.json / feed-13dg/
                          ──渲染─▶  prompts/*.md
                          ──推送─▶  stdout
```

> **数据源**：agent 触发 `/money` 时，会先 `node scripts/fetch-feed.js` 从 GitHub 拉取最新 feed 到本地缓存目录（默认 `$XDG_CACHE_HOME/follow-the-money/feed/`）。GitHub 上的 feed 由 CI 每 ~12h 自动更新，所以 agent 永远拿到的是 EDGAR 的最新数据。无需你手动 `git pull`。本地如果跑了 `aggregate.js`，fetch 失败时自动 fallback 到本地数据。

### 你需要的

- 一个能加载 `SKILL.md` 的 agent（Claude Code / Codex / OpenClaw / 其他）
- agent 能访问到本仓库的文件（feed 数据 + scripts + prompts）
- agent 能跑命令或调 HTTP API（看具体平台能力）

### 步骤

#### 1. 让 agent 能读到仓库

```bash
# 把仓库放到 agent 工作目录
git clone https://github.com/KadenLiu168/follow-the-money ~/follow-the-money
cd ~/follow-the-money
```

或在 agent 平台里导入这个 GitHub 仓库。

#### 2. 触发

在 agent 里说：

```
/money
```

或自然语言：

- "今天聪明钱有什么动作"
- "给我看今天的 fund moves"
- "今天 13D 申报有哪些"

#### 3. 配定时（让 agent 每天自动跑）

**如果 agent 平台有定时任务**（比如内置 scheduler）：在平台里加一条 "每天 08:00 触发 /money"。

**如果 agent 没有内置调度**：用系统 cron 唤醒 agent CLI。例如 Claude Code：

```cron
0 8 * * * cd ~/follow-the-money && /opt/homebrew/bin/claude --print "/money"
```

### 限制

- agent 的"定时"是平台特性，没就退化到手动
- 不能改跟踪的基金（v1 固定 8 个）

---

## 选哪条路径？

```
你日常用什么 AI agent？
│
└─ 有（Claude Code / Codex / OpenClaw 等）
    │
    └─ 试 🅰️：让 agent 加载 skill，你说 /money
        │
        ├─ agent 自带定时调度？ → 完成 ✅
        │
        └─ agent 没定时？ → 加 cron 调 agent CLI
```

---

## 数据从哪儿来

所有数据来自 **SEC EDGAR**（美国证监会公开电子数据库）。本项目有一个 GitHub Actions 每天抓两次（cron `0 12 * * *` + `0 0 * * *` UTC，约 08:00 美东、DST 下会有约 1 小时偏差），把 SEC 数据落盘到仓库的 `feed-13f.json` / `feed-13dg/`，任何人都能读。

**关键含义**：

- agent 模式：agent 读仓库的 feed 文件即可，**不打 SEC**
- 只有项目维护者跑 `aggregate.js` 才会打 SEC（GitHub Actions 自动跑）

所以无论用哪种方式，**你都不会触发 SEC rate limit**。

---

## 跟踪什么

- **8 个基金**：Berkshire Hathaway / Pershing Square / Scion / Baupost / Oaktree / ARK / Tiger Global / Coatue（v1 不可自定义）
- **全美 13D/G 申报**：任何 5%+ 持股变动，限美股市场

详细的事件类型和处理规则见 `references/alert-rules.md`。

---

## 进一步阅读

- `SKILL.md` — agent 视角的完整流程说明
- `references/onboarding.md` — 8 步首次配置
- `references/architecture.md` — 4 层数据流图
- `references/alert-rules.md` — 三级告警策略

---

## License

MIT
