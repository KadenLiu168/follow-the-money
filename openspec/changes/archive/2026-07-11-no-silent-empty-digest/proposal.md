## Why

`prepare-digest.js` 在 feed 源缺失/损坏时仍输出一个"看起来正常、实则空"的 digest 并 `exit 0`，直接违反项目 SKILL.md 自己写下的铁律："Partial output is worse than no output"。根因是 `lib/store/feed-json.js` 的 `readFeedJson` 被两头用：聚合/写入路径把它当 **bootstrap**（文件不存在→返回空 `DEFAULTS()`，正确），但 digest 读取路径也用它（文件不存在/解析失败→同样静默返回空），于是缺失的源被伪装成"无数据"。

用户已拍板两点：(1) 采用**方案 B**——把 `readFeedJson` 拆成 bootstrap 与 read 两种明确语义；(2) 判定粒度选 **P3**——任一源缺失/损坏即硬失败（最贴合铁律字面），且本次**只修 D3，不与 D2（自包含 JSON blob）联动**。

## What Changes

- **拆分 `readFeedJson` 语义**：
  - 新增 `readFeedJsonStrict(path)`：**缺失或解析失败 → 抛错**，绝不静默回退空对象。供所有读取路径（当前仅 `prepare-digest.js`）使用。
  - 原 `readFeedJson` 重命名为 `readFeedJsonOrInit(path)`：保留 `DEFAULTS()` bootstrap 行为，仅用于聚合/写入路径（`pipeline-a.js`、`upsert13FFiling`）。
- **`prepare-digest.js` 硬失败**：读取前先做 pre-flight 存在性检查；`feed-13f.json` 缺失、**或** `feed-13dg/` 目录缺失、**或** `feed-13f.json` 损坏，均 `console.error` 明确信息并 `process.exit(1)`，且**不向 stdout 写任何 digest**。
- **更新受影响的测试**：`tests/store/feed-json.test.js` 中 `readFeedJson` 引用改名；`tests/scripts/prepare-digest.test.js` 的"空 envDir"回归测试改为断言非零退出（保留"env var 不被静默忽略"的回归意图，只是从空 digest 改为硬失败）。
- **同步 SKILL.md 错误处理段**：明确 prepare 现会在源缺失/损坏时非零退出，agent 必须上报 stderr 并停止，不再产出空 digest。

**BREAKING**：`lib/store/feed-json.js` 导出名 `readFeedJson` 重命名为 `readFeedJsonOrInit`；任何外部读取调用方必须改用 `readFeedJsonStrict`。仓库内调用方同步更新。

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `feed-storage`：`readFeedJson` 拆分为 `readFeedJsonStrict`（缺失/损坏抛错）与 `readFeedJsonOrInit`（bootstrap 返回 `DEFAULTS()`）。明确"静默空回退"仅允许在写入/聚合引导路径，读取路径禁止。
- `digest-lookback`：`prepare-digest.js` 新增需求——当任一源 feed（`feed-13f.json` 或 `feed-13dg/`）缺失或 `feed-13f.json` 损坏时，必须非零退出且不输出 digest，以符合"Partial output is worse than no output"。

## Impact

- 代码：`lib/store/feed-json.js`（拆分）、`scripts/prepare-digest.js`（pre-flight + 硬失败）、`lib/aggregate/pipeline-a.js:10`（改调 `readFeedJsonOrInit`）。
- 测试：`tests/store/feed-json.test.js`、`tests/scripts/prepare-digest.test.js`。
- 文档：`SKILL.md` 错误处理段。
- 行为：本地/CI 在 feed 未拉取或目录错位时，prepare 从"静默空 digest"变为"明确报错退出"。SKILL 的 fetch→fall-through-to-local 模型不变；仅当本地同样无源时才失败（符合铁律）。
