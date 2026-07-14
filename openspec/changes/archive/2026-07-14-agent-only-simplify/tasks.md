## 1. 删除代码与测试

- [x] 1.1 删除 `scripts/print.js`
- [x] 1.2 删除 `tests/scripts/print.test.js`

## 2. 清理 SKILL.md 中的 print.js 与 🅱️ 残留

- [x] 2.1 将 Step 5 由「Print」改为「Output」：删除 `node scripts/print.js --text "<digest>"` 代码块（含标题「5. **Print**:」与代码围栏，约第 49–52 行），替换为说明『agent 直接将渲染后的 Markdown 摘要输出到会话 stdout，无需任何脚本』。保留 Step 编号（后续 Step 6 Check alerts 不变）。
- [x] 2.2 清理第 101 行「do not run `print.js` or `check-alerts.js`」→ 改为「do not run `check-alerts.js`」
- [x] 2.3 清理第 104 行「`print.js` exits non-zero → ...」整条删除（print.js 已不存在）
- [x] 2.4 删除「Feed freshness model」下的「**Local deployment:** ... optionally schedule via cron for freshness」整段（约第 75–76 行）——这是 🅱️ 自托管 `aggregate.js` + cron 的遗留说明；agent-only 下用户不本地跑 aggregate.js，亦无 cron 调度。

## 3. 清理 🅱️ 文档

- [x] 3.1 `README.md`：
  - 删除 🅱️ 本地模式整段（「## 🅱️ 本地自己跑」及内部全部内容，约第 90–201 行），含「选哪条路径」中的 🅱️ 分支（约第 220 行）。
  - 将「## 两种使用方式」对比表坍塌为 🅰️-only 叙述：删除 🅱️ 列后已是单列空表，应改写为一段「推荐用 🅰️ agent 模式」的说明，而非保留退化表格。
  - 删除所有 🅱️ 本地模式 cron 示例（使用 `print.js` / 写 `cron.log` 的部分，约第 169–201 行）。
  - **保留** 🅰️ 模式「用系统 cron 唤醒 agent CLI」的调度说明（约第 73–87 行「#### 3. 配定时」），其不属于 🅱️ 本地投递，是 agent 调度建议。
  - 改写仍残留的 🅱️ 措辞：第 22 行「先试 🅱️，够用就别折腾 🅱️」→ 去掉 🅱️ 对比，只说推荐 🅰️ agent 模式；第 233–234 行「🅱️ 本地模式」对比 → 删除 🅱️ 分支只留 agent 模式表述；第 254 行对 `references/cron-setup.md` 的引用（该文件将被删除）→ 删除该行。
  - 通读确保无悬空 🅱️ / `print.js` 引用。
- [x] 3.2 删除 `references/cron-setup.md`（🅱️ 专属）。
- [x] 3.3 `references/onboarding.md`：
  - **保留** Step 4「Delivery Method」（stdout / agent session 渲染，属 🅰️ 模式，不要误删）。
  - 删除 Step 7「Settings Reminder + Cron Setup」中的 "Cron Setup" 字样与对 `references/cron-setup.md` 的指针（约第 100 行），标题改为「Settings Reminder」。
  - 删除「After cron is set, run the welcome digest」整块（约第 102–106 行，含 `node scripts/print.js --file`），改为「run the welcome digest immediately: `node scripts/prepare-digest.js` → apply prompts → output markdown to session」。
  - 通读确认无其它 `print.js` / cron 引用。
- [x] 3.4 `references/architecture.md`：
  - 删除 Layer 3 职责列表中 `scripts/print.js` 条目（"`scripts/print.js` — emit digest/alert text to stdout"）。
  - 将 Layer 3 表格中的「User's machine (on cron)」改为 agent-only 表述，如「User's machine (agent runtime, on demand)」——"on cron" 是 🅱️ 本地调度的遗留措辞；Data Flow 图「Local Skill on user's machine → Delivery: stdout」可保留（agent 即在用户机器运行）。
  - 改写 L55「Local deployments are unaffected: `node scripts/aggregate.js` still writes to `cwd` ...」：去除 🅱️「Local deployments」自托管措辞，改为中性表述如「Running `aggregate.js` locally still works: it writes to `cwd`, which the scripts read when `FOLLOW_THE_MONEY_FEED_DIR` is unset.」（保留 cwd 兜底事实，仅去掉 🅱️ 框架）。
  - **保留**（非 🅱️ 残留，勿删）：Layer 3「Local skill」/「Stateless local skill」标题、Data Flow 图「Local Skill on user's machine」、L51「fallback to cwd for local mode」、L52「for local development」、L66「cannot be done locally on every user's machine」——这些指「skill 在用户机器本地运行 / cwd 兜底 / 本地开发」，agent-only 下依然成立。
  - 通读确认无其它 `print.js` / `Local deployments` / `Local deployment` 引用。
