# 实现逻辑差异分析：follow-the-money vs follow-builders

> 范围：架构设计、数据处理流程、核心业务逻辑层面的差异。
> 不含代码风格 / 命名规范。所有结论均有源码证据（`follow-builders/scripts/`、`follow-the-money/scripts/`、`lib/`、`SKILL.md`、`references/`）。

## 0. 结论速览（TL;DR）

| 差异点 | 一句话 | 严重度 |
| --- | --- | --- |
| **D1 Feed 目录契约不一致** | `fetch-feed.js` 默认写缓存目录，`prepare-digest.js` 默认读 `cwd`，默认配置下 fetch 步骤形同虚设 / 静默读到错误数据 | **高** |
| **D2 prepare 输出不自包含** | 不输出 `config` / `prompts` / `errors`，LLM 渲染上下文散落多处、降级不可见 | 中高 |
| **D3 空/缺 feed 被静默当正常** | 文件缺失返回空 feed 仍 exit 0，违反项目自身"严禁静默部分输出"原则 | **高** |
| **D4 state 文件被当作本地必需** | `fetch-feed.js` 把 aggregator 专用去重 state 当必需项，任一 404 即整体硬失败 | 中 |
| **D5 运行时步骤过多、缺单一编排** | 5 步 4 脚本，数据流靠 SKILL 文字约定，错位无报错 | 中 |
| **D6 单位归一在读取时重算** | 每次 digest 对全量 feed 防御性 ×1000，根因（写入方保证 schema）未贯彻 | 中 |

Follow Builders 的核心哲学是：**一个 `prepare-digest.js` 内部完成"取数 + 组装 + 加载 prompts + 输出单一自包含 JSON blob"，LLM 只做 remix**。follow-the-money 把"取数"（fetch）、"组装"（prepare）、"提示词加载"、"渲染"、"告警"拆成多个脚本与运行时约定，且多个步骤之间的数据流缺乏脚本级硬保证，从而在默认配置下就可能静默失真。

---

## 1) 关键差异点（逐项清单）

- **D1 — Feed 数据源定位契约分裂**
  follow-builders：`prepare-digest.js` 是单一脚本，内部用固定远程 URL 直接 fetch 三个内容 feed，**不依赖任何 env var 来定位数据源**。fetch 与 assemble 一体。
  follow-the-money：拆成 `fetch-feed.js`（写 feed 到目录，默认 `defaultTargetDir()` = OS 缓存目录）+ `prepare-digest.js`（读 feed，默认 `process.env.FOLLOW_THE_MONEY_FEED_DIR || process.cwd()` = repo 目录）。

- **D2 — prepare 输出非自包含**
  follow-builders：输出 JSON 含 `config` / `prompts`（已按 user>remote>local 三级优先解析好）/ `content` / `stats` / `errors`。
  follow-the-money：`prepare-digest.js` 只吐**数据 JSON**（thirteenF / thirteenDG / stats / diagnostics），**不含 config，也不含 prompts**，prompts 由运行时 LLM 自己读文件。

- **D3 — 空 feed 的处置**
  follow-builders：即便某 feed 拉取失败也输出 `status:ok` + `errors`，但 SKILL 明确要求"若 `stats` 全 0 → 告诉用户今天没更新"。
  follow-the-money：`readFeedJson` 在文件缺失/损坏时返回 `{ thirteenF: [] }`，`prepare-digest.js` 仍正常输出空数组、stats 全 0、exit 0。

- **D4 — 取数时耦合了不相关的 state 文件**
  follow-builders：prepare 只 fetch **内容 feed**，从不下载任何 state 文件（其 state 由 `generate-feed.js` 写进 repo 自己管理）。
  follow-the-money：`fetch-feed.js` 的 `STAT_IC_FILES` 包含两个**本地 skill 根本不消费**的文件（`state-13f.json`、`state-13dg.ndjson`），并把它们当作必需项整体硬失败。

