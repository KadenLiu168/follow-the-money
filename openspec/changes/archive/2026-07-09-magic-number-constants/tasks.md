## 1. 新建共享常量模块

- [x] 1.1 新建 `lib/constants.js`，导出：
  - `export const THOUSANDS_MULTIPLIER = 1000;`（注释：SEC 13F `<value>` 以千美元计，乘 1000 存美元）
  - `export const DEFAULT_RATE_LIMIT = Object.freeze({ rate: 10, capacity: 10 });`（注释：SEC EDGAR 公有速率限制的保守客户端节流）
  - 文件头注释声明"仅存放跨文件共享的领域常量"
- [x] 1.2 确认该模块为纯 ESM、`node --check` 通过、无新增依赖

## 2. 提取 + 去重共享常量

- [x] 2.1 `lib/enrich/normalize-value-units.js`：在文件顶部 `import { THOUSANDS_MULTIPLIER } from '../constants.js';`，将第 50 行 `valueUsd: (Number(h.valueUsd) || 0) * 1000` 改为使用 `THOUSANDS_MULTIPLIER`
- [x] 2.2 `scripts/aggregate.js`：在顶部 `import { DEFAULT_RATE_LIMIT } from '../lib/constants.js';`，将第 17 行 `new TokenBucket(10, 10)` 改为 `new TokenBucket(DEFAULT_RATE_LIMIT.rate, DEFAULT_RATE_LIMIT.capacity)`
- [x] 2.3 `scripts/verify-edgar.js`：在顶部 `import { DEFAULT_RATE_LIMIT } from '../lib/constants.js';`，将第 28 行 `new TokenBucket(10, 10)` 改为 `new TokenBucket(DEFAULT_RATE_LIMIT.rate, DEFAULT_RATE_LIMIT.capacity)`

## 3. 就近 co-locate + 补注释

- [x] 3.1 `lib/token-bucket.js`：在 `constructor` 前加 `const MIN_WAIT_MS = 10;`，将第 27 行 `Math.max(10, …)` 改为 `Math.max(MIN_WAIT_MS, …)`，补注释（计时器地板，避免亚毫秒忙等）
- [x] 3.2 `scripts/check-alerts.js`：为 `const DETAIL_CAP = 8;` 补注释（摘要消息长度与最相关 13D/G 曝光量的平衡）
- [x] 3.3 `lib/fetch/fetch-feed.js`：为 `DEFAULT_TIMEOUT_MS = 15000`、`DEFAULT_RETRIES = 2`、`RETRY_DELAYS_MS = [500, 1500]` 各补注释（SEC EDGAR raw 抓取超时、重试与退避取值依据）

## 4. 校验与门禁（Loop Engineering 用）

- [x] 4.1 运行 `npm test`，确认 163 测试全绿（等价替换证明零行为变更）
- [x] 4.2 运行 `npm run lint`，确认 0 error（注释/重命名不引入 lint 问题）
- [x] 4.3 运行 `npm run format:check`，确认格式一致
- [x] 4.4 运行 `openspec validate magic-number-constants --strict`，确认 spec 合法