- [x] 3.5 `references/alert-rules.md`：将 🅱️ 时代术语与 print.js 时代术语一并改写为 agent-only 表述（print.js 已删，告警由 agent 调用 `check-alerts.js` 直出 stdout）：
  - L27-28「Single cron run produces ...」→「单次 agent 调用 produces ...」（或「each agent invocation」）。
  - L58「If print crashes between output and timestamp update ...」→「If the stdout write crashes between output and timestamp update ...」（不再提 print 组件）。
  - L68「Alerts run on **every cron tick** of the local skill ...」→「Alerts run on **every agent invocation** of `check-alerts.js` ...」；「Typical local cron: 4-6× per day」→「Typical agent schedule: 4-6× per day」。
  - L70-72 对比表「Local cron (user machine)」列 →「Agent schedule (user's machine)」（中心聚合 cron 仍称 Center cron）。
  - L74「If the center hasn't updated since the last local cron run」→「... since the last agent invocation」。
  - L80「Print errors (file read failure)」→「Output/write errors (file read failure)」（指 `check-alerts.js` 的 stdout 写出，非 print.js）。
  - L81「Crash between print and timestamp write」→「Crash between stdout write and timestamp update」。
  - 通读确认无 `local skill` / `local cron` / `print` / `cron run` 残留，且不再暗示存在独立于 agent 的本地 cron 投递或 print 组件。

## 4. 套用 capability delta（archive 时并入主 spec）

- [x] 4.1 确认 `openspec/changes/agent-only-simplify/specs/delivery/spec.md` 的 REMOVED 覆盖全部 5 条 requirement
- [x] 4.2 确认 `openspec/changes/agent-only-simplify/specs/cli-path-safety/spec.md` 的 REMOVED 覆盖唯一 requirement
- [x] 4.3 确认 `openspec/changes/agent-only-simplify/specs/documentation-accuracy/spec.md` 的 REMOVED 仅删 🅱️ 那条 requirement，其余保留

## 5. 校验与收尾

- [x] 5.1 跑 `openspec validate agent-only-simplify` 通过（spec delta 格式合规）
- [x] 5.2 跑测试套件（`npm test` / vitest）确认 print.test.js 删除后无悬空引用、其余测试通过
- [x] 5.3 `/opsx:archive` **后**，手动删除因 requirement 清空而残留的空 capability 目录 `openspec/specs/delivery/` 与 `openspec/specs/cli-path-safety/`（仅含 TBD Purpose 空头）
- [x] 5.4 全仓 grep 以下模式确认无遗留引用：`print` / `print.js`、`🅱️` / `🅱`、`local cron` / `local skill` / `local deployment` / `local mode` / `self-host` / `self-run` / `cron run` / `本地` / `本地部署` / `本地自`（仅历史 archive/ 与 docs/ 分析文可保留，或一并标注过时）。
  - **保留（非 🅱️ 残留，勿删）**：architecture.md「Local Skill on user's machine」(Data Flow)、Layer 3「Local skill」/「Stateless local skill」、L51「fallback to cwd for local mode」/ L52「for local development」/ L66「locally on every user's machine」；data-formats.md「local skill reads」/「local skill has no independent alert state file」；SKILL.md L70-71「falls back to local files in cwd ... run aggregate.js locally」（均指 skill 在用户机器本地运行或 cwd 兜底，agent-only 下成立）。
  - **须已清理（🅱️ / print.js 残留）**：architecture.md L55「Local deployments」(3.4)；alert-rules.md 全部 `print`/`cron run`/`local cron` 表述(3.5)；SKILL.md L75-76「Local deployment ... cron」(2.4)；README / onboarding 的 🅱️ 段与 `print.js` 命令(3.1/3.3)；cron-setup.md 已删(3.2)。