- **D5 — 编排入口**
  follow-builders：核心两动作——`node prepare-digest.js` 然后 LLM remix 然后 `node deliver.js`。
  follow-the-money：一次 digest 需 agent 顺序执行 `fetch-feed → prepare-digest → (LLM 渲染) → print → check-alerts`，5 步 4 脚本，数据流靠 SKILL 文字约定。

- **D6 — 数值单位归一时机**
  follow-builders：单一生成器 `generate-feed.js` 统一保证 schema/单位，读取方无需再算。
  follow-the-money：在**读取时**才做 `normalizeValueUnits`（每次 digest 对全量 feed 跑一遍），依赖 `valueUnitAdjusted` 幂等保护；根因是历史上 feed 写入单位不一致，才有 `repair-feed-units.js` 补丁。

---

## 2) 各差异点对应的问题（含证据）

### D1 — 默认配置下 fetch 步骤形同虚设，且会静默失真

证据：
- `fetch-feed.js` L9-23 `defaultTargetDir()`：未设 env 时返回 `~/Library/Caches/follow-the-money/feed`（macOS）等缓存目录。
- `prepare-digest.js` L13-14：`const FEED_DIR = process.env.FOLLOW_THE_MONEY_FEED_DIR || REPO;`，`REPO = process.cwd()`。
- `check-alerts.js` L10-11：同样 `process.env.FOLLOW_THE_MONEY_FEED_DIR || REPO`。
- `SKILL.md` Step2/Step3：`FOLLOW_THE_MONEY_FEED_DIR=$FOLLOW_THE_MONEY_FEED_DIR node scripts/prepare-digest.js` —— 这里的 `$FOLLOW_THE_MONEY_FEED_DIR` 是 shell 变量，但 Step2 的 `node scripts/fetch-feed.js` **并没有 export 它**。

问题推演：当该 env 变量在 shell 中未设置（典型情况），
1. `fetch-feed.js` 走 `defaultTargetDir()` → 把数据写到**缓存目录**；
2. `prepare-digest.js` 看到 `process.env.FOLLOW_THE_MONEY_FEED_DIR` 为空 → 回落到 `cwd`（即 repo 目录）读取。

结果二选一，且都坏：
- **repo 里恰好有 CI 提交的旧 feed 文件**（`.gitignore` 排除本地、但 CI 用 `git add -f` 提交了）→ prepare 永远读 repo 那份，**fetch 步骤拉来的新鲜数据被完全绕过**，形同虚设；
- repo 里没有数据 → prepare 读到空 → 结合 D3 输出空 digest，**全程无报错**。

这直接违反 FTM 自己 SKILL 的误差哲学："Do not silently fall back to a partial digest." 一个 fetch 成功但 digest 用了陈旧/空数据的场景，正是被禁止的静默部分输出。

### D2 — 渲染上下文散落，降级不可见

证据：
- `prepare-digest.js` 的 `out`（L97-112）只有 `schemaVersion / generatedAt / lookbackDays / thirteenF / thirteenDG / stats / diagnostics`，**无 `config`、无 `prompts`、无 `errors`**。
- `SKILL.md` Step4："apply `prompts/digest-intro` + ... 到 JSON" —— 由 LLM 自己去读 5 个 prompt 文件。
- `references/prompt-customization.md`："加载顺序：用户 `~/.follow-the-money/prompts/` > 仓库 `prompts/`" —— 这个优先级**只在文档里用文字描述**，运行时是否真遵守取决于 agent 记忆。

问题：
- 渲染所需的全部依据（用户语言、delivery、5 个 prompt）散落在 `config.json` + 5 个文件，任一环节漏读/错读旧副本，digest 就不一致，且**没有机制能发现**。
- manifest mismatch 等只在 `prepare-digest.js` L66-69 打到 stderr（`console.warn`），**不进入 JSON 输出**，LLM 既不知道数据降级，也不会主动告知用户"今天数据拉取异常"。
- Follow Builders 把 prompt 解析（含用户覆盖）集中进脚本并嵌入输出 JSON，FTM 把这件确定性工作推给了运行时 agent。

