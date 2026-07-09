# follow-the-money

> **追踪美国"聪明钱"的真实动作 — 直接来自 SEC 公开数据。**

每天把 8 位顶级基金经理的持仓变动 + 全美激进股东 13D/G 申报，做成可读的中文/英文摘要推送给你。

---

## 两种使用方式

这个项目有**两种完全不同的用法**，选一个就行：

| | 🅰️ 让 AI agent 跑 | 🅱️ 本地自己跑 |
|---|---|---|
| 你做什么 | 跟 agent 对话 | 自己跑命令 + 装 cron |
| 需要 Node.js | ❌ 不需要 | ✅ 需要 |
| 需要 cron 调度 | ❌ 不需要（agent 自带） | ✅ 需要 |
| 推送渠道 | 看 agent 能力 | stdout |
| 难度 | ⭐ 极简 | ⭐⭐⭐ 中等 |
| 适合 | 90% 的用户 | 想完全控制的开发者 |

**建议**：先试 🅰️，够用就别折腾 🅱️。

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

## 🅱️ 本地自己跑

### 你需要的

| 项目 | 说明 |
|---|---|
| 操作系统 | macOS / Linux / Windows |
| Node.js | 20 或更高 |
| cron 替代品 | crontab（macOS/Linux）/ Task Scheduler（Windows）/ launchd（macOS 推荐） |

### 步骤

#### 1. 克隆 + 装依赖

```bash
git clone https://github.com/KadenLiu168/follow-the-money
cd follow-the-money
npm install
```

#### 2. 配 SEC User-Agent

SEC 要求每个请求必须带身份标识（让 SEC 能在滥用时联系你）：

```bash
# macOS / Linux：临时
export SEC_EDGAR_USER_AGENT="follow-the-money your@email.com"

# 想永久生效
echo 'export SEC_EDGAR_USER_AGENT="follow-the-money your@email.com"' >> ~/.zshrc
source ~/.zshrc

# Windows PowerShell：用户级
[Environment]::SetEnvironmentVariable("SEC_EDGAR_USER_AGENT", "follow-the-money your@email.com", "User")
```

> 注：如果只读 GitHub Actions 已抓好的 `feed-13f.json` / `feed-13dg/`，本地脚本不打 SEC，可以不设。但设了没坏处。

#### 3. 准备配置

```bash
mkdir -p ~/.follow-the-money
```

`~/.follow-the-money/config.json`：

```json
{
  "schemaVersion": 1,
  "platform": "any",
  "language": "zh",
  "timezone": "Asia/Shanghai",
  "frequency": "daily",
  "deliveryTime": "08:00",
  "lastAlertTimestamp": "2026-06-25T08:00:00.000Z",
  "onboardingComplete": true
}
```

#### 4. 跑一次试试

```bash
# 生成 digest JSON
node scripts/prepare-digest.js --lookback 7 > digest.txt

# 输出到 stdout
node scripts/print.js --file digest.txt
```

或一行串联：

```bash
node scripts/prepare-digest.js --lookback 7 | node scripts/print.js --text "$(cat)"
```

成功的话你会看到一份 **digest JSON**（`prepare-digest.js` 输出 JSON，`print.js` 只是原样回显到 stdout，不做渲染）。🅱️ 本地模式只产出 JSON；中文/英文 markdown 摘要由 🅰️ agent 模式渲染（LLM 套用 `prompts/` 模板）。如果你想要本地渲染，可基于 `prompts/` 模板自行处理这份 JSON。

#### 5. 装调度

**macOS / Linux — crontab**：

```bash
crontab -e
```

加这两行（**`node` 必须用绝对路径**，cron 的 PATH 很短）：

```cron
# 每天 08:00 推 digest
0 8 * * * cd ~/follow-the-money && /opt/homebrew/bin/node scripts/prepare-digest.js --lookback 1 > /dev/null && /opt/homebrew/bin/node scripts/print.js --file <(node scripts/prepare-digest.js --lookback 1) >> ~/.follow-the-money/cron.log 2>&1

# 每 4 小时扫 13D 新申报
0 */4 * * * cd ~/follow-the-money && /opt/homebrew/bin/node scripts/check-alerts.js >> ~/.follow-the-money/cron.log 2>&1
```

查你的 node 路径：`which node`
- Apple Silicon：`/opt/homebrew/bin/node`
- Intel Mac：`/usr/local/bin/node`
- nvm 用户：要从 `~/.nvm/versions/node/v20.x.x/bin/node` 取

**Windows**：参考 `references/cron-setup.md` 里的 PowerShell + Task Scheduler 示例。

### 验证

装完调度后等第二天，看：

```bash
tail -50 ~/.follow-the-money/cron.log   # 看 cron 执行日志
```

或在 agent 会话/cron.log 里看到第一份 digest 就说明成功了。

---

## 选哪条路径？

```
你日常用什么 AI agent？
│
├─ 有（Claude Code / Codex / OpenClaw 等）
│   │
│   └─ 试 🅰️：让 agent 加载 skill，你说 /money
│       │
│       ├─ agent 自带定时调度？ → 完成 ✅
│       │
│       └─ agent 没定时？ → 加 cron 调 agent CLI
│
└─ 没有 / 不想用 agent
    │
    └─ 用 🅱️：本地装 Node.js + cron + 命令行
```

**典型升级路径**：先用 🅰️ agent 手动触发，体验 ok → 加 agent 平台定时 / 系统 cron → 仍想要离线持久化 / 多设备 → 升级到 🅱️ 本地。

---

## 数据从哪儿来

所有数据来自 **SEC EDGAR**（美国证监会公开电子数据库）。本项目有一个 GitHub Actions 每天抓两次（cron `0 12 * * *` + `0 0 * * *` UTC，约 08:00 美东、DST 下会有约 1 小时偏差），把 SEC 数据落盘到仓库的 `feed-13f.json` / `feed-13dg/`，任何人都能读。

**关键含义**：
- 🅰️ agent 模式：agent 读仓库的 feed 文件即可，**不打 SEC**
- 🅱️ 本地模式：本地脚本读同一个 feed 文件，**也不打 SEC**
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
- `references/cron-setup.md` — 各 OS 调度方式
- `references/architecture.md` — 4 层数据流图
- `references/alert-rules.md` — 三级告警策略

---

## License

MIT