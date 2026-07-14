## Why

FTM 本就是作为 agent skill 设计，不需要双模式（🅰️ agent / 🅱️ 本地）与本地投递能力。`scripts/print.js` 在 agent 模式下只是 `console.log` 的纯透传壳（其唯一实质逻辑——`--file` 路径穿越防护——只服务于已废弃的 🅱️ 本地读文件），`check-alerts.js` 早已绕过它直出 stdout。保留 print.js 及其配套的两个 capability（`delivery`、`cli-path-safety`）只是空壳契约，比删掉还脏。

## What Changes

- **BREAKING**: 删除 `scripts/print.js`（纯 stdout 透传壳，agent 模式下无不可替代逻辑）。
- **BREAKING**: 删除 `tests/scripts/print.test.js`（唯一被测对象即 print.js 的壳 + `--file` 防护）。
- **BREAKING**: 删除 `delivery` capability（整个 spec，中心契约"经 print.js 输出到 stdout"随之作废）。
- **BREAKING**: 删除 `cli-path-safety` capability（整个 spec，其唯一要求即 print.js `--file` 防护，subject 已消失）。
- **BREAKING**: 删除 `documentation-accuracy` 中约束 "README 🅱️ 须说明 prepare-digest 出 JSON、print.js 仅回显" 的 requirement（🅱️ 段与 print.js 均被删除，该条变为指向已删内容的陈旧契约）。
- 修改 `SKILL.md`：将 Step 5「Print」整段（标题 + `node scripts/print.js --text` 代码块，约第 49–52 行）改为「Output」，说明 agent 直接把渲染后的 Markdown 输出到会话 stdout（无需脚本）；清理第 101 行 "do not run `print.js`" 引用、删除第 104 行 `print.js` 错误整条；删除「Feed freshness model」下的「Local deployment ... schedule via cron」遗留段（约第 75–76 行，🅱️ 自托管 aggregate 残留）。
- 清理 `README.md`：移除 🅱️ 本地模式整段（含对比表 🅱️ 列、"选哪条路径" 中 🅱️ 分支、🅱️ 本地 cron 示例）；将「两种使用方式」对比表坍塌为 🅰️-only 叙述（勿保留退化单列空表）；**保留** 🅰️ 模式「用系统 cron 唤醒 agent CLI」调度说明；改写残留 🅱️ 措辞（建议语、🅱️ 本地模式对比、对 `cron-setup.md` 的引用）。
- 删除 `references/cron-setup.md`（🅱️ 专属）。
- 清理 `references/onboarding.md`：**保留** Step 4「Delivery Method」（🅰️ 模式，stdout/agent session 渲染，勿误删）；删除 Step 7 的 "Cron Setup" 标题与 `cron-setup.md` 指针、以及 "After cron is set" 中 `node scripts/print.js --file` 的 welcome-digest 块（均为 🅱️ 残留）。
- 清理 `references/architecture.md`：删除 Layer 3 职责列表中 `scripts/print.js` 条目（该脚本被删除，留此条目即成悬空引用）；将 Layer 3「User's machine (on cron)」改为 agent-only 表述（"on cron" 为 🅱️ 本地调度遗留）；改写 L55「Local deployments are unaffected ...」去除 🅱️ 自托管措辞（改为「Running `aggregate.js` locally still works ...」中性表述，保留 cwd 兜底事实）。注意：Layer 3「Local skill」/「Stateless local skill」、Data Flow 图「Local Skill on user's machine」、L51「fallback to cwd for local mode」/ L52「for local development」/ L66「locally on every user's machine」指 skill 在用户机器本地运行或 cwd 兜底，agent-only 下依然成立，须保留。
- 清理 `references/alert-rules.md`：将 🅱️ 时代术语与 print.js 时代术语一并改写为 agent-only 表述——「local skill」/「Local cron (user machine)」→ agent 调度 / agent runtime；「every cron tick of the local skill」→「每次 agent 调用 `check-alerts.js` 时」；「Single cron run」→「单次 agent 调用」；「If print crashes ...」/「Print errors」/「Crash between print and timestamp write」→ 改为「output / stdout write」表述（print.js 已删，`check-alerts.js` 直出 stdout）。避免暗示存在独立于 agent 的本地 cron 投递或仍存在 print 组件。

## Capabilities

### New Capabilities

_None — 本变更只做删除与清理，不引入新契约。agent-only 下"skill 产 JSON 到 stdout、渲染+投递由 agent 负责"的契约已在 `SKILL.md` 文档化，无需新增 spec。_

### Modified Capabilities

- `delivery`: 整个 capability 被移除（所有 requirement 转入 REMOVED）。原因：print.js 删除后，本地 skill 不再拥有投递层；投递是 agent 运行时的事。
- `cli-path-safety`: 整个 capability 被移除（唯一 requirement 转入 REMOVED）。原因：其唯一要求即 print.js `--file` 路径防护，script 删除后 subject 消失。
- `documentation-accuracy`: 移除 "README 🅱️ local mode states JSON output, not markdown rendering" 这一 requirement（随 🅱️ 段删除而失效）。

## Impact

- `scripts/print.js` — 删除
- `tests/scripts/print.test.js` — 删除
- `openspec/specs/delivery/spec.md` — 经本 change 的 delta REMOVED 后清空/移除
- `openspec/specs/cli-path-safety/spec.md` — 经本 change 的 delta REMOVED 后清空/移除
- `openspec/specs/documentation-accuracy/spec.md` — 移除一条 🅱️ 相关 requirement
- `SKILL.md` — 编辑（去 print.js 步骤 + 错误处理引用 + Local deployment 段）
- `README.md` — 编辑（删 🅱️ 段）
- `references/cron-setup.md` — 删除
- `references/onboarding.md` — 编辑（删 🅱️ 步骤）
- `references/architecture.md` — 编辑（删 Layer 3 的 `scripts/print.js` 条目；Layer 3「on cron」改为 agent runtime 表述；L55「Local deployments」🅱️ 自托管措辞改写为中性 cwd 兜底表述）
- `references/alert-rules.md` — 编辑（🅱️ 时代术语 + print.js 时代术语一并改写：local cron / cron run / print crashes / Print errors 等）
- 不涉及数据文件（`state-*.json` / `feed-*` / `*.ndjson`）与聚合/抓取脚本（`aggregate.js` / `fetch-feed.js` / `prepare-digest.js` / `check-alerts.js` 保留）。