### D3 — 空 digest 当正常结果（违反项目自身铁律）

证据：
- `lib/store/feed-json.js` L13-26：`readFeedJson` 在文件不存在/解析失败时返回 `DEFAULTS()`，即 `{ thirteenF: [] }`。
- `prepare-digest.js` L61：拿到空 feed 后继续 `filterByLookback` → 输出 `{ thirteenF: [], thirteenDG: [], stats:{...:0} }`，exit 0。

问题：当 feed 拉取失败或目录错位（见 D1），prepare 输出的是一个**看起来正常、实则空空如也**的 digest。这与 SKILL.md 明确写下的 "Partial output is worse than no output" 直接冲突，是项目自身原则最该优先修复的一类回归。

### D4 — 不相关的 state 文件耦合进关键取数路径

证据：
- `lib/fetch/fetch-feed.js` L4-9 `STAT_IC_FILES` 含 `state-13f.json`、`state-13dg.ndjson`。
- L94-104：任一静态文件失败 → 返回 `{ ok:false }`，SKILL 据此"fall through to local mode"。
- `docs/superpowers/plans/2026-06-24-follow-the-money.md` L27 明确写："state-13f.json and state-13dg.ndjson ... are **only** read/written by the GitHub Action. Local skill MUST NOT read or write these files."
- `references/data-formats.md` L134-142 也确认：本地 alert 去重来自 `feed-13dg/manifest.json` + `config.lastAlertTimestamp`，**不依赖 state 文件**。

问题：本地 digest 真正只需要 `feed-13f.json` + `feed-13dg/`。但 fetch 把两个 aggregator 专用去重 state 当必需，只要它们中任一个在 raw URL 暂时不可达（或将来被改为不发布），**整个新鲜度拉取就硬失败**，连带真正需要的 feed 也不更新。把"不相关依赖"塞进关键路径，鲁棒性反而更差。

### D5 — 步骤过多、数据流靠记忆约定

证据：SKILL.md Daily path 需依次 `fetch-feed → prepare-digest → print → check-alerts`，且步骤间用 env var（`FOLLOW_THE_MONEY_FEED_DIR`）、stdin/stdout、临时文件衔接，除了 D1 的目录约定外没有任何脚本级校验。

问题：步骤越多、靠 agent 记忆的契约越多，越容易出现"某步没跑对但没报错"（D1/D3 就是实例）。Follow Builders 用"最少脚本 + 单一 JSON 契约"把这类风险压到最低。

### D6 — 单位归一时机错位（核心业务逻辑）

证据：
- `prepare-digest.js` L77：`normalizedFeed = f13.thirteenF.map((f) => normalizeValueUnits(f, ...))` —— 对**全量** feed 每次 digest 都重算。
- `lib/enrich/normalize-value-units.js`：默认 `'thousands'` 会把 `valueUsd × 1000`，靠 `valueUnitAdjusted === true` 做幂等。
- 历史债：`scripts/repair-feed-units.js` 注释明确说明"feed-13f.json 有 374 条快照单位混用（dollars vs thousands）"，才需要修复补丁。

问题：根因是**写入方未保证单位一致**（CI 的 `aggregate.js` 与本地 `node scripts/aggregate.js` 都写 feed，单位可能在本地被改坏），于是读取方被迫每次全量防御性重算。这既带来每次 digest 的 O(n) 冗余计算，也留下"数据债务"复发风险——只要某次写入漏标 `valueUnit`，下次 digest 又会错乘 1000。Follow Builders 因单一生成器统一 schema，根本没有这一层。

---

## 3) 基于 Follow Builders 的具体修正方案

> 每项给出：改动文件、改法、验证标准。均不破坏现有单测契约，按用户拍板后落地。

