## Why

审计报告 `docs/code-quality-review-2026-07-08.md` 的 L9 指出仓库存在"魔法数字散落"问题。复盘后发现：报告点名的 `ONE_BILLION`（13F 单位推断阈值）已在 H2 的 `value-units-normalization` 变更中被彻底消除；其余点名项（`DETAIL_CAP`、`DEFAULT_TIMEOUT_MS` 等）**早已是命名常量**，缺的只是"为什么取这个值"的注释。真正裸露、且重复出现的字面量只剩下少数几处（默认限速 `TokenBucket(10,10)` 跨两个脚本重复、`normalize` 的 `×1000`、token-bucket 的最小等待地板 `10`）。

因此 L9 的真实范围不是"新建常量体系"，而是**一次克制的收口**：把"取值原因不显然"或"跨文件重复"的字面量提为命名常量并补注释，其余约定俗成的单位换算（秒→毫秒、天→毫秒）保持原样以免制造噪音。

## What Changes

- **新建** `lib/constants.js`：共享领域常量单一来源（single source of truth）
  - `THOUSANDS_MULTIPLIER = 1000` —— SEC 13F `<value>` 以千美元计，需乘 1000 存储为美元
  - `DEFAULT_RATE_LIMIT`（`{ rate: 10, capacity: 10 }`，`Object.freeze`）—— SEC EDGAR 公有速率限制的保守客户端节流
- **提取 + 去重**：`scripts/aggregate.js` 与 `scripts/verify-edgar.js` 中重复的 `new TokenBucket(10, 10)` 改为从 `lib/constants.js` 引入 `DEFAULT_RATE_LIMIT`
- **提取**：`lib/enrich/normalize-value-units.js:50` 的 `* 1000` 改为 `THOUSANDS_MULTIPLIER`
- **就近 co-locate + 补注释**（不变更行为，仅命名/说明）：
  - `lib/token-bucket.js:27` 的 `Math.max(10, …)` 地板 → 同文件 `const MIN_WAIT_MS = 10`
  - `scripts/check-alerts.js` 的 `DETAIL_CAP = 8` → 补注释（摘要消息长度与最相关 13D/G 曝光量的平衡）
  - `lib/fetch/fetch-feed.js` 的 `DEFAULT_TIMEOUT_MS=15000` / `DEFAULT_RETRIES=2` / `RETRY_DELAYS_MS=[500,1500]` → 补注释（为什么是这些值）
- **明确不做（保持原样）**：`lib/http-client.js` 的 `* 1000`、`2 ** attempt * 500`、`lib/feed/filter-by-lookback.js` 与 `state-json.js` 的 `24*60*60*1000` 等约定俗成单位换算——提取它们只会增加噪音，不带来可维护性收益。

## Capabilities

### New Capabilities
- `constants-organization`: 共享领域常量集中于 `lib/constants.js` 单一来源；非显然字面量须命名并注释取值依据；禁止跨文件重复魔法数字。

### Modified Capabilities
<!-- 无 spec 级行为变更；normalize / token-bucket / fetch 的行为保持不变，仅内部常量命名与注释调整，不改动 `value-units-normalization` 等既有 spec 的 requirement。 -->

## Impact

- **代码**：`lib/constants.js`（新）、`lib/enrich/normalize-value-units.js`、`lib/token-bucket.js`、`lib/fetch/fetch-feed.js`、`scripts/check-alerts.js`、`scripts/aggregate.js`、`scripts/verify-edgar.js`
- **API**：无（纯内部常量重命名，导出签名不变）
- **依赖**：无新增
- **行为**：零运行时行为变更（等价替换）；测试套件须全绿以证明等价
- **风险**：极低，均为 `const` 提取 / 注释补充，不涉及控制流
