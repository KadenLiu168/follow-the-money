## Why

原始代码评审（`docs/code-quality-review-2026-07-08.md`）在 🟡 中优先级里标记了三处**机械性重复代码**（M1/M2/M3）。它们都属于维护债务，无运行时行为差异，修复后可消除"改一处漏五处"的漂移风险、缩小后续编辑面。本 change 将三者合并为一个低风险纯重构，在 `main` 分支一次性消除重复，不引入任何新功能。

> **范围修正（与 review 文档的偏差）**：P1-2（`ndjson-append-write`）已将 `feed-ndjson.js` / `state-ndjson.js` 改为 `appendFileSync`（O(1)），它们**不再**携带原 review 描述的 tmp+rename 模板。因此 M1 的实际落地面调整为仍使用 tmp+rename 的 3 个 writer（`feed-json.js` / `state-json.js` / `manifest.js`），并对那 2 个 NDJSON 文件做清理（移除 P1-2 后遗留的未使用 `writeFileSync`/`renameSync` import）。这是"Proposal 与实现冲突时做最小必要调整"的体现。

## What Changes

- **(M1)** 新增 `lib/store/atomic-write.js`，导出 `atomicWriteJSON(path, obj)` 与 `atomicWriteText(path, str)`：沿用现有 `tmp = ${path}.${pid}.${Date.now()}.tmp` + `writeFileSync` + `renameSync` 语义，保证原子写、无半写损坏。
- **(M1)** `feed-json.js` / `state-json.js` / `manifest.js` 改为调用新 helper，删除各自内联副本与重复的 `node:fs` import 行。
- **(M1)** `feed-ndjson.js` / `state-ndjson.js`：移除 P1-2 后遗留、现已未使用的 `writeFileSync` / `renameSync` import（其写路径已用 `appendFileSync`）。
- **(M2)** `scripts/verify-edgar.js`：删除内联的 `bucket` 单例 + `take()` + `fetchWithRetry`，改为 `import { TokenBucket } from '../lib/token-bucket.js'` 与 `import { createHttpClient } from '../lib/http-client.js'`，所有请求经共享 http client（限流行为保持一致：`new TokenBucket(10, 10)`）。
- **(M3)** 新增 `lib/edgar/archive-url.js`，导出 `edgarArchiveUrl(cik, accession)` 与 `edgarDocUrl(cik, accession, fileName)`。`fetch-thirteen-f-xml.js` 与 `pipeline-b.js` 改用它们，删除内联的 `cikNoPad` / `accNoDash` / `baseUrl` 构造。

无 **BREAKING** 变更：所有导出签名、输出内容、限流/重试行为保持不变；未新增功能。

## Capabilities

### New Capabilities
- `store-utils`：store 模块共享的原子写 helper（`atomicWriteJSON` / `atomicWriteText`），由 JSON store writer 统一调用。
- `edgar-archive-url`：规范化的 EDGAR 归档 URL 构造 helper（`edgarArchiveUrl` / `edgarDocUrl`），由 13F XML 抓取与 pipeline-b 统一调用。

### Modified Capabilities
- （无 —— 纯重构，不改动任何 requirement 级行为）

## Impact

- **Code**：
  - 新增：`lib/store/atomic-write.js`、`lib/edgar/archive-url.js`
  - 修改：`lib/store/feed-json.js`、`lib/store/state-json.js`、`lib/store/manifest.js`、`lib/store/feed-ndjson.js`、`lib/store/state-ndjson.js`、`scripts/verify-edgar.js`、`lib/edgar/fetch-thirteen-f-xml.js`、`lib/aggregate/pipeline-b.js`
- **Tests**：现有 store / edgar / pipeline / verify 测试必须仍全绿；新增 `atomicWriteJSON`/`atomicWriteText` 与 `edgarArchiveUrl`/`edgarDocUrl` 的针对性单测（含"内容等价 + 原子性 + 异常抛出"）。
- **Dependencies**：无新增 / 移除。
- **Risk**：低 —— 行为保持；由现有测试 + 新增单测覆盖。不触碰 M4/M5/M6 或其它 review 项。