### D1 修正：抽一个共享 `resolveFeedDir()`，让 fetch 与 prepare 永远同目录

- **新增** `lib/config/feed-dir.js`：

```js
import { homedir } from 'node:os';
import { join } from 'node:path';

// 与 FB 的 prepare-digest 同理：数据源位置只在此处解析一次，
// fetch 与 prepare 全部调用，消除"写到缓存 / 读到 cwd"的分裂。
export function resolveFeedDir() {
  if (process.env.FOLLOW_THE_MONEY_FEED_DIR) return process.env.FOLLOW_THE_MONEY_FEED_DIR;
  const home = homedir();
  if (process.platform === 'darwin') return join(home, 'Library', 'Caches', 'follow-the-money', 'feed');
  if (process.platform === 'win32') {
    const local = process.env.LOCALAPPDATA || join(home, 'AppData', 'Local');
    return join(local, 'follow-the-money', 'feed');
  }
  const xdg = process.env.XDG_CACHE_HOME;
  return xdg ? join(xdg, 'follow-the-money', 'feed') : join(home, '.cache', 'follow-the-money', 'feed');
}
```

- **改** `fetch-feed.js`：用 `resolveFeedDir()` 替换内联 `defaultTargetDir()`（逻辑一致，仅统一出口）。
- **改** `prepare-digest.js` L13-14、`check-alerts.js` L10-11：删除 `|| REPO` 回落，改为 `const FEED_DIR = resolveFeedDir();`。
- **SKILL.md Step2/3**：可简化为单句"运行 `node scripts/run-digest.js`"（见 D5），env var 仅在用户想自定义缓存位置时设置。

- **验证**：未设 env 时，`fetch-feed.js` 写出的 `feed-13f.json` 路径 ≡ `prepare-digest.js` 读到的路径（用同一 `resolveFeedDir()` 断言相等）；从空缓存目录跑完整流程，digest 含真实数据而非空。

### D2 修正：prepare 输出自包含 blob（对齐 FB 的 JSON 契约）

- **改** `prepare-digest.js`：在输出前读取 `config.json` 与 5 个 prompt 文件，并按 **用户 `~/.follow-the-money/prompts/` > 仓库 `prompts/`** 优先级解析（与 FB 的 user>remote>local 同构），一并写入 JSON：

```js
import { readFileSync, existsSync } from 'node:fs';
import { homedir } from 'node:os';

function loadPrompts(userDir, repoDir, files) {
  const out = {};
  for (const f of files) {
    const key = f.replace('.md', '').replace(/-/g, '_');
    const userPath = join(userDir, f);
    const repoPath = join(repoDir, f);
    if (existsSync(userPath)) out[key] = readFileSync(userPath, 'utf8');
    else if (existsSync(repoPath)) out[key] = readFileSync(repoPath, 'utf8');
  }
  return out;
}
```

- 把 `config`（读 `~/.follow-the-money/config.json`）、`prompts`（上述结果）加入 `out`；新增 `errors` / `warnings` 数组，收集 manifest mismatch、读取失败等（目前只 stderr）。
- **SKILL.md Step4** 相应改为"读取 prepare 输出的 `prompts` 字段来渲染"，不再让 LLM 自己去找 prompt 文件。

- **验证**：相同输入下，prepare 输出 JSON 含 `config.language`、`prompts.digest_intro` 等非空字段；人为制造 manifest mismatch，确认 `errors` 数组非空且内容正确。

### D3 修正：空/缺 feed 硬失败，不输出空 digest

- **改** `prepare-digest.js` 读取阶段：在 `readFeedJson` / `readManifest` 之前先检测文件存在性；若 `feed-13f.json` 与 `feed-13dg/` 均不存在（或读取后均为空），收集 error 并**非零退出**（符合项目"硬失败"策略，与 FB 的"用 stats 判无内容"互补）。
- **SKILL.md** 增加显式步骤："若 prepare 退出非 0 或输出 `empty:true`，向用户报错并停止，不要输出空 digest"。
- 注：FB 允许降级输出，但 FTM 选了更严的"无静默"策略，这里以 FTM 自身原则为准，仅在"数据根本没拿到"时硬失败，而非 FB 式的"拿到部分就发部分"。

