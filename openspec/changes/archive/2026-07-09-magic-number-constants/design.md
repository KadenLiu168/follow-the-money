## Context

本变更处理审计报告 L9（魔法数字常量化）的收口。现状复盘：

- 报告头号例子 `ONE_BILLION`（13F `$1B` 单位推断阈值）**已不存在**——H2 的 `value-units-normalization` 将其换成了显式 `valueUnit` 标记 + `valueUnitAdjusted` 守卫。
- 报告其余点名项（`DETAIL_CAP=8`、`DEFAULT_TIMEOUT_MS=15000`、`DEFAULT_RETRIES=2`、`RETRY_DELAYS_MS=[500,1500]`）**已是命名常量**，仅缺"取值依据"注释。
- 真正裸露或重复的字面量仅 3 处：
  - `new TokenBucket(10, 10)` 在 `scripts/aggregate.js:17` 与 `scripts/verify-edgar.js:28` **重复出现**（DRY 违规 + 无说明）；
  - `lib/enrich/normalize-value-units.js:50` 的 `* 1000`（领域含义明确，但未命名）；
  - `lib/token-bucket.js:27` 的 `Math.max(10, …)` 等待地板（无说明）。

仓库已有 `lib/config/load-default-sources.js`（L2/L7 建立的"配置优先"模式），但本变更处理的量是**编译期常量/行为节流默认值**，性质上不同于可热更新的数据源配置，故不进 `lib/config/`，而新建轻量 `lib/constants.js`。

## Goals / Non-Goals

**Goals:**
- 建立共享领域常量单一来源 `lib/constants.js`，消除跨文件重复字面量。
- 为"取值原因不显然"的既有命名常量补注释，满足审计核心诉求。
- 零运行时行为变更（等价 `const` 提取 / 注释补充）。

**Non-Goals:**
- 不新建通用常量体系或 lint 规则强制（L4 已建 lint 工具链，但常量命名非本次范围）。
- 不提取约定俗成的单位换算（`×1000` 秒→毫秒、`24*60*60*1000` 天→毫秒、`2**attempt*500` 退避）——提取它们只制造噪音。
- 不动 `lib/config/` 配置加载机制。
- 不修改任何控制流、导出签名或测试行为。

## Decisions

**D1 — 常量组织采用混合策略（approach C）**
- 仅"共享领域常量"（跨文件使用、有明确领域含义）进 `lib/constants.js`：`THOUSANDS_MULTIPLIER`、`DEFAULT_RATE_LIMIT`。
- 其余就近 co-locate：`MIN_WAIT_MS` 留在 `token-bucket.js` 顶部；`DETAIL_CAP` / `DEFAULT_TIMEOUT_MS` / `DEFAULT_RETRIES` / `RETRY_DELAYS_MS` 的注释补在原文件。
- 备选：全中央（A，审计报告字面建议）/ 全就近（B）。A 会制造跨模块依赖与"杂物抽屉"；B 无法消除 `TokenBucket(10,10)` 的重复。C 兼顾"单一来源"与"贴合现有代码风格"，故选 C。

**D2 — `DEFAULT_RATE_LIMIT` 用 `Object.freeze` 且为代码常量，不进 `lib/config/`**
- 它是通用客户端节流默认值，与具体数据源无关，编译期固定即可；引入 `lib/config` 的 JSON 读取反而增加不必要的 I/O 与异步复杂度。
- 形式：`export const DEFAULT_RATE_LIMIT = Object.freeze({ rate: 10, capacity: 10 });` —— `freeze` 防止调用方误改。

**D3 — `THOUSANDS_MULTIPLIER` 命名而非 `ONE_BILLION` 复活**
- 原报告的 `ONE_BILLION` 是"推断阈值"语义（已废弃）；此处是"千→美元乘子"语义，命名 `THOUSANDS_MULTIPLIER = 1000` 更准确，避免与历史混淆。

**D4 — 等价替换，靠测试套件证明零行为变更**
- 所有替换是字面量↔同名常量的 1:1 替换；`npm test` 全绿即证明等价。不新增功能测试（属注释/重命名，无需新断言）。

## Risks / Trade-offs

- [Risk] `lib/constants.js` 未来被滥用成"杂物抽屉" → Mitigation：proposal 与 spec 明确限定"仅共享领域常量"，并在文件头注释声明用途边界。
- [Risk] 注释表述主观（如"为什么是 8 条"）→ Mitigation：注释聚焦可验证的工程事实（消息长度约束、SEC 速率限制保守值），避免臆测业务理由。
- [Trade-off] 不提取 `http-client.js` 的 `×1000` 等换算常量，可能与"中央常量"读者预期不一致 → 已在 Non-Goals 明确，属有意克制。

## Migration Plan

- 纯增量，无数据迁移、无配置变更、无部署步骤。
- 回滚：单 commit 即可 `git revert`；`lib/constants.js` 为纯新增文件，删除即还原。

## Open Questions

- 无。范围与策略已与用户确认（approach C）。
