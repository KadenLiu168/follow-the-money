## Context

FTM 是一个 agent skill：用户加载 `SKILL.md`，agent 读 feed、渲染 `prompts/`、把摘要交付给人。历史上它同时维护了一条 🅱️ 本地模式（用户自己跑 Node + cron，靠 `scripts/print.js` 把 JSON 回显到 stdout，再被 `>> cron.log` 接住）。

`stdout-only-delivery` change（2026-07-08）曾把旧的 `deliver.js`（Telegram/Email，因路径 bug 从未真正工作）重命名为 `print.js` 并收窄为纯 stdout 打印机，并随之立了 `delivery` + `cli-path-safety` 两个 capability。后续 `low-priority-cleanup` 又给 print.js 加了 `--file` 路径穿越防护，催生了 `cli-path-safety`。

但这两个 capability 在 agent-only 视角下都是空壳：
- `delivery` 的中心契约"经 print.js 输出到 stdout"——在 agent 模式里 print.js 只是 `console.log` 透传；且 `check-alerts.js` 早已绕过它直接 `process.stdout.write`。
- `cli-path-safety` 的唯一要求即 print.js `--file` 防护——而 `--file` 只服务于 🅱️ 本地读文件，🅱️ 删掉后 subject 消失。

本次变更把项目明确收敛为 agent-only 最小 skill，删除 print.js 及其两个空壳 capability，并清理所有 🅱️ 文档残留。

## Goals / Non-Goals

**Goals:**
- 删除 `scripts/print.js` 与对应测试，消除 agent 模式下无逻辑的透传壳。
- 退役 `delivery` 与 `cli-path-safety` 两个空壳 capability（经 REMOVED delta 清空）。
- 清理 `documentation-accuracy` 中指向已删 🅱️/print.js 的陈旧 requirement。
- 移除 README / onboarding / cron-setup 的全部 🅱️ 内容，只留 🅰️ agent 模式。

**Non-Goals:**
- 不新增任何"本地投递"或"渲染"能力（那是 agent 运行时的事）。
- 不改动聚合/抓取/准备/告警脚本（`aggregate.js` / `fetch-feed.js` / `prepare-digest.js` / `check-alerts.js`）。
- 不重写 `SKILL.md` 的整体 digest/alert 流程；仅删 print.js 步骤、对应错误处理引用，以及 🅱️ 遗留的 Local deployment / cron 段（不新增、不改写其它流程）。
- 不动数据文件与 CI 聚合 pipeline。

## Decisions

**D1: 删除而非内联 print 逻辑**
原 `stdout-only-delivery` 的 design.md 曾考虑"把 print 内联进 prepare-digest 后删脚本"并 rejected，理由是"print.js 是稳定 stdout 接缝"。但在 agent-only 下该理由不再成立：没有下游 cron/外部脚本依赖它（cron 是 🅱️，一并删除），agent 即消费者。故本次直接删除，不再保留接缝壳。

**D2: 整体退役 capability，而非改写成"agent 负责投递"**
可选项：(a) 删 `delivery` capability；(b) 改写成"skill 产 JSON、agent 渲染投递"的新契约。选 (a)——用户明确要求"最小 skill、不留空壳"。agent 负责投递的事实已写在 `SKILL.md` 流程里，无需再立一个 spec 重复描述。

**D3: cli-path-safety 随 print.js 一并删**
其唯一要求即 print.js `--file` 防护。agent-only 下无任何脚本从 CLI 读自由文件路径（feed 路径由 `FOLLOW_THE_MONEY_FEED_DIR` 固定解析），防护失去 subject，capability 失存在意义，删除。

**D4: documentation-accuracy 只删一条 requirement，不删整个 capability**
该 capability 其余 requirement（即 "Documentation accurately reflects implementation"，内含 thirteenF 基数、CI cron UTC、alert 分类法等 scenario）仍有效，仅 🅱️/print.js 那条随 🅱️ 删除失效。精准删除单条，保留其余。

## Risks / Trade-offs

- [Risk] 外部/历史自动化仍假设 `scripts/print.js` 存在 → **Mitigation**: grep 全仓确认当前仅 `SKILL.md:51`、README 🅱️、cron-setup、onboarding 引用；这些均在本次清理范围内，无遗留调用方。
- [Risk] 删除 `delivery`/`cli-path-safety` 后，archive 时若 OpenSpec 不自动删除空 capability 目录，可能残留仅含 Purpose 空头的目录 → **Mitigation**: 实现时在 tasks 中显式检查并在 archive **后**手动删除空目录（先 archive 把 delta 并入主 spec，再删；Purpose 仍为 TBD 的旧空头，本就应收尾）。
- [Risk] README 删 🅱️ 段后，对比表/路径选择文案出现悬空引用 → **Mitigation**: tasks 要求通读 README 一并清理（对比表 🅱️ 列、"选哪条路径" 🅱️ 分支、cron 示例），保持文档自洽。
- [Trade-off] 失去"完全离线 / 多设备 / 开发者自控"的 🅱️ 用户群——这是产品定位决策（agent-only），已与用户确认。

## Migration Plan

实现步骤（见 tasks.md）：
1. 删 `scripts/print.js` + `tests/scripts/print.test.js`。
2. 改 `SKILL.md`：去 print.js 步骤与错误处理引用。
3. 清 README / onboarding 的 🅱️ 内容；删 `references/cron-setup.md`。
4. 本 change 的 specs/ delta（delivery、cli-path-safety、documentation-accuracy）在 `/opsx:archive` 时并入主 spec 并清空对应 requirement。
5. archive **后**手动删除因清空而残留的空 capability 目录（`openspec/specs/delivery/`、`openspec/specs/cli-path-safety/`）——必须先 archive 把本 change 的 delta 并入主 spec、使这些目录只剩 TBD Purpose 空头，随后再删除；顺序不可颠倒（archive 前删会导致 delta 无处并入）。

回滚：git revert 本 change 的 commit 即可恢复 print.js 与文档；capability 恢复需从 archive 历史取回。

## Open Questions

- _无_（范围与决策已明确）。