- **验证**：删掉缓存目录后跑 prepare，exit code ≠ 0 且 stderr/JSON 明确指向"feed 缺失"；repo 有真实数据时正常出 digest。

### D4 修正：state 文件降级为 best-effort

- **改** `fetch-feed.js`：把 `STAT_IC_FILES` 拆成 `REQUIRED_FILES`（`feed-13f.json`、`feed-13dg/manifest.json` + 派生 ndjson）与 `OPTIONAL_FILES`（`state-13f.json`、`state-13dg.ndjson`）。Phase1 只对 REQUIRED 做硬失败；OPTIONAL 失败仅 `console.warn`，不影响 `ok`。
- 关键路径只依赖本地真正消费的数据，与 FB"只拉内容 feed"的简洁做法对齐。

- **验证**：用 nock 让 `state-13f.json` 返回 404，断言 `fetchFeed()` 仍 `ok:true` 且 `filesWritten` 含 feed 文件。

### D5 修正：引入单一编排脚本 `scripts/run-digest.js`

- **新增** `scripts/run-digest.js`：内部按顺序调用 `fetchFeed(resolveFeedDir())` → `prepare-digest.js` 逻辑 → 输出 JSON；可选地继续 `check-alerts.js`。把"先 fetch 再 prepare"收敛进一个入口，消除 SKILL 里靠文字约定的 env 传递。
- 若不做整编，最低限度：让 `prepare-digest.js` 在 `resolveFeedDir()` 指向的目录无数据文件时，**自动先触发一次 fetch**（或显式报错并给出可执行的修复命令），而非静默回落。

- **验证**：用户只跑 `node scripts/run-digest.js` 即可得到与手动 5 步等价的 digest + alert。

### D6 修正：写入方负责归一，读取方只兜底

- **明确契约**：`aggregate.js`（pipeline-a/b）落盘前保证每条快照 `valueUnit:'thousands'` 且数值已是统一单位；`merge13FFiling`（`lib/store/feed-json.js` L40）已 stamp，需确认 pipeline 写入的即是归一后快照。
- **改** `prepare-digest.js` L77：将全量 `normalizeValueUnits` 收敛为——仅当条目**缺 `valueUnit` 标记**时才兜底乘（已有幂等保护），已标记 `valueUnit:'thousands'` 的跳过，避免每次 O(n) 重算。
- 这是把 FB"生成方统一 schema"的哲学落到 FTM 写入方，从根上减少 `repair-feed-units.js` 这类补丁的复发。

- **验证**：用一份已 stamp `valueUnit:'thousands'` 的 feed 跑 prepare，确认 `normalizeValueUnits` 命中幂等短路（不重复 ×1000），且 periodDiff 的 `deltaPct` 与修复前一致。

---

## 附：有意的差异（非问题，保留）

- **Delivery 仅 stdout**：FB 的 `deliver.js` 支持 telegram/email/stdout（含 4096 分片 + Markdown 解析失败降级）。FTM 的 `print.js` 只 stdout，但这是 SKILL 明确选定的"无秘密、纯本地"业务范围，不是缺陷。将来若要扩展 IM 推送，应直接复用 FB `deliver.js` 的分片/降级模式。
- **确定性时间接缝 `--now` / `FTM_NOW`**：FTM 的 backfill 能力比 FB 更严谨，是长处，无需改。
- **本地告警去重用 `config.lastAlertTimestamp`**：符合 FTM"无独立 state 文件、删 `~/.follow-the-money` 不丢 seen 信息"的设计，是正确设计，与 FB 不同但合理。
