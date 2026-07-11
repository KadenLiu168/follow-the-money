## Context

`scripts/prepare-digest.js` 产出 digest 的 JSON 到 stdout。当 `feed-13f.json` 缺失（当前用字面量 `{ thirteenF: [] }`）或 `feed-13dg/` 缺失（`read13DFilings` 静默返回空），又或 `feed-13f.json` 损坏（`readFeedJson` 的 `catch` 静默回 `DEFAULTS()`）时，脚本仍 `exit 0` 输出一个空 digest。这与 SKILL.md 的铁律 "Partial output is worse than no output" 冲突——用户/agent 可能基于这份"看似完整、实则空白"的视图采取行动。

根因：`lib/store/feed-json.js` 的 `readFeedJson` 同时服务两种相反语义：
- **bootstrap（写入/聚合路径）**：`pipeline-a.js:10`、`upsert13FFiling`（`feed-json.js:75`）需要"文件不存在→空 `DEFAULTS()`"作为聚合起点，正确。
- **read（digest 路径）**：`prepare-digest.js:61` 用它读源，但缺失/损坏同样被静默成空，错误。

让一个函数同时承载这两种语义，正是 D3 的源头。

## Goals / Non-Goals

**Goals:**
- 消除 `readFeedJson` 的语义重载，使"静默空回退"只在 bootstrap 路径出现。
- `prepare-digest.js` 在任一源缺失/损坏时**非零退出且不向 stdout 写任何 digest**（判定粒度 P3）。
- 现有聚合/写入行为完全不变；现有"源文件存在但内容为空"的合法场景（非 filing 日）不受影响。

**Non-Goals:**
- 不联动 D2（自包含 JSON blob / `errors` 数组优雅降级）——本次只修 D3，硬失败策略优先。
- 不改变 `read13DFilings` 对**单行损坏**的处理（feed-storage 已要求计数+上报，非硬失败）。
- 不改变 SKILL 的 fetch→fall-through-to-local 模型。

## Decisions

### D1 — 拆分 `readFeedJson` 为 strict 与 orInit（方案 B）

- 新增 `readFeedJsonStrict(path)`：**文件不存在 → 抛 `Error('feed-13f.json missing at <path>')`**；**`JSON.parse` 失败 → 抛 `Error('feed-13f.json corrupt at <path>: <msg>')`**；解析成功则返回与现有一致的规范化对象（`...DEFAULTS(), ...parsed, thirteenF, stats`）。
- 原 `readFeedJson` 重命名为 `readFeedJsonOrInit(path)`：保留 `DEFAULTS()` 回退，仅用于 bootstrap。

**为什么不是方案 A（只在 prepare 加 pre-flight 存在性检查）**：A 抓不到 `feed-13f.json` *损坏*（仍被 `readFeedJson` 静默吞）。D3 的损坏分支必须解决。
**为什么不是方案 C（返回 `{ feed, ok, error }` 判别对象）**：要改所有调用点，对本题属过度设计。

### D2 — `prepare-digest.js` pre-flight + 硬失败（粒度 P3）

读取顺序前置一段检查：

```
if (!existsSync(FEED_13F))   { console.error('[prepare-digest] feed-13f.json missing — run fetch-feed.js or aggregate.js'); process.exit(1); }
if (!existsSync(FEED_13DG_DIR)) { console.error('[prepare-digest] feed-13dg/ missing — run fetch-feed.js or aggregate.js'); process.exit(1); }
let f13;
try { f13 = readFeedJsonStrict(FEED_13F); }
catch (e) { console.error(`[prepare-digest] ${e.message}`); process.exit(1); }
```

- 移除原 `const f13 = existsSync(FEED_13F) ? readFeedJson(FEED_13F) : { thirteenF: [] };` 与 `manifest` 的缺省 else 分支（目录已保证存在，`readManifest` 按现状处理目录内 manifest）。
- **不写 stdout**：检查/读取失败在 `process.exit(1)` 前不发任何 digest，与现有 `--now` 非法（已 `exit 1` 且不写 stdout）行为一致，使 SKILL 见到"空 stdout + 非零退出"后上报 stderr。
- 判定粒度 P3：13F 缺失、13DG 缺失、13F 损坏任一成立即失败。分析文档 D3 原案的"两者都缺失才失败"被明确否决——那档与铁律自相矛盾（只给 13F 的 digest 仍是 partial）。

### D3 — bootstrap 调用方不改行为

`pipeline-a.js:10` 与 `feed-json.js:75`（`upsert13FFiling`）改调 `readFeedJsonOrInit`，行为与原 `readFeedJson` 完全一致（缺失→`DEFAULTS()`）。聚合起点语义不变。

### D4 — 13DG 单行损坏不升级为硬失败

`feed-13dg/` 目录存在但某年文件含损坏行时，`read13DFilings` 仍按 feed-storage 规范计数 `skipped` 并 `console.warn`，不退出。仅**目录缺失**算 P3 失败。"文件级缺失/损坏"与"行级损坏"分别对待。

## Risks / Trade-offs

- **[Risk] 现有测试 "empty envDir" 回归（`prepare-digest.test.js:176`）原期望空 digest exit 0** → 该测试改为断言非零退出 + stderr 含缺失信息，同时保留"env var 不被静默忽略"的意图（从"空 digest"转为"硬失败"）。见 tasks。
- **[Risk] 全新 clone 尚未 `aggregate`/拉取时，prepare 直接失败** → 这是铁律的预期结果（比空 digest 好）。错误文案明确指引 `fetch-feed.js`/`aggregate.js`，SKILL 错误处理段已约定上报 stderr 并停止。
- **[Risk] P3 比分析文档原案更严，可能让"只用 13F"的部署失败** → 用户已显式选 P3，接受此严格度；文档中说明。
- **[Trade-off] 重命名导出 `readFeedJson`→`readFeedJsonOrInit` 是 BREAKING** → 仅仓库内 2 处调用方需同步改，无外部消费方（脚本通过 `node scripts/*` 调用，不直接 import 该符号）。

## Migration Plan

1. 改 `lib/store/feed-json.js`：重命名 + 新增 strict；`upsert13FFiling` 内联改调 orInit。
2. 改 `lib/aggregate/pipeline-a.js:10` 改调 orInit。
3. 改 `scripts/prepare-digest.js` 加 pre-flight + strict 读取 + 硬失败。
4. 改测试（feed-json.test.js 改名；prepare-digest.test.js 更新空 envDir 用例）。
5. 更新 SKILL.md 错误处理段。
6. 跑 `npm test`（vitest）+ 手动 `rm -rf` 缓存后跑 prepare 验证非零退出。

回滚：git revert 单文件即可，改动相互正交。

## Open Questions

（无——P3 与 B 均已由用户拍板；D2 联动已明确排除。）
