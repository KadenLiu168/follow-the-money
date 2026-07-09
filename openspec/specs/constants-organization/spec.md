# constants-organization Specification

## Purpose
TBD - created by archiving change magic-number-constants. Update Purpose after archive.
## Requirements
### Requirement: shared domain constants reside in lib/constants.js
共享领域常量（跨文件使用、有明确领域含义）MUST 定义于 `lib/constants.js` 单一来源，禁止在多处重复书写相同字面量。

#### Scenario: rate limit constant has a single source of truth
- **WHEN** `scripts/aggregate.js` 与 `scripts/verify-edgar.js` 各自创建 HTTP 客户端节流器
- **THEN** 二者都从 `lib/constants.js` 导入同一个 `DEFAULT_RATE_LIMIT` 对象，而非各自书写 `new TokenBucket(10, 10)`

#### Scenario: thousands multiplier is named and centralized
- **WHEN** `lib/enrich/normalize-value-units.js` 将 13F 千美元值换算为美元
- **THEN** 它使用 `lib/constants.js` 导出的 `THOUSANDS_MULTIPLIER`（值为 1000），而非裸字面量 `* 1000`

### Requirement: non-obvious literal values are named with rationale comments
取值原因不显然的命名常量 MUST 附带注释，说明该值为何如此选取（约束来源、外部限制或工程权衡）。

#### Scenario: existing named constants carry rationale
- **WHEN** 读者查看 `DEFAULT_TIMEOUT_MS`、`DEFAULT_RETRIES`、`RETRY_DELAYS_MS`、`DETAIL_CAP`、`MIN_WAIT_MS`
- **THEN** 每个常量上方均有注释解释其取值依据（如 SEC EDGAR 速率限制、通知消息长度约束、计时器地板）

### Requirement: no duplicated magic numbers across files
跨文件重复出现的字面量 MUST 被提取为单一命名常量引用，MUST NOT 在多处硬编码相同值。

#### Scenario: duplicated token-bucket literals eliminated
- **WHEN** 代码库中存在两处及以上相同的限速字面量（如 `10, 10`）
- **THEN** 仅保留 `lib/constants.js` 中的 `DEFAULT_RATE_LIMIT` 定义，所有调用点引用该常量

